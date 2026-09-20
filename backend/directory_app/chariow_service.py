import hashlib
import hmac
import logging
import re
import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Payment, PhoneAccount, SellerSubscription
from .subscription_notifications import notify_seller_subscription_confirmed

logger = logging.getLogger(__name__)


class ChariowError(Exception):
    """Exception levée en cas d'erreur avec l'API ou le service Chariow."""
    pass


# Alias pour rétro-compatibilité
PaystackError = ChariowError


def _headers() -> dict[str, str]:
    api_key = getattr(settings, "CHARIOW_API_KEY", "")
    if not api_key:
        raise ChariowError("CHARIOW_API_KEY n’est pas configurée sur le serveur.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _request(method: str, path: str, **kwargs) -> dict:
    base_url = getattr(settings, "CHARIOW_BASE_URL", "https://api.chariow.com/v1").rstrip("/")
    url = f"{base_url}/{path.lstrip('/')}"
    try:
        response = requests.request(
            method,
            url,
            headers=_headers(),
            timeout=20,
            **kwargs,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            response.raise_for_status()
            raise ChariowError("Réponse Chariow non JSON.") from exc

        if not response.ok:
            message = (
                payload.get("message")
                or payload.get("error")
                or payload.get("errors")
                or f"Erreur HTTP {response.status_code} depuis Chariow."
            )
            raise ChariowError(str(message))
    except requests.RequestException as exc:
        logger.exception("Erreur réseau Chariow")
        raise ChariowError("Chariow est momentanément indisponible.") from exc

    if not isinstance(payload, dict):
        raise ChariowError("Réponse Chariow invalide.")
    return payload


def initialize_subscription_payment(user, custom_email: str | None = None) -> dict:
    reference = f"AGRILINK-{uuid.uuid4().hex[:24].upper()}"
    amount = getattr(settings, "CHARIOW_SUBSCRIPTION_AMOUNT", 5000)
    currency = getattr(settings, "CHARIOW_CURRENCY", "XOF")
    account = getattr(user, "phone_account", None)
    if not account:
        raise ChariowError("Compte d’authentification introuvable.")
    phone = account.phone_e164 or ""
    buyer_profile = getattr(user, "buyer_profile", None)

    email = (custom_email or user.email or account.email or (buyer_profile.email if buyer_profile else "")).strip()

    if email:
        try:
            validate_email(email)
        except ValidationError:
            email = ""

    if not email:
        clean_phone = re.sub(r"\D", "", phone) or str(user.pk)
        email = f"user_{clean_phone}@agrilink.ci"

    payment = Payment.objects.create(
        user=user,
        reference=reference,
        amount=amount,
        currency=currency,
    )

    api_key = getattr(settings, "CHARIOW_API_KEY", "")
    if not api_key and settings.DEBUG:
        mock_url = f"http://127.0.0.1:8000/api/payments/subscription/status/?ref={reference}"
        payment.provider_response = {
            "checkout_url": mock_url,
            "step": "payment",
            "access_code": "DEV_MODE_ACCESS_CODE",
        }
        payment.save(update_fields=["provider_response", "updated_at"])
        return {
            "reference": payment.reference,
            "authorization_url": mock_url,
            "checkout_url": mock_url,
            "amount": payment.amount,
            "currency": payment.currency,
            "dev_mode": True,
        }

    product_id = getattr(settings, "CHARIOW_SELLER_PRODUCT_ID", "")
    if not product_id:
        raise ChariowError("CHARIOW_SELLER_PRODUCT_ID n'est pas configuré sur le serveur.")

    data = {
        "product_id": product_id,
        "email": email,
        "customer_email": email,
        "first_name": user.first_name or "Vendeur",
        "last_name": user.last_name or "AgriLink",
        "metadata": {
            "reference": reference,
            "purpose": "seller_subscription",
            "user_id": str(user.id),
            "phone": phone,
        },
    }
    if phone:
        data["phone"] = phone
    callback_url = getattr(settings, "CHARIOW_CALLBACK_URL", "")
    if callback_url:
        data["callback_url"] = callback_url

    try:
        payload = _request("POST", "/checkout", json=data)
    except Exception:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "updated_at"])
        raise

    response_data = payload.get("data", payload)
    # Dans Chariow, l'URL de paiement est dans data.payment.checkout_url ou data.checkout_url
    checkout_url = (
        response_data.get("payment", {}).get("checkout_url")
        or response_data.get("checkout_url")
        or response_data.get("authorization_url")
        or ""
    )
    transaction_id = str(response_data.get("id") or response_data.get("sale_id") or "")

    payment.provider_response = response_data
    payment.transaction_id = transaction_id
    payment.paystack_transaction_id = transaction_id
    payment.save(update_fields=["provider_response", "transaction_id", "paystack_transaction_id", "updated_at"])

    return {
        "reference": payment.reference,
        "authorization_url": checkout_url,
        "checkout_url": checkout_url,
        "transaction_id": transaction_id,
        "amount": payment.amount,
        "currency": payment.currency,
    }


def _extract_sale_from_response(payload: dict, reference: str = "") -> dict:
    """Extrait l'objet de vente (dict) correspondant à la référence dans les données Chariow."""
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data", payload)
    if isinstance(data, list):
        if reference:
            for item in data:
                if isinstance(item, dict):
                    meta_ref = item.get("metadata", {}).get("reference")
                    sale_ref = item.get("reference")
                    if meta_ref == reference or sale_ref == reference:
                        return item
        for item in data:
            if isinstance(item, dict):
                return item
        return {}
    elif isinstance(data, dict):
        return data
    return {}


@transaction.atomic
def verify_and_activate_payment(user, reference: str) -> dict:
    try:
        payment = Payment.objects.select_for_update().get(reference=reference, user=user)
    except Payment.DoesNotExist as exc:
        raise ChariowError("Référence de paiement inconnue pour ce compte.") from exc

    if payment.status == Payment.Status.SUCCESS:
        subscription = SellerSubscription.objects.get(user=user)
        return {
            "status": "active",
            "role": getattr(user.phone_account, "role", ""),
            "starts_at": subscription.starts_at,
            "ends_at": subscription.ends_at,
            "reference": payment.reference,
            "channel": payment.channel,
            "idempotent": True,
        }

    api_key = getattr(settings, "CHARIOW_API_KEY", "")
    if not api_key and settings.DEBUG:
        sale_data = {
            "status": "completed",
            "reference": payment.reference,
            "amount": payment.amount,
            "currency": payment.currency,
            "channel": "dev_mode",
            "id": "DEV_MODE_CHARIOW_SALE",
        }
    else:
        # Recherche par référence via l'endpoint des ventes Chariow
        if payment.transaction_id:
            try:
                sale_res = _request("GET", f"/sales/{payment.transaction_id}")
                sale_data = _extract_sale_from_response(sale_res, reference)
            except ChariowError:
                sale_res = _request("GET", f"/sales?search={reference}")
                sale_data = _extract_sale_from_response(sale_res, reference)
        else:
            sale_res = _request("GET", f"/sales?search={reference}")
            sale_data = _extract_sale_from_response(sale_res, reference)

    sale_status = str(sale_data.get("status", "")).lower()
    sale_id = str(sale_data.get("id", ""))
    channel = str(sale_data.get("payment_method", sale_data.get("channel", "chariow")))

    payment.provider_response = sale_data
    payment.channel = channel
    payment.transaction_id = sale_id
    payment.paystack_transaction_id = sale_id

    # Les statuts de succès sur Chariow sont 'completed' ou 'settled'
    if sale_status not in ["completed", "settled", "success"]:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "channel", "transaction_id", "paystack_transaction_id", "provider_response", "updated_at"])
        raise ChariowError(f"Le paiement Chariow n’est pas complété (statut: {sale_status or 'inconnu'}).")

    now = timezone.now()
    payment.status = Payment.Status.SUCCESS
    payment.paid_at = now
    payment.save(update_fields=["status", "paid_at", "channel", "transaction_id", "paystack_transaction_id", "provider_response", "updated_at"])

    try:
        subscription = SellerSubscription.objects.select_for_update().get(user=user)
        starts_at = max(now, subscription.ends_at)
    except SellerSubscription.DoesNotExist:
        subscription = None
        starts_at = now

    sub_days = getattr(settings, "CHARIOW_SUBSCRIPTION_DAYS", 30)
    ends_at = starts_at + timedelta(days=sub_days)
    subscription, _ = SellerSubscription.objects.update_or_create(
        user=user,
        defaults={
            "payment": payment,
            "status": SellerSubscription.Status.ACTIVE,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
    )
    notify_seller_subscription_confirmed(user, subscription, payment.reference)
    account = getattr(user, "phone_account", None)
    if not account or not (account.phone_verified or account.email_verified):
        raise ChariowError("Un téléphone ou une adresse e-mail vendeur vérifié est requis.")
    account.role = PhoneAccount.Role.SELLER
    account.save(update_fields=["role", "updated_at"])
    return {
        "status": "active",
        "role": account.role,
        "starts_at": subscription.starts_at,
        "ends_at": subscription.ends_at,
        "reference": payment.reference,
        "channel": payment.channel,
    }


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    """
    Vérifie la signature HMAC-SHA256 envoyée par les Pulses de Chariow (header x-chariow-signature).
    Le header peut être sous forme 'sha256=<hex>' ou directement '<hex>'.
    """
    secret = getattr(settings, "CHARIOW_WEBHOOK_SECRET", "") or getattr(settings, "CHARIOW_API_KEY", "")
    if not secret or not signature:
        return False

    clean_signature = signature.strip()
    if clean_signature.startswith("sha256="):
        clean_signature = clean_signature[len("sha256="):]

    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, clean_signature)

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


class PaystackError(Exception):
    pass


def _headers() -> dict[str, str]:
    if not settings.PAYSTACK_SECRET_KEY:
        raise PaystackError("PAYSTACK_SECRET_KEY n’est pas configurée sur le serveur.")
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def _amount_for_paystack(amount: int) -> int:
    multiplier = int(getattr(settings, "PAYSTACK_AMOUNT_MULTIPLIER", 1))
    return amount * multiplier


def _request(method: str, path: str, **kwargs) -> dict:
    try:
        response = requests.request(
            method,
            f"{settings.PAYSTACK_BASE_URL.rstrip('/')}/{path.lstrip('/')}",
            headers=_headers(),
            timeout=20,
            **kwargs,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            response.raise_for_status()
            raise PaystackError("Réponse Paystack invalide.") from exc
        response_ok = getattr(response, "ok", True)
        if not response_ok or not payload.get("status"):
            message = payload.get("message", "Paystack a refusé la requête.")
            raise PaystackError(str(message))
    except requests.RequestException as exc:
        logger.exception("Erreur réseau Paystack")
        raise PaystackError("Paystack est momentanément indisponible.") from exc
    if not isinstance(payload, dict):
        raise PaystackError("Réponse Paystack invalide.")
    return payload


def initialize_subscription_payment(user, custom_email: str | None = None) -> dict:
    reference = f"AGRILINK-{uuid.uuid4().hex[:24].upper()}"
    amount = settings.PAYSTACK_SUBSCRIPTION_AMOUNT
    account = getattr(user, "phone_account", None)
    if not account:
        raise PaystackError("Compte d’authentification introuvable.")
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

    data = {
        "email": email,
        "amount": _amount_for_paystack(amount),
        "currency": settings.PAYSTACK_CURRENCY,
        "reference": reference,
        "channels": ["card", "mobile_money"],
        "metadata": {
            "purpose": "seller_subscription",
            "user_id": user.id,
            "phone": phone,
        },
    }
    if settings.PAYSTACK_CALLBACK_URL:
        data["callback_url"] = settings.PAYSTACK_CALLBACK_URL

    payment = Payment.objects.create(
        user=user,
        reference=reference,
        amount=amount,
        currency=settings.PAYSTACK_CURRENCY,
    )

    if not settings.PAYSTACK_SECRET_KEY and settings.DEBUG:
        payment.provider_response = {
            "authorization_url": f"http://127.0.0.1:8000/api/payments/subscription/status/",
            "access_code": "DEV_MODE_ACCESS_CODE"
        }
        payment.save(update_fields=["provider_response", "updated_at"])
        return {
            "reference": payment.reference,
            "authorization_url": payment.provider_response["authorization_url"],
            "access_code": "DEV_MODE_ACCESS_CODE",
            "amount": payment.amount,
            "currency": payment.currency,
            "dev_mode": True,
        }

    try:
        payload = _request("POST", "/transaction/initialize", json=data)
    except Exception:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "updated_at"])
        raise

    response_data = payload.get("data", {})
    payment.provider_response = {"authorization_url": response_data.get("authorization_url"), "access_code": response_data.get("access_code")}
    payment.save(update_fields=["provider_response", "updated_at"])
    return {
        "reference": payment.reference,
        "authorization_url": response_data.get("authorization_url"),
        "access_code": response_data.get("access_code"),
        "amount": payment.amount,
        "currency": payment.currency,
    }


def _valid_success_data(payment: Payment, data: dict) -> bool:
    return (
        data.get("status") == "success"
        and data.get("reference") == payment.reference
        and int(data.get("amount", -1)) == _amount_for_paystack(payment.amount)
        and str(data.get("currency", "")).upper() == payment.currency.upper()
    )


@transaction.atomic
def verify_and_activate_payment(user, reference: str) -> dict:
    try:
        payment = Payment.objects.select_for_update().get(reference=reference, user=user)
    except Payment.DoesNotExist as exc:
        raise PaystackError("Référence de paiement inconnue pour ce compte.") from exc

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

    if not settings.PAYSTACK_SECRET_KEY and settings.DEBUG:
        data = {
            "status": "success",
            "reference": payment.reference,
            "amount": _amount_for_paystack(payment.amount),
            "currency": payment.currency,
            "channel": "dev_mode",
            "id": "DEV_MODE_TX",
        }
        payload = {"status": True, "data": data}
    else:
        payload = _request("GET", f"/transaction/verify/{reference}")
        data = payload.get("data", {})

    payment.provider_response = payload
    payment.channel = data.get("channel", "")
    payment.paystack_transaction_id = str(data.get("id", ""))
    if not _valid_success_data(payment, data):
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "channel", "paystack_transaction_id", "provider_response", "updated_at"])
        raise PaystackError("Le paiement Paystack n’est pas valide ou n’est pas réussi.")

    now = timezone.now()
    payment.status = Payment.Status.SUCCESS
    payment.paid_at = now
    payment.save(update_fields=["status", "paid_at", "channel", "paystack_transaction_id", "provider_response", "updated_at"])
    try:
        subscription = SellerSubscription.objects.select_for_update().get(user=user)
        starts_at = max(now, subscription.ends_at)
    except SellerSubscription.DoesNotExist:
        subscription = None
        starts_at = now
    ends_at = starts_at + timedelta(days=settings.PAYSTACK_SUBSCRIPTION_DAYS)
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
        raise PaystackError("Un téléphone ou une adresse e-mail vendeur vérifié est requis.")
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
    if not settings.PAYSTACK_SECRET_KEY or not signature:
        return False
    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
        raw_body,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

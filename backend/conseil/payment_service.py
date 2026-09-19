import uuid
from datetime import timedelta

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from directory_app.models import Payment
from .models import ConseilSubscription


class ConseilPaymentError(Exception):
    pass


def _request(method, path, **kwargs):
    if not settings.PAYSTACK_SECRET_KEY:
        raise ConseilPaymentError("PAYSTACK_SECRET_KEY n’est pas configurée.")
    try:
        response = requests.request(method, f"{settings.PAYSTACK_BASE_URL.rstrip('/')}/{path.lstrip('/')}", headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}, timeout=20, **kwargs)
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ConseilPaymentError("Paystack est momentanément indisponible.") from exc
    if not response.ok or not payload.get("status"):
        raise ConseilPaymentError(str(payload.get("message", "Paystack a refusé la requête.")))
    return payload


def initialize_conseil_payment(user, annual=False):
    email = user.email or getattr(getattr(user, "phone_account", None), "email", "")
    try:
        validate_email(email)
    except ValidationError as exc:
        raise ConseilPaymentError("Une adresse e-mail valide est requise pour payer Conseil Pro.") from exc
    amount = 29000 if annual else 3000
    reference = f"CONSEIL-{uuid.uuid4().hex[:24].upper()}"
    payment = Payment.objects.create(user=user, reference=reference, amount=amount, currency=settings.PAYSTACK_CURRENCY)
    data = {"email": email, "amount": amount * int(getattr(settings, "PAYSTACK_AMOUNT_MULTIPLIER", 1)), "currency": settings.PAYSTACK_CURRENCY, "reference": reference, "channels": ["card", "mobile_money"], "metadata": {"purpose": "conseil_subscription", "user_id": user.id, "annual": annual}}
    if settings.PAYSTACK_CALLBACK_URL:
        data["callback_url"] = settings.PAYSTACK_CALLBACK_URL
    try:
        payload = _request("POST", "/transaction/initialize", json=data)
    except Exception:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "updated_at"])
        raise
    response_data = payload.get("data", {})
    payment.provider_response = {"purpose": "conseil_subscription", "annual": annual, "authorization_url": response_data.get("authorization_url"), "access_code": response_data.get("access_code")}
    payment.save(update_fields=["provider_response", "updated_at"])
    return {"reference": reference, "authorization_url": response_data.get("authorization_url"), "access_code": response_data.get("access_code"), "amount": amount, "currency": payment.currency}


@transaction.atomic
def verify_conseil_payment(user, reference):
    try:
        payment = Payment.objects.select_for_update().get(user=user, reference=reference)
    except Payment.DoesNotExist as exc:
        raise ConseilPaymentError("Référence de paiement inconnue.") from exc
    if payment.status == Payment.Status.SUCCESS:
        subscription = ConseilSubscription.objects.get(user=user)
        return {"status": "active", "starts_at": subscription.starts_at, "ends_at": subscription.ends_at, "reference": reference, "channel": payment.channel, "idempotent": True}

    payload = _request("GET", f"/transaction/verify/{reference}")
    data = payload.get("data", {})
    expected = payment.amount * int(getattr(settings, "PAYSTACK_AMOUNT_MULTIPLIER", 1))
    if data.get("status") != "success" or data.get("reference") != reference or int(data.get("amount", -1)) != expected:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "updated_at"])
        raise ConseilPaymentError("Le paiement Conseil Pro n’est pas valide.")
    now = timezone.now()
    payment.status = Payment.Status.SUCCESS
    payment.paid_at = now
    payment.channel = data.get("channel", "")
    payment.paystack_transaction_id = str(data.get("id", ""))
    payment.provider_response = payload
    payment.save(update_fields=["status", "paid_at", "channel", "paystack_transaction_id", "provider_response", "updated_at"])
    days = 365 if payment.amount == 29000 else 30
    old = getattr(user, "conseil_subscription", None)
    starts = max(now, old.ends_at) if old and old.is_active else now
    subscription, _ = ConseilSubscription.objects.update_or_create(user=user, defaults={"payment": payment, "status": ConseilSubscription.Status.ACTIVE, "starts_at": starts, "ends_at": starts + timedelta(days=days)})
    return {"status": "active", "starts_at": subscription.starts_at, "ends_at": subscription.ends_at, "reference": reference, "channel": payment.channel}

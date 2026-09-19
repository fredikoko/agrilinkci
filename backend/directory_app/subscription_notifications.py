import logging
from django.conf import settings
from django.core.mail import send_mail
try:
    from twilio.rest import Client
except ImportError:
    Client = None

from .models import AppNotification

logger = logging.getLogger(__name__)


def _contacts(user):
    account = getattr(user, "phone_account", None)
    profile = getattr(user, "buyer_profile", None)
    email = user.email or (account.email if account else "") or (profile.email if profile else "")
    phone = (account.phone_e164 if account else "") or (profile.phone if profile else "")
    return email, phone


def _send_sms(phone: str, body: str) -> bool:
    if not phone or not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        return False
    messaging_service = getattr(settings, "TWILIO_MESSAGING_SERVICE_SID", "")
    from_number = getattr(settings, "TWILIO_FROM_NUMBER", "")
    if not messaging_service and not from_number:
        return False
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        kwargs = {"body": body, "to": phone}
        if messaging_service:
            kwargs["messaging_service_sid"] = messaging_service
        else:
            kwargs["from_"] = from_number
        client.messages.create(**kwargs)
        return True
    except Exception:
        logger.exception("Échec d’envoi du SMS d’abonnement")
        return False


def notify_seller_subscription_confirmed(user, subscription, reference=""):
    title = "Abonnement vendeur confirmé"
    body = f"Votre abonnement vendeur est actif jusqu’au {subscription.ends_at:%d/%m/%Y}."
    if reference:
        body += f" Référence : {reference}."
    _notify(user, title, body)


def notify_seller_subscription_expiring(user, subscription, days_left: int):
    title = "Expiration de votre abonnement vendeur"
    body = f"Votre abonnement vendeur expire dans {days_left} jour(s), le {subscription.ends_at:%d/%m/%Y}. Renouvelez-le pour conserver vos fonctionnalités Pro."
    _notify(user, title, body, dedupe_marker=f"{subscription.ends_at.date()}:{days_left}")


def notify_seller_subscription_expired(user, subscription):
    title = "Votre abonnement vendeur a expiré"
    body = f"Votre abonnement vendeur a expiré le {subscription.ends_at:%d/%m/%Y}. Votre compte reste accessible avec les limites du forfait gratuit."
    _notify(user, title, body, dedupe_marker=str(subscription.ends_at.date()))


def _notify(user, title: str, body: str, dedupe_marker: str = ""):
    if dedupe_marker and AppNotification.objects.filter(recipient=user, kind=AppNotification.Kind.SUBSCRIPTION, title=title, body__contains=dedupe_marker).exists():
        return
    AppNotification.objects.create(recipient=user, kind=AppNotification.Kind.SUBSCRIPTION, title=title, body=body)
    email, phone = _contacts(user)
    if email:
        try:
            send_mail(title, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True)
        except Exception:
            logger.exception("Échec d’envoi de l’e-mail d’abonnement")
    if phone:
        _send_sms(phone, f"AgriLink CI : {body}")

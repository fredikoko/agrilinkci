import hashlib
import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

import phonenumbers
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from rest_framework.authtoken.models import Token
from django.utils import timezone
try:
    from twilio.base.exceptions import TwilioRestException
    from twilio.rest import Client
except ImportError:
    TwilioRestException = Exception
    Client = None

from .models import EmailChallenge, OtpChallenge, PhoneAccount
from .serializers import BuyerProfileSerializer

logger = logging.getLogger(__name__)


class OtpError(Exception):
    """Erreur contrôlée du flux d’authentification OTP."""


def normalize_phone(raw_phone: str) -> str:
    if not raw_phone or not raw_phone.strip():
        raise OtpError("Le numéro de téléphone est obligatoire.")
    try:
        parsed = phonenumbers.parse(raw_phone.strip(), settings.SMS_COUNTRY_CODE)
    except phonenumbers.NumberParseException as exc:
        raise OtpError("Le numéro de téléphone est invalide.") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise OtpError("Le numéro de téléphone est invalide.")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


class ConsoleSmsProvider:
    name = "console"

    def send(self, phone_e164: str, code: str) -> str:
        logger.warning("[SMS DEV] Code OTP pour %s : %s", phone_e164, code)
        return "console"

    def verify(self, phone_e164: str, code: str, challenge: OtpChallenge) -> bool:
        return hmac.compare_digest(challenge.code_hash, _hash_code(code))


class TwilioVerifyProvider:
    name = "twilio_verify"

    def __init__(self) -> None:
        missing = [
            name
            for name, value in {
                "TWILIO_ACCOUNT_SID": settings.TWILIO_ACCOUNT_SID,
                "TWILIO_AUTH_TOKEN": settings.TWILIO_AUTH_TOKEN,
                "TWILIO_VERIFY_SERVICE_SID": settings.TWILIO_VERIFY_SERVICE_SID,
            }.items()
            if not value
        ]
        if missing:
            raise OtpError(f"Configuration Twilio incomplète : {', '.join(missing)}")
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    def send(self, phone_e164: str, code: str) -> str:
        try:
            verification = (
                self.client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID)
                .verifications.create(channel="sms", to=phone_e164)
            )
        except TwilioRestException as exc:
            logger.exception("Échec d’envoi Twilio Verify")
            raise OtpError("Le SMS n’a pas pu être envoyé. Réessayez plus tard.") from exc
        return verification.sid

    def verify(self, phone_e164: str, code: str, challenge: OtpChallenge) -> bool:
        try:
            result = (
                self.client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID)
                .verification_checks.create(to=phone_e164, code=code)
            )
        except TwilioRestException as exc:
            logger.warning("Échec de validation Twilio Verify: %s", exc)
            return False
        return result.status == "approved"


def get_sms_provider():
    if settings.SMS_PROVIDER == "twilio":
        return TwilioVerifyProvider()
    if settings.SMS_PROVIDER == "console":
        return ConsoleSmsProvider()
    raise OtpError(f"SMS_PROVIDER inconnu : {settings.SMS_PROVIDER}")


@transaction.atomic
def request_otp(raw_phone: str, role: str | None = None) -> dict:
    phone_e164 = normalize_phone(raw_phone)
    role = PhoneAccount.Role.BUYER
    now = timezone.now()
    latest = (
        OtpChallenge.objects.filter(phone_e164=phone_e164, consumed_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if latest and (now - latest.created_at).total_seconds() < settings.OTP_REQUEST_COOLDOWN_SECONDS:
        raise OtpError("Un code vient déjà d’être envoyé. Attendez avant de réessayer.")

    code = _generate_code()
    provider = get_sms_provider()
    challenge = OtpChallenge.objects.create(
        phone_e164=phone_e164,
        role=role,
        provider=provider.name,
        code_hash=_hash_code(code) if provider.name == "console" else "",
        expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
    )
    try:
        challenge.provider_reference = provider.send(phone_e164, code)
        challenge.save(update_fields=["provider_reference"])
    except Exception:
        challenge.delete()
        raise

    response = {"phone": phone_e164, "expires_in": settings.OTP_TTL_SECONDS}
    if settings.DEBUG and provider.name == "console":
        response["dev_code"] = code
    return response


@transaction.atomic
def verify_otp(raw_phone: str, code: str, password: str = "", role: str | None = None) -> dict:
    phone_e164 = normalize_phone(raw_phone)
    role = PhoneAccount.Role.BUYER
    now = timezone.now()
    challenge = (
        OtpChallenge.objects.select_for_update()
        .filter(phone_e164=phone_e164, role=role, consumed_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if not challenge:
        raise OtpError("Aucun code actif pour ce numéro.")
    if challenge.expires_at <= now:
        raise OtpError("Le code a expiré. Demandez un nouveau code.")
    if challenge.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise OtpError("Nombre maximal d’essais atteint. Demandez un nouveau code.")
    if not code or len(code.strip()) != 6 or not code.strip().isdigit():
        raise OtpError("Le code doit comporter 6 chiffres.")

    challenge.attempts += 1
    challenge.save(update_fields=["attempts"])
    provider = get_sms_provider()
    if not provider.verify(phone_e164, code.strip(), challenge):
        raise OtpError("Code incorrect.")

    challenge.consumed_at = now
    challenge.save(update_fields=["consumed_at"])
    user_model = get_user_model()
    user, _ = user_model.objects.get_or_create(username=f"phone:{phone_e164}")
    account, created = PhoneAccount.objects.get_or_create(
        user=user,
        defaults={
            "phone_e164": phone_e164,
            "role": PhoneAccount.Role.BUYER,
            "phone_verified": True,
        },
    )
    if not created:
        account.phone_e164 = phone_e164
        account.phone_verified = True
        # Le rôle vendeur est accordé uniquement par le paiement Paystack;
        # une sélection de rôle dans l’écran OTP ne peut donc pas l’usurper.
        account.save(update_fields=["phone_e164", "phone_verified", "updated_at"])
    if password:
        user.set_password(password)
        user.save(update_fields=["password"])
    return {"user": user, "account": account}


@transaction.atomic
def request_email_code(raw_email: str, role: str | None = None) -> dict:
    email = raw_email.strip().lower()
    now = timezone.now()
    latest = EmailChallenge.objects.filter(email=email, consumed_at__isnull=True).order_by("-created_at").first()
    if latest and (now - latest.created_at).total_seconds() < settings.OTP_REQUEST_COOLDOWN_SECONDS:
        raise OtpError("Un code vient déjà d’être envoyé. Attendez avant de réessayer.")
    code = _generate_code()
    challenge = EmailChallenge.objects.create(
        email=email,
        code_hash=_hash_code(code),
        expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
    )
    try:
        send_mail(
            "Votre code AgriLink CI",
            f"Votre code de connexion AgriLink CI est : {code}. Il expire dans quelques minutes.",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
    except Exception as exc:
        challenge.delete()
        logger.exception("Échec d’envoi du code e-mail")
        raise OtpError("Le code e-mail n’a pas pu être envoyé. Réessayez plus tard.") from exc
    response = {"email": email, "expires_in": settings.OTP_TTL_SECONDS}
    if settings.DEBUG:
        response["dev_code"] = code
    return response


@transaction.atomic
def verify_email_code(raw_email: str, code: str, password: str = "", role: str | None = None) -> dict:
    email = raw_email.strip().lower()
    now = timezone.now()
    challenge = EmailChallenge.objects.select_for_update().filter(email=email, consumed_at__isnull=True).order_by("-created_at").first()
    if not challenge:
        raise OtpError("Aucun code actif pour cette adresse e-mail.")
    if challenge.expires_at <= now:
        raise OtpError("Le code e-mail a expiré. Demandez un nouveau code.")
    if challenge.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise OtpError("Nombre maximal d’essais atteint. Demandez un nouveau code.")
    if not code or len(code.strip()) != 6 or not code.strip().isdigit():
        raise OtpError("Le code doit comporter 6 chiffres.")
    challenge.attempts += 1
    challenge.save(update_fields=["attempts"])
    if not hmac.compare_digest(challenge.code_hash, _hash_code(code.strip())):
        raise OtpError("Code incorrect.")
    challenge.consumed_at = now
    challenge.save(update_fields=["consumed_at"])
    user_model = get_user_model()
    account = PhoneAccount.objects.select_related("user").filter(email=email).first()
    if account:
        user = account.user
    else:
        user, _ = user_model.objects.get_or_create(username=f"email:{email}", defaults={"email": email})
    if not user.email:
        user.email = email
        user.save(update_fields=["email"])
    account, created = PhoneAccount.objects.get_or_create(
        user=user,
        defaults={"email": email, "email_verified": True, "role": PhoneAccount.Role.BUYER},
    )
    if not created:
        account.email = email
        account.email_verified = True
        account.save(update_fields=["email", "email_verified", "updated_at"])
    if password:
        user.set_password(password)
        user.save(update_fields=["password"])
    return {"user": user, "account": account}


def find_account_by_identifier(identifier: str):
    """Retourne le compte correspondant à un e-mail ou à un numéro normalisé."""
    identifier = (identifier or "").strip()
    if "@" in identifier:
        return PhoneAccount.objects.select_related("user").filter(email=identifier.lower()).first()
    try:
        phone = normalize_phone(identifier)
    except OtpError:
        return None
    return PhoneAccount.objects.select_related("user").filter(phone_e164=phone).first()


def login_with_password(identifier: str, password: str) -> dict:
    account = find_account_by_identifier(identifier)
    if not account or not account.user.check_password(password):
        raise OtpError("Identifiant ou mot de passe incorrect.")
    if not (account.phone_verified or account.email_verified):
        raise OtpError("Ce compte n’est pas encore vérifié.")
    return {"user": account.user, "account": account}


@transaction.atomic
def request_password_reset(identifier: str) -> dict:
    account = find_account_by_identifier(identifier)
    if not account:
        return {"detail": "Si le compte existe, un code de réinitialisation a été envoyé."}
    code = _generate_code()
    now = timezone.now()
    if "@" in identifier:
        EmailChallenge.objects.filter(email=account.email, consumed_at__isnull=True).update(consumed_at=now)
        EmailChallenge.objects.create(email=account.email, code_hash=_hash_code(code), expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS))
        send_mail("Réinitialisation du mot de passe AgriLink CI", f"Votre code est : {code}", settings.DEFAULT_FROM_EMAIL, [account.email], fail_silently=False)
        response = {"detail": "Un code de réinitialisation a été envoyé par e-mail."}
        if settings.DEBUG:
            response["dev_code"] = code
        return response
    phone = account.phone_e164
    OtpChallenge.objects.filter(phone_e164=phone, role="password_reset", consumed_at__isnull=True).update(consumed_at=now)
    provider = get_sms_provider()
    challenge = OtpChallenge.objects.create(phone_e164=phone, role="password_reset", provider=provider.name, code_hash=_hash_code(code) if provider.name == "console" else "", expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS))
    challenge.provider_reference = provider.send(phone, code)
    challenge.save(update_fields=["provider_reference"])
    response = {"detail": "Un code de réinitialisation a été envoyé par SMS."}
    if settings.DEBUG and provider.name == "console":
        response["dev_code"] = code
    return response


@transaction.atomic
def reset_password(identifier: str, code: str, password: str) -> None:
    account = find_account_by_identifier(identifier)
    if not account:
        raise OtpError("Code ou compte invalide.")
    now = timezone.now()
    if "@" in identifier:
        challenge = EmailChallenge.objects.select_for_update().filter(email=account.email, consumed_at__isnull=True).order_by("-created_at").first()
        valid = challenge and challenge.expires_at > now and hmac.compare_digest(challenge.code_hash, _hash_code(code.strip()))
    else:
        challenge = OtpChallenge.objects.select_for_update().filter(phone_e164=account.phone_e164, role="password_reset", consumed_at__isnull=True).order_by("-created_at").first()
        valid = challenge and challenge.expires_at > now and (get_sms_provider().verify(account.phone_e164, code.strip(), challenge))
    if not valid:
        raise OtpError("Code de réinitialisation invalide ou expiré.")
    challenge.consumed_at = now
    challenge.save(update_fields=["consumed_at"])
    account.user.set_password(password)
    account.user.save(update_fields=["password"])


def auth_response(result: dict) -> dict:
    token, _ = Token.objects.get_or_create(user=result["user"])
    account = result["account"]
    profile = getattr(result["user"], "buyer_profile", None)
    return {"token": token.key, "user": {"id": result["user"].id, "username": result["user"].username}, "account": {"phone": account.phone_e164, "email": account.email, "role": account.role, "phone_verified": account.phone_verified, "email_verified": account.email_verified}, "buyer_profile": BuyerProfileSerializer(profile).data if profile else None, "profile_configured": bool(profile and profile.region_id and profile.locality_id)}
    

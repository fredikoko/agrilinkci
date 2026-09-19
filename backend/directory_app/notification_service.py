import json
import os
from typing import Iterable

from django.conf import settings

from .models import AppNotification, NotificationDevice


def _firebase_app():
    """Initialise Firebase une seule fois si les credentials sont disponibles."""
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        return None
    if firebase_admin._apps:
        return firebase_admin.get_app()
    raw = getattr(settings, "FIREBASE_CREDENTIALS_JSON", "") or os.getenv("FIREBASE_CREDENTIALS_JSON", "")
    raw = raw.strip()
    if not raw:
        return None
    try:
        info = json.loads(raw)
        return firebase_admin.initialize_app(credentials.Certificate(info))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


import logging

logger = logging.getLogger(__name__)


def send_push(devices: Iterable[NotificationDevice], title: str, body: str, data: dict | None = None) -> int:
    """Envoie une notification FCM par lots de 500 max et retourne le nombre de succès."""
    tokens = list(dict.fromkeys(
        device.token.strip()
        for device in devices
        if device.is_active and device.token and device.token.strip()
    ))
    app = _firebase_app()
    if not tokens or app is None:
        return 0

    from firebase_admin import messaging

    CHUNK_SIZE = 500
    total_success = 0
    payload_data = {str(k): str(v) for k, v in (data or {}).items()}

    for i in range(0, len(tokens), CHUNK_SIZE):
        chunk = tokens[i : i + CHUNK_SIZE]
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data=payload_data,
                tokens=chunk,
            )
            response = messaging.send_each_for_multicast(message, app=app)
            total_success += response.success_count
        except Exception as exc:
            logger.exception("Erreur lors de l'envoi push FCM du lot %d-%d : %s", i, i + len(chunk), exc)

    return total_success


def notify_users(users, title: str, body: str, kind: str = AppNotification.Kind.ADVICE, sender_vendor=None) -> int:
    """Crée les notifications en base par lots et tente leur diffusion push."""
    user_list = list(users)
    if not user_list:
        return 0

    AppNotification.objects.bulk_create(
        [
            AppNotification(recipient=user, title=title, body=body, kind=kind, sender_vendor=sender_vendor)
            for user in user_list
        ],
        batch_size=1000,
    )
    devices = NotificationDevice.objects.filter(user__in=user_list, is_active=True)
    return send_push(devices, title, body, {"kind": kind})

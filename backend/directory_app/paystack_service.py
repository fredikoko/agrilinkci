"""
Module déprécié : Remplacé par chariow_service.py.
Conservé pour la compatibilité des imports existants.
"""
import warnings

from .chariow_service import (  # noqa: F401
    ChariowError,
    PaystackError,
    initialize_subscription_payment,
    verify_and_activate_payment,
    verify_webhook_signature,
    _headers,
    _request,
)

warnings.warn(
    "paystack_service est déprécié. Utilisez chariow_service à la place.",
    DeprecationWarning,
    stacklevel=2,
)

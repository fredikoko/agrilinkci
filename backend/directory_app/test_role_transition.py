from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import PhoneAccount


class RoleTransitionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="standard-user")
        self.account = PhoneAccount.objects.create(
            user=self.user,
            phone_e164="+2250700000077",
            role=PhoneAccount.Role.BUYER,
            phone_verified=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @override_settings(SMS_PROVIDER="console", DEBUG=True)
    def test_signup_request_ignores_legacy_role_and_creates_buyer_account(self):
        client = APIClient()
        response = client.post(
            "/api/auth/request-code/",
            {"phone": "0700000066", "role": "seller"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("role", response.json())
        self.assertEqual(response.json()["phone"], "+2250700000066")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEBUG=True)
    def test_email_signup_request_does_not_expose_role_choice(self):
        client = APIClient()
        response = client.post(
            "/api/auth/request-email-code/",
            {"email": "new-user@example.com", "role": "seller"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "new-user@example.com")

    def test_free_activation_transitions_standard_user_to_seller(self):
        response = self.client.post("/api/payments/seller/free-activate/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], PhoneAccount.Role.SELLER)
        self.assertTrue(response.json()["active"])
        self.account.refresh_from_db()
        self.assertEqual(self.account.role, PhoneAccount.Role.SELLER)

    def test_free_activation_requires_verified_account(self):
        self.account.phone_verified = False
        self.account.save(update_fields=["phone_verified"])
        response = self.client.post("/api/payments/seller/free-activate/", {}, format="json")
        self.assertEqual(response.status_code, 403)
        self.account.refresh_from_db()
        self.assertEqual(self.account.role, PhoneAccount.Role.BUYER)

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    Payment,
    PhoneAccount,
    Product,
    SellerSubscription,
    Vendor,
    VendorProduct,
)
from .paystack_service import verify_and_activate_payment


class V2FinanceAndStockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        cls.region = cls._region()
        cls.locality = cls.region.localities.first()
        cls.category = cls.region.localities.first().buyer_profiles.model.preferred_categories.rel.field.related_model.objects.first()
        cls.product = Product.objects.first()

    @classmethod
    def _region(cls):
        from .models import Region
        return Region.objects.first()

    def make_seller(self, username="v2-seller"):
        user = get_user_model().objects.create_user(username=username, email=f"{username}@example.com")
        PhoneAccount.objects.create(user=user, phone_e164="+2250700000099", role=PhoneAccount.Role.SELLER, phone_verified=True)
        vendor = Vendor.objects.create(
            owner=user,
            name=f"{username} vendeur",
            vendor_type="détaillant",
            region=self.region,
            locality=self.locality,
            phone="+2250700000099",
            approval_status=Vendor.ApprovalStatus.APPROVED,
            is_verified=True,
        )
        return user, vendor

    @override_settings(PAYSTACK_AMOUNT_MULTIPLIER=1, PAYSTACK_SUBSCRIPTION_DAYS=30)
    def test_paystack_verification_is_idempotent(self):
        user = get_user_model().objects.create_user(username="idempotent-paystack", email="idempotent@example.com")
        account = PhoneAccount.objects.create(user=user, phone_e164="+2250700000088", role=PhoneAccount.Role.BUYER, phone_verified=True)
        payment = Payment.objects.create(user=user, reference="AGRILINK-IDEMPOTENT", amount=5000, currency="XOF", status=Payment.Status.SUCCESS, channel="card", paid_at=timezone.now())
        subscription = SellerSubscription.objects.create(user=user, payment=payment, starts_at=timezone.now(), ends_at=timezone.now() + timedelta(days=30))
        original_end = subscription.ends_at

        with patch("directory_app.paystack_service._request") as verify_request:
            result = verify_and_activate_payment(user, payment.reference)

        verify_request.assert_not_called()
        self.assertTrue(result["idempotent"])
        subscription.refresh_from_db()
        self.assertEqual(subscription.ends_at, original_end)
        self.assertEqual(account.role, PhoneAccount.Role.BUYER)

    def test_stock_movement_updates_quantity_and_blocks_insufficient_output(self):
        user, vendor = self.make_seller()
        stock = VendorProduct.objects.create(vendor=vendor, product=self.product, quantity_available=10, alert_threshold=3)
        client = APIClient()
        client.force_authenticate(user=user)

        outgoing = client.post("/api/stock-movements/", {"stock": stock.id, "movement_type": "out", "quantity": 6, "reason": "Vente directe"}, format="json")
        self.assertEqual(outgoing.status_code, 201)
        stock.refresh_from_db()
        self.assertEqual(stock.quantity_available, 4)
        self.assertTrue(stock.is_available)

        insufficient = client.post("/api/stock-movements/", {"stock": stock.id, "movement_type": "out", "quantity": 5}, format="json")
        self.assertEqual(insufficient.status_code, 400)
        stock.refresh_from_db()
        self.assertEqual(stock.quantity_available, 4)

        incoming = client.post("/api/stock-movements/", {"stock": stock.id, "movement_type": "in", "quantity": 8}, format="json")
        self.assertEqual(incoming.status_code, 201)
        stock.refresh_from_db()
        self.assertEqual(stock.quantity_available, 12)
        self.assertEqual(stock.movements.count(), 2)

    def test_financial_dashboard_requires_admin_and_returns_subscription_metrics(self):
        regular, _vendor = self.make_seller(username="regular-dashboard")
        client = APIClient()
        client.force_authenticate(user=regular)
        self.assertEqual(client.get("/api/admin/financial-dashboard/").status_code, 403)

        admin = get_user_model().objects.create_superuser(username="finance-admin", email="admin@example.com", password="safe-password")
        client.force_authenticate(user=admin)
        response = client.get("/api/admin/financial-dashboard/?days=30")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIn("subscriptions", response.json()["data"])
        self.assertIn("seller_active", response.json()["data"]["subscriptions"])

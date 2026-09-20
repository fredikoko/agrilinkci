import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from unittest.mock import patch
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import BuyerProfile, Payment, PhoneAccount, Region, Vendor, VendorReview



class AgriLinkApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        cls.client = APIClient()
        cls.gontougo = Region.objects.get(name="Gontougo")
        cls.bondoukou = cls.gontougo.localities.get(name="Bondoukou")

    def test_health_endpoint(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["database"], "connected")

    def test_vendor_filter_by_locality(self):
        response = self.client.get("/api/vendors/", {"locality": self.bondoukou.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        self.assertTrue(all(item["locality_name"] == "Bondoukou" for item in response.json()))

    def test_vendor_search_by_product(self):
        response = self.client.get("/api/vendors/", {"search": "semence de chou"})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 2)
        self.assertTrue(any("Semence de chou" in item["product_names"] for item in response.json()))

    def test_vendor_detail_contains_stock(self):
        vendor = Vendor.objects.get(name="Coopérative Agricole du Gontougo")
        response = self.client.get(f"/api/vendors/{vendor.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("stock_items", response.json())
        self.assertGreaterEqual(len(response.json()["stock_items"]), 1)

    @override_settings(SMS_PROVIDER="console", DEBUG=True)
    def test_phone_otp_flow_creates_authenticated_account(self):
        request = self.client.post(
            "/api/auth/request-code/",
            {"phone": "0700000010", "role": "buyer"},
            format="json",
        )
        self.assertEqual(request.status_code, 200)
        dev_code = request.json()["dev_code"]
        verify = self.client.post(
            "/api/auth/verify-code/",
            {"phone": "0700000010", "code": dev_code, "role": "buyer"},
            format="json",
        )
        self.assertEqual(verify.status_code, 200)
        self.assertEqual(PhoneAccount.objects.get().phone_e164, "+2250700000010")
        authenticated_client = APIClient()
        authenticated_client.credentials(HTTP_AUTHORIZATION=f"Token {verify.json()['token']}")
        me = authenticated_client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["account"]["role"], "buyer")

    def test_create_buyer_profile(self):
        category_id = self.gontougo.buyer_profiles.model.preferred_categories.rel.field.related_model.objects.get(
            slug="semences"
        ).id
        payload = {
            "full_name": "Koko",
            "phone": "+2250700000010",
            "region": self.gontougo.id,
            "locality": self.bondoukou.id,
            "preferred_categories": [category_id],
            "culture_profile": "Maraîcher",
        }
        client = APIClient()
        user = get_user_model().objects.create_user(username="buyer-test")
        PhoneAccount.objects.create(
            user=user,
            phone_e164="+2250700000010",
            role="buyer",
            phone_verified=True,
        )
        client.force_authenticate(user=user)
        response = client.post("/api/buyer-profiles/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(BuyerProfile.objects.count(), 1)

    @override_settings(
        CHARIOW_API_KEY="sk_test_demo",
        CHARIOW_SELLER_PRODUCT_ID="prd_test_seller",
        CHARIOW_SUBSCRIPTION_AMOUNT=5000,
        CHARIOW_CURRENCY="XOF",
        CHARIOW_SUBSCRIPTION_DAYS=30,
    )
    def test_chariow_payment_activates_seller_subscription(self):
        user = get_user_model().objects.create_user(username="buyer-payment-test", email="buyer.payment@example.com")
        PhoneAccount.objects.create(
            user=user,
            phone_e164="+2250700000020",
            role="buyer",
            phone_verified=True,
        )
        client = APIClient()
        client.force_authenticate(user=user)

        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload
                self.ok = True
                self.status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return self.payload

        reference_holder = {}

        def fake_chariow_request(method, url, **kwargs):
            if method == "POST":
                reference_holder["value"] = kwargs["json"]["metadata"]["reference"]
                return FakeResponse(
                    {
                        "data": {
                            "step": "payment",
                            "payment": {
                                "checkout_url": "https://chariow.com/checkout/demo",
                            },
                            "id": "sale_chariow_12345",
                        },
                    }
                )
            return FakeResponse(
                {
                    "data": [
                        {
                            "status": "completed",
                            "reference": reference_holder.get("value"),
                            "amount": 5000,
                            "currency": "XOF",
                            "payment_method": "orange_money",
                            "id": "sale_chariow_12345",
                        }
                    ],
                }
            )

        with patch(
            "directory_app.chariow_service.requests.request",
            side_effect=fake_chariow_request,
        ):
            initialized = client.post("/api/payments/subscription/initialize/", {}, format="json")
            self.assertEqual(initialized.status_code, 201)
            reference = initialized.json()["reference"]
            verified = client.post(
                "/api/payments/subscription/verify/",
                {"reference": reference},
                format="json",
            )

        self.assertEqual(verified.status_code, 200)
        self.assertTrue(user.seller_subscription.is_active)
        user.phone_account.refresh_from_db()
        self.assertEqual(user.phone_account.role, PhoneAccount.Role.SELLER)
        self.assertEqual(verified.json()["role"], PhoneAccount.Role.SELLER)
        created = client.post(
            "/api/vendors/",
            {
                "name": "Vendeur Paystack Test",
                "vendor_type": "détaillant",
                "region": self.gontougo.id,
                "locality": self.bondoukou.id,
                "phone": "+2250700000020",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["approval_status"], "pending")
        self.assertFalse(created.json()["is_verified"])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEBUG=True)
    def test_email_authentication_flow(self):
        requested = self.client.post(
            "/api/auth/request-email-code/",
            {"email": "agriculteur@example.com", "role": "buyer"},
            format="json",
        )
        self.assertEqual(requested.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        code = re.search(r"(\d{6})", mail.outbox[0].body).group(1)
        verified = self.client.post(
            "/api/auth/verify-email-code/",
            {"email": "agriculteur@example.com", "code": code, "role": "buyer"},
            format="json",
        )
        self.assertEqual(verified.status_code, 200)
        account = PhoneAccount.objects.get(email="agriculteur@example.com")
        self.assertTrue(account.email_verified)
        self.assertEqual(verified.json()["account"]["email"], "agriculteur@example.com")


    @override_settings(SMS_PROVIDER="console", DEBUG=True)
    def test_buyer_profile_and_local_recommendations(self):
        user = get_user_model().objects.create_user(username="buyer-local-test")
        PhoneAccount.objects.create(
            user=user,
            phone_e164="+2250700000030",
            role="buyer",
            phone_verified=True,
        )
        client = APIClient()
        client.force_authenticate(user=user)

        empty = client.get("/api/buyer/me/")
        self.assertEqual(empty.status_code, 200)
        self.assertFalse(empty.json()["configured"])

        saved = client.patch(
            "/api/buyer/me/",
            {
                "full_name": "Acheteur Local",
                "region": self.gontougo.id,
                "locality": self.bondoukou.id,
            },
            format="json",
        )
        self.assertEqual(saved.status_code, 201)
        self.assertEqual(saved.json()["profile"]["locality_name"], "Bondoukou")

        recommendations = client.get("/api/buyer/recommendations/")
        self.assertEqual(recommendations.status_code, 200)
        self.assertTrue(recommendations.json()["configured"])
        results = recommendations.json()["results"]
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["locality_name"], "Bondoukou")

    def test_get_mine_vendors(self):
        user = get_user_model().objects.create_user(username="seller-mine-test")
        PhoneAccount.objects.create(
            user=user,
            phone_e164="+2250700000040",
            role="seller",
            phone_verified=True,
        )
        vendor = Vendor.objects.create(
            name="Point Vente Test",
            vendor_type="détaillant",
            region=self.gontougo,
            locality=self.bondoukou,
            phone="+2250700000040",
            owner=user,
            is_verified=True,
            is_active=True,
            approval_status=Vendor.ApprovalStatus.APPROVED,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get("/api/vendors/?mine=true")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        results = data if isinstance(data, list) else data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], vendor.id)

    def test_vendor_review_upsert(self):
        user = get_user_model().objects.create_user(username="reviewer-test")
        PhoneAccount.objects.create(
            user=user,
            phone_e164="+2250700000050",
            role="buyer",
            phone_verified=True,
        )
        vendor = Vendor.objects.create(
            name="Vendeur Avis Test",
            vendor_type="détaillant",
            region=self.gontougo,
            locality=self.bondoukou,
            phone="+2250700000050",
            is_verified=True,
            is_active=True,
            approval_status=Vendor.ApprovalStatus.APPROVED,
        )
        client = APIClient()
        client.force_authenticate(user=user)

        # Premier avis -> 201 Created
        first = client.post("/api/vendor-reviews/", {"vendor": vendor.id, "rating": 4, "comment": "Bien"}, format="json")
        self.assertEqual(first.status_code, 201)

        # Deuxième avis par le même auteur -> 200 OK (mise à jour sans IntegrityError)
        second = client.post("/api/vendor-reviews/", {"vendor": vendor.id, "rating": 5, "comment": "Super"}, format="json")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["rating"], 5)
        self.assertEqual(VendorReview.objects.filter(vendor=vendor, author=user).count(), 1)

    def test_seller_can_access_buyer_recommendations(self):
        user = get_user_model().objects.create_user(username="seller-rec-test")
        PhoneAccount.objects.create(
            user=user,
            phone_e164="+2250700000060",
            role="seller",
            phone_verified=True,
        )
        BuyerProfile.objects.create(
            user=user,
            full_name="Vendeur Acheteur",
            region=self.gontougo,
            locality=self.bondoukou,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get("/api/buyer/recommendations/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["configured"])

    def test_seller_analytics_view(self):
        user = get_user_model().objects.create_user(username="seller-analytics-user")
        PhoneAccount.objects.create(
            user=user,
            phone_e164="+2250700000070",
            role="seller",
            phone_verified=True,
        )
        vendor = Vendor.objects.create(
            name="Vendeur Analytics Test",
            vendor_type="détaillant",
            region=self.gontougo,
            locality=self.bondoukou,
            phone="+2250700000070",
            owner=user,
            is_verified=True,
            is_active=True,
            approval_status=Vendor.ApprovalStatus.APPROVED,
        )
        product = self.gontougo.buyer_profiles.model.preferred_categories.rel.field.related_model.objects.first()
        from .models import VendorSale
        VendorSale.objects.create(
            vendor=vendor,
            product_id=1,
            quantity=5,
            unit_price=1000,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get("/api/seller/analytics/?days=30")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["sales_count"], 1)
        self.assertEqual(data["total_revenue"], 5000)
        self.assertEqual(len(data["daily"]), 1)
        self.assertEqual(data["daily"][0]["revenue"], 5000)

    def test_vendor_proximity_filter(self):
        # Set latitude/longitude for locality and vendor
        self.bondoukou.latitude = 8.0400
        self.bondoukou.longitude = -2.8000
        self.bondoukou.save()

        # Near vendor (within ~5km of 8.04, -2.80)
        v_near = Vendor.objects.create(
            name="Near Vendor Proximity Test",
            vendor_type="détaillant",
            region=self.gontougo,
            locality=self.bondoukou,
            phone="+2250700000088",
            latitude=8.0410,
            longitude=-2.8010,
            is_verified=True,
            is_active=True,
            approval_status=Vendor.ApprovalStatus.APPROVED,
        )

        # Far vendor (in Abidjan ~400km away)
        v_far = Vendor.objects.create(
            name="Far Vendor Proximity Test",
            vendor_type="détaillant",
            region=self.gontougo,
            locality=self.bondoukou,
            phone="+2250700000089",
            latitude=5.3500,
            longitude=-4.0000,
            is_verified=True,
            is_active=True,
            approval_status=Vendor.ApprovalStatus.APPROVED,
        )

        # Query near (8.04, -2.80) with 10km radius
        response = self.client.get("/api/vendors/", {"near_lat": "8.0400", "near_lng": "-2.8000", "radius_km": "10"})
        self.assertEqual(response.status_code, 200)
        names = [item["name"] for item in response.json()]
        self.assertIn("Near Vendor Proximity Test", names)
        self.assertNotIn("Far Vendor Proximity Test", names)

    def test_change_password_validates_password(self):
        user = get_user_model().objects.create_user(username="pwd-test-user", password="InitialPassword123!")
        client = APIClient()
        client.force_authenticate(user=user)

        # Rejet mot de passe trop court ou trop simple
        res_weak = client.post("/api/auth/change-password/", {"old_password": "InitialPassword123!", "new_password": "123"}, format="json")
        self.assertEqual(res_weak.status_code, 400)

        # Succès mot de passe robuste
        res_ok = client.post("/api/auth/change-password/", {"old_password": "InitialPassword123!", "new_password": "RobustPassword456!"}, format="json")
        self.assertEqual(res_ok.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("RobustPassword456!"))

    @override_settings(
        CHARIOW_API_KEY="sk_test_demo",
        CHARIOW_WEBHOOK_SECRET="whsec_test_secret",
        CHARIOW_SUBSCRIPTION_DAYS=30,
    )
    def test_chariow_webhook_activates_seller_subscription(self):
        import hashlib
        import hmac
        import json

        user = get_user_model().objects.create_user(username="webhook-user", email="webhook@example.com")
        PhoneAccount.objects.create(user=user, phone_e164="+2250700000077", role="buyer", phone_verified=True)
        payment = Payment.objects.create(
            user=user,
            reference="AGRILINK-WH-TEST-1",
            amount=5000,
            currency="XOF",
            status=Payment.Status.PENDING,
        )

        payload_dict = {
            "event": "successful.sale",
            "data": {
                "id": "sale_wh_999",
                "status": "completed",
                "reference": payment.reference,
                "amount": 5000,
                "currency": "XOF",
                "payment_method": "orange_money",
                "metadata": {
                    "reference": payment.reference,
                    "purpose": "seller_subscription",
                },
            },
        }
        body = json.dumps(payload_dict).encode("utf-8")
        sig = hmac.new("whsec_test_secret".encode("utf-8"), body, hashlib.sha256).hexdigest()

        with patch("directory_app.chariow_service._request") as mock_req:
            mock_req.return_value = {"data": {"id": "sale_wh_999", "status": "completed", "reference": payment.reference}}
            response = self.client.post(
                "/api/payments/chariow/webhook/",
                data=body,
                content_type="application/json",
                HTTP_X_CHARIOW_SIGNATURE=f"sha256={sig}",
                HTTP_X_PULSE_EVENT="successful.sale",
            )

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertTrue(user.seller_subscription.is_active)
        user.phone_account.refresh_from_db()
        self.assertEqual(user.phone_account.role, PhoneAccount.Role.SELLER)







import json

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth_permissions import IsVerifiedAccount
from .models import Payment, PhoneAccount, SellerSubscription
from conseil.payment_service import ConseilPaymentError, verify_conseil_payment
from .paystack_service import PaystackError, initialize_subscription_payment, verify_and_activate_payment, verify_webhook_signature


class SellerFreeActivateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerifiedAccount]

    def post(self, request):
        account = getattr(request.user, "phone_account", None)
        if not account:
            return Response({"detail": "Compte d’authentification introuvable."}, status=status.HTTP_400_BAD_REQUEST)
        account.role = PhoneAccount.Role.SELLER
        account.save(update_fields=["role", "updated_at"])
        return Response({"active": True, "plan": "free", "role": account.role}, status=status.HTTP_200_OK)


class SubscriptionPaymentInitializeView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerifiedAccount]

    def post(self, request):
        try:
            email = request.data.get("email") if isinstance(request.data, dict) else None
            result = initialize_subscription_payment(request.user, custom_email=email)
        except PaystackError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_201_CREATED)



class SubscriptionPaymentVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerifiedAccount]

    def post(self, request):
        reference = str(request.data.get("reference", "")).strip()
        if not reference:
            return Response({"detail": "La référence Paystack est obligatoire."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = verify_and_activate_payment(request.user, reference)
        except PaystackError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class SubscriptionStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerifiedAccount]

    def get(self, request):
        try:
            subscription = request.user.seller_subscription
        except SellerSubscription.DoesNotExist:
            return Response({"active": False, "status": "none"})
        if subscription.status == SellerSubscription.Status.ACTIVE and subscription.ends_at <= timezone.now():
            subscription.status = SellerSubscription.Status.EXPIRED
            subscription.save(update_fields=["status", "updated_at"])
        return Response(
            {
                "active": subscription.is_active,
                "status": subscription.status,
                "starts_at": subscription.starts_at,
                "ends_at": subscription.ends_at,
            }
        )


class PaystackWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        signature = request.headers.get("x-paystack-signature", "")
        if not verify_webhook_signature(request.body, signature):
            return Response({"detail": "Signature invalide."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            event = json.loads(request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Response({"detail": "Payload JSON invalide."}, status=status.HTTP_400_BAD_REQUEST)

        if event.get("event") == "charge.success":
            reference = event.get("data", {}).get("reference")
            try:
                payment = Payment.objects.get(reference=reference)
                purpose = (payment.provider_response or {}).get("purpose")
                event_purpose = event.get("data", {}).get("metadata", {}).get("purpose")
                if purpose == "conseil_subscription" or event_purpose == "conseil_subscription":
                    verify_conseil_payment(payment.user, reference)
                else:
                    verify_and_activate_payment(payment.user, reference)
            except (Payment.DoesNotExist, PaystackError, ConseilPaymentError):
                # Retourner 200 évite les retries infinis pour un événement connu mais non traitable.
                pass
        return Response({"received": True}, status=status.HTTP_200_OK)

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AppNotification, NotificationDevice, PromotionQuota, SellerSubscription, Vendor
from .notification_service import notify_users


class NotificationDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = str(request.data.get("token", "")).strip()
        if not token:
            return Response({"detail": "Le token FCM est obligatoire."}, status=status.HTTP_400_BAD_REQUEST)
        device, _ = NotificationDevice.objects.update_or_create(
            token=token,
            defaults={"user": request.user, "platform": request.data.get("platform", ""), "is_active": True},
        )
        return Response({"id": device.id, "registered": True})


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = AppNotification.objects.filter(recipient=request.user)[:100]
        return Response([{
            "id": item.id,
            "kind": item.kind,
            "title": item.title,
            "body": item.body,
            "is_read": item.is_read,
            "sent_at": item.sent_at,
        } for item in items])


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        updated = AppNotification.objects.filter(pk=pk, recipient=request.user).update(is_read=True)
        if not updated:
            return Response({"detail": "Notification introuvable."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"is_read": True})


class VendorPromotionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        vendor = Vendor.objects.filter(owner=request.user, is_active=True).first()
        subscription = SellerSubscription.objects.filter(user=request.user, status=SellerSubscription.Status.ACTIVE, ends_at__gt=timezone.now()).first()
        if not vendor or not subscription:
            return Response({"detail": "Un abonnement vendeur Pro actif est requis."}, status=status.HTTP_403_FORBIDDEN)
        title = str(request.data.get("title", "Promotion vendeur")).strip()
        body = str(request.data.get("body", "")).strip()
        if not body:
            return Response({"detail": "Le contenu de la promotion est obligatoire."}, status=status.HTTP_400_BAD_REQUEST)
        today = timezone.localdate()
        quota, _ = PromotionQuota.objects.get_or_create(vendor=vendor, defaults={"month": today, "sent_count": 0})
        if quota.month.year != today.year or quota.month.month != today.month:
            quota.month = today
            quota.sent_count = 0
        if quota.sent_count >= 15:
            return Response({"detail": "Le quota de 15 promotions mensuelles est atteint."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        recipients = request.user.__class__.objects.exclude(pk=request.user.pk).filter(is_active=True)
        push_count = notify_users(recipients, title, body, AppNotification.Kind.PROMOTION, vendor)
        quota.sent_count += 1
        quota.save(update_fields=["month", "sent_count"])
        return Response({"sent": True, "push_delivered": push_count, "promotions_remaining": 15 - quota.sent_count}, status=status.HTTP_201_CREATED)

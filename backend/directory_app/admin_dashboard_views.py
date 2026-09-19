from datetime import timedelta

from django.db.models import Count, ExpressionWrapper, F, IntegerField, Sum
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment, SellerSubscription, VendorSale
from conseil.models import ConseilSubscription


class AdminFinancialDashboardView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        try:
            days = max(1, min(int(request.query_params.get("days", 30)), 365))
        except (TypeError, ValueError):
            days = 30
        start = timezone.now() - timedelta(days=days)
        successful = Payment.objects.filter(status=Payment.Status.SUCCESS, paid_at__gte=start)
        failed = Payment.objects.filter(status=Payment.Status.FAILED, created_at__gte=start)
        pending = Payment.objects.filter(status=Payment.Status.PENDING, created_at__gte=start)
        seller_payments = successful.filter(subscriptions__isnull=False)
        conseil_payments = successful.filter(conseil_subscriptions__isnull=False)
        sales = VendorSale.objects.filter(sold_at__gte=start)
        seller_revenue = seller_payments.aggregate(amount=Sum("amount"), count=Count("id"))
        conseil_revenue = conseil_payments.aggregate(amount=Sum("amount"), count=Count("id"))
        total_sale_amount = ExpressionWrapper(F("quantity") * F("unit_price"), output_field=IntegerField())
        marketplace_sales = sales.aggregate(amount=Sum("quantity"), revenue=Sum(total_sale_amount), count=Count("id"))
        top_sellers = list(
            sales.values("vendor_id", "vendor__name")
            .annotate(revenue=Sum(total_sale_amount), units=Sum("quantity"), transactions=Count("id"))
            .order_by("-revenue")[:10]
        )
        return Response(
            {
                "success": True,
                "data": {
                    "period_days": days,
                    "generated_at": timezone.now(),
                    "payments": {
                        "successful_count": successful.count(),
                        "successful_amount": successful.aggregate(total=Sum("amount"))["total"] or 0,
                        "failed_count": failed.count(),
                        "pending_count": pending.count(),
                    },
                    "subscriptions": {
                        "seller_active": SellerSubscription.objects.filter(status=SellerSubscription.Status.ACTIVE, ends_at__gt=timezone.now()).count(),
                        "seller_expired": SellerSubscription.objects.filter(status=SellerSubscription.Status.EXPIRED).count(),
                        "seller_revenue": seller_revenue["amount"] or 0,
                        "seller_payment_count": seller_revenue["count"] or 0,
                        "conseil_active": ConseilSubscription.objects.filter(status=ConseilSubscription.Status.ACTIVE, ends_at__gt=timezone.now()).count(),
                        "conseil_expired": ConseilSubscription.objects.filter(status=ConseilSubscription.Status.EXPIRED).count(),
                        "conseil_revenue": conseil_revenue["amount"] or 0,
                        "conseil_payment_count": conseil_revenue["count"] or 0,
                    },
                    "sales": {
                        "transaction_count": marketplace_sales["count"] or 0,
                        "units_sold": marketplace_sales["amount"] or 0,
                        "recorded_revenue": marketplace_sales["revenue"] or 0,
                        "top_sellers": top_sellers,
                    },
                },
            },
            status=status.HTTP_200_OK,
        )

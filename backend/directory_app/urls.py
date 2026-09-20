from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.views import TokenBlacklistView, TokenRefreshView

from .auth_views import (
    ChangePasswordView, LogoutView, MeView, PasswordLoginView, PasswordResetConfirmView,
    PasswordResetRequestView, RequestCodeView, RequestEmailCodeView, VerifyCodeView, VerifyEmailCodeView,
)
from .buyer_views import BuyerProfileMeView, BuyerRecommendationsView
from .admin_dashboard_views import AdminFinancialDashboardView
from .notification_views import NotificationDeviceView, NotificationListView, NotificationReadView, VendorPromotionView
from .payment_views import (
    ChariowWebhookView,
    PaystackWebhookView,
    SellerFreeActivateView,
    SubscriptionPaymentInitializeView,
    SubscriptionPaymentVerifyView,
    SubscriptionStatusView,
)
from .views import (
    VendorAnalyticsView,
    BuyerProfileViewSet,
    CategoryViewSet,
    LocalityViewSet,
    ProductViewSet,
    RegionViewSet,
    VendorViewSet,
    VendorProductViewSet,
    VendorSaleViewSet,
    StockMovementViewSet,
    VendorFavoriteViewSet,
    ProductFavoriteViewSet,
    VendorReviewViewSet,
    ServiceProviderViewSet,
    ProvidedServiceViewSet,
    ServiceProviderReviewViewSet,
)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        from django.core.cache import cache
        from django.db import connection
        from rest_framework import status

        db_status = "connected"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as exc:
            db_status = f"unhealthy: {exc}"

        cache_status = "connected"
        try:
            cache.set("_health_ping", "1", timeout=5)
            if cache.get("_health_ping") != "1":
                cache_status = "unresponsive"
        except Exception as exc:
            cache_status = f"unhealthy: {exc}"

        healthy = db_status == "connected"
        status_code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(
            {
                "status": "ok" if healthy else "degraded",
                "service": "AgriLink CI API",
                "database": db_status,
                "cache": cache_status,
            },
            status=status_code,
        )


router = DefaultRouter()
router.register("regions", RegionViewSet, basename="region")
router.register("localities", LocalityViewSet, basename="locality")
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")
router.register("vendors", VendorViewSet, basename="vendor")
router.register("stock", VendorProductViewSet, basename="stock")
router.register("seller-sales", VendorSaleViewSet, basename="seller-sale")
router.register("stock-movements", StockMovementViewSet, basename="stock-movement")
router.register("vendor-favorites", VendorFavoriteViewSet, basename="vendor-favorite")
router.register("product-favorites", ProductFavoriteViewSet, basename="product-favorite")
router.register("vendor-reviews", VendorReviewViewSet, basename="vendor-review")
router.register("buyer-profiles", BuyerProfileViewSet, basename="buyer-profile")
router.register("service-providers", ServiceProviderViewSet, basename="service-provider")
router.register("provided-services", ProvidedServiceViewSet, basename="provided-service")
router.register("provider-reviews", ServiceProviderReviewViewSet, basename="provider-review")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("admin/financial-dashboard/", AdminFinancialDashboardView.as_view(), name="admin-financial-dashboard"),
    path("auth/request-code/", RequestCodeView.as_view(), name="auth-request-code"),
    path("auth/verify-code/", VerifyCodeView.as_view(), name="auth-verify-code"),
    path("auth/request-email-code/", RequestEmailCodeView.as_view(), name="auth-request-email-code"),
    path("auth/verify-email-code/", VerifyEmailCodeView.as_view(), name="auth-verify-email-code"),
    path("auth/login/", PasswordLoginView.as_view(), name="auth-login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/token/blacklist/", TokenBlacklistView.as_view(), name="token-blacklist"),
    path("auth/password-reset/request/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),


    path("notifications/device/", NotificationDeviceView.as_view(), name="notification-device"),
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path("notifications/<int:pk>/read/", NotificationReadView.as_view(), name="notification-read"),
    path("notifications/promote/", VendorPromotionView.as_view(), name="vendor-promotion"),
    path("buyer/me/", BuyerProfileMeView.as_view(), name="buyer-me"),
    path("buyer/recommendations/", BuyerRecommendationsView.as_view(), name="buyer-recommendations"),
    path("payments/seller/free-activate/", SellerFreeActivateView.as_view(), name="seller-free-activate"),
    path("payments/subscription/initialize/", SubscriptionPaymentInitializeView.as_view(), name="subscription-payment-initialize"),
    path("payments/subscription/verify/", SubscriptionPaymentVerifyView.as_view(), name="subscription-payment-verify"),
    path("payments/subscription/status/", SubscriptionStatusView.as_view(), name="subscription-status"),
    path("payments/chariow/webhook/", ChariowWebhookView.as_view(), name="chariow-webhook"),
    path("payments/webhook/", ChariowWebhookView.as_view(), name="payment-webhook"),
    path("payments/paystack/webhook/", PaystackWebhookView.as_view(), name="paystack-webhook"),
    path("seller/analytics/", VendorAnalyticsView.as_view(), name="seller-analytics"),
    path("", include(router.urls)),
]

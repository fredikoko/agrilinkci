from django.utils import timezone
from directory_app.models import AppNotification, Region, VendorFavorite, ProductFavorite, SellerSubscription
from conseil.models import ConseilSubscription


def web_context(request):
    """Context processor fournissant les variables globales pour les templates web."""
    context = {
        "user_account": None,
        "is_seller": False,
        "is_pro_seller": False,
        "is_pro_conseil": False,
        "unread_notifications_count": 0,
        "user_favorite_vendor_ids": set(),
        "user_favorite_product_ids": set(),
        "nav_regions": Region.objects.prefetch_related("localities").all()[:15],
    }

    if request.user.is_authenticated:
        account = getattr(request.user, "phone_account", None)
        context["user_account"] = account
        context["is_seller"] = bool(account and account.role == "seller")

        try:
            seller_sub = request.user.seller_subscription
            context["is_pro_seller"] = bool(seller_sub.is_active)
        except Exception:
            context["is_pro_seller"] = False

        try:
            conseil_sub = getattr(request.user, "conseil_subscription", None)
            context["is_pro_conseil"] = bool(conseil_sub and conseil_sub.is_active)
        except Exception:
            context["is_pro_conseil"] = False

        try:
            context["unread_notifications_count"] = AppNotification.objects.filter(
                user=request.user, is_read=False
            ).count()
        except Exception:
            context["unread_notifications_count"] = 0

        context["user_favorite_vendor_ids"] = set(
            VendorFavorite.objects.filter(user=request.user).values_list("vendor_id", flat=True)
        )
        context["user_favorite_product_ids"] = set(
            ProductFavorite.objects.filter(user=request.user).values_list("product_id", flat=True)
        )

    return context

import math

from django.core.management.base import BaseCommand
from django.utils import timezone

from directory_app.models import SellerSubscription
from directory_app.subscription_notifications import (
    notify_seller_subscription_expired,
    notify_seller_subscription_expiring,
)


class Command(BaseCommand):
    help = "Envoie les alertes d’expiration des abonnements vendeurs."

    def handle(self, *args, **options):
        now = timezone.now()
        processed = 0
        for subscription in SellerSubscription.objects.select_related("user").filter(status=SellerSubscription.Status.ACTIVE):
            if subscription.ends_at <= now:
                subscription.status = SellerSubscription.Status.EXPIRED
                subscription.save(update_fields=["status", "updated_at"])
                notify_seller_subscription_expired(subscription.user, subscription)
                processed += 1
                continue
            days_left = max(1, math.ceil((subscription.ends_at - now).total_seconds() / 86400))
            if days_left in (7, 1):
                notify_seller_subscription_expiring(subscription.user, subscription, days_left)
                processed += 1
        self.stdout.write(self.style.SUCCESS(f"{processed} abonnement(s) vendeur traité(s)."))

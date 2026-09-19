from rest_framework.permissions import BasePermission


class IsVerifiedBuyer(BasePermission):
    message = "Un téléphone ou une adresse e-mail vérifié est requis."

    def has_permission(self, request, view) -> bool:
        account = getattr(request.user, "phone_account", None)
        return bool(
            request.user
            and request.user.is_authenticated
            and account
            and (account.phone_verified or account.email_verified)
            and account.role in {"buyer", "seller"}
        )



class IsActiveSellerSubscriber(BasePermission):
    message = "Un abonnement vendeur actif est requis."

    def has_permission(self, request, view) -> bool:
        account = getattr(request.user, "phone_account", None)
        subscription = getattr(request.user, "seller_subscription", None)
        return bool(
            request.user
            and request.user.is_authenticated
            and account
            and (account.phone_verified or account.email_verified)
            and account.role == "seller"
            and subscription
            and subscription.is_active
        )


class IsVerifiedAccount(BasePermission):
    message = "Un téléphone ou une adresse e-mail vérifié est requis."

    def has_permission(self, request, view) -> bool:
        account = getattr(request.user, "phone_account", None)
        return bool(
            request.user
            and request.user.is_authenticated
            and account
            and (account.phone_verified or account.email_verified)
            and account.role in {"buyer", "seller"}
        )


class IsVerifiedSeller(BasePermission):
    message = "Un téléphone ou une adresse e-mail vendeur vérifié est requis."

    def has_permission(self, request, view) -> bool:
        account = getattr(request.user, "phone_account", None)
        return bool(
            request.user
            and request.user.is_authenticated
            and account
            and (account.phone_verified or account.email_verified)
            and account.role == "seller"
        )

from django.contrib import admin
from django.utils import timezone

from .models import (
    AppNotification, BuyerProfile, Category, Locality, NotificationDevice,
    OtpChallenge, Payment, PhoneAccount, Product, PromotionQuota, Region,
    SellerSubscription, Vendor, VendorProduct, VendorSale, StockMovement,
    VendorFavorite, ProductFavorite, VendorReview,
    ServiceProvider, ProvidedService, ServiceProviderReview,
)


@admin.register(PhoneAccount)
class PhoneAccountAdmin(admin.ModelAdmin):
    list_display = ("phone_e164", "email", "role", "phone_verified", "email_verified", "created_at")
    list_filter = ("role", "phone_verified", "email_verified")
    search_fields = ("phone_e164", "email", "user__username")


@admin.register(OtpChallenge)
class OtpChallengeAdmin(admin.ModelAdmin):
    list_display = ("phone_e164", "role", "provider", "attempts", "expires_at", "consumed_at")
    list_filter = ("provider", "role", "consumed_at")
    search_fields = ("phone_e164", "provider_reference")
    readonly_fields = ("code_hash",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "amount", "currency", "status", "channel", "created_at")
    list_filter = ("status", "currency", "channel")
    search_fields = ("reference", "user__username", "paystack_transaction_id")
    readonly_fields = ("provider_response",)


@admin.register(SellerSubscription)
class SellerSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "starts_at", "ends_at", "payment")
    list_filter = ("status",)
    search_fields = ("user__username", "payment__reference")


@admin.register(VendorFavorite)
class VendorFavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "vendor", "created_at")
    search_fields = ("user__username", "vendor__name")


@admin.register(ProductFavorite)
class ProductFavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    search_fields = ("user__username", "product__name")


@admin.register(VendorReview)
class VendorReviewAdmin(admin.ModelAdmin):
    list_display = ("vendor", "author", "rating", "is_published", "created_at")
    list_filter = ("rating", "is_published")
    search_fields = ("vendor__name", "author__username", "comment")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("stock", "movement_type", "quantity", "previous_quantity", "new_quantity", "created_by", "created_at")
    list_filter = ("movement_type", "created_at")
    search_fields = ("stock__vendor__name", "stock__product__name", "reason")
    readonly_fields = ("previous_quantity", "new_quantity", "created_by", "created_at")


@admin.register(VendorSale)
class VendorSaleAdmin(admin.ModelAdmin):
    list_display = ("vendor", "product", "quantity", "unit_price", "total_amount", "sold_at")
    list_filter = ("sold_at",)
    search_fields = ("vendor__name", "product__name", "buyer_contact")
    readonly_fields = ("total_amount",)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(Locality)
class LocalityAdmin(admin.ModelAdmin):
    list_display = ("name", "region", "latitude", "longitude")
    list_filter = ("region",)
    search_fields = ("name", "region__name")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "unit")
    list_filter = ("category",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


class VendorProductInline(admin.TabularInline):
    model = VendorProduct
    extra = 1


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor_type", "locality", "region", "approval_status", "is_verified", "is_active")
    list_filter = ("approval_status", "vendor_type", "region", "is_verified", "is_active")
    search_fields = ("name", "address", "phone", "locality__name", "owner__username")
    readonly_fields = ("approved_by", "approved_at")
    actions = ("approve_vendors", "reject_vendors")
    inlines = (VendorProductInline,)

    @admin.action(description="Approuver les vendeurs sélectionnés")
    def approve_vendors(self, request, queryset):
        updated = queryset.update(
            approval_status=Vendor.ApprovalStatus.APPROVED,
            is_verified=True,
            is_active=True,
            approved_by=request.user,
            approved_at=timezone.now(),
            rejection_reason="",
        )
        self.message_user(request, f"{updated} vendeur(s) approuvé(s).")

    @admin.action(description="Rejeter les vendeurs sélectionnés")
    def reject_vendors(self, request, queryset):
        updated = queryset.update(
            approval_status=Vendor.ApprovalStatus.REJECTED,
            is_verified=False,
            is_active=False,
            approved_by=None,
            approved_at=None,
        )
        self.message_user(request, f"{updated} vendeur(s) rejeté(s).")


@admin.register(VendorProduct)
class VendorProductAdmin(admin.ModelAdmin):
    list_display = ("vendor", "product", "quantity_available", "is_available", "updated_at")
    list_filter = ("is_available", "product__category")
    search_fields = ("vendor__name", "product__name")


@admin.register(NotificationDevice)
class NotificationDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "is_active", "updated_at")
    list_filter = ("platform", "is_active")
    search_fields = ("user__username", "token")
    readonly_fields = ("token",)


@admin.register(AppNotification)
class AppNotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "recipient", "sender_vendor", "is_read", "sent_at")
    list_filter = ("kind", "is_read")
    search_fields = ("title", "body", "recipient__username")


@admin.register(PromotionQuota)
class PromotionQuotaAdmin(admin.ModelAdmin):
    list_display = ("vendor", "month", "sent_count")
    list_filter = ("month",)


@admin.register(BuyerProfile)
class BuyerProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "region", "locality", "culture_profile", "created_at")
    list_filter = ("region", "locality", "culture_profile")
    search_fields = ("full_name", "phone", "email")
    filter_horizontal = ("preferred_categories",)


class ProvidedServiceInline(admin.TabularInline):
    model = ProvidedService
    extra = 1


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "provider_type", "region", "locality", "phone", "is_available", "is_verified", "approval_status")
    list_filter = ("provider_type", "approval_status", "is_verified", "is_available", "region")
    search_fields = ("name", "phone", "description", "locality__name", "region__name")
    inlines = [ProvidedServiceInline]
    actions = ["approve_providers", "reject_providers"]

    @admin.action(description="Approuver les prestataires sélectionnés")
    def approve_providers(self, request, queryset):
        updated = queryset.update(
            approval_status=ServiceProvider.ApprovalStatus.APPROVED,
            is_verified=True,
            is_active=True,
            approved_by=request.user,
            approved_at=timezone.now(),
        )
        self.message_user(request, f"{updated} prestataire(s) approuvé(s).")

    @admin.action(description="Rejeter les prestataires sélectionnés")
    def reject_providers(self, request, queryset):
        updated = queryset.update(
            approval_status=ServiceProvider.ApprovalStatus.REJECTED,
            is_active=False,
            approved_by=None,
            approved_at=None,
        )
        self.message_user(request, f"{updated} prestataire(s) rejeté(s).")


@admin.register(ProvidedService)
class ProvidedServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "provider", "rate", "unit", "is_available", "created_at")
    list_filter = ("is_available", "unit")
    search_fields = ("title", "description", "provider__name")


@admin.register(ServiceProviderReview)
class ServiceProviderReviewAdmin(admin.ModelAdmin):
    list_display = ("provider", "author", "rating", "is_published", "created_at")
    list_filter = ("rating", "is_published")
    search_fields = ("provider__name", "author__username", "comment")


from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class PhoneAccount(models.Model):
    class Role(models.TextChoices):
        BUYER = "buyer", "Acheteur"
        SELLER = "seller", "Vendeur"
        PROVIDER = "provider", "Prestataire"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="phone_account")
    phone_e164 = models.CharField(max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.BUYER)
    phone_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Compte téléphone"
        verbose_name_plural = "Comptes téléphone"

    def __str__(self) -> str:
        return f"{self.phone_e164} ({self.get_role_display()})"


class OtpChallenge(models.Model):
    phone_e164 = models.CharField(max_length=20, db_index=True)
    role = models.CharField(max_length=20, choices=PhoneAccount.Role.choices, default=PhoneAccount.Role.BUYER)
    provider = models.CharField(max_length=40, default="console")
    provider_reference = models.CharField(max_length=180, blank=True)
    code_hash = models.CharField(max_length=128, blank=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)
    last_sent_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["phone_e164", "created_at"])]
        verbose_name = "Défi OTP"
        verbose_name_plural = "Défis OTP"

    def __str__(self) -> str:
        return f"OTP {self.phone_e164} — {self.created_at:%Y-%m-%d %H:%M}"


class EmailChallenge(models.Model):
    email = models.EmailField(db_index=True)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email", "created_at"])]
        verbose_name = "Défi e-mail"
        verbose_name_plural = "Défis e-mail"


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        SUCCESS = "success", "Réussi"
        FAILED = "failed", "Échoué"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments")
    reference = models.CharField(max_length=120, unique=True)
    amount = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=8, default="XOF")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    channel = models.CharField(max_length=40, blank=True)
    paystack_transaction_id = models.CharField(max_length=80, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "status"])]
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"


class SellerSubscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expirée"
        CANCELLED = "cancelled", "Annulée"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seller_subscription")
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-ends_at"]
        verbose_name = "Abonnement vendeur"
        verbose_name_plural = "Abonnements vendeurs"

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE and self.ends_at > timezone.now()


class Region(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.SlugField(max_length=40, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Région"
        verbose_name_plural = "Régions"

    def __str__(self) -> str:
        return self.name


class Locality(models.Model):
    name = models.CharField(max_length=120)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="localities")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["region", "name"], name="unique_locality_by_region")
        ]
        verbose_name = "Localité"
        verbose_name_plural = "Localités"

    def __str__(self) -> str:
        return f"{self.name} ({self.region.name})"


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=40, default="unité")

    class Meta:
        ordering = ["name"]
        verbose_name = "Produit"
        verbose_name_plural = "Produits"

    def __str__(self) -> str:
        return self.name


class Vendor(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendor_profiles",
    )

    class VendorType(models.TextChoices):
        WHOLESALER = "grossiste", "Grossiste"
        RETAILER = "détaillant", "Détaillant"
        COOPERATIVE = "coopérative", "Coopérative"

    name = models.CharField(max_length=180)
    vendor_type = models.CharField(max_length=30, choices=VendorType.choices)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="vendors")
    locality = models.ForeignKey(Locality, on_delete=models.PROTECT, related_name="vendors")
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=30)
    whatsapp_number = models.CharField(max_length=30, blank=True)
    opening_hours = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "En attente"
        APPROVED = "approved", "Approuvé"
        REJECTED = "rejected", "Rejeté"

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    approval_status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="vendeurs_valides")
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["region", "locality"]),
            models.Index(fields=["vendor_type", "is_active"]),
        ]
        verbose_name = "Vendeur"
        verbose_name_plural = "Vendeurs"

    def __str__(self) -> str:
        return self.name


class VendorProduct(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="stock_items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="vendor_stocks")
    quantity_available = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    alert_threshold = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    price_note = models.CharField(max_length=120, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    is_available = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product__name"]
        constraints = [
            models.UniqueConstraint(fields=["vendor", "product"], name="unique_product_per_vendor")
        ]
        verbose_name = "Stock vendeur"
        verbose_name_plural = "Stocks vendeurs"

    def __str__(self) -> str:
        return f"{self.vendor.name} — {self.product.name}"


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        IN = "in", "Entrée"
        OUT = "out", "Sortie"
        ADJUSTMENT = "adjustment", "Correction"

    stock = models.ForeignKey(VendorProduct, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    previous_quantity = models.PositiveIntegerField(default=0)
    new_quantity = models.PositiveIntegerField(default=0)
    reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["stock", "created_at"])]
        verbose_name = "Mouvement de stock"
        verbose_name_plural = "Mouvements de stock"


class VendorFavorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_vendors")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="favorite_by_users")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "vendor"], name="unique_vendor_favorite")]


class ProductFavorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_products")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="favorite_by_users")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="unique_product_favorite")]


class VendorReview(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vendor_reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["vendor", "author"], name="unique_vendor_review_by_author")]
        indexes = [models.Index(fields=["vendor", "is_published"])]


class BuyerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="buyer_profile",
    )
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="buyer_profiles")
    locality = models.ForeignKey(Locality, on_delete=models.PROTECT, related_name="buyer_profiles")
    preferred_categories = models.ManyToManyField(Category, blank=True, related_name="buyer_profiles")
    culture_profile = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Profil acheteur"
        verbose_name_plural = "Profils acheteurs"

    def __str__(self) -> str:
        return self.full_name or f"Acheteur #{self.pk}"


class NotificationDevice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_devices")
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Appareil de notification"
        verbose_name_plural = "Appareils de notification"


class AppNotification(models.Model):
    class Kind(models.TextChoices):
        PROMOTION = "promotion", "Promotion"
        ADVICE = "advice", "Conseil agricole"
        STOCK = "stock", "Stock"
        SUBSCRIPTION = "subscription", "Abonnement"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="app_notifications")
    sender_vendor = models.ForeignKey("Vendor", on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_notifications")
    kind = models.CharField(max_length=30, choices=Kind.choices, default=Kind.ADVICE)
    title = models.CharField(max_length=180)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"


class VendorSale(models.Model):
    vendor = models.ForeignKey("Vendor", on_delete=models.CASCADE, related_name="sales")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="vendor_sales")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.PositiveBigIntegerField(default=0)
    buyer_contact = models.CharField(max_length=80, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    sold_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sold_at"]
        indexes = [models.Index(fields=["vendor", "sold_at"])]
        verbose_name = "Vente vendeur"
        verbose_name_plural = "Ventes vendeurs"

    @property
    def total_amount(self):
        return self.quantity * self.unit_price


class PromotionQuota(models.Model):
    vendor = models.OneToOneField("Vendor", on_delete=models.CASCADE, related_name="promotion_quota")
    month = models.DateField()
    sent_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Quota promotion"
        verbose_name_plural = "Quotas promotions"
        constraints = [models.UniqueConstraint(fields=["vendor", "month"], name="unique_vendor_promotion_month")]


class ServiceProvider(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_provider_profiles",
    )

    class ProviderType(models.TextChoices):
        MECANISATION = "mecanisation", "Mécanisation & Labour"
        LOCATION = "location", "Location de matériel & engins"
        TRAITEMENT = "traitement", "Traitement phytosanitaire & Pulvérisation"
        TRANSPORT = "transport", "Transport & Logistique de récolte"
        IRRIGATION = "irrigation", "Forage & Irrigation"
        MAIN_DOEUVRE = "main_doeuvre", "Main d’œuvre & Récolte"
        CONSEIL = "conseil", "Conseil technique & Analyse de sol"
        AUTRE = "autre", "Autre service agricole"

    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "En attente"
        APPROVED = "approved", "Approuvé"
        REJECTED = "rejected", "Rejeté"

    name = models.CharField(max_length=180)
    provider_type = models.CharField(max_length=30, choices=ProviderType.choices, default=ProviderType.MECANISATION)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="service_providers")
    locality = models.ForeignKey(Locality, on_delete=models.PROTECT, related_name="service_providers")
    intervention_zone = models.CharField(max_length=255, blank=True, help_text="Zones ou localités d’intervention")
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=30)
    whatsapp_number = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True, help_text="Présentation du prestataire, machines et matériels disponibles")
    years_of_experience = models.PositiveSmallIntegerField(default=1)
    is_available = models.BooleanField(default=True, help_text="Disponible pour de nouvelles interventions")
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    approval_status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.APPROVED)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="prestataires_valides")
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["region", "locality"]),
            models.Index(fields=["provider_type", "is_active"]),
        ]
        verbose_name = "Prestataire de services"
        verbose_name_plural = "Prestataires de services"

    def __str__(self) -> str:
        return f"{self.name} ({self.get_provider_type_display()})"


class ProvidedService(models.Model):
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name="services")
    title = models.CharField(max_length=180, help_text="Ex. Labour profond au tracteur")
    rate = models.PositiveBigIntegerField(default=0, help_text="Tarif indicatif en FCFA")
    unit = models.CharField(max_length=60, default="par hectare", help_text="Ex. par hectare, par jour, par heure, par voyage")
    description = models.TextField(blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "Prestation proposée"
        verbose_name_plural = "Prestations proposées"

    def __str__(self) -> str:
        return f"{self.title} — {self.provider.name}"


class ServiceProviderReview(models.Model):
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="provider_reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["provider", "author"], name="unique_provider_review_by_author")]
        indexes = [models.Index(fields=["provider", "is_published"])]
        verbose_name = "Avis prestataire"
        verbose_name_plural = "Avis prestataires"

    def __str__(self) -> str:
        return f"Avis sur {self.provider.name} ({self.rating}/5)"

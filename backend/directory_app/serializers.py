from rest_framework import serializers

from .models import (
    BuyerProfile,
    Category,
    Locality,
    Product,
    Region,
    Vendor,
    VendorProduct,
    VendorSale,
    StockMovement,
    VendorFavorite,
    ProductFavorite,
    VendorReview,
    ServiceProvider,
    ProvidedService,
    ServiceProviderReview,
)


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ["id", "name", "code"]


class LocalitySerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)

    class Meta:
        model = Locality
        fields = ["id", "name", "region", "region_name", "latitude", "longitude"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "category_name",
            "category_slug",
            "description",
            "unit",
        ]


class VendorProductSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    availability_label = serializers.SerializerMethodField()

    class Meta:
        model = VendorProduct
        fields = [
            "id",
            "product",
            "quantity_available",
            "alert_threshold",
            "price_note",
            "notes",
            "is_available",
            "availability_label",
            "updated_at",
        ]

    def get_availability_label(self, obj: VendorProduct) -> str:
        if not obj.is_available or obj.quantity_available == 0:
            return "Rupture de stock"
        if obj.quantity_available < 10:
            return "Stock limité"
        return "Disponible"


class VendorFavoriteSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    class Meta:
        model = VendorFavorite
        fields = ["id", "vendor", "vendor_name", "created_at"]
        read_only_fields = ["created_at"]


class ProductFavoriteSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = ProductFavorite
        fields = ["id", "product", "product_name", "created_at"]
        read_only_fields = ["created_at"]


class VendorReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = VendorReview
        fields = ["id", "vendor", "author_name", "rating", "comment", "is_published", "created_at", "updated_at"]
        read_only_fields = ["author_name", "is_published", "created_at", "updated_at"]


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="stock.product.name", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id", "stock", "product_name", "movement_type", "quantity",
            "previous_quantity", "new_quantity", "reason", "created_at",
        ]
        read_only_fields = ["previous_quantity", "new_quantity", "created_at"]


class VendorListSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)
    locality_name = serializers.CharField(source="locality.name", read_only=True)
    product_names = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    total_available_stock = serializers.SerializerMethodField()
    is_pro = serializers.SerializerMethodField()
    pro_badge = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Vendor
        fields = [
            "id",
            "owner",
            "name",
            "vendor_type",
            "region",
            "region_name",
            "locality",
            "locality_name",
            "address",
            "phone",
            "whatsapp_number",
            "opening_hours",
            "latitude",
            "longitude",
            "is_verified",
            "approval_status",
            "approved_at",
            "rejection_reason",
            "product_names",
            "categories",
            "total_available_stock",
            "is_pro",
            "pro_badge",
            "average_rating",
            "review_count",
        ]
        read_only_fields = ["owner", "is_verified", "approval_status", "approved_at", "approved_by", "rejection_reason"]

    def get_product_names(self, obj: Vendor) -> list[str]:
        return list(
            obj.stock_items.filter(is_available=True, quantity_available__gt=0)
            .values_list("product__name", flat=True)
        )

    def get_categories(self, obj: Vendor) -> list[str]:
        return list(
            obj.stock_items.filter(is_available=True, quantity_available__gt=0)
            .values_list("product__category__name", flat=True)
            .distinct()
        )

    def get_is_pro(self, obj: Vendor) -> bool:
        subscription = getattr(obj.owner, "seller_subscription", None) if obj.owner_id else None
        return bool(subscription and subscription.is_active)

    def get_pro_badge(self, obj: Vendor) -> str:
        return "Vendeur Pro" if self.get_is_pro(obj) else "Vendeur gratuit"

    def get_total_available_stock(self, obj: Vendor) -> int:
        return sum(
            item.quantity_available
            for item in obj.stock_items.all()
            if item.is_available
        )


class VendorDetailSerializer(VendorListSerializer):
    stock_items = VendorProductSerializer(many=True, read_only=True)

    class Meta(VendorListSerializer.Meta):
        fields = VendorListSerializer.Meta.fields + ["stock_items", "created_at", "updated_at"]


class BuyerProfileSerializer(serializers.ModelSerializer):
    preferred_categories = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Category.objects.all(),
        required=False,
    )
    region_name = serializers.CharField(source="region.name", read_only=True)
    locality_name = serializers.CharField(source="locality.name", read_only=True)

    def validate(self, attrs):
        region = attrs.get("region", self.instance.region if self.instance else None)
        locality = attrs.get("locality", self.instance.locality if self.instance else None)
        if region and locality and locality.region_id != region.id:
            raise serializers.ValidationError({"locality": "Cette localité n’appartient pas à la région sélectionnée."})
        return attrs

    class Meta:
        model = BuyerProfile
        fields = [
            "id",
            "user",
            "full_name",
            "phone",
            "email",
            "region",
            "region_name",
            "locality",
            "locality_name",
            "preferred_categories",
            "culture_profile",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user"]


class VendorSaleSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    total_amount = serializers.IntegerField(read_only=True)

    class Meta:
        model = VendorSale
        fields = ["id", "vendor", "product", "product_name", "quantity", "unit_price", "total_amount", "buyer_contact", "notes", "sold_at", "created_at"]
        read_only_fields = ["id", "product_name", "total_amount", "created_at"]


class VendorProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorProduct
        fields = [
            "id",
            "vendor",
            "product",
            "quantity_available",
            "price_note",
            "notes",
            "is_available",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class ProvidedServiceSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source="provider.name", read_only=True)

    class Meta:
        model = ProvidedService
        fields = ["id", "provider", "provider_name", "title", "rate", "unit", "description", "is_available", "created_at", "updated_at"]
        read_only_fields = ["id", "provider_name", "created_at", "updated_at"]


class ServiceProviderReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = ServiceProviderReview
        fields = ["id", "provider", "author_name", "rating", "comment", "is_published", "created_at", "updated_at"]
        read_only_fields = ["id", "author_name", "is_published", "created_at", "updated_at"]


class ServiceProviderListSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)
    locality_name = serializers.CharField(source="locality.name", read_only=True)
    provider_type_display = serializers.CharField(source="get_provider_type_display", read_only=True)
    service_titles = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ServiceProvider
        fields = [
            "id", "owner", "name", "provider_type", "provider_type_display",
            "region", "region_name", "locality", "locality_name",
            "intervention_zone", "address", "phone", "whatsapp_number",
            "description", "years_of_experience", "is_available", "is_verified",
            "approval_status", "service_titles", "average_rating", "review_count",
            "latitude", "longitude",
        ]
        read_only_fields = ["owner", "is_verified", "approval_status", "approved_at", "approved_by", "rejection_reason"]

    def get_service_titles(self, obj: ServiceProvider) -> list[str]:
        return list(obj.services.filter(is_available=True).values_list("title", flat=True)[:5])


class ServiceProviderDetailSerializer(ServiceProviderListSerializer):
    services = ProvidedServiceSerializer(many=True, read_only=True)
    reviews = ServiceProviderReviewSerializer(many=True, read_only=True)

    class Meta(ServiceProviderListSerializer.Meta):
        fields = ServiceProviderListSerializer.Meta.fields + ["services", "reviews", "created_at", "updated_at"]


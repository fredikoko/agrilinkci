from datetime import timedelta

from django.db import transaction
from django.db.models import Avg, Case, Count, ExpressionWrapper, F, IntegerField, Prefetch, Q, Sum, When
from django.db.models.functions import TruncDate
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.views import APIView

from .auth_permissions import IsActiveSellerSubscriber, IsVerifiedBuyer, IsVerifiedSeller
from .models import SellerSubscription
from .filters import VendorFilter
from .models import (
    BuyerProfile, Category, Locality, PhoneAccount, Product, Region, Vendor,
    VendorProduct, VendorSale, StockMovement, VendorFavorite, ProductFavorite, VendorReview,
    ServiceProvider, ProvidedService, ServiceProviderReview,
)

from .serializers import (
    BuyerProfileSerializer,
    CategorySerializer,
    LocalitySerializer,
    ProductSerializer,
    RegionSerializer,
    VendorDetailSerializer,
    VendorListSerializer,
    VendorProductWriteSerializer,
    VendorSaleSerializer,
    StockMovementSerializer,
    VendorFavoriteSerializer,
    ProductFavoriteSerializer,
    VendorReviewSerializer,
    ProvidedServiceSerializer,
    ServiceProviderListSerializer,
    ServiceProviderDetailSerializer,
    ServiceProviderReviewSerializer,
)


from django.core.cache import cache

class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer

    def list(self, request, *args, **kwargs):
        cache_key = "regions_list_all"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=86400)
        return response

    @action(detail=True, methods=["get"])
    def localities(self, request, pk=None):
        region = self.get_object()
        serializer = LocalitySerializer(region.localities.all(), many=True)
        return Response(serializer.data)


class LocalityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Locality.objects.select_related("region").all()
    serializer_class = LocalitySerializer
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["name", "region__name"]
    ordering_fields = ["name", "region__name"]


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ["name"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ["name"]

    def list(self, request, *args, **kwargs):
        search = request.query_params.get("search", "").strip()
        if not search:
            cache_key = "categories_list_all"
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data)
        response = super().list(request, *args, **kwargs)
        if not search:
            cache.set("categories_list_all", response.data, timeout=86400)
        return response


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.select_related("category").all()
    serializer_class = ProductSerializer
    search_fields = ["name", "description", "category__name"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ["name", "category__name"]



class VendorViewSet(viewsets.ModelViewSet):
    queryset = (
        Vendor.objects.filter(is_active=True)
        .select_related("region", "locality")
        .prefetch_related(
            Prefetch(
                "stock_items",
                queryset=VendorProduct.objects.select_related("product", "product__category"),
            )
        )
    )
    filterset_class = VendorFilter
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = [
        "name",
        "address",
        "locality__name",
        "region__name",
        "stock_items__product__name",
    ]
    ordering_fields = ["name", "locality__name", "region__name", "is_verified"]
    ordering = ["-pro_priority", "name"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ["list", "retrieve", "suggestions"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsVerifiedSeller()]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_authenticated and (
            self.action in ["update", "partial_update", "destroy"]
            or self.request.query_params.get("mine") == "true"
        ):
            queryset = queryset.filter(owner=self.request.user)
        else:
            queryset = queryset.filter(approval_status=Vendor.ApprovalStatus.APPROVED, is_verified=True)

        near_lat = self.request.query_params.get("near_lat")
        near_lng = self.request.query_params.get("near_lng")
        radius_km = self.request.query_params.get("radius_km")
        if near_lat and near_lng:
            try:
                lat = float(near_lat)
                lng = float(near_lng)
                r = float(radius_km) if radius_km else 25.0
                d_lat = r / 111.0
                import math
                d_lng = r / (111.0 * max(math.cos(math.radians(lat)), 0.01))
                queryset = queryset.filter(
                    Q(latitude__range=(lat - d_lat, lat + d_lat), longitude__range=(lng - d_lng, lng + d_lng))
                    | Q(locality__latitude__range=(lat - d_lat, lat + d_lat), locality__longitude__range=(lng - d_lng, lng + d_lng))
                )
            except (ValueError, TypeError):
                pass

        return queryset.annotate(
            average_rating=Avg("reviews__rating", filter=Q(reviews__is_published=True)),
            review_count=Count("reviews", filter=Q(reviews__is_published=True), distinct=True),
            pro_priority=Case(
                When(owner__seller_subscription__status=SellerSubscription.Status.ACTIVE,
                     owner__seller_subscription__ends_at__gt=timezone.now(), then=1),
                default=0,
                output_field=IntegerField(),
            )
        )


    def perform_create(self, serializer):
        user = self.request.user
        account = getattr(user, "phone_account", None)
        buyer_profile = getattr(user, "buyer_profile", None)

        extra_kwargs = {
            "owner": user,
            "approval_status": Vendor.ApprovalStatus.PENDING,
            "is_verified": False,
            "is_active": True,
        }

        if not serializer.validated_data.get("phone"):
            phone_fallback = (account.phone_e164 if account else "") or (buyer_profile.phone if buyer_profile else "")
            if phone_fallback:
                extra_kwargs["phone"] = phone_fallback

        if not serializer.validated_data.get("name") and buyer_profile and buyer_profile.full_name:
            extra_kwargs["name"] = buyer_profile.full_name

        if buyer_profile:
            if not serializer.validated_data.get("region") and buyer_profile.region:
                extra_kwargs["region"] = buyer_profile.region
            if not serializer.validated_data.get("locality") and buyer_profile.locality:
                extra_kwargs["locality"] = buyer_profile.locality

        vendor = serializer.save(**extra_kwargs)

        if account and account.role != PhoneAccount.Role.SELLER:
            account.role = PhoneAccount.Role.SELLER
            account.save(update_fields=["role", "updated_at"])


    def get_serializer_class(self):
        if self.action == "retrieve":
            return VendorDetailSerializer
        return VendorListSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).distinct()
        near_lat = request.query_params.get("near_lat")
        near_lng = request.query_params.get("near_lng")
        radius_km = request.query_params.get("radius_km", 50)
        if near_lat and near_lng:
            try:
                lat1 = float(near_lat)
                lng1 = float(near_lng)
                max_dist = float(radius_km)
                import math
                filtered_ids = []
                for v in queryset:
                    v_lat = float(v.latitude) if v.latitude else (float(v.locality.latitude) if v.locality and v.locality.latitude else None)
                    v_lng = float(v.longitude) if v.longitude else (float(v.locality.longitude) if v.locality and v.locality.longitude else None)
                    if v_lat is not None and v_lng is not None:
                        dlat = math.radians(v_lat - lat1)
                        dlng = math.radians(v_lng - lng1)
                        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(v_lat)) * math.sin(dlng / 2)**2
                        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                        dist = 6371.0 * c
                        if dist <= max_dist:
                            filtered_ids.append(v.id)
                queryset = queryset.filter(id__in=filtered_ids)
            except (ValueError, TypeError):
                pass
        ordering = request.query_params.get("ordering", "")
        if ordering.lstrip("-") == "stock":
            queryset = queryset.annotate(
                stock_total=Sum("stock_items__quantity_available")
            ).order_by("-stock_total" if ordering.startswith("-") else "stock_total")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        if ordering.lstrip("-") != "stock":
            queryset = queryset.order_by("-pro_priority", "name")
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def suggestions(self, request):
        """Retourne d'abord les vendeurs de la localité, puis ceux de la région."""
        locality_id = request.query_params.get("locality")
        region_id = request.query_params.get("region")
        queryset = self.filter_queryset(self.get_queryset()).distinct()

        if locality_id:
            local = queryset.filter(locality_id=locality_id)
            if region_id:
                nearby = queryset.filter(region_id=region_id).exclude(locality_id=locality_id)
                queryset = local.union(nearby, all=True)
            else:
                queryset = local
        elif region_id:
            queryset = queryset.filter(region_id=region_id)

        queryset = queryset.order_by("-pro_priority", "name")
        serializer = VendorListSerializer(queryset[:50], many=True)
        return Response(serializer.data)


class VendorProductViewSet(viewsets.ModelViewSet):
    queryset = VendorProduct.objects.select_related("vendor", "product", "product__category").all()
    serializer_class = VendorProductWriteSerializer

    def get_permissions(self):
        if self.action == "list":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsVerifiedSeller()]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_authenticated and (
            self.action in ["retrieve", "update", "partial_update", "destroy"]
            or self.request.query_params.get("mine") == "true"
        ):
            return queryset.filter(vendor__owner=self.request.user)
        return queryset

    def perform_create(self, serializer):
        vendor = serializer.validated_data["vendor"]
        if vendor.owner_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous ne pouvez gérer que le stock de vos propres vendeurs.")
        subscription = getattr(self.request.user, "seller_subscription", None)
        if not (subscription and subscription.is_active):
            if vendor.stock_items.values("product_id").distinct().count() >= 10:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"product": "Le forfait gratuit est limité à 10 produits. Passez à Vendeur Pro pour un catalogue illimité."})
        serializer.save()

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["vendor__name", "product__name"]
    ordering_fields = ["updated_at", "quantity_available"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]


class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.select_related("stock", "stock__vendor", "stock__product").all()
    serializer_class = StockMovementSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        return [permissions.IsAuthenticated(), IsVerifiedSeller()]

    def get_queryset(self):
        return self.queryset.filter(stock__vendor__owner=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        movement = serializer.validated_data["movement_type"]
        quantity = serializer.validated_data["quantity"]
        stock = VendorProduct.objects.select_for_update().get(pk=serializer.validated_data["stock"].pk)
        if stock.vendor.owner_id != self.request.user.id:
            raise PermissionDenied("Vous ne pouvez modifier que votre propre stock.")
        previous = stock.quantity_available
        if movement == StockMovement.MovementType.IN:
            new_quantity = previous + quantity
        elif movement == StockMovement.MovementType.OUT:
            new_quantity = previous - quantity
            if new_quantity < 0:
                raise ValidationError({"quantity": "Stock insuffisant pour cette sortie."})
        else:
            new_quantity = quantity
        stock.quantity_available = new_quantity
        stock.is_available = new_quantity > 0
        stock.save(update_fields=["quantity_available", "is_available", "updated_at"])
        serializer.save(previous_quantity=previous, new_quantity=new_quantity, created_by=self.request.user)


class VendorFavoriteViewSet(viewsets.ModelViewSet):
    queryset = VendorFavorite.objects.select_related("vendor").all()
    serializer_class = VendorFavoriteSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        vendor = serializer.validated_data["vendor"]
        if not (vendor.approval_status == Vendor.ApprovalStatus.APPROVED and vendor.is_verified and vendor.is_active):
            raise ValidationError({"vendor": "Ce vendeur n’est pas disponible publiquement."})
        serializer.save(user=self.request.user)


class ProductFavoriteViewSet(viewsets.ModelViewSet):
    queryset = ProductFavorite.objects.select_related("product").all()
    serializer_class = ProductFavoriteSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class VendorReviewViewSet(viewsets.ModelViewSet):
    queryset = VendorReview.objects.select_related("vendor", "author").filter(is_published=True)
    serializer_class = VendorReviewSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = self.queryset
        if self.request.user.is_authenticated and self.action in ["update", "partial_update", "destroy"]:
            return queryset.filter(author=self.request.user)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vendor = serializer.validated_data["vendor"]
        if not (vendor.approval_status == Vendor.ApprovalStatus.APPROVED and vendor.is_verified and vendor.is_active):
            raise ValidationError({"vendor": "Ce vendeur n’est pas disponible publiquement."})
        review, created = VendorReview.objects.update_or_create(
            vendor=vendor,
            author=request.user,
            defaults={
                "rating": serializer.validated_data["rating"],
                "comment": serializer.validated_data.get("comment", ""),
                "is_published": True,
            },
        )
        output_serializer = self.get_serializer(review)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(output_serializer.data, status=status_code)



class VendorSaleViewSet(viewsets.ModelViewSet):
    queryset = VendorSale.objects.select_related("vendor", "product").all()
    serializer_class = VendorSaleSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["sold_at", "quantity", "unit_price"]
    ordering = ["-sold_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        return [permissions.IsAuthenticated(), IsVerifiedSeller()]

    def get_queryset(self):
        return super().get_queryset().filter(vendor__owner=self.request.user)

    def perform_create(self, serializer):
        vendor = serializer.validated_data["vendor"]
        if vendor.owner_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous ne pouvez enregistrer que les ventes de votre propre vendeur.")
        serializer.save()


class VendorAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerifiedSeller]

    def get(self, request):
        vendor = Vendor.objects.filter(owner=request.user, is_active=True).first()
        if not vendor:
            return Response({"detail": "Aucune fiche vendeur active."}, status=status.HTTP_404_NOT_FOUND)
        try:
            days = min(max(int(request.query_params.get("days", 30)), 1), 365)
        except (TypeError, ValueError):
            days = 30
        start = timezone.now() - timedelta(days=days)
        sales = VendorSale.objects.filter(vendor=vendor, sold_at__gte=start).select_related("product")
        total_quantity = sum(item.quantity for item in sales)
        total_revenue = sum(item.total_amount for item in sales)
        top_products = {}
        for item in sales:
            entry = top_products.setdefault(item.product_id, {"product_id": item.product_id, "product_name": item.product.name, "quantity": 0, "revenue": 0})
            entry["quantity"] += item.quantity
            entry["revenue"] += item.total_amount
        daily = sales.annotate(
            day=TruncDate("sold_at"),
            line_total=F("quantity") * F("unit_price"),
        ).values("day").annotate(
            sales_count=Count("id"),
            quantity=Sum("quantity"),
            revenue=Sum("line_total"),
        ).order_by("day")

        return Response({
            "vendor": {"id": vendor.id, "name": vendor.name},
            "period_days": days,
            "orders_count": sales.count(),
            "sales_count": sales.count(),
            "total_quantity": total_quantity,
            "total_revenue": total_revenue,
            "average_sale": round(total_revenue / sales.count()) if sales.count() else 0,
            "top_products": sorted(top_products.values(), key=lambda item: item["revenue"], reverse=True)[:5],
            "daily": [{"day": row["day"], "sales_count": row["sales_count"], "quantity": row["quantity"], "revenue": row["revenue"]} for row in daily],
        })


class BuyerProfileViewSet(viewsets.ModelViewSet):
    queryset = BuyerProfile.objects.select_related("region", "locality").prefetch_related(
        "preferred_categories"
    )
    serializer_class = BuyerProfileSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        return [permissions.IsAuthenticated(), IsVerifiedBuyer()]

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        if BuyerProfile.objects.filter(user=self.request.user).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"detail": "Un profil acheteur existe déjà pour ce compte."})
        account = getattr(self.request.user, "phone_account", None)
        serializer.save(
            user=self.request.user,
            phone=account.phone_e164 if account else "",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ServiceProviderViewSet(viewsets.ModelViewSet):
    queryset = ServiceProvider.objects.select_related("region", "locality", "owner").prefetch_related("services", "reviews").all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "services__title", "locality__name", "region__name", "intervention_zone"]
    ordering_fields = ["name", "created_at", "average_rating", "years_of_experience"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ServiceProviderDetailSerializer
        return ServiceProviderListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_authenticated and (
            self.action in ["update", "partial_update", "destroy"]
            or self.request.query_params.get("mine") == "true"
        ):
            queryset = queryset.filter(owner=self.request.user)
        else:
            queryset = queryset.filter(is_active=True, approval_status=ServiceProvider.ApprovalStatus.APPROVED)

        provider_type = self.request.query_params.get("provider_type")
        if provider_type:
            queryset = queryset.filter(provider_type=provider_type)

        region_id = self.request.query_params.get("region")
        if region_id:
            queryset = queryset.filter(region_id=region_id)

        locality_id = self.request.query_params.get("locality")
        if locality_id:
            queryset = queryset.filter(locality_id=locality_id)

        available_only = self.request.query_params.get("available")
        if available_only == "true":
            queryset = queryset.filter(is_available=True)

        return queryset.annotate(
            average_rating=Avg("reviews__rating", filter=Q(reviews__is_published=True)),
            review_count=Count("reviews", filter=Q(reviews__is_published=True), distinct=True),
        )

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        account = getattr(user, "phone_account", None) if user else None
        provider = serializer.save(
            owner=user,
            approval_status=ServiceProvider.ApprovalStatus.APPROVED,
            is_verified=True,
            is_active=True,
        )
        if account and account.role != PhoneAccount.Role.PROVIDER:
            account.role = PhoneAccount.Role.PROVIDER
            account.save(update_fields=["role", "updated_at"])

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def my_profile(self, request):
        provider = ServiceProvider.objects.filter(owner=request.user).first()
        if not provider:
            return Response({"detail": "Aucun profil prestataire trouvé."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ServiceProviderDetailSerializer(provider)
        return Response(serializer.data)


class ProvidedServiceViewSet(viewsets.ModelViewSet):
    queryset = ProvidedService.objects.select_related("provider").all()
    serializer_class = ProvidedServiceSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "description", "provider__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        provider_id = self.request.query_params.get("provider")
        if provider_id:
            queryset = queryset.filter(provider_id=provider_id)
        if self.request.user.is_authenticated and self.request.query_params.get("mine") == "true":
            queryset = queryset.filter(provider__owner=self.request.user)
        return queryset

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            provider = ServiceProvider.objects.filter(owner=self.request.user).first()
            if provider and not serializer.validated_data.get("provider"):
                serializer.save(provider=provider)
                return
        serializer.save()


class ServiceProviderReviewViewSet(viewsets.ModelViewSet):
    queryset = ServiceProviderReview.objects.select_related("provider", "author").all()
    serializer_class = ServiceProviderReviewSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_published=True)
        provider_id = self.request.query_params.get("provider")
        if provider_id:
            queryset = queryset.filter(provider_id=provider_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, is_published=True)


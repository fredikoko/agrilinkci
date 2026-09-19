from django.db.models import Case, IntegerField, Prefetch, Q, Value, When
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth_permissions import IsVerifiedBuyer
from .models import BuyerProfile, Locality, Vendor, VendorProduct
from .serializers import BuyerProfileSerializer, VendorListSerializer


class BuyerProfileMeView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerifiedBuyer]

    def get(self, request):
        try:
            profile = request.user.buyer_profile
        except BuyerProfile.DoesNotExist:
            return Response({"configured": False, "profile": None})
        return Response({"configured": True, "profile": BuyerProfileSerializer(profile).data})

    def put(self, request):
        return self._save(request)

    def patch(self, request):
        return self._save(request, partial=True)

    def _save(self, request, partial=False):
        try:
            profile = request.user.buyer_profile
        except BuyerProfile.DoesNotExist:
            profile = None
        serializer = BuyerProfileSerializer(profile, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        account = getattr(request.user, "phone_account", None)
        defaults = dict(serializer.validated_data)
        preferred_categories = defaults.pop("preferred_categories", None)
        defaults["user"] = request.user
        submitted_phone = defaults.get("phone") or ""
        defaults["phone"] = (account.phone_e164 or submitted_phone) if account else submitted_phone
        submitted_email = defaults.get("email") or ""
        if account and submitted_email:
            account.email = submitted_email
            account.save(update_fields=["email", "updated_at"])
        if submitted_email and not request.user.email:
            request.user.email = submitted_email
            request.user.save(update_fields=["email"])
        created = profile is None
        if created:
            if not defaults.get("region") or not defaults.get("locality"):
                return Response(
                    {"detail": "La région et la localité sont obligatoires pour créer le profil."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            profile = BuyerProfile.objects.create(**defaults)
        else:
            for key, value in defaults.items():
                if key != "user" and key != "preferred_categories":
                    setattr(profile, key, value)
            profile.save()
        if preferred_categories is not None:
            profile.preferred_categories.set(preferred_categories)
        return Response(
            {"configured": True, "profile": BuyerProfileSerializer(profile).data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class BuyerRecommendationsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerifiedBuyer]

    def get(self, request):
        try:
            profile = request.user.buyer_profile
        except BuyerProfile.DoesNotExist:
            return Response(
                {"configured": False, "detail": "Configurez votre région et votre localité pour recevoir des recommandations."},
                status=status.HTTP_200_OK,
            )

        vendors = (
            Vendor.objects.filter(
                is_active=True,
            )
            .filter(Q(locality=profile.locality) | Q(region=profile.region))
            .select_related("region", "locality")
            .prefetch_related(
                Prefetch(
                    "stock_items",
                    queryset=VendorProduct.objects.select_related("product", "product__category").filter(
                        is_available=True,
                        quantity_available__gt=0,
                    ),
                )
            )
            .annotate(
                location_priority=Case(
                    When(locality=profile.locality, then=Value(0)),
                    When(region=profile.region, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
            .order_by("location_priority", "-is_verified", "name")
            .distinct()
        )
        serializer = VendorListSerializer(vendors, many=True)
        return Response(
            {
                "configured": True,
                "location": {
                    "region": profile.region.name,
                    "locality": profile.locality.name,
                },
                "results": serializer.data,
            }
        )

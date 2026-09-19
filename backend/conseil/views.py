from django.db.models import Avg, Count, F, Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Alerte, AlerteLue, Article, ArticleFavori, ArticleReview, CategorieConseil, ConseilSubscription, FreeArticleUsage
from .payment_service import ConseilPaymentError, initialize_conseil_payment, verify_conseil_payment
from .serializers import (
    AlerteSerializer,
    ArticleDetailSerializer,
    ArticleFavoriSerializer,
    ArticleListSerializer,
    ArticleReviewSerializer,
    CategorieConseilSerializer,
)


class CategorieConseilViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CategorieConseil.objects.all()
    serializer_class = CategorieConseilSerializer
    permission_classes = [permissions.AllowAny]


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        queryset = (
            Article.objects.filter(est_publie=True)
            .select_related("categorie")
            .prefetch_related("produits_associes", "reviews")
            .annotate(
                average_rating=Avg("reviews__rating"),
                review_count=Count("reviews", distinct=True),
            )
        )
        categorie = self.request.query_params.get("categorie")
        culture = self.request.query_params.get("culture")
        niveau = self.request.query_params.get("niveau")
        search = self.request.query_params.get("search", "").strip()
        if categorie:
            categorie = categorie.strip()
            if categorie.isdigit():
                queryset = queryset.filter(categorie_id=int(categorie))
            else:
                queryset = queryset.filter(categorie__nom__iexact=categorie)
        if culture:
            queryset = queryset.filter(culture__icontains=culture)
        if niveau:
            queryset = queryset.filter(niveau=niveau.upper())
        if search:
            queryset = queryset.filter(Q(titre__icontains=search) | Q(resume__icontains=search) | Q(contenu__icontains=search))
        return queryset


    def get_serializer_class(self):
        return ArticleDetailSerializer if self.action == "retrieve" else ArticleListSerializer

    def retrieve(self, request, *args, **kwargs):
        article = self.get_object()
        if article.est_premium:
            subscription = getattr(request.user, "conseil_subscription", None) if request.user.is_authenticated else None
            if not (subscription and subscription.is_active):
                msg = "Abonnez-vous à Conseil Pro pour lire cet article premium." if request.user.is_authenticated else "Connectez-vous et abonnez-vous à Conseil Pro pour lire cet article."
                return Response({
                    "detail": msg,
                    "premium": True,
                    "subscription_required": True,
                }, status=status.HTTP_402_PAYMENT_REQUIRED)

        Article.objects.filter(pk=article.pk).update(nombre_vues=F("nombre_vues") + 1)
        article.refresh_from_db()
        return Response(self.get_serializer(article).data)


    @action(detail=False, methods=["get"], url_path="epingles")
    def epingles(self, request):
        queryset = self.get_queryset().filter(est_epingle=True)
        return Response(ArticleListSerializer(queryset, many=True, context={"request": request}).data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="recommandes")
    def recommandes(self, request):
        profile = getattr(request.user, "buyer_profile", None)
        queryset = self.get_queryset()
        if profile and profile.culture_profile:
            queryset = queryset.filter(Q(culture__icontains=profile.culture_profile) | Q(culture=""))
        return Response(ArticleListSerializer(queryset[:20], many=True, context={"request": request}).data)


class ArticleFavoriViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleFavoriSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return ArticleFavori.objects.filter(utilisateur=self.request.user).select_related("article__categorie")

    def perform_create(self, serializer):
        article = serializer.validated_data["article"]
        subscription = getattr(self.request.user, "conseil_subscription", None)
        if not (subscription and subscription.is_active) and ArticleFavori.objects.filter(utilisateur=self.request.user).count() >= 3:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"detail": "Le forfait gratuit est limité à 3 favoris. Passez à Conseil Pro pour les favoris illimités."})
        favori, created = ArticleFavori.objects.get_or_create(utilisateur=self.request.user, article=article)
        if created:
            Article.objects.filter(pk=article.pk).update(nombre_favoris=F("nombre_favoris") + 1)
        serializer.instance = favori

    def destroy(self, request, *args, **kwargs):
        favori = self.get_object()
        article_id = favori.article_id
        favori.delete()
        Article.objects.filter(pk=article_id, nombre_favoris__gt=0).update(nombre_favoris=F("nombre_favoris") - 1)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ArticleReviewViewSet(viewsets.ModelViewSet):
    queryset = ArticleReview.objects.select_related("article", "author").all()
    serializer_class = ArticleReviewSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = self.queryset
        if self.request.user.is_authenticated and self.action in ["update", "partial_update", "destroy"]:
            return queryset.filter(author=self.request.user)
        article_id = self.request.query_params.get("article")
        if article_id:
            queryset = queryset.filter(article_id=article_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        article = serializer.validated_data["article"]
        review, created = ArticleReview.objects.update_or_create(
            article=article,
            author=request.user,
            defaults={
                "rating": serializer.validated_data["rating"],
                "comment": serializer.validated_data.get("comment", ""),
            },
        )
        output_serializer = self.get_serializer(review)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(output_serializer.data, status=status_code)




class AlerteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlerteSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        now = timezone.now()
        queryset = Alerte.objects.filter(est_active=True, date_debut__lte=now).filter(Q(date_fin__isnull=True) | Q(date_fin__gte=now))
        type_alerte = self.request.query_params.get("type")
        if type_alerte:
            queryset = queryset.filter(type_alerte=type_alerte.upper())
        region = self.request.query_params.get("region")
        if region:
            queryset = queryset.filter(Q(region__iexact=region) | Q(region=""))
        return queryset

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="ma-region")
    def ma_region(self, request):
        profile = getattr(request.user, "buyer_profile", None)
        region = profile.region.name if profile and profile.region_id else ""
        queryset = self.get_queryset().filter(Q(region__iexact=region) | Q(region="")) if region else self.get_queryset().filter(region="")
        return Response(AlerteSerializer(queryset, many=True, context={"request": request}).data)


class MarquerAlerteLueView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            alerte = Alerte.objects.get(pk=pk)
        except Alerte.DoesNotExist:
            return Response({"detail": "Alerte introuvable."}, status=status.HTTP_404_NOT_FOUND)
        lecture, _ = AlerteLue.objects.get_or_create(utilisateur=request.user, alerte=alerte)
        return Response({"read": True, "date_lecture": lecture.date_lecture}, status=status.HTTP_200_OK)


class ConseilPaymentInitializeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            annual_value = request.data.get("annual", False)
            annual = annual_value is True or str(annual_value).lower() in {"1", "true", "yes", "oui"}
            return Response(initialize_conseil_payment(request.user, annual))
        except ConseilPaymentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class ConseilPaymentVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        reference = str(request.data.get("reference", "")).strip()
        if not reference:
            return Response({"detail": "La référence de paiement est obligatoire."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response(verify_conseil_payment(request.user, reference))
        except ConseilPaymentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class ConseilAbonnementView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        subscription = getattr(request.user, "conseil_subscription", None)
        active = bool(subscription and subscription.is_active)
        year_month = timezone.now().strftime("%Y-%m")
        used_free = FreeArticleUsage.objects.filter(user=request.user, year_month=year_month).count()
        return Response({
            "active": active,
            "plan": "Conseil Pro" if active else "Gratuit",
            "price_monthly": 3000,
            "free_limits": {"articles_monthly": 5, "favorites": 3, "regional_alerts": False},
            "free_articles_used_this_month": used_free,
            "pro_features": {"unlimited_articles": True, "unlimited_favorites": True, "regional_alerts": True, "agronome_chats_monthly": 3},
            "starts_at": subscription.starts_at if active else None,
            "ends_at": subscription.ends_at if active else None,
        })



class ConseilStatistiquesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "articles_favoris": ArticleFavori.objects.filter(utilisateur=request.user).count(),
            "alertes_lues": AlerteLue.objects.filter(utilisateur=request.user).count(),
        })

import json
import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Avg, Count, F
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from directory_app.models import (
    Category, Region, Locality, Product, Vendor, VendorProduct,
    StockMovement, VendorFavorite, ProductFavorite, VendorReview,
    ServiceProvider, ProvidedService, ServiceProviderReview,
    PhoneAccount, BuyerProfile, AppNotification, Payment, SellerSubscription,
    VendorSale, OtpChallenge, EmailChallenge
)
from directory_app.auth_services import (
    request_otp, verify_otp, request_email_code, verify_email_code,
    request_password_reset, reset_password, OtpError
)
from directory_app.chariow_service import (
    initialize_subscription_payment, verify_and_activate_payment
)
from conseil.models import (
    CategorieConseil, Article, ArticleFavori, ArticleReview,
    Alerte, AlerteLue, ConseilSubscription
)
from conseil.payment_service import (
    initialize_conseil_payment, verify_conseil_payment
)
from .forms import (
    LoginForm, SignupForm, VendorForm, VendorProductForm, StockMovementForm,
    VendorReviewForm, ArticleReviewForm, ServiceProviderForm, ProvidedServiceForm,
    UserProfileForm, PasswordChangeWebForm,
    AdvancedSearchForm, RecordSaleForm, BuyerProfileConfigForm,
    PasswordResetRequestForm, PasswordResetConfirmForm, VerifySignupCodeForm, VerifySellerPaymentForm
)

logger = logging.getLogger(__name__)
User = get_user_model()


# ==============================================================================
# 1. PAGE D'ACCUEIL / MARKETPLACE
# ==============================================================================

def home_view(request):
    """Page d'accueil responsive inspirée de HomeScreen Kivy."""
    query = request.GET.get("q", "").strip()
    region_id = request.GET.get("region", "")
    locality_id = request.GET.get("locality", "")
    category_id = request.GET.get("category", "")

    # Données des filtres
    regions = Region.objects.prefetch_related("localities").all()
    categories = Category.objects.all()

    # Vendeurs à la une / recommandés
    vendors_qs = Vendor.objects.filter(is_active=True, approval_status=Vendor.ApprovalStatus.APPROVED).select_related("region", "locality")

    # Si l'utilisateur est connecté et a une localisation préférée
    user_locality = None
    if request.user.is_authenticated:
        profile = getattr(request.user, "buyer_profile", None)
        if profile and profile.locality:
            user_locality = profile.locality

    if locality_id:
        vendors_qs = vendors_qs.filter(locality_id=locality_id)
    elif region_id:
        vendors_qs = vendors_qs.filter(region_id=region_id)
    elif user_locality:
        # Recommandations locales par défaut
        local_vendors = vendors_qs.filter(locality=user_locality)
        if local_vendors.exists():
            vendors_qs = local_vendors

    if category_id:
        vendors_qs = vendors_qs.filter(stock_items__product__category_id=category_id).distinct()

    if query:
        vendors_qs = vendors_qs.filter(
            Q(name__icontains=query) |
            Q(stock_items__product__name__icontains=query) |
            Q(locality__name__icontains=query)
        ).distinct()

    # Trier par vérifié puis récence
    featured_vendors = vendors_qs.order_by("-is_verified", "-created_at")[:8]

    # Produits récents disponibles en stock
    recent_products = VendorProduct.objects.filter(
        vendor__is_active=True,
        vendor__approval_status=Vendor.ApprovalStatus.APPROVED,
        quantity_available__gt=0
    ).select_related("product", "vendor", "vendor__region", "vendor__locality")[:8]

    # Conseils agricoles épinglés / à la une
    pinned_articles = Article.objects.filter(
        est_publie=True, est_epingle=True
    ).select_related("categorie")[:3]

    # Alertes météo ou phytosanitaires actives
    active_alerts = Alerte.objects.filter(
        date_debut__lte=timezone.now()
    ).filter(
        Q(date_fin__isnull=True) | Q(date_fin__gte=timezone.now())
    )[:3]

    # Aperçu prestataires
    featured_providers = ServiceProvider.objects.filter(is_active=True).select_related("region", "locality")[:4]

    context = {
        "regions": regions,
        "categories": categories,
        "featured_vendors": featured_vendors,
        "recent_products": recent_products,
        "pinned_articles": pinned_articles,
        "active_alerts": active_alerts,
        "featured_providers": featured_providers,
        "selected_region": region_id,
        "selected_locality": locality_id,
        "selected_category": category_id,
        "search_query": query,
    }
    return render(request, "web/index.html", context)


# ==============================================================================
# 2. ANNUAIRE DES VENDEURS & RECHERCHE AVANCÉE
# ==============================================================================

def vendor_list_view(request):
    """Liste complète des vendeurs avec filtres avancés (VendorListScreen + AdvancedSearchScreen)."""
    query = request.GET.get("q", "").strip()
    region_id = request.GET.get("region", "")
    locality_id = request.GET.get("locality", "")
    category_id = request.GET.get("category", "")
    vendor_type = request.GET.get("type", "")
    verified_only = request.GET.get("verified", "") == "1"

    vendors_qs = Vendor.objects.filter(
        is_active=True, approval_status=Vendor.ApprovalStatus.APPROVED
    ).select_related("region", "locality").prefetch_related("stock_items__product")

    if query:
        vendors_qs = vendors_qs.filter(
            Q(name__icontains=query) |
            Q(stock_items__product__name__icontains=query) |
            Q(address__icontains=query) |
            Q(locality__name__icontains=query)
        ).distinct()

    if region_id:
        vendors_qs = vendors_qs.filter(region_id=region_id)
    if locality_id:
        vendors_qs = vendors_qs.filter(locality_id=locality_id)
    if category_id:
        vendors_qs = vendors_qs.filter(stock_items__product__category_id=category_id).distinct()
    if vendor_type:
        vendors_qs = vendors_qs.filter(vendor_type=vendor_type)
    if verified_only:
        vendors_qs = vendors_qs.filter(is_verified=True)

    vendors_qs = vendors_qs.order_by("-is_verified", "-created_at")

    paginator = Paginator(vendors_qs, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    regions = Region.objects.prefetch_related("localities").all()
    categories = Category.objects.all()

    context = {
        "page_obj": page_obj,
        "regions": regions,
        "categories": categories,
        "total_count": paginator.count,
        "selected_region": region_id,
        "selected_locality": locality_id,
        "selected_category": category_id,
        "selected_type": vendor_type,
        "verified_only": verified_only,
        "search_query": query,
    }
    return render(request, "web/vendors/list.html", context)


def vendor_detail_view(request, pk):
    """Fiche vendeur détaillée (VendorDetailScreen) avec stock, avis et contact direct."""
    vendor = get_object_or_404(
        Vendor.objects.select_related("region", "locality", "owner")
        .prefetch_related("stock_items__product", "reviews__author"),
        pk=pk
    )

    # Incrémenter le compteur de vues analytiques si disponible
    if hasattr(vendor, "profile_views"):
        Vendor.objects.filter(pk=pk).update(profile_views=F("profile_views") + 1)

    stock_items = vendor.stock_items.select_related("product").all()
    reviews = vendor.reviews.filter(is_published=True).order_by("-created_at")
    review_form = VendorReviewForm()

    # Formulaire d'avis si connecté
    if request.method == "POST" and request.user.is_authenticated:
        review_form = VendorReviewForm(request.POST)
        if review_form.is_valid():
            review, created = VendorReview.objects.update_or_create(
                vendor=vendor,
                author=request.user,
                defaults={
                    "rating": review_form.cleaned_data["rating"],
                    "comment": review_form.cleaned_data["comment"],
                    "is_published": True,
                }
            )
            messages.success(request, "Votre avis a été enregistré avec succès !")
            return redirect("web:vendor-detail", pk=pk)

    # Calcul de note moyenne
    avg_rating = reviews.aggregate(Avg("rating"))["rating__avg"] or 0.0

    context = {
        "vendor": vendor,
        "stock_items": stock_items,
        "reviews": reviews,
        "review_form": review_form,
        "avg_rating": round(avg_rating, 1),
        "review_count": reviews.count(),
        "is_favorited": request.user.is_authenticated and VendorFavorite.objects.filter(user=request.user, vendor=vendor).exists(),
    }
    return render(request, "web/vendors/detail.html", context)


@require_POST
def vendor_track_contact(request, pk):
    """Endpoint de tracking analytique lors d'un appel ou message WhatsApp."""
    contact_type = request.POST.get("type", "whatsapp")
    vendor = Vendor.objects.filter(pk=pk).first()
    if vendor:
        if contact_type == "whatsapp" and hasattr(vendor, "whatsapp_clicks"):
            Vendor.objects.filter(pk=pk).update(whatsapp_clicks=F("whatsapp_clicks") + 1)
        elif contact_type != "whatsapp" and hasattr(vendor, "call_clicks"):
            Vendor.objects.filter(pk=pk).update(call_clicks=F("call_clicks") + 1)
    return JsonResponse({"status": "tracked"})


def advanced_search_view(request):
    """Recherche avancée avec rayon géographique et type de vendeur (AdvancedSearchScreen + ResultsScreen)."""
    form = AdvancedSearchForm(request.GET or None)
    vendors_qs = Vendor.objects.filter(is_active=True, approval_status=Vendor.ApprovalStatus.APPROVED).select_related("region", "locality").prefetch_related("stock_items__product")

    q = request.GET.get("q", "").strip()
    vendor_type = request.GET.get("vendor_type", "").strip()
    radius_km = request.GET.get("radius_km", "").strip()
    region_id = request.GET.get("region", "")
    locality_id = request.GET.get("locality", "")

    has_searched = bool(q or vendor_type or radius_km or region_id or locality_id)

    if q:
        vendors_qs = vendors_qs.filter(
            Q(name__icontains=q) |
            Q(stock_items__product__name__icontains=q) |
            Q(locality__name__icontains=q)
        ).distinct()

    if vendor_type:
        vendors_qs = vendors_qs.filter(vendor_type=vendor_type)

    if locality_id:
        vendors_qs = vendors_qs.filter(locality_id=locality_id)
    elif region_id:
        vendors_qs = vendors_qs.filter(region_id=region_id)

    paginator = Paginator(vendors_qs.order_by("-is_verified", "-created_at"), 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "form": form,
        "page_obj": page_obj,
        "total_results": paginator.count,
        "has_searched": has_searched,
        "criteria": {
            "q": q,
            "vendor_type": vendor_type,
            "radius_km": radius_km,
        }
    }
    return render(request, "web/search/advanced.html", context)



# ==============================================================================
# 3. CONSEIL AGRICOLE & CONSEIL PRO
# ==============================================================================

def conseil_list_view(request):
    """Liste des conseils agricoles et alertes (ConseilScreen)."""
    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    culture = request.GET.get("culture", "").strip()

    articles_qs = Article.objects.filter(est_publie=True).select_related("categorie")

    if query:
        articles_qs = articles_qs.filter(
            Q(titre__icontains=query) |
            Q(contenu__icontains=query) |
            Q(culture__icontains=query)
        )
    if category_id:
        articles_qs = articles_qs.filter(categorie_id=category_id)
    if culture:
        articles_qs = articles_qs.filter(culture__icontains=culture)

    articles_qs = articles_qs.order_by("-est_epingle", "-date_publication")

    paginator = Paginator(articles_qs, 9)
    page_obj = paginator.get_page(request.GET.get("page"))

    categories = CategorieConseil.objects.all()
    active_alerts = Alerte.objects.filter(date_debut__lte=timezone.now()).filter(
        Q(date_fin__isnull=True) | Q(date_fin__gte=timezone.now())
    )

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "active_alerts": active_alerts,
        "selected_category": category_id,
        "selected_culture": culture,
        "search_query": query,
    }
    return render(request, "web/conseil/list.html", context)


def conseil_detail_view(request, slug):
    """Fiche article détaillée avec lecteur et restriction Conseil Pro (ArticleDetailScreen)."""
    article = get_object_or_404(Article.objects.select_related("categorie"), slug=slug, est_publie=True)

    # Vérification d'accès Conseil Pro
    is_pro_member = False
    if request.user.is_authenticated:
        sub = getattr(request.user, "conseil_subscription", None)
        if sub and sub.is_active:
            is_pro_member = True

    requires_subscription = article.est_premium and not is_pro_member

    # Incrémenter les vues si autorisé
    if not requires_subscription:
        Article.objects.filter(pk=article.pk).update(nombre_vues=F("nombre_vues") + 1)

    reviews = article.reviews.all().select_related("author").order_by("-created_at")
    review_form = ArticleReviewForm()

    if request.method == "POST" and request.user.is_authenticated and not requires_subscription:
        review_form = ArticleReviewForm(request.POST)
        if review_form.is_valid():
            ArticleReview.objects.update_or_create(
                article=article,
                author=request.user,
                defaults={
                    "rating": review_form.cleaned_data["rating"],
                    "comment": review_form.cleaned_data["comment"],
                }
            )
            messages.success(request, "Merci pour votre évaluation !")
            return redirect("web:conseil-detail", slug=slug)

    is_favorited = (
        request.user.is_authenticated
        and ArticleFavori.objects.filter(utilisateur=request.user, article=article).exists()
    )

    context = {
        "article": article,
        "requires_subscription": requires_subscription,
        "is_pro_member": is_pro_member,
        "reviews": reviews,
        "review_form": review_form,
        "is_favorited": is_favorited,
        "related_articles": Article.objects.filter(categorie=article.categorie, est_publie=True).exclude(pk=article.pk)[:3],
    }
    return render(request, "web/conseil/detail.html", context)


def conseil_diagnostic_view(request):
    """Outil de diagnostic agricole interactif (ConseilDiagnosticScreen)."""
    # Exemples de diagnostics types en Côte d'Ivoire
    diagnostics = [
        {
            "culture": "Tomate",
            "symptom": "Feuilles jaunissantes avec taches brunes, flétrissement rapide",
            "diagnosis": "Mildiou de la tomate (Phytophthora infestans) ou Flétrissement bactérien",
            "solution": "Appliquer un fongicide à base de cuivre ou mancozèbe. Éviter d'arroser le feuillage en soirée.",
            "urgency": "Haute"
        },
        {
            "culture": "Manioc",
            "symptom": "Mosaïque jaune sur les feuilles et déformation des limbes",
            "diagnosis": "Maladie de la mosaïque du manioc (CMD - transmise par aleurodes)",
            "solution": "Utiliser des boutures saines certifiées résistantes (ex: variétés IITA / CNRA). Arracher les plants atteints.",
            "urgency": "Moyenne"
        },
        {
            "culture": "Piment / Aubergine",
            "symptom": "Enroulement des feuilles vers le haut, nanisme de la plante",
            "diagnosis": "Attaque de pucerons ou virus de l'enroulement",
            "solution": "Traiter avec du savon noir ou un insecticide homologué. Désherber autour des parcelles.",
            "urgency": "Moyenne"
        },
        {
            "culture": "Maïs",
            "symptom": "Trous dans les feuilles en cornet et sciure végétale visible",
            "diagnosis": "Chenille légionnaire d'automne (Spodoptera frugiperda)",
            "solution": "Inspecter tôt le matin. Traitement ciblé bio (Bacillus thuringiensis) ou insecticide homologué au stade précoce.",
            "urgency": "Critique"
        },
    ]

    selected_culture = request.GET.get("culture", "")
    if selected_culture:
        filtered = [d for d in diagnostics if d["culture"].lower() == selected_culture.lower()]
    else:
        filtered = diagnostics

    context = {
        "diagnostics": filtered,
        "selected_culture": selected_culture,
        "cultures": ["Tomate", "Manioc", "Piment / Aubergine", "Maïs"],
    }
    return render(request, "web/conseil/diagnostic.html", context)


@login_required
def conseil_subscription_view(request):
    """Page d'abonnement Conseil Pro avec paiement Chariow (ConseilSubscriptionScreen)."""
    sub = getattr(request.user, "conseil_subscription", None)
    is_active = bool(sub and sub.is_active)

    if request.method == "POST":
        plan_type = request.POST.get("plan", "monthly")
        annual = (plan_type == "annual")
        try:
            result = initialize_conseil_payment(request.user, annual=annual)
            checkout_url = result.get("checkout_url") or result.get("authorization_url")
            if checkout_url:
                return redirect(checkout_url)
            else:
                messages.error(request, "URL de paiement Chariow indisponible.")
        except Exception as exc:
            messages.error(request, f"Erreur lors de l'initialisation Chariow : {exc}")

    # Vérification manuelle de référence
    ref_to_verify = request.GET.get("ref", "").strip()
    if ref_to_verify:
        try:
            res = verify_conseil_payment(request.user, ref_to_verify)
            messages.success(request, "Félicitations ! Votre abonnement Conseil Pro est activé.")
            return redirect("web:conseil-subscription")
        except Exception as exc:
            messages.error(request, f"Impossible de vérifier le paiement : {exc}")

    context = {
        "subscription": sub,
        "is_active": is_active,
    }
    return render(request, "web/conseil/subscription.html", context)


@login_required
def conseil_dashboard_view(request):
    """Mon Espace Conseil avec calendrier cultural et statistiques personnelles (ConseilDashboardScreen)."""
    sub = getattr(request.user, "conseil_subscription", None)
    is_pro_active = bool(sub and sub.is_active)

    # Statistiques
    articles_favoris_count = request.user.articles_favoris.count()
    profile = getattr(request.user, "buyer_profile", None)
    raw_cultures = profile.culture_profile if (profile and profile.culture_profile) else "Tomate, Chou, Piment"
    user_cultures = [c.strip() for c in raw_cultures.split(",") if c.strip()]

    # Alertes reçues actives
    active_alerts_count = Alerte.objects.filter(
        date_debut__lte=timezone.now()
    ).filter(
        Q(date_fin__isnull=True) | Q(date_fin__gte=timezone.now())
    ).count()

    # Recommandations d'articles selon ses cultures
    recommended_articles = Article.objects.filter(est_publie=True)
    if user_cultures:
        query_cultures = Q()
        for c in user_cultures:
            query_cultures |= Q(culture__icontains=c) | Q(titre__icontains=c)
        recommended_articles = recommended_articles.filter(query_cultures)
    recommended_articles = recommended_articles.order_by("-est_epingle", "-date_publication")[:4]

    # Calendrier cultural type
    calendar_stages = [
        {"stage": "Préparation du sol & Labour", "status": "Terminée", "badge": "bg-green-100 text-green-800", "icon": "fa-check"},
        {"stage": "Semis en pépinière & Germination", "status": "En cours", "badge": "bg-amber-100 text-amber-800", "icon": "fa-spinner"},
        {"stage": "Repiquage en pleine terre", "status": "Prochaine étape (J+15)", "badge": "bg-blue-100 text-blue-800", "icon": "fa-calendar-day"},
        {"stage": "Fertilisation & Traitement phytosanitaire", "status": "À planifier", "badge": "bg-gray-100 text-gray-700", "icon": "fa-clock"},
        {"stage": "Récolte & Conditionnement", "status": "À venir", "badge": "bg-gray-100 text-gray-700", "icon": "fa-wheat-awn"},
    ]

    context = {
        "subscription": sub,
        "is_pro_active": is_pro_active,
        "articles_favoris_count": articles_favoris_count,
        "active_alerts_count": active_alerts_count,
        "user_cultures": user_cultures,
        "recommended_articles": recommended_articles,
        "calendar_stages": calendar_stages,
    }
    return render(request, "web/conseil/dashboard.html", context)


def alertes_list_view(request):
    """Liste complète des alertes agricoles avec filtres régionaux et priorité (AlertesScreen)."""
    filter_mode = request.GET.get("filter", "all")

    alerts_qs = Alerte.objects.filter(
        date_debut__lte=timezone.now()
    ).filter(
        Q(date_fin__isnull=True) | Q(date_fin__gte=timezone.now())
    ).order_by("-priorite", "-date_debut")

    user_region = None
    if request.user.is_authenticated:
        profile = getattr(request.user, "buyer_profile", None)
        if profile and profile.region:
            user_region = profile.region.name

    if filter_mode == "my_region" and user_region:
        alerts_qs = alerts_qs.filter(Q(region__icontains=user_region) | Q(region=""))

    read_alert_ids = set()
    if request.user.is_authenticated:
        read_alert_ids = set(AlerteLue.objects.filter(utilisateur=request.user).values_list("alerte_id", flat=True))

    paginator = Paginator(alerts_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "filter_mode": filter_mode,
        "user_region": user_region,
        "read_alert_ids": read_alert_ids,
        "total_active": alerts_qs.count(),
    }
    return render(request, "web/conseil/alertes.html", context)


@login_required
@require_POST
def alerte_mark_read_view(request, pk):
    """Marque une alerte comme lue (AlerteLue)."""
    alerte = get_object_or_404(Alerte, pk=pk)
    AlerteLue.objects.get_or_create(utilisateur=request.user, alerte=alerte)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": "read", "id": pk})
    messages.success(request, f"L'alerte « {alerte.titre} » a été marquée comme lue.")
    return redirect("web:alertes-list")


def tips_view(request):
    """Conseils pratiques agronomiques (TipsScreen)."""
    return render(request, "web/conseil/tips.html")



# ==============================================================================
# 4. PRESTATAIRES DE SERVICES AGRICOLES
# ==============================================================================

def provider_list_view(request):
    """Annuaire des prestataires de services agricoles (ProviderListScreen)."""
    query = request.GET.get("q", "").strip()
    provider_type = request.GET.get("type", "")
    region_id = request.GET.get("region", "")
    locality_id = request.GET.get("locality", "")

    providers_qs = ServiceProvider.objects.filter(is_active=True).select_related("region", "locality").prefetch_related("services")

    if query:
        providers_qs = providers_qs.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(services__title__icontains=query)
        ).distinct()
    if provider_type:
        providers_qs = providers_qs.filter(provider_type=provider_type)
    if region_id:
        providers_qs = providers_qs.filter(region_id=region_id)
    if locality_id:
        providers_qs = providers_qs.filter(locality_id=locality_id)

    paginator = Paginator(providers_qs.order_by("-is_verified", "-created_at"), 9)
    page_obj = paginator.get_page(request.GET.get("page"))

    regions = Region.objects.prefetch_related("localities").all()

    context = {
        "page_obj": page_obj,
        "regions": regions,
        "provider_types": ServiceProvider.ProviderType.choices,
        "selected_type": provider_type,
        "selected_region": region_id,
        "selected_locality": locality_id,
        "search_query": query,
    }
    return render(request, "web/providers/list.html", context)


def provider_detail_view(request, pk):
    """Fiche prestataire détaillée (ProviderDetailScreen)."""
    provider = get_object_or_404(
        ServiceProvider.objects.select_related("region", "locality", "owner").prefetch_related("services", "reviews__author"),
        pk=pk
    )
    services = provider.services.all()
    reviews = provider.reviews.filter(is_published=True).order_by("-created_at")

    context = {
        "provider": provider,
        "services": services,
        "reviews": reviews,
    }
    return render(request, "web/providers/detail.html", context)


@login_required
def provider_space_view(request):
    """Espace de gestion pour les prestataires de services (ProviderScreen)."""
    provider = ServiceProvider.objects.filter(owner=request.user).first()
    form = ServiceProviderForm(instance=provider)
    service_form = ProvidedServiceForm()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_provider":
            form = ServiceProviderForm(request.POST, instance=provider)
            if form.is_valid():
                p = form.save(commit=False)
                p.owner = request.user
                p.save()
                messages.success(request, "Profil prestataire mis à jour !")
                return redirect("web:provider-space")
        elif action == "add_service" and provider:
            service_form = ProvidedServiceForm(request.POST)
            if service_form.is_valid():
                s = service_form.save(commit=False)
                s.provider = provider
                s.save()
                messages.success(request, f"Service « {s.title} » ajouté avec succès !")
                return redirect("web:provider-space")

    context = {
        "provider": provider,
        "form": form,
        "service_form": service_form,
        "services": provider.services.all() if provider else [],
    }
    return render(request, "web/providers/space.html", context)


# ==============================================================================
# 5. ESPACE VENDEUR & GESTION DES STOCKS
# ==============================================================================

@login_required
def seller_dashboard_view(request):
    """Tableau de bord vendeur et analytics (SellerScreen + SellerAnalyticsScreen)."""
    account = getattr(request.user, "phone_account", None)
    vendor = Vendor.objects.filter(owner=request.user).select_related("region", "locality").first()

    # Si l'utilisateur n'a pas encore de rôle vendeur
    if not account or account.role != "seller":
        return redirect("web:seller-subscription")

    vendor_form = VendorForm(instance=vendor)
    if request.method == "POST" and request.POST.get("action") == "update_vendor":
        vendor_form = VendorForm(request.POST, instance=vendor)
        if vendor_form.is_valid():
            v = vendor_form.save(commit=False)
            v.owner = request.user
            v.save()
            messages.success(request, "Votre fiche vendeur a été enregistrée avec succès !")
            return redirect("web:seller-dashboard")

    # Statistiques analytiques
    stats = {
        "profile_views": getattr(vendor, "profile_views", 0) if vendor else 0,
        "whatsapp_clicks": getattr(vendor, "whatsapp_clicks", 0) if vendor else 0,
        "call_clicks": getattr(vendor, "call_clicks", 0) if vendor else 0,
        "products_count": vendor.stock_items.count() if vendor else 0,
        "reviews_count": vendor.reviews.count() if vendor else 0,
    }

    # Statut abonnement
    seller_sub = getattr(request.user, "seller_subscription", None)

    context = {
        "vendor": vendor,
        "vendor_form": vendor_form,
        "stats": stats,
        "seller_sub": seller_sub,
        "is_pro": bool(seller_sub and seller_sub.is_active),
    }
    return render(request, "web/seller/dashboard.html", context)


@login_required
def seller_stock_view(request):
    """Gestion des stocks et mouvements d'inventaire (SellerStockScreen)."""
    vendor = get_object_or_404(Vendor, owner=request.user)
    stock_items = vendor.stock_items.select_related("product").all()
    add_product_form = VendorProductForm()
    movement_form = StockMovementForm()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_product":
            add_product_form = VendorProductForm(request.POST)
            if add_product_form.is_valid():
                item = add_product_form.save(commit=False)
                item.vendor = vendor
                item.save()
                messages.success(request, f"Produit {item.product.name} ajouté au stock !")
                return redirect("web:seller-stock")
        elif action == "record_movement":
            stock_id = request.POST.get("stock_id")
            stock_item = get_object_or_404(VendorProduct, id=stock_id, vendor=vendor)
            movement_form = StockMovementForm(request.POST)
            if movement_form.is_valid():
                qty = movement_form.cleaned_data["quantity"]
                m_type = movement_form.cleaned_data["movement_type"]
                if m_type == "out" and stock_item.quantity_available < qty:
                    messages.error(request, "Stock insuffisant pour cette sortie !")
                else:
                    if m_type == "in":
                        stock_item.quantity_available += qty
                    else:
                        stock_item.quantity_available -= qty
                    stock_item.save(update_fields=["quantity_available", "updated_at"])

                    movement = movement_form.save(commit=False)
                    movement.stock = stock_item
                    movement.save()
                    messages.success(request, "Mouvement de stock enregistré avec succès !")
                    return redirect("web:seller-stock")

    recent_movements = StockMovement.objects.filter(
        stock__vendor=vendor
    ).select_related("stock__product").order_by("-created_at")[:10]

    context = {
        "vendor": vendor,
        "stock_items": stock_items,
        "add_product_form": add_product_form,
        "movement_form": movement_form,
        "recent_movements": recent_movements,
    }
    return render(request, "web/seller/stock.html", context)


@login_required
def seller_subscription_view(request):
    """Choix du plan vendeur (Gratuit vs Vendeur Pro 5 000 FCFA/mois via Chariow)."""
    account = getattr(request.user, "phone_account", None)
    seller_sub = getattr(request.user, "seller_subscription", None)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "free":
            # Forfait gratuit
            if account:
                account.role = PhoneAccount.Role.SELLER
                account.save(update_fields=["role", "updated_at"])
            messages.success(request, "Forfait gratuit activé ! Vous pouvez maintenant gérer votre fiche vendeur.")
            return redirect("web:seller-dashboard")
        elif action == "pro":
            # Forfait Vendeur Pro Chariow
            try:
                result = initialize_subscription_payment(request.user)
                checkout_url = result.get("checkout_url") or result.get("authorization_url")
                if checkout_url:
                    return redirect(checkout_url)
                else:
                    messages.error(request, "L'URL de paiement Chariow est introuvable.")
            except Exception as exc:
                messages.error(request, f"Erreur de paiement Chariow : {exc}")

    # Vérification manuelle de référence
    ref_to_verify = request.GET.get("ref", "").strip()
    if ref_to_verify:
        try:
            res = verify_and_activate_payment(request.user, ref_to_verify)
            messages.success(request, "Paiement Chariow confirmé ! Votre badge Vendeur Pro est actif.")
            return redirect("web:seller-dashboard")
        except Exception as exc:
            messages.error(request, f"Impossible de valider la référence : {exc}")

    context = {
        "account": account,
        "seller_sub": seller_sub,
        "is_active": bool(seller_sub and seller_sub.is_active),
    }
    return render(request, "web/seller/subscription.html", context)


@login_required
def seller_analytics_view(request):
    """Tableau de bord analytique vendeur avec enregistrement de vente directe (SellerAnalyticsScreen)."""
    vendor = Vendor.objects.filter(owner=request.user).first()
    if not vendor:
        messages.info(request, "Veuillez d'abord créer votre fiche vendeur.")
        return redirect("web:seller-dashboard")

    days = int(request.GET.get("days", 30))
    if days not in [7, 30, 90]:
        days = 30
    start_date = timezone.now() - timedelta(days=days)

    sales_qs = VendorSale.objects.filter(vendor=vendor, sold_at__gte=start_date)

    sales_count = sales_qs.count()
    total_quantity = sum(s.quantity for s in sales_qs)
    total_revenue = sum(s.quantity * s.unit_price for s in sales_qs)
    average_sale = (total_revenue // sales_count) if sales_count > 0 else 0

    # Calcul exact des top produits
    product_stats = {}
    for s in sales_qs.select_related("product"):
        pname = s.product.name
        if pname not in product_stats:
            product_stats[pname] = {"quantity": 0, "revenue": 0, "count": 0}
        product_stats[pname]["quantity"] += s.quantity
        product_stats[pname]["revenue"] += s.quantity * s.unit_price
        product_stats[pname]["count"] += 1

    top_products = sorted(
        [{"product_name": k, **v} for k, v in product_stats.items()],
        key=lambda x: x["revenue"],
        reverse=True
    )[:5]

    # Historique récent des ventes
    recent_sales = sales_qs.select_related("product").order_by("-sold_at")[:15]

    # Formulaire d'enregistrement d'une vente directe
    sale_form = RecordSaleForm()
    if request.method == "POST":
        sale_form = RecordSaleForm(request.POST)
        if sale_form.is_valid():
            product = sale_form.cleaned_data["product"]
            qty = sale_form.cleaned_data["quantity"]
            price = sale_form.cleaned_data["unit_price"]
            buyer_contact = sale_form.cleaned_data["buyer_contact"]
            notes = sale_form.cleaned_data["notes"]

            VendorSale.objects.create(
                vendor=vendor,
                product=product,
                quantity=qty,
                unit_price=price,
                buyer_contact=buyer_contact,
                notes=notes,
                sold_at=timezone.now()
            )

            # Mettre à jour le stock disponible si présent
            vp = VendorProduct.objects.filter(vendor=vendor, product=product).first()
            if vp:
                vp.quantity_available = max(0, vp.quantity_available - qty)
                vp.is_available = vp.quantity_available > 0
                vp.save(update_fields=["quantity_available", "is_available", "updated_at"])
                StockMovement.objects.create(
                    stock=vp,
                    movement_type=StockMovement.MovementType.OUT,
                    quantity=qty,
                    previous_quantity=vp.quantity_available + qty,
                    new_quantity=vp.quantity_available,
                    reason=f"Vente directe manuelle ({notes or 'au comptoir'})"[:255]
                )

            messages.success(request, f"Vente de {qty} {product.name} ({price * qty:,} FCFA) enregistrée avec succès !")
            return redirect("web:seller-analytics")

    context = {
        "vendor": vendor,
        "days": days,
        "sales_count": sales_count,
        "total_quantity": total_quantity,
        "total_revenue": total_revenue,
        "average_sale": average_sale,
        "top_products": top_products,
        "recent_sales": recent_sales,
        "sale_form": sale_form,
    }
    return render(request, "web/seller/analytics.html", context)


@login_required
@require_POST
def verify_seller_payment_view(request):
    """Vérification manuelle d'une référence Chariow pour le statut Vendeur Pro (UserProfileScreen + SellerScreen)."""
    form = VerifySellerPaymentForm(request.POST)
    if form.is_valid():
        ref = form.cleaned_data["reference"].strip()
        try:
            res = verify_and_activate_payment(request.user, ref)
            messages.success(request, "Paiement Chariow confirmé ! Votre badge Vendeur Pro est désormais actif.")
        except Exception as exc:
            messages.error(request, f"Impossible de valider la référence Chariow : {exc}")
    else:
        messages.error(request, "Veuillez fournir une référence de paiement valide.")
    return redirect("web:seller-dashboard")



# ==============================================================================
# 6. AUTHENTIFICATION & GESTION DE COMPTE
# ==============================================================================

def login_view(request):
    """Connexion avec téléphone ou nom d'utilisateur (LoginScreen)."""
    if request.user.is_authenticated:
        return redirect("web:home")

    form = LoginForm()
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            ident = form.cleaned_data["identifier"].strip()
            pwd = form.cleaned_data["password"]

            # Essayer d'abord par nom d'utilisateur direct
            user = authenticate(request, username=ident, password=pwd)

            # Si échec, essayer par téléphone
            if not user:
                account = PhoneAccount.objects.filter(phone_e164=ident).first()
                if account:
                    user = authenticate(request, username=account.user.username, password=pwd)

            if user:
                login(request, user)
                messages.success(request, f"Bienvenue, {user.first_name or user.username} !")
                next_url = request.GET.get("next") or reverse("web:home")
                return redirect(next_url)
            else:
                messages.error(request, "Identifiants invalides. Vérifiez votre numéro/identifiant et mot de passe.")

    return render(request, "web/auth/login.html", {"form": form})


def signup_view(request):
    """Inscription acheteur ou vendeur (SignupScreen)."""
    if request.user.is_authenticated:
        return redirect("web:home")

    form = SignupForm()
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data["phone"].strip()
            name = form.cleaned_data["full_name"].strip()
            email = form.cleaned_data.get("email", "").strip()
            role = form.cleaned_data["role"]
            region = form.cleaned_data.get("region")
            locality = form.cleaned_data.get("locality")
            pwd = form.cleaned_data["password"]

            # Création utilisateur
            username = f"user_{phone.replace('+', '')}"
            if User.objects.filter(username=username).exists():
                messages.error(request, "Ce numéro de téléphone est déjà enregistré.")
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=name,
                    password=pwd
                )
                PhoneAccount.objects.create(
                    user=user,
                    phone_e164=phone,
                    role=role,
                    phone_verified=True  # Pré-validé en web standard
                )
                BuyerProfile.objects.create(
                    user=user,
                    full_name=name,
                    phone=phone,
                    email=email,
                    region=region,
                    locality=locality,
                )
                login(request, user)
                messages.success(request, "Votre compte AgriLink CI a été créé avec succès !")
                if role == "seller":
                    return redirect("web:seller-subscription")
                return redirect("web:home")

    return render(request, "web/auth/signup.html", {"form": form})


def logout_view(request):
    """Déconnexion."""
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect("web:home")


def get_or_create_buyer_profile(user):
    """Récupère ou initialise un profil acheteur en fournissant des régions par défaut si nécessaire."""
    profile = BuyerProfile.objects.filter(user=user).first()
    if not profile:
        reg = Region.objects.first()
        loc = Locality.objects.filter(region=reg).first() if reg else None
        if not loc:
            loc = Locality.objects.first()
        if reg and loc:
            profile, _ = BuyerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "region": reg,
                    "locality": loc,
                    "full_name": user.get_full_name() or user.username,
                    "email": user.email
                }
            )
    return profile


@login_required
def profile_view(request):
    """Profil utilisateur et localisation acheteur (UserProfileScreen + BuyerProfileScreen)."""
    profile = get_or_create_buyer_profile(request.user)
    account = getattr(request.user, "phone_account", None)

    profile_form = UserProfileForm(initial={
        "full_name": (profile.full_name if profile else "") or request.user.first_name,
        "email": (profile.email if profile else "") or request.user.email,
        "culture_profile": profile.culture_profile if profile else "",
        "region": profile.region if profile else None,
        "locality": profile.locality if profile else None,
    })
    password_form = PasswordChangeWebForm()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_profile":
            profile_form = UserProfileForm(request.POST)
            if profile_form.is_valid():
                if not profile:
                    profile = BuyerProfile(user=request.user)
                profile.full_name = profile_form.cleaned_data["full_name"]
                profile.email = profile_form.cleaned_data["email"]
                profile.culture_profile = profile_form.cleaned_data["culture_profile"]
                profile.region = profile_form.cleaned_data["region"]
                profile.locality = profile_form.cleaned_data["locality"]
                profile.save()

                request.user.first_name = profile.full_name
                request.user.email = profile.email
                request.user.save(update_fields=["first_name", "email"])

                messages.success(request, "Votre profil a été mis à jour avec succès !")
                return redirect("web:profile")
        elif action == "change_password":
            password_form = PasswordChangeWebForm(request.POST)
            if password_form.is_valid():
                old_p = password_form.cleaned_data["old_password"]
                new_p = password_form.cleaned_data["new_password"]
                if not request.user.check_password(old_p):
                    messages.error(request, "L'ancien mot de passe est incorrect.")
                else:
                    request.user.set_password(new_p)
                    request.user.save()
                    login(request, request.user)  # Reconnexion immédiate
                    messages.success(request, "Votre mot de passe a été modifié avec succès !")
                    return redirect("web:profile")

    context = {
        "profile": profile,
        "account": account,
        "profile_form": profile_form,
        "password_form": password_form,
    }
    return render(request, "web/account/profile.html", context)


@login_required
def buyer_profile_view(request):
    """Configuration de la zone de l'acheteur pour recevoir les vendeurs proches (BuyerProfileScreen)."""
    profile = get_or_create_buyer_profile(request.user)
    account = getattr(request.user, "phone_account", None)

    if request.method == "POST":
        form = BuyerProfileConfigForm(request.POST)
        if form.is_valid():
            if not profile:
                profile = BuyerProfile(user=request.user)
            profile.full_name = form.cleaned_data["full_name"]
            profile.phone = form.cleaned_data["phone"]
            profile.email = form.cleaned_data["email"]
            profile.region = form.cleaned_data["region"]
            profile.locality = form.cleaned_data["locality"]
            profile.culture_profile = form.cleaned_data["culture_profile"]
            profile.save()

            if profile.full_name:
                request.user.first_name = profile.full_name
            if profile.email:
                request.user.email = profile.email
            request.user.save(update_fields=["first_name", "email"])

            messages.success(request, f"Votre localisation ({profile.locality.name}, {profile.region.name}) a été enregistrée avec succès !")
            return redirect("web:home")
    else:
        form = BuyerProfileConfigForm(initial={
            "full_name": (profile.full_name if profile else "") or request.user.first_name,
            "phone": (profile.phone if profile else "") or (account.phone_e164 if account else ""),
            "email": (profile.email if profile else "") or request.user.email,
            "region": profile.region if profile and hasattr(profile, "region") else None,
            "locality": profile.locality if profile and hasattr(profile, "locality") else None,
            "culture_profile": profile.culture_profile if profile else "",
        })

    local_vendors = []
    if profile and profile.locality:
        local_vendors = Vendor.objects.filter(
            is_active=True,
            approval_status=Vendor.ApprovalStatus.APPROVED,
            locality=profile.locality
        ).order_by("-is_verified", "-created_at")[:6]

    context = {
        "profile": profile,
        "form": form,
        "local_vendors": local_vendors,
    }
    return render(request, "web/account/buyer_profile.html", context)


@login_required
def favorites_view(request):
    """Liste des vendeurs, produits et articles de conseils favoris (FavoritesScreen)."""
    favorite_vendors = Vendor.objects.filter(
        favorite_by_users__user=request.user
    ).select_related("region", "locality")

    favorite_products = Product.objects.filter(
        favorite_by_users__user=request.user
    ).select_related("category")

    favorite_articles = Article.objects.filter(
        favoris_utilisateurs__utilisateur=request.user
    ).select_related("categorie")

    context = {
        "favorite_vendors": favorite_vendors,
        "favorite_products": favorite_products,
        "favorite_articles": favorite_articles,
    }
    return render(request, "web/account/favorites.html", context)


@login_required
@require_POST
def toggle_favorite(request):
    """Ajout / Retrait en favori par AJAX (FavoritesScreen)."""
    target_type = request.POST.get("type")
    target_id = request.POST.get("id")

    if target_type == "vendor":
        fav = VendorFavorite.objects.filter(user=request.user, vendor_id=target_id)
        if fav.exists():
            fav.delete()
            return JsonResponse({"status": "removed", "is_favorited": False})
        else:
            VendorFavorite.objects.create(user=request.user, vendor_id=target_id)
            return JsonResponse({"status": "added", "is_favorited": True})

    elif target_type == "product":
        fav = ProductFavorite.objects.filter(user=request.user, product_id=target_id)
        if fav.exists():
            fav.delete()
            return JsonResponse({"status": "removed", "is_favorited": False})
        else:
            ProductFavorite.objects.create(user=request.user, product_id=target_id)
            return JsonResponse({"status": "added", "is_favorited": True})

    elif target_type == "article":
        fav = ArticleFavori.objects.filter(utilisateur=request.user, article_id=target_id)
        if fav.exists():
            fav.delete()
            return JsonResponse({"status": "removed", "is_favorited": False})
        else:
            ArticleFavori.objects.create(utilisateur=request.user, article_id=target_id)
            return JsonResponse({"status": "added", "is_favorited": True})

    return JsonResponse({"error": "Paramètres invalides"}, status=400)


@login_required
def notifications_view(request):
    """Centre de notifications et alertes (NotificationsScreen + AlertesScreen)."""
    user_notifications = AppNotification.objects.filter(recipient=request.user).order_by("-sent_at")

    if request.method == "POST" and request.POST.get("action") == "mark_all_read":
        user_notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, "Toutes les notifications sont marquées comme lues.")
        return redirect("web:notifications")

    active_alerts = Alerte.objects.filter(date_debut__lte=timezone.now()).filter(
        Q(date_fin__isnull=True) | Q(date_fin__gte=timezone.now())
    ).order_by("-priorite", "-date_debut")

    context = {
        "notifications": user_notifications[:30],
        "active_alerts": active_alerts,
    }
    return render(request, "web/account/notifications.html", context)


def password_reset_request_view(request):
    """Demande de réinitialisation de mot de passe avec code à 6 chiffres (LoginScreen reset mode)."""
    form = PasswordResetRequestForm()
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            identity = form.cleaned_data["identity"].strip()
            try:
                result = request_password_reset(identity)
                request.session["reset_identity"] = identity
                dev_code = result.get("dev_code") if isinstance(result, dict) else None
                msg = "Un code de validation à 6 chiffres vous a été envoyé."
                if dev_code:
                    msg += f" (Code dev : {dev_code})"
                messages.info(request, msg)
                return redirect("web:password-reset-confirm")
            except Exception as exc:
                messages.error(request, f"Erreur : {exc}")

    return render(request, "web/auth/password_reset.html", {"form": form})


def password_reset_confirm_view(request):
    """Confirmation du code et définition du nouveau mot de passe (LoginScreen reset confirm)."""
    identity = request.session.get("reset_identity", "")
    if not identity and request.method == "GET":
        messages.warning(request, "Veuillez d'abord demander un code de réinitialisation.")
        return redirect("web:password-reset-request")

    form = PasswordResetConfirmForm(initial={"identity": identity})
    if request.method == "POST":
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            ident = form.cleaned_data["identity"] or identity
            code = form.cleaned_data["code"].strip()
            new_password = form.cleaned_data["new_password"]
            try:
                reset_password(ident, code, new_password)
                request.session.pop("reset_identity", None)
                messages.success(request, "Votre mot de passe a été réinitialisé avec succès ! Vous pouvez maintenant vous connecter.")
                return redirect("web:login")
            except Exception as exc:
                messages.error(request, f"Erreur lors de la réinitialisation : {exc}")

    return render(request, "web/auth/password_reset_confirm.html", {"form": form, "identity": identity})


def signup_verify_view(request):
    """Validation du code OTP à 6 chiffres pour finaliser l'inscription (SignupVerifyScreen)."""
    identity = request.session.get("signup_identity", "")
    password = request.session.get("signup_password", "")

    if not identity and request.method == "GET":
        return redirect("web:signup")

    form = VerifySignupCodeForm(initial={"identity": identity, "password": password})
    if request.method == "POST":
        form = VerifySignupCodeForm(request.POST)
        if form.is_valid():
            ident = form.cleaned_data["identity"] or identity
            code = form.cleaned_data["code"].strip()
            pwd = form.cleaned_data["password"] or password

            try:
                if "@" in ident:
                    verify_result = verify_email_code(ident, code, pwd)
                else:
                    verify_result = verify_otp(ident, code, pwd)

                user = verify_result.get("user")
                if user:
                    login(request, user)
                    request.session.pop("signup_identity", None)
                    request.session.pop("signup_password", None)
                    messages.success(request, "Compte vérifié avec succès ! Veuillez configurer votre zone géographique.")
                    return redirect("web:buyer-profile")
            except Exception as exc:
                messages.error(request, f"Code invalide ou expiré : {exc}")

    return render(request, "web/auth/verify_code.html", {"form": form, "identity": identity})


def ajax_localities_by_region(request, region_id):
    """Renvoie les localités d'une région en JSON pour les listes déroulantes dynamiques."""
    localities = Locality.objects.filter(region_id=region_id).values("id", "name").order_by("name")
    return JsonResponse({"localities": list(localities)})


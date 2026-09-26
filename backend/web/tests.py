from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from directory_app.models import (
    Region, Locality, Category, Product, Vendor, VendorProduct,
    PhoneAccount, BuyerProfile, ServiceProvider, ProvidedService
)
from conseil.models import CategorieConseil, Article

User = get_user_model()


class WebFrontendTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Données de base
        self.region = Region.objects.create(name="Lagunes", code="LAG")
        self.locality = Locality.objects.create(name="Abidjan", region=self.region)
        self.category = Category.objects.create(name="Vivriers", slug="vivriers")
        self.product = Product.objects.create(name="Manioc", slug="manioc", category=self.category)

        # Utilisateur normal / Acheteur
        self.user = User.objects.create_user(
            username="testuser",
            password="Password123!",
            first_name="Jean Kouassi",
            email="jean@agrilink.ci"
        )
        self.account = PhoneAccount.objects.create(
            user=self.user,
            phone_e164="+2250700000001",
            role=PhoneAccount.Role.BUYER
        )
        self.buyer_profile = BuyerProfile.objects.create(
            user=self.user,
            full_name="Jean Kouassi",
            region=self.region,
            locality=self.locality
        )

        # Vendeur et stock
        self.seller_user = User.objects.create_user(
            username="selleruser",
            password="Password123!",
            first_name="Awa Traoré"
        )
        self.seller_account = PhoneAccount.objects.create(
            user=self.seller_user,
            phone_e164="+2250700000002",
            role=PhoneAccount.Role.SELLER
        )
        self.vendor = Vendor.objects.create(
            owner=self.seller_user,
            name="Coopérative Vivriers d'Abidjan",
            region=self.region,
            locality=self.locality,
            is_active=True,
            approval_status=Vendor.ApprovalStatus.APPROVED,
            is_verified=True,
            phone="+2250700000002",
            whatsapp_number="+2250700000002"
        )
        self.stock_item = VendorProduct.objects.create(
            vendor=self.vendor,
            product=self.product,
            price_note="500 FCFA / kg",
            quantity_available=100
        )

        # Conseils
        self.conseil_cat = CategorieConseil.objects.create(nom="Grandes cultures")
        self.article_free = Article.objects.create(
            titre="Comment cultiver le manioc",
            slug="comment-cultiver-le-manioc",
            categorie=self.conseil_cat,
            culture="Manioc",
            contenu="Guide complet de bouturage...",
            est_publie=True,
            est_premium=False,
            est_epingle=True
        )
        self.article_pro = Article.objects.create(
            titre="Protocole fertilisation NPK",
            slug="protocole-fertilisation-npk",
            categorie=self.conseil_cat,
            culture="Maïs",
            contenu="Dosages précis...",
            est_publie=True,
            est_premium=True
        )

        # Prestataire
        self.provider = ServiceProvider.objects.create(
            owner=self.seller_user,
            name="AgriTracteur CI",
            provider_type=ServiceProvider.ProviderType.MECANISATION,
            region=self.region,
            locality=self.locality,
            phone="+2250100000001",
            is_active=True,
            is_verified=True
        )
        self.provided_service = ProvidedService.objects.create(
            provider=self.provider,
            title="Labour profond",
            rate=45000,
            unit="hectare"
        )

    def test_home_view(self):
        """Test page d'accueil web responsive."""
        response = self.client.get(reverse("web:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AgriLink")
        self.assertContains(response, "Coopérative Vivriers")
        self.assertContains(response, "Comment cultiver le manioc")

    def test_vendor_list_and_search(self):
        """Test annuaire des vendeurs et filtres."""
        response = self.client.get(reverse("web:vendor-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Coopérative Vivriers")

        # Recherche filtrée
        response_search = self.client.get(reverse("web:vendor-list"), {"q": "Vivriers"})
        self.assertEqual(response_search.status_code, 200)
        self.assertContains(response_search, "Coopérative Vivriers")

    def test_vendor_detail_view(self):
        """Test fiche vendeur détaillée."""
        response = self.client.get(reverse("web:vendor-detail", kwargs={"pk": self.vendor.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Coopérative Vivriers")
        self.assertContains(response, "500 FCFA")

    def test_conseil_list_and_detail(self):
        """Test liste conseils et paywall Conseil Pro."""
        response = self.client.get(reverse("web:conseil-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comment cultiver le manioc")

        # Article gratuit
        res_free = self.client.get(reverse("web:conseil-detail", kwargs={"slug": self.article_free.slug}))
        self.assertEqual(res_free.status_code, 200)
        self.assertContains(res_free, "Guide complet de bouturage")

        # Article Pro réservé aux abonnés (utilisateur non connecté)
        res_pro = self.client.get(reverse("web:conseil-detail", kwargs={"slug": self.article_pro.slug}))
        self.assertEqual(res_pro.status_code, 200)
        self.assertContains(res_pro, "Contenu Réservé aux Membres Conseil Pro")

    def test_conseil_diagnostic(self):
        """Test outil de diagnostic agricole interactif."""
        response = self.client.get(reverse("web:conseil-diagnostic"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Diagnostic Rapide")
        self.assertContains(response, "Manioc")

    def test_provider_list_and_detail(self):
        """Test annuaire des prestataires et fiches."""
        response = self.client.get(reverse("web:provider-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AgriTracteur CI")

        res_detail = self.client.get(reverse("web:provider-detail", kwargs={"pk": self.provider.pk}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, "Labour profond")

    def test_auth_login_and_profile(self):
        """Test connexion et modification du profil."""
        login_response = self.client.post(reverse("web:login"), {
            "identifier": "+2250700000001",
            "password": "Password123!"
        }, follow=True)
        self.assertEqual(login_response.status_code, 200)

        # Accès profil connecté
        prof_res = self.client.get(reverse("web:profile"))
        self.assertEqual(prof_res.status_code, 200)
        self.assertContains(prof_res, "Jean Kouassi")

    def test_favorites_toggle_ajax(self):
        """Test ajout et suppression en favori."""
        self.client.login(username="testuser", password="Password123!")
        
        # Ajouter le vendeur en favori
        res_add = self.client.post(reverse("web:favorite-toggle"), {
            "type": "vendor",
            "id": self.vendor.id
        })
        self.assertEqual(res_add.status_code, 200)
        data = res_add.json()
        self.assertTrue(data.get("is_favorited"))

        # Vérifier la page des favoris
        fav_page = self.client.get(reverse("web:favorites"))
        self.assertEqual(fav_page.status_code, 200)
        self.assertContains(fav_page, "Coopérative Vivriers")

    def test_seller_space_flow(self):
        """Test navigation et gestion de stock dans l'espace vendeur."""
        self.client.login(username="selleruser", password="Password123!")

        # Dashboard vendeur
        dash_res = self.client.get(reverse("web:seller-dashboard"))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, "Coopérative Vivriers")

        # Page de stock
        stock_res = self.client.get(reverse("web:seller-stock"))
        self.assertEqual(stock_res.status_code, 200)
        self.assertContains(stock_res, "Manioc")

    def test_ajax_localities(self):
        """Test API AJAX pour chargement dynamique des localités."""
        res = self.client.get(reverse("web:ajax-localities", kwargs={"region_id": self.region.id}))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data.get("localities", [])), 1)
        self.assertEqual(data["localities"][0]["name"], "Abidjan")

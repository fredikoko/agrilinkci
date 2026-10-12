from datetime import timedelta
from django.utils import timezone
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from directory_app.models import (
    Region, Locality, Category, Product, Vendor, VendorProduct,
    PhoneAccount, BuyerProfile, ServiceProvider, ProvidedService
)
from conseil.models import CategorieConseil, Article, Alerte, AlerteLue, ArticleFavori

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

        # Acheteur dédié buyeruser pour les tests de profil et alertes
        self.buyer_user = User.objects.create_user(
            username="buyeruser",
            password="Password123!",
            first_name="Acheteur Test",
            email="acheteur@agrilink.ci"
        )
        self.buyer_account = PhoneAccount.objects.create(
            user=self.buyer_user,
            phone_e164="+2250700000003",
            role=PhoneAccount.Role.BUYER
        )
        self.buyer_user_profile = BuyerProfile.objects.create(
            user=self.buyer_user,
            full_name="Acheteur Test",
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
            vendor_type=Vendor.VendorType.COOPERATIVE,
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

        # Alertes agricoles
        self.alerte = Alerte.objects.create(
            titre="Alerte Sécheresse",
            message="Mesures d'irrigation recommandées dans le sud.",
            region="Lagunes",
            localite="Abidjan",
            culture="Manioc",
            priorite="URGENTE",
            type_alerte="METEO",
            date_debut=timezone.now() - timedelta(days=1),
            est_active=True
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

    def test_unauthenticated_redirects_and_login_aliases(self):
        """Test que les pages protégées redirigent vers la page de connexion sans 404."""
        # Non connecté accédant à l'espace prestataire
        res_provider = self.client.get(reverse("web:provider-space"))
        self.assertEqual(res_provider.status_code, 302)
        self.assertIn("/auth/login/", res_provider.url)

        # Non connecté accédant à l'abonnement conseil
        res_conseil = self.client.get(reverse("web:conseil-subscription"))
        self.assertEqual(res_conseil.status_code, 302)
        self.assertIn("/auth/login/", res_conseil.url)

        # Accès direct aux alias de connexion
        self.assertEqual(self.client.get("/accounts/login/").status_code, 200)
        self.assertEqual(self.client.get("/login/").status_code, 200)
        self.assertEqual(self.client.get("/connexion/").status_code, 200)

    def test_advanced_search_view(self):
        """Test recherche avancée avec mot-clé, type et rayon kilométrique."""
        # Sans filtre
        res = self.client.get(reverse("web:advanced-search"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Recherche Avancée")

        # Avec filtres
        res_filter = self.client.get(reverse("web:advanced-search"), {
            "q": "Manioc",
            "vendor_type": "coopérative",
            "radius_km": "10",
        })
        self.assertEqual(res_filter.status_code, 200)
        self.assertContains(res_filter, "Coopérative Vivriers")
        self.assertContains(res_filter, "Rayon : 10 km")

    def test_conseil_dashboard_and_tips(self):
        """Test Mon Espace Conseil et Conseils pratiques."""
        # Non connecté
        res_unauth = self.client.get(reverse("web:conseil-dashboard"))
        self.assertEqual(res_unauth.status_code, 302)

        # Connecté
        self.client.login(username="buyeruser", password="Password123!")
        res_dash = self.client.get(reverse("web:conseil-dashboard"))
        self.assertEqual(res_dash.status_code, 200)
        self.assertContains(res_dash, "Mon Espace Conseil")
        self.assertContains(res_dash, "Mon Calendrier Cultural")

        # Astuces pratiques
        res_tips = self.client.get(reverse("web:tips"))
        self.assertEqual(res_tips.status_code, 200)
        self.assertContains(res_tips, "Bien choisir ses semences")

    def test_alertes_and_mark_read(self):
        """Test liste des alertes et marquage comme lue."""
        self.client.login(username="buyeruser", password="Password123!")
        res_list = self.client.get(reverse("web:alertes-list"))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, "Alerte Sécheresse")

        # Marquer comme lue
        res_read = self.client.post(reverse("web:alerte-mark-read", kwargs={"pk": self.alerte.pk}), follow=True)
        self.assertEqual(res_read.status_code, 200)
        self.assertContains(res_read, "marquée comme lue")

    def test_seller_analytics_and_record_sale(self):
        """Test tableau de bord analytique vendeur et enregistrement d'une vente directe."""
        self.client.login(username="selleruser", password="Password123!")
        res_analytics = self.client.get(reverse("web:seller-analytics"))
        self.assertEqual(res_analytics.status_code, 200)
        self.assertContains(res_analytics, "Tableau de Bord Analytique")

        # Enregistrer une vente directe
        post_sale = self.client.post(reverse("web:seller-analytics"), {
            "product": self.product.id,
            "quantity": 5,
            "unit_price": 600,
            "buyer_contact": "+2250709999999",
            "notes": "Vente test comptoir",
        }, follow=True)
        self.assertEqual(post_sale.status_code, 200)
        self.assertContains(post_sale, "Vente de 5")

    def test_article_favorite_toggle(self):
        """Test ajout et retrait d'un article de conseil en favoris."""
        self.client.login(username="buyeruser", password="Password123!")
        # Ajout
        res_add = self.client.post(reverse("web:favorite-toggle"), {
            "type": "article",
            "id": self.article_free.id,
        })
        self.assertEqual(res_add.status_code, 200)
        self.assertTrue(res_add.json()["is_favorited"])

        # Retrait
        res_rem = self.client.post(reverse("web:favorite-toggle"), {
            "type": "article",
            "id": self.article_free.id,
        })
        self.assertEqual(res_rem.status_code, 200)
        self.assertFalse(res_rem.json()["is_favorited"])

    def test_buyer_profile_view(self):
        """Test configuration de la zone acheteur."""
        self.client.login(username="buyeruser", password="Password123!")
        res_get = self.client.get(reverse("web:buyer-profile"))
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, "Mon Profil Acheteur")

        # Sauvegarde
        res_post = self.client.post(reverse("web:buyer-profile"), {
            "full_name": "Acheteur Test Modifié",
            "phone": "+2250700000001",
            "email": "acheteur.modifie@exemple.ci",
            "region": self.region.id,
            "locality": self.locality.id,
            "culture_profile": "Manioc, Cacao, Piment",
        }, follow=True)
        self.assertEqual(res_post.status_code, 200)


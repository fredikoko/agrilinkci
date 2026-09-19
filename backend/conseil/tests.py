from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Alerte, Article, ArticleFavori, CategorieConseil


class ConseilApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="conseil-user")
        self.category = CategorieConseil.objects.create(nom="Légumes", description="Cultures maraîchères")
        self.article = Article.objects.create(
            titre="Préparer son sol pour la tomate",
            contenu="Une bonne préparation du sol améliore la reprise des plants.",
            resume="Les étapes essentielles avant la plantation.",
            categorie=self.category,
            culture="Tomate",
            est_epingle=True,
            est_publie=True,
        )
        self.alert = Alerte.objects.create(
            titre="Période de semis",
            message="La saison des semis commence.",
            region="",
            date_debut=timezone.now() - timedelta(days=1),
        )
        self.client = APIClient()

    def test_articles_and_detail_increment_views(self):
        response = self.client.get("/api/conseil/articles/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        detail = self.client.get(f"/api/conseil/articles/{self.article.slug}/")
        self.assertEqual(detail.status_code, 200)
        self.article.refresh_from_db()
        self.assertEqual(self.article.nombre_vues, 1)

    def test_articles_filter_by_category_name_or_id(self):
        by_name = self.client.get("/api/conseil/articles/", {"categorie": "Légumes"})
        self.assertEqual(by_name.status_code, 200)
        self.assertEqual(len(by_name.json()), 1)

        by_id = self.client.get("/api/conseil/articles/", {"categorie": str(self.category.id)})
        self.assertEqual(by_id.status_code, 200)
        self.assertEqual(len(by_id.json()), 1)

    def test_authenticated_user_can_add_favorite(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/conseil/favoris/", {"article_id": self.article.id}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(ArticleFavori.objects.filter(utilisateur=self.user, article=self.article).exists())
        self.article.refresh_from_db()
        self.assertEqual(self.article.nombre_favoris, 1)

    def test_active_alerts_are_public(self):
        response = self.client.get("/api/conseil/alertes/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["titre"], "Période de semis")

    def test_create_article_review(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/conseil/article-reviews/",
            {"article": self.article.id, "rating": 5, "comment": "Très bon conseil!"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["rating"], 5)

        # Re-submitting updates existing review (200 OK)
        update_response = self.client.post(
            "/api/conseil/article-reviews/",
            {"article": self.article.id, "rating": 4, "comment": "Mis à jour!"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["rating"], 4)

    def test_premium_article_requires_subscription(self):
        self.article.est_premium = True
        self.article.save()

        # Unauthenticated request -> 402
        res_anon = self.client.get(f"/api/conseil/articles/{self.article.slug}/")
        self.assertEqual(res_anon.status_code, 402)
        self.assertTrue(res_anon.json()["subscription_required"])

        # Authenticated user without subscription -> 402
        self.client.force_authenticate(user=self.user)
        res_user = self.client.get(f"/api/conseil/articles/{self.article.slug}/")
        self.assertEqual(res_user.status_code, 402)
        self.assertTrue(res_user.json()["subscription_required"])



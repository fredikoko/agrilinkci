from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient


class DynamicCategoryApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_product_categories_endpoint_returns_named_categories(self):
        response = APIClient().get("/api/categories/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        results = payload.get("results", payload) if isinstance(payload, dict) else payload
        self.assertIsInstance(results, list)
        self.assertTrue(results)
        self.assertTrue(all(item.get("name") for item in results))

    def test_conseil_categories_endpoint_returns_named_categories(self):
        response = APIClient().get("/api/conseil/categories/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        results = payload.get("results", payload) if isinstance(payload, dict) else payload
        self.assertIsInstance(results, list)
        self.assertTrue(all(item.get("name") or item.get("nom") for item in results))

    def test_category_cache_invalidation_on_save_and_delete(self):
        from django.core.cache import cache
        from directory_app.models import Category

        client = APIClient()
        # 1. Requête initiale pour peupler le cache
        res1 = client.get("/api/categories/")
        self.assertEqual(res1.status_code, 200)
        self.assertIsNotNone(cache.get("categories_list_all"))

        # 2. Création d'une catégorie -> signal post_save invalide le cache
        new_cat = Category.objects.create(name="Fleurs Comestibles", slug="fleurs-comestibles")
        self.assertIsNone(cache.get("categories_list_all"))

        # 3. La nouvelle requête recharge le cache avec le nouvel élément
        res2 = client.get("/api/categories/")
        names = [c["name"] for c in res2.json()]
        self.assertIn("Fleurs Comestibles", names)
        self.assertIsNotNone(cache.get("categories_list_all"))

        # 4. Suppression -> signal post_delete invalide le cache
        new_cat.delete()
        self.assertIsNone(cache.get("categories_list_all"))


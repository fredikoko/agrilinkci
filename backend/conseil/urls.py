from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AlerteViewSet, ArticleFavoriViewSet, ArticleReviewViewSet, ArticleViewSet,
    CategorieConseilViewSet, ConseilAbonnementView, ConseilPaymentInitializeView,
    ConseilPaymentVerifyView, ConseilStatistiquesView, MarquerAlerteLueView,
)

router = DefaultRouter()
router.register("articles", ArticleViewSet, basename="conseil-article")
router.register("favoris", ArticleFavoriViewSet, basename="conseil-favori")
router.register("article-reviews", ArticleReviewViewSet, basename="conseil-article-review")
router.register("categories", CategorieConseilViewSet, basename="conseil-categorie")
router.register("alertes", AlerteViewSet, basename="conseil-alerte")


urlpatterns = [
    path("", include(router.urls)),
    path("alertes/lire/<int:pk>/", MarquerAlerteLueView.as_view(), name="conseil-alerte-lire"),
    path("statistiques/", ConseilStatistiquesView.as_view(), name="conseil-statistiques"),
    path("abonnement/", ConseilAbonnementView.as_view(), name="conseil-abonnement"),
    path("abonnement/initialize/", ConseilPaymentInitializeView.as_view(), name="conseil-abonnement-initialize"),
    path("abonnement/verify/", ConseilPaymentVerifyView.as_view(), name="conseil-abonnement-verify"),
]

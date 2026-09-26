from django.urls import path
from . import views

app_name = "web"

urlpatterns = [
    # Accueil / Marketplace
    path("", views.home_view, name="home"),

    # Vendeurs
    path("vendors/", views.vendor_list_view, name="vendor-list"),
    path("vendors/<int:pk>/", views.vendor_detail_view, name="vendor-detail"),
    path("vendors/<int:pk>/track/", views.vendor_track_contact, name="vendor-track"),

    # Conseil Agricole & Conseil Pro
    path("conseil/", views.conseil_list_view, name="conseil-list"),
    path("conseil/diagnostic/", views.conseil_diagnostic_view, name="conseil-diagnostic"),
    path("conseil/subscription/", views.conseil_subscription_view, name="conseil-subscription"),
    path("conseil/<slug:slug>/", views.conseil_detail_view, name="conseil-detail"),

    # Prestataires de services
    path("providers/", views.provider_list_view, name="provider-list"),
    path("providers/space/", views.provider_space_view, name="provider-space"),
    path("providers/<int:pk>/", views.provider_detail_view, name="provider-detail"),

    # Espace Vendeur
    path("seller/", views.seller_dashboard_view, name="seller-dashboard"),
    path("seller/stock/", views.seller_stock_view, name="seller-stock"),
    path("seller/subscription/", views.seller_subscription_view, name="seller-subscription"),

    # Authentification & Compte
    path("auth/login/", views.login_view, name="login"),
    path("auth/signup/", views.signup_view, name="signup"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("account/profile/", views.profile_view, name="profile"),
    path("account/favorites/", views.favorites_view, name="favorites"),
    path("account/favorites/toggle/", views.toggle_favorite, name="favorite-toggle"),
    path("account/notifications/", views.notifications_view, name="notifications"),

    # AJAX Helpers
    path("ajax/regions/<int:region_id>/localities/", views.ajax_localities_by_region, name="ajax-localities"),
]

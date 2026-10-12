from django.urls import path
from . import views

app_name = "web"

urlpatterns = [
    # Accueil / Marketplace
    path("", views.home_view, name="home"),

    # Vendeurs & Recherche avancée
    path("vendors/", views.vendor_list_view, name="vendor-list"),
    path("vendors/<int:pk>/", views.vendor_detail_view, name="vendor-detail"),
    path("vendors/<int:pk>/track/", views.vendor_track_contact, name="vendor-track"),
    path("search/advanced/", views.advanced_search_view, name="advanced-search"),
    path("recherche-avancee/", views.advanced_search_view, name="advanced-search-alias"),

    # Conseil Agricole & Conseil Pro
    path("conseil/", views.conseil_list_view, name="conseil-list"),
    path("conseil/espace/", views.conseil_dashboard_view, name="conseil-dashboard"),
    path("conseil/alertes/", views.alertes_list_view, name="alertes-list"),
    path("conseil/alertes/<int:pk>/lire/", views.alerte_mark_read_view, name="alerte-mark-read"),
    path("conseil/astuces/", views.tips_view, name="tips"),
    path("conseil/tips/", views.tips_view, name="tips-alias"),
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
    path("seller/analytics/", views.seller_analytics_view, name="seller-analytics"),
    path("seller/subscription/", views.seller_subscription_view, name="seller-subscription"),
    path("seller/verify-payment/", views.verify_seller_payment_view, name="seller-verify-payment"),

    # Authentification & Compte
    path("auth/login/", views.login_view, name="login"),
    path("login/", views.login_view, name="login-alias"),
    path("connexion/", views.login_view, name="connexion-alias"),
    path("accounts/login/", views.login_view, name="accounts-login-alias"),
    path("auth/signup/", views.signup_view, name="signup"),
    path("signup/", views.signup_view, name="signup-alias"),
    path("inscription/", views.signup_view, name="inscription-alias"),
    path("auth/verify-code/", views.signup_verify_view, name="verify-code"),
    path("auth/password-reset/", views.password_reset_request_view, name="password-reset-request"),
    path("auth/password-reset/confirm/", views.password_reset_confirm_view, name="password-reset-confirm"),
    path("mot-de-passe-oublie/", views.password_reset_request_view, name="password-reset-alias"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("logout/", views.logout_view, name="logout-alias"),
    path("deconnexion/", views.logout_view, name="deconnexion-alias"),
    path("account/profile/", views.profile_view, name="profile"),
    path("account/buyer/", views.buyer_profile_view, name="buyer-profile"),
    path("account/favorites/", views.favorites_view, name="favorites"),
    path("account/favorites/toggle/", views.toggle_favorite, name="favorite-toggle"),
    path("account/notifications/", views.notifications_view, name="notifications"),

    # AJAX Helpers
    path("ajax/regions/<int:region_id>/localities/", views.ajax_localities_by_region, name="ajax-localities"),
]

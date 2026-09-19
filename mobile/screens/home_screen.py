import json
import os
import re
import webbrowser
from typing import Any
from urllib.parse import urlencode

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

try:
    from ..core import *
except ImportError:
    from core import *

class HomeScreen(BaseScreen):
    regions: list[dict[str, Any]] = []
    categories: list[dict[str, Any]] = []
    localities: list[dict[str, Any]] = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.region_by_name: dict[str, dict[str, Any]] = {}
        self.category_by_name: dict[str, dict[str, Any]] = {}
        self.locality_by_name: dict[str, dict[str, Any]] = {}
        self.location_ready = False
        self.categories_loading = False
        self.skip_auto_recommendations = False
        self.build_ui()

    def build_ui(self) -> None:
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        self.scroll_view = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=dp(5))
        self.scroll_view.add_widget(content)
        header = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(8))
        title = self.make_label("AgriLink CI", size=24, color=PRIMARY, bold=True, height=50)
        title.size_hint_x = 0.62
        header.add_widget(title)
        profile_button = self.make_button("Profil", self.open_user_profile, height=42, color=(0.12, 0.50, 0.27, 1))
        profile_button.size_hint_x = 0.20
        header.add_widget(profile_button)
        notifications_button = self.make_button("Notifications", self.open_notifications, height=42, color=(0.95, 0.48, 0.08, 1), font_size=11)
        notifications_button.size_hint_x = 0.28
        header.add_widget(notifications_button)
        content.add_widget(header)

        self.location_label = self.make_label("Localisation : configurez votre région et votre localité", size=15, color=MUTED, height=34)
        content.add_widget(self.location_label)
        intro = self.make_label(
            "Vendeurs près de vous",
            size=20,
            color=TEXT,
            bold=True,
            height=38,
        )
        content.add_widget(intro)
        content.add_widget(self.make_button("Liste de tous les vendeurs par région →", self.open_vendor_list, height=42, color=(0.95, 0.48, 0.08, 1)))
        content.add_widget(self.make_button("Espace vendeur", self.open_seller, height=42, color=(0.12, 0.50, 0.27, 1)))
        provider_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        provider_row.add_widget(self.make_button("Prestataires de services →", self.open_provider_list, height=42, color=(0.18, 0.45, 0.55, 1)))
        provider_row.add_widget(self.make_button("Espace prestataire", self.open_provider_space, height=42, color=(0.25, 0.40, 0.35, 1)))
        content.add_widget(provider_row)

        # Configuration du popup pour les options de filtre
        popup_content = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))

        region_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        region_label = self.make_label("Région", size=14, color=PRIMARY, bold=True, height=40)
        region_label.size_hint_x = 0.30
        region_row.add_widget(region_label)
        self.region_spinner = Spinner(text="Chargement...", values=[], size_hint_y=None, height=dp(40), size_hint_x=0.70)
        self.configure_spinner(self.region_spinner)
        self.region_spinner.bind(text=self.on_region_selected)
        region_row.add_widget(self.region_spinner)
        popup_content.add_widget(region_row)

        locality_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        locality_label = self.make_label("Localité", size=14, color=PRIMARY, bold=True, height=40)
        locality_label.size_hint_x = 0.30
        locality_row.add_widget(locality_label)
        self.locality_spinner = Spinner(text="Choisir une localité", values=[], size_hint_y=None, height=dp(40), size_hint_x=0.70)
        self.configure_spinner(self.locality_spinner)
        locality_row.add_widget(self.locality_spinner)
        popup_content.add_widget(locality_row)

        cat_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        cat_label = self.make_label("Catégorie", size=14, color=PRIMARY, bold=True, height=40)
        cat_label.size_hint_x = 0.30
        cat_row.add_widget(cat_label)
        self.category_spinner = Spinner(
            text="Toutes catégories",
            values=["Toutes catégories"],
            size_hint_y=None,
            height=dp(40),
            size_hint_x=0.70,
        )
        self.configure_spinner(self.category_spinner, font_size=12)
        cat_row.add_widget(self.category_spinner)
        popup_content.add_widget(cat_row)

        popup_actions = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        popup_actions.add_widget(self.make_button("Appliquer", self.apply_popup_filters, height=40, color=PRIMARY))
        popup_actions.add_widget(self.make_button("Réinitialiser", self.reset_filters, height=40, color=(0.35, 0.45, 0.38, 1)))
        popup_actions.add_widget(self.make_button("Fermer", lambda *_: self.filter_popup.dismiss(), height=40, color=(0.60, 0.60, 0.60, 1)))
        popup_content.add_widget(popup_actions)

        self.filter_popup = Popup(
            title="Options de filtre",
            title_size=dp(17),
            title_color=WHITE,
            separator_color=PRIMARY,
            content=popup_content,
            size_hint=(0.92, None),
            height=dp(285),
            auto_dismiss=True,
        )

        search_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.search_input = TextInput(
            hint_text="Produit ou vendeur (ex. semence de chou)",
            multiline=False,
            size_hint_x=0.70,
            font_size=dp(14),
        )
        search_row.add_widget(self.search_input)
        self.filter_button = self.make_button("Filtres", self.open_filter_popup, height=44, color=(0.12, 0.50, 0.27, 1))
        self.filter_button.size_hint_x = 0.30
        search_row.add_widget(self.filter_button)
        content.add_widget(search_row)

        self.filter_summary_label = self.make_label("Filtres : Toutes les régions • Toutes catégories", size=12, color=MUTED, height=22)
        content.add_widget(self.filter_summary_label)

        action_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        action_row.add_widget(self.make_button("Rechercher", self.search_vendors))
        action_row.add_widget(self.make_button("Vendeurs proches", self.load_recommendations))
        action_row.add_widget(self.make_button("Réinitialiser", self.reset_filters, color=(0.35, 0.45, 0.38, 1)))
        content.add_widget(action_row)

        self.status_label = self.make_label("Chargement des régions ivoiriennes...", size=13, color=MUTED, height=28)
        content.add_widget(self.status_label)
        self.featured_label = self.make_label("Conseils à la une : chargement...", size=13, color=TEXT, height=34)
        content.add_widget(self.featured_label)
        content.add_widget(self.make_button("Ouvrir les conseils agricoles →", self.open_conseil, height=40, color=(0.90, 0.95, 0.90, 1), text_color=PRIMARY))

        self.quick_categories_content = BoxLayout(
            orientation="horizontal",
            size_hint=(None, None),
            height=dp(46),
            spacing=dp(6),
        )
        self.quick_categories_content.bind(minimum_width=self.quick_categories_content.setter("width"))
        self.quick_categories_scroll = ScrollView(size_hint_y=None, height=dp(46), do_scroll_x=True, do_scroll_y=False, bar_width=dp(4))
        self.quick_categories_scroll.add_widget(self.quick_categories_content)
        self._render_quick_categories([])
        content.add_widget(self.quick_categories_scroll)

        navigation = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        navigation.add_widget(self.make_button("Accueil", self.go_home, height=42, color=PRIMARY))
        navigation.add_widget(self.make_button("Recherche avancée", self.open_advanced_search, height=42, color=(0.35, 0.45, 0.38, 1)))
        navigation.add_widget(self.make_button("Conseil", self.open_conseil, height=42, color=(0.35, 0.45, 0.38, 1)))
        navigation.add_widget(self.make_button("Favoris", self.open_favorites, height=42, color=(0.35, 0.45, 0.38, 1)))
        navigation.add_widget(self.make_button("Profil", self.open_user_profile, height=42, color=(0.35, 0.45, 0.38, 1)))
        content.add_widget(navigation)
        self.add_widget(self.scroll_view)

    def on_pre_enter(self, *args):
        if not self.location_ready:
            Clock.schedule_once(lambda dt: self.load_locations(), 0)
        self.skip_auto_recommendations = False
        Clock.schedule_once(lambda dt: self.load_featured(), 0)

    def go_home(self, *_args) -> None:
        if hasattr(self, "scroll_view") and self.scroll_view:
            self.scroll_view.scroll_y = 1
        self.load_featured()

    def load_featured(self) -> None:
        ApiClient.request("conseil/articles/epingles/", self._featured_loaded, lambda error: None)

    def _featured_loaded(self, data: Any) -> None:
        articles = data.get("results", data) if isinstance(data, dict) else data
        titles = [article.get("titre", "") for article in articles[:2] if article.get("titre")]
        self.featured_label.text = "Conseils à la une : " + (" | ".join(titles) if titles else "aucun article publié")

    def search_category(self, category: str, *_args) -> None:
        if category in self.category_by_name:
            self.category_spinner.text = category
        self.update_filter_summary()
        self.search_vendors()

    def open_filter_popup(self, *_args) -> None:
        self.filter_popup.open()

    def apply_popup_filters(self, *_args) -> None:
        self.filter_popup.dismiss()
        self.update_filter_summary()
        self.search_vendors()

    def update_filter_summary(self) -> None:
        if not hasattr(self, "filter_summary_label"):
            return
        region = self.region_spinner.text if hasattr(self, "region_spinner") and self.region_spinner.text else "Toutes régions"
        locality = self.locality_spinner.text if hasattr(self, "locality_spinner") and self.locality_spinner.text else "Toutes localités"
        category = self.category_spinner.text if hasattr(self, "category_spinner") and self.category_spinner.text else "Toutes catégories"
        self.filter_summary_label.text = f"Filtres : {region} • {locality} • {category}"

    def open_advanced_search(self, *_args) -> None:
        self.manager.current = "advanced-search"

    def open_vendors(self, *_args) -> None:
        self.manager.current = "vendors"

    def open_notifications(self, *_args):
        self.manager.current = "notifications"

    def open_vendor_list(self, *_args) -> None:
        self.manager.current = "vendors"

    def open_provider_list(self, *_args) -> None:
        self.manager.current = "providers"

    def open_provider_space(self, *_args) -> None:
        self.manager.current = "provider-space"

    def open_favorites(self, *_args) -> None:
        self.manager.current = "favorites"

    def open_conseil(self, *_args) -> None:
        self.manager.current = "conseil"

    def open_user_profile(self, *_args) -> None:
        if not ApiClient.auth_token:
            login = self.manager.get_screen("login")
            login.next_screen = "user-profile"
            self.manager.current = "login"
            return
        self.manager.current = "user-profile"

    def open_buyer_profile(self, *_args) -> None:
        if not ApiClient.auth_token:
            login = self.manager.get_screen("login")
            login.next_screen = "buyer-profile"
            self.manager.current = "login"
            return
        self.manager.current = "buyer-profile"

    def load_recommendations(self, *_args) -> None:
        if not ApiClient.auth_token:
            self.set_status("Connectez-vous comme acheteur pour recevoir des recommandations.", (0.7, 0.1, 0.1, 1))
            return
        self.set_status("Chargement des vendeurs de votre zone...")
        ApiClient.request(
            "buyer/recommendations/",
            self._recommendations_loaded,
            lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)),
        )

    def _recommendations_loaded(self, data: Any) -> None:
        if not data.get("configured", True):
            self.set_status("Configurez votre localité pour recevoir des vendeurs proches.", (0.7, 0.1, 0.1, 1))
            self.manager.current = "buyer-profile"
            return
        location = data.get("location", {})
        self._vendors_loaded(data)
        self.location_label.text = f"Localisation : {location.get('locality', '')}, {location.get('region', '')}"
        self.set_status(f"Vendeurs recommandés autour de {location.get('locality', '')}, {location.get('region', '')}")

    def load_locations(self) -> None:
        ApiClient.request("regions/", self._regions_loaded, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)))
        cached = load_category_cache("products")
        if cached:
            self._categories_loaded(cached, from_cache=True)
        else:
            self.categories_loading = True
            self._render_quick_categories([], loading=True)
        ApiClient.request("categories/", self._categories_loaded, self._categories_error)

    def _regions_loaded(self, data: Any) -> None:
        self.regions = extract_results(data)
        self.region_by_name = {item["name"]: item for item in self.regions}
        names = list(self.region_by_name.keys()) or ["Aucune région"]
        self.region_spinner.values = names
        self.region_spinner.text = names[0]
        self.on_region_selected(self.region_spinner, names[0])
        self.location_ready = True
        self.set_status("Sélectionnez votre zone puis recherchez un intrant.")
        self.update_filter_summary()

    def _categories_loaded(self, data: Any, from_cache: bool = False) -> None:
        self.categories_loading = False
        self.categories = extract_results(data)
        if not from_cache:
            save_category_cache("products", self.categories)
        self.category_by_name = {item["name"]: item for item in self.categories if item.get("name")}
        names = list(self.category_by_name.keys())
        self.category_spinner.values = ["Toutes catégories"] + names
        self._render_quick_categories(names)
        self.update_filter_summary()

    def _categories_error(self, error: str) -> None:
        self.categories_loading = False
        if self.categories:
            self._render_quick_categories(list(self.category_by_name.keys()))
            self.set_status("Catégories hors connexion : dernières données affichées.", MUTED)
        else:
            self._render_quick_categories([], error=True)
            self.set_status(f"Catégories indisponibles : {error}", (0.7, 0.1, 0.1, 1))

    def _render_quick_categories(self, names: list[str], loading: bool = False, error: bool = False) -> None:
        self.quick_categories_content.clear_widgets()
        labels = names or (["Chargement..."] if loading else ["Catégories indisponibles"] if error else ["Aucune catégorie"])
        for label in labels:
            button = self.make_button(
                label,
                lambda btn, value=label: self.search_category(value),
                height=42,
                color=(0.90, 0.95, 0.90, 1),
                text_color=PRIMARY,
                font_size=12,
                bold=True,
            )
            button.size_hint_x = None
            button.width = max(dp(110), dp(8 * len(label) + 30))
            button.disabled = loading or error or not names
            self.quick_categories_content.add_widget(button)

    def on_region_selected(self, spinner, region_name: str) -> None:
        region = self.region_by_name.get(region_name)
        if not region:
            return
        ApiClient.request(
            f"regions/{region['id']}/localities/",
            self._localities_loaded,
            lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)),
        )

    def _localities_loaded(self, data: Any) -> None:
        self.localities = extract_results(data)
        self.locality_by_name = {item["name"]: item for item in self.localities}
        names = list(self.locality_by_name.keys()) or ["Toutes les localités"]
        self.locality_spinner.values = names
        self.locality_spinner.text = names[0]
        self.update_filter_summary()

    def reset_filters(self, *_args) -> None:
        self.search_input.text = ""
        self.category_spinner.text = "Toutes catégories"
        if self.regions:
            names = list(self.region_by_name.keys())
            if names:
                self.region_spinner.text = names[0]
                self.on_region_selected(self.region_spinner, names[0])
        if hasattr(self, "filter_popup") and self.filter_popup:
            self.filter_popup.dismiss()
        self.update_filter_summary()
        self.set_status("Filtres réinitialisés.")

    def search_vendors(self, *_args, extra_params=None) -> None:
        params = {"available": "true", "ordering": "name"}
        locality = self.locality_by_name.get(self.locality_spinner.text)
        region = self.region_by_name.get(self.region_spinner.text)
        category = self.category_by_name.get(self.category_spinner.text)
        if locality:
            params["locality"] = locality["id"]
            if locality.get("latitude") and locality.get("longitude"):
                params["near_lat"] = locality["latitude"]
                params["near_lng"] = locality["longitude"]
        if region:
            params["region"] = region["id"]
        if category:
            params["category"] = category["id"]
        query = self.search_input.text.strip()
        if query:
            params["search"] = query
        if isinstance(extra_params, dict):
            params.update(extra_params)
        self.set_status("Recherche en cours...")
        ApiClient.request(
            f"vendors/?{urlencode(params)}",
            self._vendors_loaded,
            lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)),
        )

    def _vendors_loaded(self, data: Any) -> None:
        vendors = data.get("vendors", data.get("results", [])) if isinstance(data, dict) else extract_results(data)
        results = self.manager.get_screen("results")
        results.set_results(vendors, self._criteria_summary())
        self.set_status(f"{len(vendors)} vendeur(s) trouvé(s)")
        self.manager.current = "results"

    def _criteria_summary(self) -> str:
        region = self.region_spinner.text or "Toutes les régions"
        locality = self.locality_spinner.text or "Toutes les localités"
        category = self.category_spinner.text or "Toutes catégories"
        query = self.search_input.text.strip() or "Aucun produit ou vendeur"
        return f"Région : {region} | Localité : {locality} | Catégorie : {category}\nRecherche : {query}"

    def open_vendor(self, vendor_id: int) -> None:
        detail = self.manager.get_screen("detail")
        detail.load_vendor(vendor_id)
        self.manager.current = "detail"

    def open_seller(self, *_args) -> None:
        if not ApiClient.auth_token:
            login = self.manager.get_screen("login")
            login.next_screen = "seller-subscription"
            self.manager.current = "login"
            return
        ApiClient.request(
            "auth/me/",
            self._seller_entry_loaded,
            lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)),
        )

    def _seller_entry_loaded(self, data: Any) -> None:
        account = data.get("account", {}) if isinstance(data, dict) else {}
        self.manager.current = "seller" if account.get("role") == "seller" else "seller-subscription"

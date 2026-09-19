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
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

try:
    from ..core import *
except ImportError:
    from core import *


class ResultsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vendors: list[dict[str, Any]] = []
        self.build_ui()

    def build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))

        header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        header.add_widget(self.make_button("← Filtres", self.back_to_filters, height=42, color=(0.35, 0.45, 0.38, 1)))
        header.add_widget(self.make_label("Résultats", size=22, color=PRIMARY, bold=True, height=42))
        root.add_widget(header)

        self.criteria_label = self.make_label("Résultats correspondant à vos critères", size=14, color=MUTED, height=42)
        root.add_widget(self.criteria_label)
        self.status_label = self.make_label("Aucun résultat chargé.", size=14, color=TEXT, height=34)
        root.add_widget(self.status_label)

        self.results_layout = GridLayout(cols=1, spacing=dp(10), size_hint_y=None, padding=(0, dp(4)))
        self.results_layout.bind(minimum_height=self.results_layout.setter("height"))
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        scroll.add_widget(self.results_layout)
        root.add_widget(scroll)

        root.add_widget(self.make_button("Modifier les filtres", self.back_to_filters, height=44, color=(0.95, 0.48, 0.08, 1)))
        self.add_widget(root)

    def set_results(self, vendors: list[dict[str, Any]], criteria: str = "") -> None:
        self.vendors = vendors or []
        self.criteria_label.text = criteria or "Résultats correspondant à vos critères"
        self.results_layout.clear_widgets()
        self.set_status(f"{len(self.vendors)} vendeur(s) trouvé(s)")

        if not self.vendors:
            self.results_layout.add_widget(
                self.make_label(
                    "Aucun vendeur trouvé pour ces critères.\nEssayez une autre localité, catégorie ou produit.",
                    size=16,
                    color=MUTED,
                    height=82,
                )
            )
            self.results_layout.add_widget(self.make_button("Retourner aux filtres", self.back_to_filters, height=46))
            return

        for vendor in self.vendors:
            card = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(3), size_hint_y=None, height=dp(132))
            card.bind(minimum_height=card.setter("height"))
            title = f"{vendor.get('name', 'Vendeur')}" + ("  • Vérifié" if vendor.get("is_verified") else "")
            card.add_widget(self.make_label(title, size=17, color=PRIMARY, bold=True, height=28))
            card.add_widget(self.make_label(
                f"{vendor.get('vendor_type', '').capitalize()} • {vendor.get('locality_name', '')}, {vendor.get('region_name', '')}",
                size=13,
                color=MUTED,
                height=24,
            ))
            products = ", ".join(vendor.get("product_names", [])[:3]) or "Stock disponible à confirmer"
            card.add_widget(self.make_label(f"Produits : {products}", size=13, height=28))
            card.add_widget(self.make_button("Voir le détail", lambda btn, vendor_id=vendor["id"]: self.open_vendor(vendor_id), height=36))
            self.results_layout.add_widget(card)

    def open_vendor(self, vendor_id: int) -> None:
        detail = self.manager.get_screen("detail")
        detail.load_vendor(vendor_id)
        self.manager.current = "detail"

    def back_to_filters(self, *_args) -> None:
        home = self.manager.get_screen("home")
        home.skip_auto_recommendations = True
        self.manager.current = "home"

    def go_home(self, *_args) -> None:
        self.manager.get_screen("home").skip_auto_recommendations = True
        self.manager.current = "home"

    def on_pre_enter(self, *_args) -> None:
        if not self.vendors:
            self.set_status("Utilisez les filtres pour rechercher un vendeur.")

    def on_enter(self, *_args) -> None:
        self.results_layout.parent.do_scroll_y = True
        self.results_layout.parent.scroll_y = 1

    def on_leave(self, *_args) -> None:
        pass

    def open_advanced_search(self, *_args) -> None:
        self.manager.current = "advanced-search"

    def open_favorites(self, *_args) -> None:
        self.manager.current = "favorites"

    def open_user_profile(self, *_args) -> None:
        self.manager.current = "user-profile"

    def open_buyer_profile(self, *_args) -> None:
        self.manager.current = "buyer-profile"

    def load_vendors(self, *_args) -> None:
        pass

    def search_vendors(self, *_args) -> None:
        pass

    def reset_filters(self, *_args) -> None:
        self.back_to_filters()

    def _vendors_loaded(self, data: Any) -> None:
        self.set_results(extract_results(data))

    def load_locations(self) -> None:
        pass

    def on_region_selected(self, *_args) -> None:
        pass

    def _regions_loaded(self, *_args) -> None:
        pass

    def _categories_loaded(self, *_args) -> None:
        pass

    def _localities_loaded(self, *_args) -> None:
        pass

    def _recommendations_loaded(self, data: Any) -> None:
        self.set_results(extract_results(data))

    def open_seller(self, *_args) -> None:
        self.manager.current = "seller"

    def search_category(self, category: str, *_args) -> None:
        self.back_to_filters()

    def set_status(self, message: str, color=MUTED) -> None:
        if self.status_label:
            self.status_label.text = message
            self.status_label.color = color

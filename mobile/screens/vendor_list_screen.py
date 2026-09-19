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

class VendorListScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        header.add_widget(self.make_button("←", self.go_home, height=42, color=(0.35, 0.45, 0.38, 1)))
        header.add_widget(self.make_label("Liste des vendeurs par région", size=21, color=PRIMARY, bold=True, height=42))
        root.add_widget(header)
        root.add_widget(self.make_button("Filtres et recherche avancée", self.open_advanced_search, height=42, color=(0.95, 0.48, 0.08, 1)))
        self.status_label = self.make_label("Chargement des vendeurs...", size=13, color=MUTED, height=30)
        root.add_widget(self.status_label)
        self.results_layout = GridLayout(cols=1, spacing=dp(10), size_hint_y=None, padding=(0, dp(4)))
        self.results_layout.bind(minimum_height=self.results_layout.setter("height"))
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(self.results_layout)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_pre_enter(self, *args):
        self.load_vendors()

    def load_vendors(self, *_args) -> None:
        self.set_status("Chargement des vendeurs...")
        ApiClient.request("vendors/?ordering=region__name,name", self._loaded, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)))

    def _loaded(self, data: Any) -> None:
        vendors = extract_results(data)
        self.results_layout.clear_widgets()
        vendors = sorted(vendors, key=lambda item: (item.get("region_name", ""), item.get("name", "")))
        self.set_status(f"{len(vendors)} vendeur(s) approuvé(s)")
        current_region = None
        for vendor in vendors:
            region_name = vendor.get("region_name", "Région non renseignée")
            if region_name != current_region:
                current_region = region_name
                self.results_layout.add_widget(self.make_label(f"Région : {region_name}", size=18, color=PRIMARY, bold=True, height=38))
            card = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(3), size_hint_y=None, height=dp(132))
            card.bind(minimum_height=card.setter("height"))
            card.add_widget(self.make_label(vendor.get("name", "Vendeur"), size=17, color=PRIMARY, bold=True, height=28))
            card.add_widget(self.make_label(f"{vendor.get('vendor_type', '').capitalize()} • {vendor.get('locality_name', '')}, {vendor.get('region_name', '')}", size=13, color=MUTED, height=24))
            products = ", ".join(vendor.get("product_names", [])[:3]) or "Stock disponible à confirmer"
            card.add_widget(self.make_label(f"Produits : {products}", size=13, height=28))
            card.add_widget(self.make_button("Voir le détail", lambda btn, vendor_id=vendor["id"]: self.open_vendor(vendor_id), height=36))
            self.results_layout.add_widget(card)

    def open_vendor(self, vendor_id: int) -> None:
        detail = self.manager.get_screen("detail")
        detail.load_vendor(vendor_id)
        self.manager.current = "detail"

    def open_advanced_search(self, *_args) -> None:
        self.manager.current = "advanced-search"

    def go_home(self, *_args) -> None:
        self.manager.get_screen("home").skip_auto_recommendations = True
        self.manager.current = "home"

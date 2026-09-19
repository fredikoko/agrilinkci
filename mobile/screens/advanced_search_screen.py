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

class AdvancedSearchScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self) -> None:
        scroll = ScrollView(do_scroll_x=False)
        root = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(10), size_hint_y=None)
        root.bind(minimum_height=root.setter("height"))

        root.add_widget(self.make_button("← Retour", self.go_home, height=42, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(self.make_label("Recherche avancée", size=24, color=PRIMARY, bold=True, height=48))

        root.add_widget(self.make_label("Mots-clés / Produit", size=14, color=PRIMARY, bold=True, height=28))
        self.product_input = TextInput(hint_text="Produit, ex. semence de chou", multiline=False, size_hint_y=None, height=dp(44))
        root.add_widget(self.product_input)

        root.add_widget(self.make_label("Type de vendeur", size=14, color=PRIMARY, bold=True, height=28))
        self.vendor_type_spinner = Spinner(
            text="Tous les types",
            values=["Tous les types", "grossiste", "détaillant", "coopérative"],
            size_hint_y=None,
            height=dp(44),
        )
        self.configure_spinner(self.vendor_type_spinner)
        root.add_widget(self.vendor_type_spinner)

        root.add_widget(self.make_label("Rayon de recherche géographique", size=14, color=PRIMARY, bold=True, height=28))
        self.radius_spinner = Spinner(
            text="Toutes distances",
            values=["Toutes distances", "5 km", "10 km", "25 km", "50 km"],
            size_hint_y=None,
            height=dp(44),
        )
        self.configure_spinner(self.radius_spinner)
        root.add_widget(self.radius_spinner)

        self.status_label = self.make_label("Choisissez vos critères de proximité et d'activité.", size=13, color=MUTED, height=44)
        root.add_widget(self.status_label)

        root.add_widget(self.make_button("LANCER LA RECHERCHE AVANCÉE", self.search, height=48, color=(0.95, 0.48, 0.08, 1)))
        root.add_widget(Label(size_hint_y=None, height=dp(20)))

        scroll.add_widget(root)
        self.add_widget(scroll)

    def search(self, *_args) -> None:
        extra_params = {}
        vtype = self.vendor_type_spinner.text
        if vtype in ["grossiste", "détaillant", "coopérative"]:
            extra_params["vendor_type"] = vtype

        r_text = self.radius_spinner.text
        if "km" in r_text:
            radius = re.sub(r"[^\d]", "", r_text)
            if radius:
                extra_params["radius_km"] = radius

        home = self.manager.get_screen("home")
        home.search_input.text = self.product_input.text.strip()
        home.search_vendors(extra_params=extra_params)

    def go_home(self, *_args) -> None:
        self.manager.get_screen("home").skip_auto_recommendations = True
        self.manager.current = "home"

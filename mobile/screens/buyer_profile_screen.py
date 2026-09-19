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

class BuyerProfileScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.regions: list[dict[str, Any]] = []
        self.localities: list[dict[str, Any]] = []
        self.region_by_name: dict[str, dict[str, Any]] = {}
        self.locality_by_name: dict[str, dict[str, Any]] = {}
        self.saved_locality_id = None
        self.signup_role = "buyer"
        self.build_ui()

    def build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(10))
        root.add_widget(self.make_label("Mon profil acheteur", size=23, color=PRIMARY, bold=True, height=44))
        root.add_widget(self.make_label("Indiquez votre zone pour recevoir les vendeurs proches.", size=14, color=MUTED, height=42))
        self.full_name_input = TextInput(hint_text="Nom complet", multiline=False, size_hint_y=None, height=dp(44))
        root.add_widget(self.full_name_input)
        self.phone_input = TextInput(hint_text="Téléphone (facultatif)", multiline=False, size_hint_y=None, height=dp(44))
        root.add_widget(self.phone_input)
        self.email_input = TextInput(hint_text="E-mail (facultatif)", multiline=False, size_hint_y=None, height=dp(44))
        root.add_widget(self.email_input)
        self.region_spinner = Spinner(text="Chargement des régions...", values=[], size_hint_y=None, height=dp(44))
        self.configure_spinner(self.region_spinner)
        self.region_spinner.bind(text=self.on_region_selected)
        root.add_widget(self.region_spinner)
        self.locality_spinner = Spinner(text="Choisir une localité", values=[], size_hint_y=None, height=dp(44))
        self.configure_spinner(self.locality_spinner)
        root.add_widget(self.locality_spinner)
        self.status_label = self.make_label("Chargement du profil...", size=13, color=MUTED, height=58)
        root.add_widget(self.status_label)
        root.add_widget(self.make_button("Enregistrer ma localisation", self.save_profile, height=46))
        root.add_widget(self.make_button("Voir les vendeurs proches", self.open_home, height=44, color=(0.12, 0.50, 0.27, 1)))
        root.add_widget(Label())
        self.add_widget(root)

    def on_pre_enter(self, *args):
        ApiClient.request("auth/me/", self._account_loaded, lambda error: None)
        ApiClient.request("buyer/me/", self._profile_loaded, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)))
        ApiClient.request("regions/", self._regions_loaded, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)))

    def _account_loaded(self, data: Any) -> None:
        account = data.get("account", {})
        if not self.phone_input.text:
            self.phone_input.text = account.get("phone") or ""
        if not self.email_input.text:
            self.email_input.text = account.get("email") or ""

    def _profile_loaded(self, data: Any) -> None:
        profile = data.get("profile")
        if not profile:
            self.set_status("Choisissez votre région et votre localité.")
            return
        self.full_name_input.text = profile.get("full_name", "")
        self.phone_input.text = profile.get("phone") or self.phone_input.text
        self.email_input.text = profile.get("email") or self.email_input.text
        self.saved_locality_id = profile.get("locality")
        self.saved_region_id = profile.get("region")
        self._apply_saved_region()
        self.set_status(f"Localisation actuelle : {profile.get('locality_name', '')}, {profile.get('region_name', '')}")

    def _regions_loaded(self, data: Any) -> None:
        self.regions = extract_results(data)
        self.region_by_name = {item["name"]: item for item in self.regions}
        names = list(self.region_by_name.keys()) or ["Aucune région"]
        self.region_spinner.values = names
        self._apply_saved_region()
        if not getattr(self, "saved_region_id", None) and names:
            self.region_spinner.text = names[0]

    def _apply_saved_region(self) -> None:
        region_id = getattr(self, "saved_region_id", None)
        if not region_id or not self.region_by_name:
            return
        region = next((item for item in self.regions if item["id"] == region_id), None)
        if region:
            self.region_spinner.text = region["name"]

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
        names = list(self.locality_by_name.keys()) or ["Aucune localité"]
        self.locality_spinner.values = names
        saved_id = getattr(self, "saved_locality_id", None)
        saved = next((item for item in self.localities if item["id"] == saved_id), None)
        self.locality_spinner.text = saved["name"] if saved else names[0]

    def save_profile(self, *_args) -> None:
        region = self.region_by_name.get(self.region_spinner.text)
        locality = self.locality_by_name.get(self.locality_spinner.text)
        if not region or not locality:
            self.set_status("Sélectionnez une région et une localité.", (0.7, 0.1, 0.1, 1))
            return
        self.set_status("Enregistrement de votre localisation...")
        ApiClient.request(
            "buyer/me/",
            self._profile_saved,
            lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)),
            method="PATCH",
            payload={
                "full_name": self.full_name_input.text.strip(),
                "phone": self.phone_input.text.strip(),
                "email": self.email_input.text.strip(),
                "region": region["id"],
                "locality": locality["id"],
            },
        )

    def _profile_saved(self, data: Any) -> None:
        if getattr(self, "signup_role", "buyer") == "seller":
            self.set_status("Localité enregistrée. Redirection vers l’abonnement vendeur...", PRIMARY)
            self.manager.current = "seller-subscription"
            return
        self.set_status("Profil enregistré. Les vendeurs proches sont maintenant disponibles.", PRIMARY)
        self.open_home()

    def open_home(self, *_args) -> None:
        self.manager.get_screen("home").skip_auto_recommendations = True
        self.manager.current = "home"

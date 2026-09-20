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

class SellerScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.regions: list[dict[str, Any]] = []
        self.localities: list[dict[str, Any]] = []
        self.subscription_active = False
        self.payment_reference = ""
        self.build_ui()

    def build_ui(self) -> None:
        scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp(6),
            scroll_type=["bars", "content"],
        )
        root = BoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(8),
            size_hint_y=None,
        )
        root.bind(minimum_height=root.setter("height"))
        root.add_widget(self.make_button("← Retour à l’accueil", self.go_home, height=42, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(self.make_label("Référencer mon point de vente", size=22, color=PRIMARY, bold=True, height=42))
        root.add_widget(self.make_label("Choisissez un forfait pour développer votre activité. Le forfait gratuit permet de commencer avec un catalogue limité.", size=14, color=MUTED, height=42))
        root.add_widget(self.make_button("Tableau de bord analytique", self.open_analytics, height=42, color=(0.90, 0.95, 0.90, 1), text_color=PRIMARY))
        root.add_widget(self.make_button("Gérer mes produits et mon stock", self.open_stock, height=42, color=(0.90, 0.95, 0.90, 1), text_color=PRIMARY))
        self.subscription_status_label = self.make_label("Vérification de l’abonnement...", size=13, color=MUTED, height=34)
        root.add_widget(self.subscription_status_label)
        payment_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        payment_row.add_widget(self.make_button("Payer l’abonnement", self.start_subscription_payment, height=42))
        payment_row.add_widget(self.make_button("Vérifier le paiement", self.verify_subscription_payment, height=42, color=(0.12, 0.50, 0.27, 1)))
        root.add_widget(payment_row)
        self.payment_reference_input = TextInput(hint_text="Référence Chariow après paiement", multiline=False, size_hint_y=None, height=dp(40))
        root.add_widget(self.payment_reference_input)
        self.name_input = TextInput(hint_text="Nom du vendeur ou de la coopérative", multiline=False, size_hint_y=None, height=dp(42))
        root.add_widget(self.name_input)
        self.type_spinner = Spinner(text="détaillant", values=["grossiste", "détaillant", "coopérative"], size_hint_y=None, height=dp(42))
        root.add_widget(self.type_spinner)
        self.region_spinner = Spinner(text="Chargement des régions...", values=[], size_hint_y=None, height=dp(42))
        self.configure_spinner(self.region_spinner)
        self.region_spinner.bind(text=self.on_region_selected)
        root.add_widget(self.region_spinner)
        self.locality_spinner = Spinner(text="Choisir une localité", values=[], size_hint_y=None, height=dp(42))
        self.configure_spinner(self.locality_spinner)
        root.add_widget(self.locality_spinner)
        self.phone_input = TextInput(hint_text="Téléphone", multiline=False, size_hint_y=None, height=dp(42))
        root.add_widget(self.phone_input)
        self.address_input = TextInput(hint_text="Adresse ou point de repère", multiline=False, size_hint_y=None, height=dp(42))
        root.add_widget(self.address_input)
        self.status_label = self.make_label("", size=13, color=MUTED, height=42)
        root.add_widget(self.status_label)
        root.add_widget(self.make_button("Créer ma fiche vendeur", self.submit, height=46))
        root.add_widget(Label(size_hint_y=None, height=dp(16)))
        scroll.add_widget(root)
        self.add_widget(scroll)

    def on_pre_enter(self, *args):
        self.load_subscription_status()
        if not self.regions:
            ApiClient.request("regions/", self._regions_loaded, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)))


    def load_subscription_status(self) -> None:
        ApiClient.request(
            "payments/subscription/status/",
            self._subscription_loaded,
            lambda error: self._set_subscription_status(error, False),
        )

    def _subscription_loaded(self, data: Any) -> None:
        if bool(data.get("active")):
            ends_at = data.get("ends_at", "")
            self._set_subscription_status(f"Vendeur Pro actif jusqu’au {ends_at}", True)
        ApiClient.request("auth/me/", self._seller_account_loaded, lambda error: None)
        ApiClient.request("vendors/?mine=true", self._existing_vendor_loaded, lambda error: None)

    def _seller_account_loaded(self, data: Any) -> None:
        account = data.get("account", {}) if isinstance(data, dict) else {}
        profile = data.get("buyer_profile") or data.get("profile") or {}
        if account.get("role") == "seller" and not self.subscription_active:
            self._set_subscription_status("Forfait vendeur gratuit actif — catalogue limité à 10 produits.", True)
        elif not self.subscription_active:
            self._set_subscription_status("Choisissez un forfait vendeur avant de créer votre fiche.", False)

        # Autoremplissage des données de l'utilisateur
        if not self.name_input.text and profile.get("full_name"):
            self.name_input.text = profile.get("full_name")
        if not self.phone_input.text:
            self.phone_input.text = account.get("phone") or profile.get("phone") or ""

        if profile.get("region"):
            self.saved_region_id = profile.get("region")
        if profile.get("locality"):
            self.saved_locality_id = profile.get("locality")
        self._apply_saved_region()

    def _existing_vendor_loaded(self, data: Any) -> None:
        vendors = extract_results(data)
        if vendors and isinstance(vendors, list):
            vendor = vendors[0]
            self.name_input.text = vendor.get("name") or self.name_input.text
            self.phone_input.text = vendor.get("phone") or self.phone_input.text
            self.address_input.text = vendor.get("address") or self.address_input.text
            if vendor.get("vendor_type") in self.type_spinner.values:
                self.type_spinner.text = vendor.get("vendor_type")
            if vendor.get("region"):
                self.saved_region_id = vendor.get("region")
            if vendor.get("locality"):
                self.saved_locality_id = vendor.get("locality")
            self._apply_saved_region()

    def _set_subscription_status(self, message: str, active: bool) -> None:
        self.subscription_active = active
        self.subscription_status_label.text = message
        self.subscription_status_label.color = PRIMARY if active else (0.7, 0.1, 0.1, 1)

    def start_subscription_payment(self, *_args) -> None:
        self._set_subscription_status("Initialisation du paiement Chariow...", False)
        ApiClient.request(
            "payments/subscription/initialize/",
            self._payment_initialized,
            lambda error: self._set_subscription_status(error, False),
            method="POST",
        )

    def _payment_initialized(self, data: Any) -> None:
        self.payment_reference = data.get("reference", "")
        self.payment_reference_input.text = self.payment_reference
        authorization_url = data.get("checkout_url") or data.get("authorization_url")
        if authorization_url:
            webbrowser.open(authorization_url)
            self._set_subscription_status("Paiement ouvert dans votre navigateur. Terminez-le puis cliquez sur Vérifier le paiement.", False)
        else:
            self._set_subscription_status("URL Chariow introuvable.", False)

    def verify_subscription_payment(self, *_args) -> None:
        reference = self.payment_reference_input.text.strip() or self.payment_reference
        if not reference:
            self._set_subscription_status("Saisissez ou initialisez une référence Chariow.", False)
            return
        self._set_subscription_status("Vérification du paiement...", False)
        ApiClient.request(
            "payments/subscription/verify/",
            self._payment_verified,
            lambda error: self._set_subscription_status(error, False),
            method="POST",
            payload={"reference": reference},
        )

    def _payment_verified(self, data: Any) -> None:
        ends_at = data.get("ends_at", "")
        self._set_subscription_status(f"Paiement confirmé. Abonnement actif jusqu’au {ends_at}", True)

    def _regions_loaded(self, data: Any) -> None:
        self.regions = extract_results(data)
        self.region_by_name = {item["name"]: item for item in self.regions}
        names = list(self.region_by_name.keys()) or ["Aucune région"]
        self.region_spinner.values = names
        self._apply_saved_region()

    def _apply_saved_region(self) -> None:
        region_id = getattr(self, "saved_region_id", None)
        if not region_id or not getattr(self, "region_by_name", None):
            return
        region = next((item for item in self.regions if item["id"] == region_id), None)
        if region and self.region_spinner.text != region["name"]:
            self.region_spinner.text = region["name"]
            self.on_region_selected(self.region_spinner, region["name"])

    def on_region_selected(self, spinner, region_name: str) -> None:
        region = getattr(self, "region_by_name", {}).get(region_name)
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


    def submit(self, *_args) -> None:
        if not self.subscription_active:
            self.set_status("Choisissez un forfait vendeur avant de créer votre fiche.", (0.7, 0.1, 0.1, 1))
            return
        region = getattr(self, "region_by_name", {}).get(self.region_spinner.text)
        locality = getattr(self, "locality_by_name", {}).get(self.locality_spinner.text)
        if not self.name_input.text.strip() or not self.phone_input.text.strip() or not region or not locality:
            self.set_status("Nom, téléphone, région et localité sont obligatoires.", (0.7, 0.1, 0.1, 1))
            return
        payload = {
            "name": self.name_input.text.strip(),
            "vendor_type": self.type_spinner.text,
            "region": region["id"],
            "locality": locality["id"],
            "phone": self.phone_input.text.strip(),
            "address": self.address_input.text.strip(),
        }
        self.set_status("Enregistrement en cours...")
        ApiClient.request(
            "vendors/",
            self._created,
            lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)),
            method="POST",
            payload=payload,
        )

    def _created(self, data: Any) -> None:
        self.set_status("Fiche envoyée. Elle sera visible après validation par un administrateur.", PRIMARY)
        self.name_input.text = ""
        self.phone_input.text = ""
        self.address_input.text = ""

    def open_analytics(self, *_args) -> None:
        self.manager.current = "seller-analytics"

    def open_stock(self, *_args) -> None:
        self.manager.current = "seller-stock"

    def go_home(self, *_args) -> None:
        self.manager.get_screen("home").skip_auto_recommendations = True
        self.manager.current = "home"

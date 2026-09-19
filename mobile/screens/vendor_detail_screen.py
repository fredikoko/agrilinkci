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

class VendorDetailScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vendor: dict[str, Any] = {}
        self.build_ui()

    def build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        root.add_widget(self.make_button("← Retour à la recherche", self.go_home, height=42, color=(0.35, 0.45, 0.38, 1)))
        self.content = GridLayout(cols=1, spacing=dp(6), size_hint_y=None, padding=(0, dp(6)))
        self.content.bind(minimum_height=self.content.setter("height"))
        scroll = ScrollView()
        scroll.add_widget(self.content)
        root.add_widget(scroll)
        self.add_widget(root)

    def load_vendor(self, vendor_id: int) -> None:
        self.content.clear_widgets()
        self.content.add_widget(self.make_label("Chargement de la fiche...", color=MUTED, height=50))
        ApiClient.request(
            f"vendors/{vendor_id}/",
            self._vendor_loaded,
            lambda error: self._show_error(error),
        )

    def _show_error(self, message: str) -> None:
        self.content.clear_widgets()
        self.content.add_widget(self.make_label(message, color=(0.7, 0.1, 0.1, 1), height=70))

    def _vendor_loaded(self, vendor: dict[str, Any]) -> None:
        self.vendor = vendor
        self.content.clear_widgets()
        self.content.add_widget(self.make_label(vendor["name"], size=24, color=PRIMARY, bold=True, height=44))
        self.content.add_widget(self.make_label(
            f"{vendor.get('vendor_type', '').capitalize()} — {vendor.get('locality_name', '')}, {vendor.get('region_name', '')}",
            size=15,
            color=MUTED,
            height=30,
        ))
        if vendor.get("is_verified"):
            self.content.add_widget(self.make_label("Vendeur référencé comme vérifié", size=14, color=PRIMARY, height=28))
        self.content.add_widget(self.make_label(f"Adresse : {vendor.get('address') or 'Non renseignée'}", size=14, height=30))
        self.content.add_widget(self.make_label(f"Horaires : {vendor.get('opening_hours') or 'À confirmer'}", size=14, height=30))
        self.content.add_widget(self.make_label("Stock disponible", size=18, color=PRIMARY, bold=True, height=36))
        for item in vendor.get("stock_items", []):
            product = item.get("product", {})
            label = f"• {product.get('name', '')} — {item.get('availability_label', '')} ({item.get('quantity_available', 0)} {product.get('unit', '')})"
            self.content.add_widget(self.make_label(label, size=14, height=34))
        self.content.add_widget(self.make_button("Contacter ce vendeur", self.open_contact, height=44, color=(0.95, 0.48, 0.08, 1)))
        contacts = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        contacts.add_widget(self.make_button("Appeler", self.call_vendor, height=44))
        contacts.add_widget(self.make_button("WhatsApp", self.whatsapp_vendor, height=44, color=(0.12, 0.50, 0.27, 1)))
        self.content.add_widget(contacts)

        # Section Avis & Notation
        rating_avg = vendor.get("average_rating") or 0.0
        review_cnt = vendor.get("review_count") or 0
        rating_title = f"Évaluations ({review_cnt}) — ★ {rating_avg:.1f} / 5" if rating_avg else "Évaluations (0 avis)"
        self.content.add_widget(self.make_label(rating_title, size=18, color=PRIMARY, bold=True, height=36))

        self.review_rating = 5
        self.rating_label = self.make_label("Votre note : ★★★★★ (5/5)", size=14, color=TEXT, height=30)
        self.content.add_widget(self.rating_label)

        stars_box = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(4))
        for score in range(1, 6):
            btn = Button(
                text=f"★ {score}",
                size_hint_y=None,
                height=dp(34),
                background_color=(0.95, 0.70, 0.10, 1),
                color=(1, 1, 1, 1),
            )
            btn.bind(on_release=lambda _btn, s=score: self.set_review_rating(s))
            stars_box.add_widget(btn)
        self.content.add_widget(stars_box)

        self.review_comment_input = TextInput(
            hint_text="Votre avis ou expérience (optionnel)...",
            multiline=True,
            size_hint_y=None,
            height=dp(60),
        )
        self.content.add_widget(self.review_comment_input)

        self.review_status = self.make_label("", size=13, color=MUTED, height=24)
        self.content.add_widget(self.review_status)

        self.content.add_widget(self.make_button("Publier mon avis sur ce vendeur", self.submit_vendor_review, height=40, color=PRIMARY))

    def set_review_rating(self, score: int) -> None:
        self.review_rating = score
        stars = "★" * score + "☆" * (5 - score)
        self.rating_label.text = f"Votre note : {stars} ({score}/5)"

    def submit_vendor_review(self, *_args) -> None:
        if not ApiClient.auth_token and not ApiClient.access_token:
            self.review_status.text = "Connectez-vous pour publier un avis."
            self.review_status.color = (0.8, 0.2, 0.2, 1)
            return

        payload = {
            "vendor": self.vendor.get("id"),
            "rating": self.review_rating,
            "comment": self.review_comment_input.text.strip(),
        }
        self.review_status.text = "Envoi de votre avis..."
        self.review_status.color = MUTED

        def on_ok(_res):
            self.review_status.text = "Merci ! Votre avis a été enregistré."
            self.review_status.color = (0.1, 0.6, 0.2, 1)
            self.review_comment_input.text = ""
            Clock.schedule_once(lambda _dt: self.load_vendor(self.vendor.get("id")), 1.5)

        def on_err(msg):
            self.review_status.text = f"Erreur : {msg}"
            self.review_status.color = (0.8, 0.2, 0.2, 1)

        ApiClient.request("vendor-reviews/", on_ok, on_err, method="POST", payload=payload)

    def open_contact(self, *_args) -> None:
        contact = self.manager.get_screen("contact")
        contact.load_vendor(self.vendor)
        self.manager.current = "contact"

    def call_vendor(self, *_args) -> None:
        phone = self.vendor.get("phone", "")
        if phone:
            webbrowser.open(f"tel:{phone}")

    def whatsapp_vendor(self, *_args) -> None:
        phone = re.sub(r"\D", "", self.vendor.get("whatsapp_number") or self.vendor.get("phone", ""))
        if phone:
            webbrowser.open(f"https://wa.me/{phone}")

    def go_home(self, *_args) -> None:
        self.manager.get_screen("home").skip_auto_recommendations = True
        self.manager.current = "home"


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

class ContactScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vendor: dict[str, Any] = {}
        self.build_ui()

    def build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(12))
        root.add_widget(self.make_button("← Retour", self.go_back, height=42, color=(0.35, 0.45, 0.38, 1)))
        self.title_label = self.make_label("Contacter le vendeur", size=23, color=PRIMARY, bold=True, height=48)
        root.add_widget(self.title_label)
        self.phone_label = self.make_label("Téléphone :", size=17, color=TEXT, height=40)
        root.add_widget(self.phone_label)
        root.add_widget(self.make_button("APPELER", self.call_vendor, height=50, color=(0.12, 0.50, 0.27, 1)))
        root.add_widget(self.make_button("WHATSAPP", self.whatsapp_vendor, height=50, color=(0.10, 0.55, 0.25, 1)))
        root.add_widget(self.make_label("Un message pré-rempli peut être envoyé au vendeur pour demander la disponibilité d’un produit.", size=14, color=MUTED, height=70))
        root.add_widget(Label())
        self.add_widget(root)

    def load_vendor(self, vendor: dict[str, Any]) -> None:
        self.vendor = vendor
        self.title_label.text = f"Contacter {vendor.get('name', 'le vendeur')}"
        self.phone_label.text = f"Téléphone : {vendor.get('phone', '')}"

    def call_vendor(self, *_args) -> None:
        if self.vendor.get("phone"):
            webbrowser.open(f"tel:{self.vendor['phone']}")

    def whatsapp_vendor(self, *_args) -> None:
        phone = re.sub(r"\\D", "", self.vendor.get("whatsapp_number") or self.vendor.get("phone", ""))
        if phone:
            webbrowser.open(f"https://wa.me/{phone}")

    def go_back(self, *_args) -> None:
        self.manager.current = "detail"

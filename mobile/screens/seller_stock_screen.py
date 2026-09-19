from typing import Any

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

try:
    from ..core import *
except ImportError:
    from core import *


class SellerStockScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vendor_id = None
        self.products = []
        self.product_by_name = {}
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        root.add_widget(self.make_button("← Espace vendeur", self.go_back, height=42, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(self.make_label("Gestion des produits et du stock", size=21, color=PRIMARY, bold=True, height=46))
        self.vendor_label = self.make_label("Chargement de votre fiche vendeur...", size=14, color=MUTED, height=38)
        root.add_widget(self.vendor_label)
        scroll = ScrollView(do_scroll_x=False)
        content = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        self.stock_label = self.make_label("", size=14, color=TEXT, height=180)
        content.add_widget(self.stock_label)
        content.add_widget(self.make_label("Ajouter ou mettre à jour un produit", size=18, color=PRIMARY, bold=True, height=36))
        self.product_spinner = Spinner(text="Choisir un produit", values=[], size_hint_y=None, height=dp(42))
        self.configure_spinner(self.product_spinner, font_size=12)
        content.add_widget(self.product_spinner)
        self.quantity_input = TextInput(hint_text="Quantité disponible", input_filter="int", multiline=False, size_hint_y=None, height=dp(42))
        content.add_widget(self.quantity_input)
        self.price_input = TextInput(hint_text="Prix ou indication de prix", multiline=False, size_hint_y=None, height=dp(42))
        content.add_widget(self.price_input)
        self.notes_input = TextInput(hint_text="Notes sur le produit", multiline=False, size_hint_y=None, height=dp(42))
        content.add_widget(self.notes_input)
        self.status_label = self.make_label("", size=13, color=MUTED, height=44)
        content.add_widget(self.status_label)
        content.add_widget(self.make_button("Enregistrer dans mon stock", self.save_stock, height=46, color=(0.12, 0.50, 0.27, 1)))
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_pre_enter(self, *args):
        if not ApiClient.auth_token:
            self.set_status("Connectez-vous comme vendeur.", (0.7, 0.1, 0.1, 1))
            return
        ApiClient.request("vendors/?mine=true", self._vendor_loaded, self._error)
        ApiClient.request("products/", self._products_loaded, self._error)

    def _vendor_loaded(self, data: Any):
        vendors = extract_results(data)
        if not vendors:
            self.vendor_id = None
            self.vendor_label.text = "Aucune fiche vendeur trouvée. Créez d’abord votre fiche vendeur."
            self.stock_label.text = ""
            return
        vendor = vendors[0]
        self.vendor_id = vendor.get("id")
        self.vendor_label.text = f"{vendor.get('name', 'Vendeur')} — statut : {vendor.get('approval_status', 'en attente')}"
        ApiClient.request(f"stock/?mine=true", self._stock_loaded, self._error)

    def _stock_loaded(self, data: Any):
        stock = extract_results(data)
        self.stock_label.text = "\n".join(f"{item.get('product_name', item.get('product', 'Produit'))} — {item.get('quantity_available', 0)} disponible(s) — {item.get('price_note', '')}" for item in stock) or "Votre stock est actuellement vide."

    def _products_loaded(self, data: Any):
        self.products = extract_results(data)
        self.product_by_name = {item.get("name"): item for item in self.products if item.get("name")}
        self.product_spinner.values = list(self.product_by_name) or ["Aucun produit"]
        self.product_spinner.text = self.product_spinner.values[0]

    def save_stock(self, *_args):
        product = self.product_by_name.get(self.product_spinner.text)
        if not self.vendor_id or not product:
            self.set_status("Créez une fiche vendeur et sélectionnez un produit.", (0.7, 0.1, 0.1, 1))
            return
        try:
            quantity = int(self.quantity_input.text)
        except (TypeError, ValueError):
            self.set_status("La quantité doit être un nombre entier.", (0.7, 0.1, 0.1, 1))
            return
        if quantity < 0:
            self.set_status("La quantité ne peut pas être négative.", (0.7, 0.1, 0.1, 1))
            return
        payload = {"vendor": self.vendor_id, "product": product["id"], "quantity_available": quantity, "price_note": self.price_input.text.strip(), "notes": self.notes_input.text.strip(), "is_available": quantity > 0}
        ApiClient.request("stock/", lambda data: self._saved(), self._error, method="POST", payload=payload)

    def _saved(self):
        self.set_status("Stock enregistré avec succès.", PRIMARY)
        self.quantity_input.text = ""
        self.price_input.text = ""
        self.notes_input.text = ""
        ApiClient.request("stock/?mine=true", self._stock_loaded, self._error)

    def _error(self, error):
        self.set_status(error, (0.7, 0.1, 0.1, 1))

    def set_status(self, text, color=MUTED):
        self.status_label.text = text
        self.status_label.color = color

    def go_back(self, *_args):
        self.manager.current = "seller"

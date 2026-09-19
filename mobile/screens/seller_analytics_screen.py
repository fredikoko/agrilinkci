from typing import Any

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

try:
    from ..core import *
except ImportError:
    from core import *


class SellerAnalyticsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.products = []
        self.product_by_name = {}
        self.vendor_id = None
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        root.add_widget(self.make_button("← Espace vendeur", self.go_back, height=42, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(self.make_label("Tableau de bord analytique", size=22, color=PRIMARY, bold=True, height=46))
        self.period_spinner = Spinner(text="30 derniers jours", values=["7 derniers jours", "30 derniers jours", "90 derniers jours"], size_hint_y=None, height=dp(42))
        self.configure_spinner(self.period_spinner, font_size=12)
        self.period_spinner.bind(text=lambda *_: self.load_analytics())
        root.add_widget(self.period_spinner)
        scroll = ScrollView(do_scroll_x=False)
        content = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        self.status_label = self.make_label("Chargement des statistiques...", size=13, color=MUTED, height=32)
        content.add_widget(self.status_label)
        self.stats_label = self.make_label("", size=16, color=TEXT, height=112)
        content.add_widget(self.stats_label)
        content.add_widget(self.make_label("Meilleures ventes", size=18, color=PRIMARY, bold=True, height=36))
        self.top_label = self.make_label("", size=14, color=TEXT, height=100)
        content.add_widget(self.top_label)
        content.add_widget(self.make_label("Évolution quotidienne", size=18, color=PRIMARY, bold=True, height=36))
        self.daily_label = self.make_label("", size=13, color=TEXT, height=130)
        content.add_widget(self.daily_label)
        content.add_widget(self.make_label("Enregistrer une vente directe", size=18, color=PRIMARY, bold=True, height=36))
        self.product_spinner = Spinner(text="Choisir un produit", values=[], size_hint_y=None, height=dp(42))
        self.configure_spinner(self.product_spinner, font_size=12)
        content.add_widget(self.product_spinner)
        form = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(42))
        self.quantity_input = TextInput(hint_text="Quantité", input_filter="int", multiline=False)
        self.price_input = TextInput(hint_text="Prix unitaire FCFA", input_filter="int", multiline=False)
        form.add_widget(self.quantity_input)
        form.add_widget(self.price_input)
        content.add_widget(form)
        content.add_widget(self.make_button("Enregistrer la vente", self.record_sale, height=42, color=(0.12, 0.50, 0.27, 1)))
        content.add_widget(self.make_label("Les ventes sont saisies manuellement, car AgriLink CI ne propose pas de commande en ligne.", size=12, color=MUTED, height=44))
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_pre_enter(self, *args):
        if not ApiClient.auth_token:
            self.set_status("Connectez-vous comme vendeur pour accéder aux statistiques.", (0.7, 0.1, 0.1, 1))
            return
        self.load_analytics()
        ApiClient.request("products/", self._products_loaded, lambda error: None)

    def load_analytics(self, *_args):
        days = {"7 derniers jours": 7, "30 derniers jours": 30, "90 derniers jours": 90}.get(self.period_spinner.text, 30)
        ApiClient.request(f"seller/analytics/?days={days}", self._analytics_loaded, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)))

    def _analytics_loaded(self, data: Any):
        self.vendor_id = data.get("vendor", {}).get("id")
        self.status_label.text = f"{data.get('vendor', {}).get('name', 'Vendeur')} — {data.get('period_days', 30)} jours"
        self.stats_label.text = f"Ventes enregistrées : {data.get('sales_count', 0)}\nQuantité vendue : {data.get('total_quantity', 0)}\nChiffre d’affaires : {data.get('total_revenue', 0):,} FCFA\nVente moyenne : {data.get('average_sale', 0):,} FCFA".replace(",", " ")
        top = data.get("top_products", [])
        self.top_label.text = "\n".join(f"{index}. {item.get('product_name')} — {item.get('quantity')} unités — {item.get('revenue'):,} FCFA".replace(",", " ") for index, item in enumerate(top, 1)) or "Aucune vente sur cette période."
        daily = data.get("daily", [])[-10:]
        self.daily_label.text = "\n".join(f"{row.get('day')}: {row.get('sales_count')} vente(s), {row.get('revenue'):,} FCFA".replace(",", " ") for row in daily) or "Aucune donnée quotidienne."

    def _products_loaded(self, data: Any):
        self.products = extract_results(data)
        self.product_by_name = {item.get("name"): item for item in self.products}
        self.product_spinner.values = list(self.product_by_name) or ["Aucun produit"]
        self.product_spinner.text = self.product_spinner.values[0]

    def record_sale(self, *_args):
        product = self.product_by_name.get(self.product_spinner.text)
        try:
            quantity = int(self.quantity_input.text)
            unit_price = int(self.price_input.text)
        except (TypeError, ValueError):
            self.set_status("Saisissez une quantité et un prix valides.", (0.7, 0.1, 0.1, 1))
            return
        if not product or quantity < 1 or unit_price < 0:
            self.set_status("Sélectionnez un produit et saisissez des valeurs valides.", (0.7, 0.1, 0.1, 1))
            return
        if not self.vendor_id:
            self.set_status("Chargez d’abord le tableau de bord du vendeur.", (0.7, 0.1, 0.1, 1))
            return
        self.set_status("Enregistrement de la vente...")
        ApiClient.request("seller-sales/", lambda result: self._sale_saved(), lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)), method="POST", payload={"vendor": self.vendor_id, "product": product["id"], "quantity": quantity, "unit_price": unit_price})

    def _post_sale(self, data, product, quantity, unit_price):
        pass

    def _sale_saved(self):
        self.quantity_input.text = ""
        self.price_input.text = ""
        self.set_status("Vente enregistrée.", PRIMARY)
        self.load_analytics()

    def go_back(self, *_args):
        self.manager.current = "seller"

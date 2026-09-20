import webbrowser
from typing import Any

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView

try:
    from ..core import *
except ImportError:
    from core import *


class SellerSubscriptionScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.payment_reference = ""
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        root.add_widget(self.make_button("← Retour à l’accueil", self.go_home, height=42, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(self.make_label("Abonnement Vendeur", size=22, color=PRIMARY, bold=True, height=46))
        scroll = ScrollView(do_scroll_x=False)
        content = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(self.make_label("Choisissez le plan adapté à votre activité agricole.", size=18, color=TEXT, height=58))
        content.add_widget(self.plan_card("VENDEUR GRATUIT", "0 FCFA / mois", ["Jusqu’à 10 produits", "Présence dans les résultats standards", "Gestion de vos produits et stocks", "Contact direct par téléphone et WhatsApp", "Pas de badge Pro", "Pas de promotions push"], free=True))
        content.add_widget(self.plan_card("VENDEUR PRO", "5 000 FCFA / mois", ["Produits illimités", "Affichage prioritaire dans les résultats", "Badge Vendeur Pro", "Alertes de stock", "Statistiques avancées", "15 promotions par mois", "Validation administrative de la fiche vendeur"], free=False))
        content.add_widget(self.make_label("Paiement sécurisé : Orange Money, MTN MoMo, Wave ou carte bancaire via Chariow.", size=13, color=MUTED, height=48))
        self.reference_input = TextInput(hint_text="Référence Chariow après paiement", multiline=False, size_hint_y=None, height=dp(40))
        content.add_widget(self.reference_input)
        content.add_widget(self.make_button("J’ai payé — vérifier mon abonnement", self.verify_payment, height=42, color=(0.12, 0.50, 0.27, 1)))
        self.status_label = self.make_label("", size=13, color=MUTED, height=48)
        content.add_widget(self.status_label)
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def plan_card(self, name, price, features, free=False):
        card = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(5), size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(self.make_label(name, size=18, color=PRIMARY, bold=True, height=30))
        card.add_widget(self.make_label(price, size=15, color=TEXT, height=30))
        for feature in features:
            card.add_widget(self.make_label("- " + feature, size=13, color=TEXT, height=25))
        if free:
            card.add_widget(self.make_button("Choisir le forfait gratuit", self.choose_free, height=42, color=(0.90, 0.95, 0.90, 1), text_color=PRIMARY))
        else:
            card.add_widget(self.make_button("S’abonner à Vendeur Pro", self.start_pro_payment, height=42, color=(0.12, 0.50, 0.27, 1)))
        return card

    def choose_free(self, *_args):
        if not ApiClient.auth_token:
            login = self.manager.get_screen("login")
            login.next_screen = "seller-subscription"
            self.manager.current = "login"
            return
        self.set_status("Activation du forfait vendeur gratuit...")
        ApiClient.request("payments/seller/free-activate/", self._free_activated, self._payment_error, method="POST", payload={})

    def _free_activated(self, data: Any):
        self.set_status("Forfait gratuit activé. Complétez maintenant votre fiche vendeur.", PRIMARY)
        self.manager.current = "seller"

    def start_pro_payment(self, *_args):
        if not ApiClient.auth_token:
            login = self.manager.get_screen("login")
            login.next_screen = "seller-subscription"
            self.manager.current = "login"
            return
        self.set_status("Initialisation du paiement Chariow...")
        ApiClient.request("payments/subscription/initialize/", self._payment_initialized, self._payment_error, method="POST", payload={})

    def _payment_initialized(self, data: Any):
        self.payment_reference = data.get("reference", "")
        self.reference_input.text = self.payment_reference
        url = data.get("checkout_url") or data.get("authorization_url")
        if url:
            webbrowser.open(url)
            self.set_status("Paiement ouvert. Terminez-le puis revenez vérifier la référence.")
        else:
            self.set_status("URL Chariow indisponible.", (0.7, 0.1, 0.1, 1))

    def verify_payment(self, *_args):
        reference = self.reference_input.text.strip() or self.payment_reference
        if not reference:
            self.set_status("Saisissez la référence Chariow après le paiement.", (0.7, 0.1, 0.1, 1))
            return
        ApiClient.request("payments/subscription/verify/", self._payment_verified, self._payment_error, method="POST", payload={"reference": reference})

    def _payment_verified(self, data: Any):
        self.set_status("Paiement confirmé. Votre espace vendeur est activé.", PRIMARY)
        self.manager.current = "seller"

    def _payment_error(self, error):
        self.set_status(error, (0.7, 0.1, 0.1, 1))

    def go_home(self, *_args):
        self.manager.get_screen("home").skip_auto_recommendations = True
        self.manager.current = "home"

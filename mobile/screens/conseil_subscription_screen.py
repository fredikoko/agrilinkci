import webbrowser
from typing import Any

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

try:
    from ..core import *
except ImportError:
    from core import *


class ConseilSubscriptionScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        root.add_widget(self.make_button("← Conseil agricole", self.go_back, height=42, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(self.make_label("Abonnement Conseil", size=22, color=PRIMARY, bold=True, height=46))
        scroll = ScrollView(do_scroll_x=False)
        content = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(self.make_label("Améliorez vos rendements avec AgriLink Conseil Pro.", size=18, color=TEXT, height=58))
        content.add_widget(self.plan_card("GRATUIT", "0 FCFA / mois", ["5 articles par mois", "Alertes nationales", "3 favoris", "Pas d’alertes régionales", "Pas de diagnostic"], None))
        content.add_widget(self.plan_card("CONSEIL PRO", "3 000 FCFA / mois ou 29 000 FCFA / an", ["Articles illimités", "Alertes par région et par culture", "Favoris illimités", "Historique consulté", "Diagnostic et plan de fertilisation", "Agronome : 3 chats par mois", "Quiz et export PDF"], self.start_payment))
        content.add_widget(self.make_label("Paiement sécurisé : Orange Money, MTN MoMo, Wave ou carte bancaire.", size=13, color=MUTED, height=48))
        content.add_widget(self.make_label("Offre spéciale : 14 jours gratuits pour un nouvel abonnement Conseil Pro.", size=14, color=PRIMARY, height=48))
        self.status_label = self.make_label("", size=13, color=MUTED, height=42)
        content.add_widget(self.status_label)
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def plan_card(self, name, price, features, action):
        card = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(5), size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(self.make_label(name, size=18, color=PRIMARY, bold=True, height=30))
        card.add_widget(self.make_label(price, size=15, color=TEXT, height=30))
        for feature in features:
            card.add_widget(self.make_label("- " + feature, size=13, color=TEXT, height=25))
        if action:
            card.add_widget(self.make_button("S’abonner maintenant — mensuel", action, height=40, color=(0.12, 0.50, 0.27, 1)))
            card.add_widget(self.make_button("Choisir l’offre annuelle — 29 000 FCFA", self.start_annual_payment, height=38, color=(0.90, 0.95, 0.90, 1), text_color=PRIMARY, font_size=12))
        return card

    def start_payment(self, *_args):
        if not ApiClient.auth_token:
            self.set_status("Connectez-vous avant de vous abonner.", (0.7, 0.1, 0.1, 1))
            self.manager.current = "login"
            return
        ApiClient.request("conseil/abonnement/initialize/", self._payment_ready, self._payment_error, method="POST", payload={"annual": False})

    def start_annual_payment(self, *_args):
        if not ApiClient.auth_token:
            self.set_status("Connectez-vous avant de vous abonner.", (0.7, 0.1, 0.1, 1))
            self.manager.current = "login"
            return
        ApiClient.request("conseil/abonnement/initialize/", self._payment_ready, self._payment_error, method="POST", payload={"annual": True})

    def _payment_ready(self, data: Any):
        url = data.get("authorization_url") if isinstance(data, dict) else None
        if url:
            webbrowser.open(url)
            self.set_status("Paiement ouvert. Revenez ensuite pour vérifier la référence.")
        else:
            self.set_status("URL de paiement indisponible.", (0.7, 0.1, 0.1, 1))

    def _payment_error(self, error):
        self.set_status(error, (0.7, 0.1, 0.1, 1))

    def go_back(self, *_args):
        self.manager.current = "conseil"

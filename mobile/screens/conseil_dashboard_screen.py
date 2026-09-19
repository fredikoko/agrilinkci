from typing import Any

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView

try:
    from ..core import *
except ImportError:
    from core import *


class ConseilDashboardScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        root.add_widget(self.make_button("← Conseil agricole", self.go_back, height=42, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(self.make_label("Mon Espace Conseil", size=22, color=PRIMARY, bold=True, height=46))
        scroll = ScrollView(do_scroll_x=False)
        content = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        self.identity = self.make_label("Chargement du forfait...", size=16, color=TEXT, height=34)
        content.add_widget(self.identity)
        content.add_widget(self.make_label("Vos statistiques", size=18, color=PRIMARY, bold=True, height=34))
        self.stats = self.make_label("", size=15, color=TEXT, height=100)
        content.add_widget(self.stats)
        content.add_widget(self.make_label("Mes cultures", size=18, color=PRIMARY, bold=True, height=34))
        content.add_widget(self.make_label("Tomate    Chou    Piment", size=15, color=TEXT, height=48))
        content.add_widget(self.make_label("Mon calendrier cultural", size=18, color=PRIMARY, bold=True, height=34))
        content.add_widget(self.make_label("Préparation du sol : terminée\nSemis en pépinière : en cours\nRepiquage : prochaine étape", size=15, color=TEXT, height=96))
        content.add_widget(self.make_button("Lancer un diagnostic", self.open_diagnostic, height=42, color=PRIMARY))
        content.add_widget(self.make_button("Consulter l’agronome", self.open_diagnostic, height=42, color=(0.12, 0.50, 0.27, 1)))
        content.add_widget(self.make_button("Lire un article recommandé", self.open_conseil, height=42, color=(0.90, 0.95, 0.90, 1), text_color=PRIMARY))
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_pre_enter(self, *args):
        if not ApiClient.auth_token:
            self.identity.text = "Connectez-vous pour accéder à votre espace Conseil."
            return
        ApiClient.request("conseil/abonnement/", self._subscription_loaded, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)))
        ApiClient.request("conseil/statistiques/", self._stats_loaded, lambda error: None)

    def _subscription_loaded(self, data: Any):
        self.identity.text = f"Forfait : {data.get('plan', 'Gratuit')}"

    def _stats_loaded(self, data: Any):
        self.stats.text = f"Articles lus : {data.get('articles_lus', 0)}\nFavoris : {data.get('articles_favoris', 0)}\nAlertes reçues : {data.get('alertes_recues', 0)}\nCultures suivies : {data.get('cultures_suivies', 0)}"

    def open_diagnostic(self, *_args):
        self.manager.current = "conseil-diagnostic"

    def open_conseil(self, *_args):
        self.manager.current = "conseil"

    def go_back(self, *_args):
        self.manager.current = "conseil"

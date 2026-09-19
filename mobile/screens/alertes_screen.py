from typing import Any

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView

try:
    from ..core import *
except ImportError:
    from core import *


class AlertesScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        root.add_widget(self.make_button("← Retour aux conseils", self.go_back, height=42, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(self.make_label("Alertes agricoles", size=23, color=PRIMARY, bold=True, height=48))
        root.add_widget(self.make_label("Informations locales et saisonnières affichées dans l’application.", size=13, color=MUTED, height=34))
        self.status_label = self.make_label("Chargement...", size=13, color=MUTED, height=30)
        root.add_widget(self.status_label)
        self.alert_layout = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        self.alert_layout.bind(minimum_height=self.alert_layout.setter("height"))
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        scroll.add_widget(self.alert_layout)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_pre_enter(self, *args):
        endpoint = "conseil/alertes/ma-region/" if ApiClient.auth_token else "conseil/alertes/"
        ApiClient.request(endpoint, self._loaded, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)))

    def _loaded(self, data: Any):
        alerts = data.get("results", data) if isinstance(data, dict) else data
        self.alert_layout.clear_widgets()
        self.set_status(f"{len(alerts)} alerte(s) active(s)")
        for alert in alerts:
            priority = alert.get("priorite_label", alert.get("priorite", "Moyenne"))
            card = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(3), size_hint_y=None, height=dp(126))
            card.add_widget(self.make_label(f"{priority} — {alert.get('titre', 'Alerte')}", size=16, color=PRIMARY, bold=True, height=28))
            card.add_widget(self.make_label(f"{alert.get('type_label', alert.get('type_alerte', 'Information'))} • {alert.get('region', 'Nationale')}", size=12, color=MUTED, height=22))
            card.add_widget(self.make_label(alert.get("message", ""), size=13, color=TEXT, height=40))
            if ApiClient.auth_token and not alert.get("est_lue"):
                card.add_widget(self.make_button("Marquer comme lue", lambda btn, pk=alert.get("id"): self.mark_read(pk), height=30))
            self.alert_layout.add_widget(card)

    def mark_read(self, pk: int):
        ApiClient.request(f"conseil/alertes/lire/{pk}/", lambda data: self.on_pre_enter(), lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)), method="POST", payload={})

    def go_back(self, *_args):
        self.manager.current = "conseil"

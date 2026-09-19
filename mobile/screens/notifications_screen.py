from typing import Any

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView

try:
    from ..core import *
except ImportError:
    from core import *


class NotificationsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        root.add_widget(self.make_button("← Accueil", self.go_home, height=42, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(self.make_label("Notifications", size=23, color=PRIMARY, bold=True, height=48))
        self.status_label = self.make_label("Chargement...", size=13, color=MUTED, height=30)
        root.add_widget(self.status_label)
        self.items = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        self.items.bind(minimum_height=self.items.setter("height"))
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(self.items)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_pre_enter(self, *args):
        if not ApiClient.auth_token:
            self.items.clear_widgets()
            self.set_status("Connectez-vous pour recevoir vos notifications.")
            return
        ApiClient.request("notifications/", self._loaded, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)))

    def _loaded(self, data: Any):
        self.items.clear_widgets()
        notifications = extract_results(data)
        self.set_status(f"{len(notifications)} notification(s)")
        if not notifications:
            self.items.add_widget(self.make_label("Aucune notification pour le moment.", size=15, color=MUTED, height=60))
            return
        for item in notifications:
            card = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(4), size_hint_y=None, height=dp(100))
            card.bind(minimum_height=card.setter("height"))
            card.add_widget(self.make_label(item.get("title", "Notification"), size=16, color=PRIMARY, bold=True, height=28))
            card.add_widget(self.make_label(item.get("body", ""), size=13, color=TEXT, height=42))
            if not item.get("is_read"):
                card.add_widget(self.make_button("Marquer comme lue", lambda btn, pk=item.get("id"): self.mark_read(pk), height=30))
            self.items.add_widget(card)

    def mark_read(self, pk: int):
        ApiClient.request(f"notifications/{pk}/read/", lambda data: self.on_pre_enter(), lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)), method="POST", payload={})

    def go_home(self, *_args):
        self.manager.current = "home"

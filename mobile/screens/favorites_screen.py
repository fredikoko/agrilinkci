from typing import Any

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

try:
    from ..core import *
except ImportError:
    from core import *


class FavoritesScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(10))
        root.add_widget(self.make_button("← Retour à l’accueil", self.go_home, height=42, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(self.make_label("Mes conseils favoris", size=23, color=PRIMARY, bold=True, height=48))
        self.status_label = self.make_label("Connectez-vous pour consulter vos articles favoris.", size=14, color=MUTED, height=42)
        root.add_widget(self.status_label)
        self.items_layout = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        self.items_layout.bind(minimum_height=self.items_layout.setter("height"))
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        scroll.add_widget(self.items_layout)
        root.add_widget(scroll)
        root.add_widget(self.make_button("Découvrir les conseils →", self.discover, height=46, color=(0.95, 0.48, 0.08, 1)))
        self.add_widget(root)

    def on_pre_enter(self, *args):
        self.items_layout.clear_widgets()
        if not ApiClient.auth_token:
            self.set_status("Connectez-vous pour consulter vos articles favoris.")
            return
        ApiClient.request("conseil/favoris/", self._loaded, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)))

    def _loaded(self, data: Any):
        favorites = data.get("results", data) if isinstance(data, dict) else data
        self.set_status(f"{len(favorites)} article(s) favori(s)")
        if not favorites:
            self.items_layout.add_widget(self.make_label("Aucun article favori pour le moment.", size=16, color=MUTED, height=60))
            return
        for favorite in favorites:
            article = favorite.get("article", {})
            card = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(3), size_hint_y=None, height=dp(96))
            card.add_widget(self.make_label(article.get("titre", "Article"), size=16, color=PRIMARY, bold=True, height=28))
            card.add_widget(self.make_label(article.get("resume", ""), size=13, color=TEXT, height=32))
            card.add_widget(self.make_button("Lire →", lambda btn, slug=article.get("slug"): self.open_article(slug), height=30))
            self.items_layout.add_widget(card)

    def open_article(self, slug: str):
        detail = self.manager.get_screen("article-detail")
        detail.load_article(slug)
        self.manager.current = "article-detail"

    def discover(self, *_args) -> None:
        self.manager.current = "conseil"

    def go_home(self, *_args) -> None:
        self.manager.get_screen("home").skip_auto_recommendations = True
        self.manager.current = "home"

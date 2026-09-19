from typing import Any
from urllib.parse import urlencode

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

try:
    from ..core import *
except ImportError:
    from core import *


class ConseilScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.articles = []
        self.selected_category = "Tous"
        self.categories_loading = False
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        header = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        header.add_widget(self.make_button("← Accueil", self.go_home, height=42, color=(0.35, 0.45, 0.38, 1)))
        header.add_widget(self.make_label("Conseil agricole", size=21, color=PRIMARY, bold=True, height=42))
        root.add_widget(header)
        self.search_input = TextInput(hint_text="Rechercher un article ou une culture...", multiline=False, size_hint_y=None, height=dp(42))
        self.search_input.bind(on_text_validate=self.load_articles)
        root.add_widget(self.search_input)
        self.filter_row_content = BoxLayout(orientation="horizontal", size_hint=(None, None), height=dp(42), spacing=dp(6))
        self.filter_row_content.bind(minimum_width=self.filter_row_content.setter("width"))
        self.filter_scroll = ScrollView(size_hint_y=None, height=dp(42), do_scroll_x=True, do_scroll_y=False, bar_width=dp(4))
        self.filter_scroll.add_widget(self.filter_row_content)
        self._render_category_filters([])
        root.add_widget(self.filter_scroll)
        root.add_widget(self.make_button("Voir les alertes agricoles", self.open_alertes, height=42, color=(0.95, 0.48, 0.08, 1)))
        pro_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        pro_row.add_widget(self.make_button("Abonnement Conseil", self.open_subscription, height=40, color=(0.90, 0.95, 0.90, 1), text_color=PRIMARY, font_size=12))
        pro_row.add_widget(self.make_button("Espace Conseil Pro", self.open_dashboard, height=40, color=(0.12, 0.50, 0.27, 1), font_size=12))
        root.add_widget(pro_row)
        self.status_label = self.make_label("Chargement des conseils...", size=13, color=MUTED, height=30)
        root.add_widget(self.status_label)
        self.article_layout = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None, padding=(0, dp(4)))
        self.article_layout.bind(minimum_height=self.article_layout.setter("height"))
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        scroll.add_widget(self.article_layout)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_pre_enter(self, *args):
        self.load_categories()
        self.load_articles()

    def load_categories(self) -> None:
        cached = load_category_cache("conseil")
        if cached:
            self._categories_loaded(cached, from_cache=True)
        else:
            self.categories_loading = True
            self._render_category_filters([], loading=True)
        ApiClient.request("conseil/categories/", self._categories_loaded, self._categories_error)

    def _categories_loaded(self, data: Any, from_cache: bool = False) -> None:
        self.categories_loading = False
        categories = extract_results(data)
        if not from_cache:
            save_category_cache("conseil", categories)
        names = [item.get("name") or item.get("nom") for item in categories if item.get("name") or item.get("nom")]
        self._render_category_filters(names)

    def _categories_error(self, error: str) -> None:
        self.categories_loading = False
        if self._cached_category_names():
            self._render_category_filters(self._cached_category_names())
            self.set_status("Catégories hors connexion : dernières données affichées.", MUTED)
        else:
            self._render_category_filters([], error=True)
            self.set_status(f"Catégories indisponibles : {error}", (0.7, 0.1, 0.1, 1))

    def _cached_category_names(self) -> list[str]:
        return [item.get("name") or item.get("nom") for item in load_category_cache("conseil") if item.get("name") or item.get("nom")]

    def _render_category_filters(self, names: list[str], loading: bool = False, error: bool = False) -> None:
        self.filter_row_content.clear_widgets()
        labels = ["Tous"] + (["Chargement..."] if loading else ["Catégories indisponibles"] if error else names or ["Aucune catégorie"])
        for label in labels:
            button = self.make_button(label, lambda btn, value=label: self.filter_articles(value), height=40, color=(0.90, 0.95, 0.90, 1), text_color=PRIMARY, font_size=12)
            button.size_hint_x = None
            button.width = max(dp(92), dp(8 * len(label) + 30))
            button.disabled = loading or error or (not names and label != "Tous")
            self.filter_row_content.add_widget(button)

    def load_articles(self, *_args):
        params = {}
        query = self.search_input.text.strip()
        if query:
            params["search"] = query
        if self.selected_category != "Tous" and self.selected_category != "Aucune catégorie":
            params["categorie"] = self.selected_category
        path = "conseil/articles/"
        if params:
            path += "?" + urlencode(params)
        ApiClient.request(path, self._loaded, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)))

    def filter_articles(self, category: str, *_args):
        """Filtre les articles par nom de catégorie et conserve la recherche saisie."""
        self.selected_category = category or "Tous"
        self.set_status(f"Filtrage des conseils : {self.selected_category}...")
        self.load_articles()

    def _loaded(self, data: Any):
        self.articles = data.get("results", data) if isinstance(data, dict) else data
        self.article_layout.clear_widgets()
        self.set_status(f"{len(self.articles)} conseil(s) disponible(s)")
        if not self.articles:
            self.article_layout.add_widget(self.make_label("Aucun article ne correspond à votre recherche.", size=16, color=MUTED, height=60))
            return
        from kivy.uix.image import AsyncImage

        for article in self.articles:
            img_url = article.get("image_url")
            card_h = dp(260) if img_url else dp(136)
            card = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(3), size_hint_y=None, height=card_h)
            card.bind(minimum_height=card.setter("height"))

            if img_url:
                img_widget = AsyncImage(
                    source=img_url,
                    size_hint_y=None,
                    height=dp(125),
                    fit_mode="fill",
                )
                card.add_widget(img_widget)

            title = article.get("titre", "Article")
            is_prem = article.get("est_premium")
            access = "⭐ Article Premium (Conseil Pro)" if is_prem else "Article gratuit"
            badge_color = (0.95, 0.48, 0.08, 1) if is_prem else MUTED
            card.add_widget(self.make_label(access, size=12, color=badge_color, bold=is_prem, height=20))
            card.add_widget(self.make_label(title, size=16, color=PRIMARY, bold=True, height=28))
            card.add_widget(self.make_label(f"{article.get('categorie_nom', '')} • {article.get('niveau_label', article.get('niveau', ''))}", size=12, color=MUTED, height=22))
            card.add_widget(self.make_label(article.get("resume", ""), size=13, color=TEXT, height=42))
            btn_text = "⭐ Lire l’article (Premium) →" if is_prem else "Lire l’article →"
            btn_color = (0.12, 0.50, 0.27, 1) if is_prem else PRIMARY
            card.add_widget(self.make_button(btn_text, lambda btn, slug=article.get("slug"): self.open_article(slug), height=34, color=btn_color))
            self.article_layout.add_widget(card)

    def open_article(self, slug: str):
        detail = self.manager.get_screen("article-detail")
        detail.load_article(slug)
        self.manager.current = "article-detail"

    def open_alertes(self, *_args):
        self.manager.current = "alertes"

    def open_subscription(self, *_args):
        self.manager.current = "conseil-subscription"

    def open_dashboard(self, *_args):
        self.manager.current = "conseil-dashboard"

    def go_home(self, *_args):
        self.manager.get_screen("home").skip_auto_recommendations = True
        self.manager.current = "home"

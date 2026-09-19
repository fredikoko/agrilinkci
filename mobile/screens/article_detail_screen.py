import webbrowser
from typing import Any
from urllib.parse import quote

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

try:
    from ..core import *
except ImportError:
    from core import *


class ArticleDetailScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.article = {}
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        root.add_widget(self.make_button("← Retour aux conseils", self.go_back, height=42, color=(0.35, 0.45, 0.38, 1)))

        self.title_label = self.make_label("Article", size=23, color=PRIMARY, bold=True, height=58)
        root.add_widget(self.title_label)
        self.meta_label = self.make_label("", size=13, color=MUTED, height=32)
        root.add_widget(self.meta_label)

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        content = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None, padding=(0, dp(4)))
        content.bind(minimum_height=content.setter("height"))

        # Paywall Container (Top priority when restricted)
        self.paywall_box = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None, padding=dp(12))
        self.paywall_box.bind(minimum_height=self.paywall_box.setter("height"))
        content.add_widget(self.paywall_box)

        # Article Main Body Container
        self.article_body_box = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        self.article_body_box.bind(minimum_height=self.article_body_box.setter("height"))

        self.content_container = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        self.content_container.bind(minimum_height=self.content_container.setter("height"))
        self.article_body_box.add_widget(self.content_container)

        self.favorite_button = self.make_button("Ajouter aux favoris", self.toggle_favorite, height=44, color=(0.95, 0.48, 0.08, 1))
        self.article_body_box.add_widget(self.favorite_button)
        self.article_body_box.add_widget(self.make_button("Partager sur WhatsApp", self.share, height=44, color=(0.12, 0.50, 0.27, 1)))
        self.article_body_box.add_widget(self.make_button("Voir les vendeurs associés", self.open_vendors, height=44, color=(0.35, 0.45, 0.38, 1)))

        # Section Notation & Évaluation de l'article conseil
        self.review_section = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.review_section.bind(minimum_height=self.review_section.setter("height"))
        self.article_rating_label = self.make_label("Évaluer ce conseil", size=17, color=PRIMARY, bold=True, height=34)
        self.review_section.add_widget(self.article_rating_label)

        self.article_user_rating = 5
        self.user_rating_text = self.make_label("Votre note : ★★★★★ (5/5)", size=14, color=TEXT, height=28)
        self.review_section.add_widget(self.user_rating_text)

        stars_box = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(4))
        for score in range(1, 6):
            btn = Button(
                text=f"★ {score}",
                size_hint_y=None,
                height=dp(34),
                background_color=(0.95, 0.70, 0.10, 1),
                color=(1, 1, 1, 1),
            )
            btn.bind(on_release=lambda _btn, s=score: self.set_article_rating(s))
            stars_box.add_widget(btn)
        self.review_section.add_widget(stars_box)

        from kivy.uix.textinput import TextInput
        self.review_comment = TextInput(
            hint_text="Votre commentaire ou retour d'expérience...",
            multiline=True,
            size_hint_y=None,
            height=dp(55),
        )
        self.review_section.add_widget(self.review_comment)

        self.review_status_lbl = self.make_label("", size=13, color=MUTED, height=24)
        self.review_section.add_widget(self.review_status_lbl)

        self.review_section.add_widget(self.make_button("Publier mon avis sur ce conseil", self.submit_article_review, height=40, color=PRIMARY))
        self.article_body_box.add_widget(self.review_section)

        content.add_widget(self.article_body_box)

        scroll.add_widget(content)
        root.add_widget(scroll)
        self.status_label = self.make_label("", size=13, color=MUTED, height=34)
        root.add_widget(self.status_label)
        self.add_widget(root)

    def load_article(self, slug: str):
        self.slug = slug
        self.paywall_box.clear_widgets()
        self.paywall_box.size_hint_y = None
        self.paywall_box.height = 0
        self.paywall_box.opacity = 0
        self.paywall_box.disabled = True

        self.article_body_box.opacity = 1
        self.article_body_box.disabled = False
        self.content_container.clear_widgets()
        self.content_container.add_widget(self.make_label("Chargement du conseil...", size=15, color=TEXT, height=60))

        ApiClient.request(f"conseil/articles/{slug}/", self._loaded, self._on_load_error)

    def _on_load_error(self, error: str):
        self._show_paywall(error)

    def _show_paywall(self, error_msg: str):
        self.title_label.text = "🔒 Article Premium — Conseil Pro"
        self.meta_label.text = "Accès réservé aux membres abonnés"

        self.article_body_box.opacity = 0
        self.article_body_box.disabled = True

        self.paywall_box.clear_widgets()
        self.paywall_box.opacity = 1
        self.paywall_box.disabled = False

        self.paywall_box.add_widget(self.make_label("⭐ INVITATION À L'ABONNEMENT CONSEIL PRO", size=18, color=PRIMARY, bold=True, height=36))

        info_text = (
            "Cet article agricole est réservé aux membres Conseil Pro.\n"
            "Passez à la version payante pour accéder à l'intégralité des guides, fiches techniques et alertes agronomiques !"
        )
        self.paywall_box.add_widget(self.make_label(info_text, size=14, color=TEXT, height=64))

        features_text = (
            "Avantages de votre abonnement Conseil Pro :\n"
            "• Consultation illimitée de tous les articles et guides\n"
            "• Alertes météo et sanitaires ciblées par région & culture\n"
            "• Diagnostic personnalisé et plans de fertilisation\n"
            "• Support agronome en direct par chat"
        )
        self.paywall_box.add_widget(self.make_label(features_text, size=13, color=MUTED, height=95))

        self.paywall_box.add_widget(self.make_label("Tarifs : 3 000 FCFA / mois  ou  29 000 FCFA / an", size=14, color=PRIMARY, bold=True, height=30))

        self.paywall_box.add_widget(
            self.make_button(
                "⭐ PASSER À CONSEIL PRO — SEULEMENT 3 000 FCFA/MOIS",
                self.open_subscription,
                height=52,
                color=(0.12, 0.50, 0.27, 1),
            )
        )

        self.paywall_box.add_widget(
            self.make_button(
                "Opter pour l'offre annuelle — 29 000 FCFA (Économisez)",
                self.open_subscription,
                height=44,
                color=(0.95, 0.48, 0.08, 1),
            )
        )

        if not ApiClient.auth_token and not ApiClient.access_token:
            self.paywall_box.add_widget(
                self.make_button(
                    "Se connecter à mon compte",
                    self.open_login,
                    height=42,
                    color=(0.35, 0.45, 0.38, 1),
                )
            )

    def open_subscription(self, *_args):
        self.manager.current = "conseil-subscription"

    def open_login(self, *_args):
        self.manager.current = "login"

    def _loaded(self, data: Any):
        self.article = data
        self.title_label.text = data.get("titre", "Article")
        avg = data.get("average_rating") or 0.0
        cnt = data.get("review_count") or 0
        rating_info = f" • ★ {avg:.1f}/5 ({cnt} avis)" if avg else ""
        self.meta_label.text = f"{data.get('categorie_nom', '')} • {data.get('niveau_label', '')} • {data.get('nombre_vues', 0)} vues{rating_info}"
        self.favorite_button.text = "Retirer des favoris" if data.get("est_favori") else "Ajouter aux favoris"
        self.render_article_body(data)

    def render_article_body(self, data: dict):
        self.content_container.clear_widgets()
        from kivy.uix.image import AsyncImage
        import re

        base = API_BASE_URL.rsplit("/api", 1)[0]

        def resolve_media_url(raw_url: str) -> str:
            if not raw_url:
                return ""
            if raw_url.startswith("http://") or raw_url.startswith("https://"):
                return raw_url
            clean = raw_url.lstrip("/")
            if not clean.startswith("media/") and not clean.startswith("static/"):
                clean = f"media/{clean}"
            return f"{base}/{clean}"

        # Main Banner Image
        img_url = resolve_media_url(data.get("image_url"))
        if img_url:
            self.content_container.add_widget(
                AsyncImage(
                    source=img_url,
                    size_hint_y=None,
                    height=dp(190),
                    fit_mode="contain",
                )
            )

        content_text = data.get("contenu", data.get("resume", ""))

        # Parse embedded [IMG:url] or ![alt](url) tags inserted by admins
        parts = re.split(r'(\[IMG:.+?\]|!\[.*?\]\(.+?\))', content_text)
        for part in parts:
            part = part.strip()
            if not part:
                continue

            img_match = re.match(r'\[IMG:(.+?)\]', part) or re.match(r'!\[.*?\]\((.+?)\)', part)
            if img_match:
                url = resolve_media_url(img_match.group(1).strip())
                self.content_container.add_widget(
                    AsyncImage(source=url, size_hint_y=None, height=dp(180), fit_mode="contain")
                )
            else:
                lbl = self.make_label(part, size=15, color=TEXT, height=max(dp(40), dp(22) * (len(part) // 55 + 2)))
                lbl.text_size = (None, None)
                self.content_container.add_widget(lbl)

        # Additional content images uploaded by admins
        images_contenu = data.get("images_contenu", [])
        if images_contenu:
            for item in images_contenu:
                u = resolve_media_url(item.get("image_url"))
                if u:
                    self.content_container.add_widget(
                        AsyncImage(source=u, size_hint_y=None, height=dp(180), fit_mode="contain")
                    )
                    if item.get("legende"):
                        leg = self.make_label(item["legende"], size=13, color=MUTED, height=24)
                        self.content_container.add_widget(leg)

    def set_article_rating(self, score: int):
        self.article_user_rating = score
        stars = "★" * score + "☆" * (5 - score)
        self.user_rating_text.text = f"Votre note : {stars} ({score}/5)"

    def submit_article_review(self, *_args):
        if not ApiClient.auth_token and not ApiClient.access_token:
            self.review_status_lbl.text = "Connectez-vous pour publier votre avis."
            self.review_status_lbl.color = (0.8, 0.2, 0.2, 1)
            return
        payload = {
            "article": self.article.get("id"),
            "rating": self.article_user_rating,
            "comment": self.review_comment.text.strip(),
        }
        self.review_status_lbl.text = "Envoi de votre avis..."
        self.review_status_lbl.color = MUTED

        def on_ok(_res):
            self.review_status_lbl.text = "Merci pour votre note !"
            self.review_status_lbl.color = (0.1, 0.6, 0.2, 1)
            self.review_comment.text = ""
            if self.article.get("slug"):
                Clock.schedule_once(lambda _dt: self.load_article(self.article.get("slug")), 1.5)

        def on_err(msg):
            self.review_status_lbl.text = f"Erreur : {msg}"
            self.review_status_lbl.color = (0.8, 0.2, 0.2, 1)

        ApiClient.request("conseil/article-reviews/", on_ok, on_err, method="POST", payload=payload)

    def toggle_favorite(self, *_args):
        if not ApiClient.auth_token and not ApiClient.access_token:
            self.set_status("Connectez-vous pour enregistrer vos favoris.", (0.7, 0.1, 0.1, 1))
            return
        if self.article.get("est_favori"):
            self.set_status("La suppression d’un favori se fait depuis la liste des favoris.")
            return
        ApiClient.request("conseil/favoris/", lambda data: self._favorite_done(data), lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)), method="POST", payload={"article_id": self.article.get("id")})

    def _favorite_done(self, data: Any):
        self.article["est_favori"] = True
        self.favorite_button.text = "Retirer des favoris"
        self.set_status("Article ajouté à vos favoris.", PRIMARY)

    def share(self, *_args):
        text = f"{self.article.get('titre', 'Conseil agricole')} - AgriLink CI"
        webbrowser.open(f"https://wa.me/?text={quote(text)}")

    def open_vendors(self, *_args):
        self.manager.current = "home"

    def go_back(self, *_args):
        self.manager.current = "conseil"


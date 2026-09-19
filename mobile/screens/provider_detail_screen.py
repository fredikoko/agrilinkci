import webbrowser
from typing import Any
from urllib.parse import quote

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

try:
    from ..core import *
except ImportError:
    from core import *


class ProviderDetailScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.provider: dict[str, Any] = {}
        self.review_rating = 5
        self.build_ui()

    def build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        root.add_widget(self.make_button("← Tous les prestataires", self.go_back, height=42, color=(0.35, 0.45, 0.38, 1)))

        self.content = GridLayout(cols=1, spacing=dp(8), size_hint_y=None, padding=(0, dp(6)))
        self.content.bind(minimum_height=self.content.setter("height"))

        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(self.content)
        root.add_widget(scroll)

        self.add_widget(root)

    def load_provider(self, provider_id: int) -> None:
        self.content.clear_widgets()
        self.content.add_widget(self.make_label("Chargement de la fiche prestataire...", color=MUTED, height=50))
        ApiClient.request(
            f"service-providers/{provider_id}/",
            self._provider_loaded,
            lambda error: self._show_error(error),
        )

    def _show_error(self, message: str) -> None:
        self.content.clear_widgets()
        self.content.add_widget(self.make_label(message, color=(0.7, 0.1, 0.1, 1), height=70))

    def _provider_loaded(self, provider: dict[str, Any]) -> None:
        self.provider = provider
        self.content.clear_widgets()

        # En-tête : Nom et Type
        self.content.add_widget(self.make_label(provider.get("name", "Prestataire"), size=23, color=PRIMARY, bold=True, height=44))

        p_type = provider.get("provider_type_display") or provider.get("provider_type", "")
        self.content.add_widget(self.make_label(
            f"{p_type} — {provider.get('locality_name', '')}, {provider.get('region_name', '')}",
            size=14,
            color=MUTED,
            height=28,
        ))

        # Badges : Vérifié et Disponibilité
        badges_row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        if provider.get("is_verified"):
            badges_row.add_widget(self.make_label("• Vérifié AgriLink", size=13, color=PRIMARY, bold=True, height=28))
        avail_text = "✓ Disponible pour missions" if provider.get("is_available") else "Occupé / Indisponible"
        avail_color = (0.12, 0.50, 0.27, 1) if provider.get("is_available") else (0.5, 0.5, 0.5, 1)
        badges_row.add_widget(self.make_label(avail_text, size=13, color=avail_color, bold=True, height=28))
        self.content.add_widget(badges_row)

        # Zone d'intervention
        zone = provider.get("intervention_zone") or f"{provider.get('locality_name', '')} et sa région"
        self.content.add_widget(self.make_label(f"Zone d’intervention : {zone}", size=14, height=30))
        if provider.get("years_of_experience"):
            self.content.add_widget(self.make_label(f"Expérience : {provider.get('years_of_experience')} an(s)", size=13, color=MUTED, height=24))

        # Description / Équipements
        if provider.get("description"):
            self.content.add_widget(self.make_label("Présentation & Équipements", size=16, color=PRIMARY, bold=True, height=34))
            self.content.add_widget(self.make_label(provider["description"], size=13, color=TEXT, height=64))

        # Boutons de contact direct
        self.content.add_widget(self.make_label("Contacter le prestataire", size=16, color=PRIMARY, bold=True, height=34))
        contact_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        contact_row.add_widget(self.make_button("Appeler", self.call_provider, height=44, color=PRIMARY))
        contact_row.add_widget(self.make_button("WhatsApp", self.whatsapp_provider, height=44, color=(0.12, 0.50, 0.27, 1)))
        self.content.add_widget(contact_row)

        # Prestations et tarifs
        self.content.add_widget(self.make_label("Prestations & Tarifs indicatifs", size=18, color=PRIMARY, bold=True, height=38))
        services = provider.get("services", [])
        if not services:
            self.content.add_widget(self.make_label("Tarifs et prestations à convenir directement avec le prestataire.", size=13, color=MUTED, height=32))
        else:
            for s in services:
                card = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(2), size_hint_y=None, height=dp(84))
                card.bind(minimum_height=card.setter("height"))
                card.add_widget(self.make_label(f"• {s.get('title', 'Service')}", size=15, color=PRIMARY, bold=True, height=26))
                rate_text = f"Tarif : {s.get('rate', 0):,} FCFA {s.get('unit', '')}".replace(",", " ")
                card.add_widget(self.make_label(rate_text, size=13, color=TEXT, bold=True, height=24))
                if s.get("description"):
                    card.add_widget(self.make_label(s["description"], size=12, color=MUTED, height=24))
                self.content.add_widget(card)

        # Section Avis & Évaluations
        rating_avg = provider.get("average_rating") or 0.0
        review_cnt = provider.get("review_count") or 0
        rating_title = f"Avis & Évaluations ({review_cnt}) — ★ {rating_avg:.1f} / 5" if rating_avg else "Avis & Évaluations (0 avis)"
        self.content.add_widget(self.make_label(rating_title, size=17, color=PRIMARY, bold=True, height=36))

        # Affichage des avis existants
        for r in provider.get("reviews", []):
            rev_box = BoxLayout(orientation="vertical", padding=dp(6), spacing=dp(2), size_hint_y=None, height=dp(64))
            rev_box.bind(minimum_height=rev_box.setter("height"))
            stars = "★" * int(r.get("rating", 5))
            rev_box.add_widget(self.make_label(f"{stars} par {r.get('author_name', 'Client')}", size=13, color=PRIMARY, bold=True, height=24))
            if r.get("comment"):
                rev_box.add_widget(self.make_label(f"« {r['comment']} »", size=12, color=TEXT, height=30))
            self.content.add_widget(rev_box)

        # Formulaire d'évaluation
        self.content.add_widget(self.make_label("Donner votre avis sur ce prestataire :", size=14, color=PRIMARY, bold=True, height=32))
        self.rating_label = self.make_label("Votre note : ★★★★★ (5/5)", size=13, color=TEXT, height=26)
        self.content.add_widget(self.rating_label)

        stars_box = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(4))
        for score in range(1, 6):
            btn = Button(
                text=f"★ {score}",
                size_hint_y=None,
                height=dp(32),
                background_color=(0.95, 0.70, 0.10, 1),
                color=(1, 1, 1, 1),
            )
            btn.bind(on_release=lambda _btn, s=score: self.set_rating(s))
            stars_box.add_widget(btn)
        self.content.add_widget(stars_box)

        self.comment_input = TextInput(hint_text="Votre commentaire (ex. Ponctuel et travail soigné...)", multiline=True, size_hint_y=None, height=dp(60))
        self.content.add_widget(self.comment_input)

        self.content.add_widget(self.make_button("Publier mon avis", self.submit_review, height=40, color=PRIMARY))
        self.review_status = self.make_label("", size=13, color=MUTED, height=30)
        self.content.add_widget(self.review_status)

    def set_rating(self, score: int):
        self.review_rating = score
        stars = "★" * score + "☆" * (5 - score)
        self.rating_label.text = f"Votre note : {stars} ({score}/5)"

    def submit_review(self, *_args):
        if not ApiClient.auth_token:
            login = self.manager.get_screen("login")
            login.next_screen = "provider-detail"
            self.manager.current = "login"
            return

        comment = self.comment_input.text.strip()
        payload = {
            "provider": self.provider.get("id"),
            "rating": self.review_rating,
            "comment": comment,
        }
        self.review_status.text = "Envoi de votre avis..."
        ApiClient.request(
            "provider-reviews/",
            self._review_submitted,
            lambda err: self._review_error(err),
            method="POST",
            payload=payload,
        )

    def _review_submitted(self, _data: Any):
        self.review_status.text = "Merci ! Votre avis a été publié avec succès."
        self.review_status.color = PRIMARY
        self.comment_input.text = ""
        # Recharger la fiche
        self.load_provider(self.provider.get("id"))

    def _review_error(self, error: str):
        self.review_status.text = f"Erreur : {error}"
        self.review_status.color = (0.7, 0.1, 0.1, 1)

    def call_provider(self, *_args) -> None:
        phone = self.provider.get("phone", "")
        if phone:
            webbrowser.open(f"tel:{phone}")

    def whatsapp_provider(self, *_args) -> None:
        number = self.provider.get("whatsapp_number") or self.provider.get("phone", "")
        clean_num = "".join(c for c in number if c.isdigit())
        pname = self.provider.get("name", "Prestataire")
        msg = quote(f"Bonjour {pname}, je vous contacte via AgriLink CI concernant vos prestations de services agricoles.")
        if clean_num:
            webbrowser.open(f"https://wa.me/{clean_num}?text={msg}")

    def go_back(self, *_args) -> None:
        self.manager.current = "providers"

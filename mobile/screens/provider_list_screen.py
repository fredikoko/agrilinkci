from typing import Any
from urllib.parse import urlencode

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner

try:
    from ..core import *
except ImportError:
    from core import *


SERVICE_TYPES = [
    ("Tous les types de service", ""),
    ("Mécanisation & Labour", "mecanisation"),
    ("Location de matériel", "location"),
    ("Traitement & Pulvérisation", "traitement"),
    ("Transport & Récolte", "transport"),
    ("Forage & Irrigation", "irrigation"),
    ("Main d’œuvre & Récolte", "main_doeuvre"),
    ("Conseil & Analyse", "conseil"),
]


class ProviderListScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.providers: list[dict[str, Any]] = []
        self.selected_type = ""
        self.build_ui()

    def build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))

        # En-tête
        header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        header.add_widget(self.make_button("←", self.go_home, height=42, color=(0.35, 0.45, 0.38, 1)))
        header.add_widget(self.make_label("Prestataires de services", size=20, color=PRIMARY, bold=True, height=42))
        root.add_widget(header)

        # Barre d'actions rapides : filtre par type et espace prestataire
        action_bar = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        self.type_spinner = Spinner(
            text="Tous les types de service",
            values=[label for label, _ in SERVICE_TYPES],
            size_hint_y=None,
            height=dp(42),
            size_hint_x=0.65,
        )
        self.configure_spinner(self.type_spinner, font_size=12)
        self.type_spinner.bind(text=self.on_type_changed)
        action_bar.add_widget(self.type_spinner)

        provider_space_btn = self.make_button("Espace Pro", self.open_provider_space, height=42, color=(0.12, 0.50, 0.27, 1))
        provider_space_btn.size_hint_x = 0.35
        action_bar.add_widget(provider_space_btn)
        root.add_widget(action_bar)

        self.status_label = self.make_label("Chargement des prestataires...", size=13, color=MUTED, height=28)
        root.add_widget(self.status_label)

        # Liste déroulante des résultats
        self.results_layout = GridLayout(cols=1, spacing=dp(10), size_hint_y=None, padding=(0, dp(4)))
        self.results_layout.bind(minimum_height=self.results_layout.setter("height"))
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(self.results_layout)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_pre_enter(self, *args):
        self.load_providers()

    def on_type_changed(self, _spinner, selected_label: str):
        type_code = ""
        for label, code in SERVICE_TYPES:
            if label == selected_label:
                type_code = code
                break
        self.selected_type = type_code
        self.load_providers()

    def load_providers(self, *_args) -> None:
        self.set_status("Chargement des prestataires...")
        params = {"ordering": "name"}
        if self.selected_type:
            params["provider_type"] = self.selected_type
        endpoint = f"service-providers/?{urlencode(params)}"
        ApiClient.request(endpoint, self._loaded, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)))

    def _loaded(self, data: Any) -> None:
        providers = extract_results(data)
        self.providers = providers
        self.results_layout.clear_widgets()
        self.set_status(f"{len(providers)} prestataire(s) trouvé(s)")

        if not providers:
            self.results_layout.add_widget(
                self.make_label("Aucun prestataire trouvé pour ce critère.\nEssayez un autre type de service.", size=15, color=MUTED, height=60)
            )
            return

        current_region = None
        for p in providers:
            region_name = p.get("region_name", "Région non renseignée")
            if region_name != current_region:
                current_region = region_name
                self.results_layout.add_widget(self.make_label(f"Région : {region_name}", size=17, color=PRIMARY, bold=True, height=36))

            card = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(3), size_hint_y=None, height=dp(140))
            card.bind(minimum_height=card.setter("height"))

            verified_tag = "  • Vérifié" if p.get("is_verified") else ""
            card.add_widget(self.make_label(f"{p.get('name', 'Prestataire')}{verified_tag}", size=16, color=PRIMARY, bold=True, height=28))

            p_type = p.get("provider_type_display") or p.get("provider_type", "")
            loc = f"{p.get('locality_name', '')}, {p.get('region_name', '')}"
            card.add_widget(self.make_label(f"{p_type} • {loc}", size=13, color=MUTED, height=24))

            avail_text = "✓ Disponible pour missions" if p.get("is_available") else "Occupé / Indisponible"
            avail_color = (0.12, 0.50, 0.27, 1) if p.get("is_available") else (0.5, 0.5, 0.5, 1)
            card.add_widget(self.make_label(avail_text, size=12, color=avail_color, height=22))

            services = ", ".join(p.get("service_titles", [])[:3]) or "Prestations sur demande"
            card.add_widget(self.make_label(f"Services : {services}", size=13, height=26))

            card.add_widget(self.make_button("Voir les prestations & tarifs →", lambda _btn, pid=p["id"]: self.open_provider_detail(pid), height=36))
            self.results_layout.add_widget(card)

    def open_provider_detail(self, provider_id: int) -> None:
        detail = self.manager.get_screen("provider-detail")
        detail.load_provider(provider_id)
        self.manager.current = "provider-detail"

    def open_provider_space(self, *_args) -> None:
        self.manager.current = "provider-space"

    def go_home(self, *_args) -> None:
        home = self.manager.get_screen("home")
        home.skip_auto_recommendations = True
        self.manager.current = "home"

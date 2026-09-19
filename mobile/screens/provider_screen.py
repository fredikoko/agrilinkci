from typing import Any

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

try:
    from ..core import *
except ImportError:
    from core import *


PROVIDER_TYPES = [
    ("Mécanisation & Labour", "mecanisation"),
    ("Location de matériel & engins", "location"),
    ("Traitement phytosanitaire & Pulvérisation", "traitement"),
    ("Transport & Logistique de récolte", "transport"),
    ("Forage & Irrigation", "irrigation"),
    ("Main d’œuvre & Récolte", "main_doeuvre"),
    ("Conseil technique & Analyse de sol", "conseil"),
    ("Autre service agricole", "autre"),
]

UNIT_CHOICES = ["par hectare", "par jour", "par heure", "par voyage", "forfait", "par sac", "par tonne"]


class ProviderScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.provider_profile: dict[str, Any] | None = None
        self.regions: list[dict[str, Any]] = []
        self.region_by_name: dict[str, dict[str, Any]] = {}
        self.localities: list[dict[str, Any]] = []
        self.locality_by_name: dict[str, dict[str, Any]] = {}
        self.build_ui()

    def build_ui(self) -> None:
        self.clear_widgets()
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))

        header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        header.add_widget(self.make_button("← Accueil", self.go_home, height=42, color=(0.35, 0.45, 0.38, 1)))
        header.add_widget(self.make_label("Espace Prestataire", size=20, color=PRIMARY, bold=True, height=42))
        root.add_widget(header)

        self.status_label = self.make_label("", size=13, color=MUTED, height=30)
        root.add_widget(self.status_label)

        self.content_layout = GridLayout(cols=1, spacing=dp(10), size_hint_y=None, padding=(0, dp(4)))
        self.content_layout.bind(minimum_height=self.content_layout.setter("height"))

        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(self.content_layout)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_pre_enter(self, *args):
        if not ApiClient.auth_token:
            self._render_login_required()
            return
        self.load_profile()

    def _render_login_required(self):
        self.content_layout.clear_widgets()
        self.content_layout.add_widget(
            self.make_label("Connectez-vous pour accéder à votre espace prestataire.", size=15, color=MUTED, height=50)
        )
        login_btn = self.make_button("Se connecter", self.open_login, height=44, color=PRIMARY)
        self.content_layout.add_widget(login_btn)

    def open_login(self, *_args):
        login = self.manager.get_screen("login")
        login.next_screen = "provider-space"
        self.manager.current = "login"

    def load_profile(self, *_args):
        self.set_status("Chargement du profil prestataire...")
        ApiClient.request(
            "service-providers/my_profile/",
            self._profile_loaded,
            lambda err: self._no_profile_found(),
        )

    def _profile_loaded(self, data: Any):
        self.provider_profile = data
        self.set_status("Profil prestataire chargé.", PRIMARY)
        self._render_dashboard()

    def _no_profile_found(self):
        self.provider_profile = None
        self.set_status("Aucune fiche prestataire associée à ce compte.")
        # Charger les régions pour le formulaire d'inscription
        if not self.regions:
            ApiClient.request("regions/", self._regions_loaded, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)))
        else:
            self._render_create_form()

    def _regions_loaded(self, data: Any):
        self.regions = extract_results(data)
        self.region_by_name = {item["name"]: item for item in self.regions}
        self._render_create_form()

    def _render_create_form(self):
        self.content_layout.clear_widgets()
        self.content_layout.add_widget(
            self.make_label("Créer votre fiche prestataire de services agricoles", size=17, color=PRIMARY, bold=True, height=36)
        )
        self.content_layout.add_widget(
            self.make_label("Faites connaître vos matériels et services aux agriculteurs de votre zone.", size=13, color=MUTED, height=32)
        )

        self.name_input = TextInput(hint_text="Nom de l’entreprise ou du prestataire", multiline=False, size_hint_y=None, height=dp(42))
        self.content_layout.add_widget(self.name_input)

        self.type_spinner = Spinner(
            text=PROVIDER_TYPES[0][0],
            values=[label for label, _ in PROVIDER_TYPES],
            size_hint_y=None,
            height=dp(42),
        )
        self.configure_spinner(self.type_spinner, font_size=12)
        self.content_layout.add_widget(self.type_spinner)

        # Sélecteurs Région et Localité
        names = list(self.region_by_name.keys()) or ["Aucune région"]
        self.region_spinner = Spinner(text=names[0], values=names, size_hint_y=None, height=dp(42))
        self.configure_spinner(self.region_spinner, font_size=12)
        self.region_spinner.bind(text=self.on_region_selected)
        self.content_layout.add_widget(self.region_spinner)

        self.locality_spinner = Spinner(text="Choisir une localité", values=[], size_hint_y=None, height=dp(42))
        self.configure_spinner(self.locality_spinner, font_size=12)
        self.content_layout.add_widget(self.locality_spinner)
        if names:
            self.on_region_selected(self.region_spinner, names[0])

        self.zone_input = TextInput(hint_text="Zone d’intervention couverte (ex. Korhogo, Dikodougou)", multiline=False, size_hint_y=None, height=dp(42))
        self.content_layout.add_widget(self.zone_input)

        self.phone_input = TextInput(hint_text="Numéro de téléphone d’appel", multiline=False, size_hint_y=None, height=dp(42))
        self.content_layout.add_widget(self.phone_input)

        self.whatsapp_input = TextInput(hint_text="Numéro WhatsApp (facultatif)", multiline=False, size_hint_y=None, height=dp(42))
        self.content_layout.add_widget(self.whatsapp_input)

        self.exp_input = TextInput(hint_text="Années d’expérience (ex. 5)", multiline=False, input_filter="int", size_hint_y=None, height=dp(42))
        self.content_layout.add_widget(self.exp_input)

        self.desc_input = TextInput(hint_text="Description de vos activités, engins et équipements disponibles", multiline=True, size_hint_y=None, height=dp(70))
        self.content_layout.add_widget(self.desc_input)

        submit_btn = self.make_button("Créer ma fiche prestataire", self.submit_provider_profile, height=44, color=PRIMARY)
        self.content_layout.add_widget(submit_btn)

    def on_region_selected(self, _spinner, region_name: str):
        region = self.region_by_name.get(region_name)
        if not region:
            return
        ApiClient.request(f"regions/{region['id']}/localities/", self._localities_loaded, lambda err: None)

    def _localities_loaded(self, data: Any):
        self.localities = extract_results(data)
        self.locality_by_name = {item["name"]: item for item in self.localities}
        names = list(self.locality_by_name.keys()) or ["Toutes les localités"]
        self.locality_spinner.values = names
        self.locality_spinner.text = names[0]

    def submit_provider_profile(self, *_args):
        name = self.name_input.text.strip()
        phone = self.phone_input.text.strip()
        region = self.region_by_name.get(self.region_spinner.text)
        locality = self.locality_by_name.get(self.locality_spinner.text)

        if not name or not phone:
            self.set_status("Le nom et le téléphone sont obligatoires.", (0.7, 0.1, 0.1, 1))
            return
        if not region or not locality:
            self.set_status("Sélectionnez votre région et votre localité.", (0.7, 0.1, 0.1, 1))
            return

        type_code = "mecanisation"
        for label, code in PROVIDER_TYPES:
            if label == self.type_spinner.text:
                type_code = code
                break

        payload = {
            "name": name,
            "provider_type": type_code,
            "region": region["id"],
            "locality": locality["id"],
            "intervention_zone": self.zone_input.text.strip(),
            "phone": phone,
            "whatsapp_number": self.whatsapp_input.text.strip(),
            "years_of_experience": int(self.exp_input.text.strip() or 1),
            "description": self.desc_input.text.strip(),
            "is_available": True,
        }

        self.set_status("Création de votre fiche prestataire en cours...")
        ApiClient.request(
            "service-providers/",
            self._profile_created,
            lambda err: self.set_status(f"Erreur : {err}", (0.7, 0.1, 0.1, 1)),
            method="POST",
            payload=payload,
        )

    def _profile_created(self, data: Any):
        self.set_status("Fiche prestataire créée avec succès !", PRIMARY)
        self.load_profile()

    def _render_dashboard(self):
        p = self.provider_profile or {}
        self.content_layout.clear_widgets()

        # Carte d'identité
        self.content_layout.add_widget(self.make_label(p.get("name", ""), size=22, color=PRIMARY, bold=True, height=36))
        self.content_layout.add_widget(self.make_label(
            f"{p.get('provider_type_display', '')} • {p.get('locality_name', '')}, {p.get('region_name', '')}",
            size=14, color=MUTED, height=26,
        ))

        # Bascule de disponibilité
        is_avail = p.get("is_available", True)
        avail_str = "Actuellement : DISPONIBLE pour missions" if is_avail else "Actuellement : OCCUPÉ / INDISPONIBLE"
        avail_col = (0.12, 0.50, 0.27, 1) if is_avail else (0.6, 0.2, 0.2, 1)
        self.content_layout.add_widget(self.make_label(avail_str, size=13, color=avail_col, bold=True, height=26))

        toggle_btn_text = "Passer en Occupé" if is_avail else "Passer en Disponible"
        toggle_btn = self.make_button(toggle_btn_text, self.toggle_availability, height=38, color=(0.35, 0.45, 0.38, 1))
        self.content_layout.add_widget(toggle_btn)

        # Formulaire d'ajout de service
        self.content_layout.add_widget(Label(size_hint_y=None, height=dp(10)))
        self.content_layout.add_widget(self.make_label("Ajouter une prestation à votre catalogue :", size=16, color=PRIMARY, bold=True, height=32))

        self.service_title_input = TextInput(hint_text="Intitulé du service (ex. Labour profond au tracteur)", multiline=False, size_hint_y=None, height=dp(42))
        self.content_layout.add_widget(self.service_title_input)

        row_rate = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        self.service_rate_input = TextInput(hint_text="Tarif en FCFA (ex. 35000)", input_filter="int", multiline=False, size_hint_x=0.50)
        row_rate.add_widget(self.service_rate_input)

        self.service_unit_spinner = Spinner(text=UNIT_CHOICES[0], values=UNIT_CHOICES, size_hint_x=0.50)
        self.configure_spinner(self.service_unit_spinner, font_size=12)
        row_rate.add_widget(self.service_unit_spinner)
        self.content_layout.add_widget(row_rate)

        self.service_desc_input = TextInput(hint_text="Description courte de la prestation (facultatif)", multiline=False, size_hint_y=None, height=dp(42))
        self.content_layout.add_widget(self.service_desc_input)

        add_service_btn = self.make_button("+ Ajouter cette prestation", self.submit_new_service, height=42, color=PRIMARY)
        self.content_layout.add_widget(add_service_btn)

        # Liste des prestations actuelles
        self.content_layout.add_widget(Label(size_hint_y=None, height=dp(10)))
        services = p.get("services", [])
        self.content_layout.add_widget(self.make_label(f"Vos prestations enregistrées ({len(services)}) :", size=16, color=PRIMARY, bold=True, height=32))

        if not services:
            self.content_layout.add_widget(self.make_label("Aucune prestation enregistrée pour le moment.", size=13, color=MUTED, height=30))
        else:
            for s in services:
                card = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(2), size_hint_y=None, height=dp(66))
                card.bind(minimum_height=card.setter("height"))
                card.add_widget(self.make_label(f"• {s.get('title', '')}", size=14, color=PRIMARY, bold=True, height=24))
                rate_info = f"Tarif : {s.get('rate', 0):,} FCFA {s.get('unit', '')}".replace(",", " ")
                card.add_widget(self.make_label(rate_info, size=13, color=TEXT, height=22))
                self.content_layout.add_widget(card)

    def toggle_availability(self, *_args):
        if not self.provider_profile:
            return
        new_avail = not self.provider_profile.get("is_available", True)
        pid = self.provider_profile.get("id")
        self.set_status("Mise à jour de la disponibilité...")
        ApiClient.request(
            f"service-providers/{pid}/",
            lambda data: self.load_profile(),
            lambda err: self.set_status(f"Erreur : {err}", (0.7, 0.1, 0.1, 1)),
            method="PATCH",
            payload={"is_available": new_avail},
        )

    def submit_new_service(self, *_args):
        if not self.provider_profile:
            return
        title = self.service_title_input.text.strip()
        rate_str = self.service_rate_input.text.strip()
        if not title:
            self.set_status("L’intitulé de la prestation est obligatoire.", (0.7, 0.1, 0.1, 1))
            return

        payload = {
            "provider": self.provider_profile.get("id"),
            "title": title,
            "rate": int(rate_str) if rate_str.isdigit() else 0,
            "unit": self.service_unit_spinner.text,
            "description": self.service_desc_input.text.strip(),
            "is_available": True,
        }
        self.set_status("Ajout de la prestation...")
        ApiClient.request(
            "provided-services/",
            self._service_added,
            lambda err: self.set_status(f"Erreur : {err}", (0.7, 0.1, 0.1, 1)),
            method="POST",
            payload=payload,
        )

    def _service_added(self, _data: Any):
        self.set_status("Prestation ajoutée avec succès !", PRIMARY)
        self.load_profile()

    def go_home(self, *_args) -> None:
        home = self.manager.get_screen("home")
        home.skip_auto_recommendations = True
        self.manager.current = "home"

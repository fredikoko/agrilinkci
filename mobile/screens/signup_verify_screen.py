from typing import Any

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

try:
    from ..core import *
except ImportError:
    from core import *


class SignupVerifyScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.identity = ""
        self.password = ""
        self.channel = "email"
        self.build_ui()

    def build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=(dp(24), dp(24)), spacing=dp(10))
        root.add_widget(Label(size_hint_y=None, height=dp(28)))
        root.add_widget(self.make_label("AgriLink CI", size=28, color=PRIMARY, bold=True, height=52))
        root.add_widget(self.make_label("Confirmer l’inscription", size=21, color=TEXT, bold=True, height=42))
        self.info_label = self.make_label("Saisissez le code reçu.", size=14, color=MUTED, height=60)
        root.add_widget(self.info_label)
        self.code_input = TextInput(hint_text="Code de validation à 6 chiffres", input_filter="int", multiline=False, size_hint_y=None, height=dp(48), font_size=dp(16))
        root.add_widget(self.code_input)
        root.add_widget(self.make_button("VALIDER LE CODE", self.verify_code, height=48, color=PRIMARY))
        self.status_label = self.make_label("", size=13, color=MUTED, height=58)
        root.add_widget(self.status_label)
        root.add_widget(self.make_button("Renvoyer le code", self.resend_code, height=40, color=(0.95, 0.48, 0.08, 1)))
        root.add_widget(self.make_button("Modifier l’identifiant", self.back_to_signup, height=38, color=WHITE, text_color=PRIMARY, font_size=14))
        root.add_widget(Label())
        self.add_widget(root)

    def prepare(self, identity: str, password: str) -> None:
        self.identity = identity.strip()
        self.password = password
        self.channel = "email" if "@" in self.identity else "phone"
        destination = f"l’adresse {self.identity}" if self.channel == "email" else f"le numéro {self.identity}"
        self.info_label.text = f"Un code a été envoyé sur {destination}. Saisissez-le ci-dessous."
        self.code_input.text = ""

    def verify_code(self, *_args) -> None:
        code = self.code_input.text.strip()
        if len(code) != 6:
            self.set_status("Le code doit comporter 6 chiffres.", (0.7, 0.1, 0.1, 1))
            return
        endpoint = "auth/verify-email-code/" if self.channel == "email" else "auth/verify-code/"
        payload = ({"email": self.identity, "code": code, "password": self.password} if self.channel == "email" else {"phone": self.identity, "code": code, "password": self.password})
        self.set_status("Validation en cours...")
        ApiClient.request(endpoint, self._authenticated, self._error, method="POST", payload=payload)

    def resend_code(self, *_args) -> None:
        endpoint = "auth/request-email-code/" if self.channel == "email" else "auth/request-code/"
        payload = {"email": self.identity} if self.channel == "email" else {"phone": self.identity}
        ApiClient.request(endpoint, self._resent, self._error, method="POST", payload=payload)

    def _resent(self, data: Any) -> None:
        dev_code = data.get("dev_code") if isinstance(data, dict) else None
        self.set_status("Nouveau code envoyé." + (f" Code de développement : {dev_code}" if dev_code else ""), PRIMARY)

    def _authenticated(self, data: Any) -> None:
        ApiClient.set_token(data.get("token", ""))
        profile = self.manager.get_screen("buyer-profile")
        profile.signup_role = "buyer"
        self.manager.current = "buyer-profile"

    def back_to_signup(self, *_args) -> None:
        self.manager.current = "signup"

    def set_status(self, text: str, color=MUTED) -> None:
        self.status_label.text = text
        self.status_label.color = color

    def _error(self, message: str) -> None:
        self.set_status(message, (0.7, 0.1, 0.1, 1))

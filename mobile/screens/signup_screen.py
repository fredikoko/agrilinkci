from typing import Any

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

try:
    from ..core import *
except ImportError:
    from core import *


class SignupScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=(dp(24), dp(24)), spacing=dp(10))
        root.add_widget(Label(size_hint_y=None, height=dp(28)))
        root.add_widget(self.make_label("AgriLink CI", size=28, color=PRIMARY, bold=True, height=52))
        root.add_widget(self.make_label("Créer un compte", size=21, color=TEXT, bold=True, height=42))
        root.add_widget(self.make_label("Étape 1 : vos informations de connexion", size=13, color=MUTED, height=34))
        self.identity_input = TextInput(hint_text="Numéro de téléphone ou email", multiline=False, size_hint_y=None, height=dp(48), font_size=dp(15))
        root.add_widget(self.identity_input)
        self.password_input = TextInput(hint_text="Créer un mot de passe", password=True, multiline=False, size_hint_y=None, height=dp(48), font_size=dp(15))
        root.add_widget(self.password_input)
        root.add_widget(self.make_label("Tous les nouveaux comptes commencent comme utilisateurs.", size=13, color=MUTED, height=38))
        root.add_widget(self.make_button("ENVOYER LE CODE", self.request_code, height=48, color=PRIMARY))
        self.status_label = self.make_label("", size=13, color=MUTED, height=58)
        root.add_widget(self.status_label)
        root.add_widget(self.make_button("Déjà inscrit ? Se connecter", self.open_login, height=40, color=WHITE, text_color=PRIMARY, font_size=14))
        root.add_widget(Label())
        self.add_widget(root)

    def request_code(self, *_args) -> None:
        identity = self.identity_input.text.strip()
        password = self.password_input.text
        if not identity or not password:
            self.set_status("Saisissez votre identifiant et votre mot de passe.", (0.7, 0.1, 0.1, 1))
            return
        endpoint = "auth/request-email-code/" if "@" in identity else "auth/request-code/"
        payload = {"email": identity} if "@" in identity else {"phone": identity}
        self.set_status("Envoi du code...")
        ApiClient.request(endpoint, lambda data: self._code_sent(data, identity, password), self._error, method="POST", payload=payload)

    def _code_sent(self, data: Any, identity: str, password: str) -> None:
        verify = self.manager.get_screen("signup-verify")
        verify.prepare(identity, password)
        self.manager.current = "signup-verify"

    def set_status(self, text: str, color=MUTED) -> None:
        self.status_label.text = text
        self.status_label.color = color

    def _error(self, message: str) -> None:
        self.set_status(message, (0.7, 0.1, 0.1, 1))

    def open_login(self, *_args) -> None:
        self.manager.current = "login"

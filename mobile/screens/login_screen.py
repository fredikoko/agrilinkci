from typing import Any

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

try:
    from ..core import *
except ImportError:
    from core import *


class LoginScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.next_screen = "home"
        self.mode = "login"
        self.build_ui()

    def build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=(dp(24), dp(24)), spacing=dp(10))
        root.add_widget(Label(size_hint_y=None, height=dp(28)))
        root.add_widget(self.make_label("AgriLink CI", size=28, color=PRIMARY, bold=True, height=52))
        root.add_widget(self.make_label("Connexion", size=21, color=TEXT, bold=True, height=42))

        self.identity_input = TextInput(
            hint_text="Numéro de téléphone ou email",
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            font_size=dp(15),
        )
        root.add_widget(self.identity_input)
        self.password_input = TextInput(
            hint_text="Mot de passe",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            font_size=dp(15),
        )
        root.add_widget(self.password_input)

        self.code_input = TextInput(hint_text="Code de validation à 6 chiffres", input_filter="int", multiline=False, size_hint_y=None, height=0)
        root.add_widget(self.code_input)

        self.primary_button = self.make_button("SE CONNECTER", self.submit, height=48, color=PRIMARY)
        root.add_widget(self.primary_button)
        root.add_widget(self.make_label("────────  ou  ────────", size=13, color=MUTED, height=30))

        self.signup_link = self.make_button("S’inscrire", self.show_signup, height=38, color=(1, 1, 1, 1), text_color=PRIMARY, font_size=14)
        root.add_widget(self.signup_link)
        self.reset_link = self.make_button("Mot de passe oublié ?", self.show_reset, height=38, color=(1, 1, 1, 1), text_color=PRIMARY, font_size=14)
        root.add_widget(self.reset_link)

        self.send_code_button = self.make_button("Envoyer le code d’inscription", self.request_signup_code, height=0, color=(0.95, 0.48, 0.08, 1))
        root.add_widget(self.send_code_button)
        self.status_label = self.make_label("", size=13, color=MUTED, height=58)
        root.add_widget(self.status_label)
        root.add_widget(self.make_button("Continuer sans connexion", self.continue_without_login, height=40, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(Label())
        self.add_widget(root)

    def _identity(self) -> str:
        return self.identity_input.text.strip()

    def _is_email(self) -> bool:
        return "@" in self._identity()

    def _set_visible(self, widget, height: int, visible: bool = True) -> None:
        widget.height = dp(height) if visible else 0
        widget.opacity = 1 if visible else 0
        widget.disabled = not visible

    def _clear_mode_links(self) -> None:
        self.signup_link.text = "S’inscrire"
        self.reset_link.text = "Mot de passe oublié ?"

    def show_signup(self, *_args) -> None:
        self.manager.current = "signup"

    def show_reset(self, *_args) -> None:
        self.mode = "reset"
        self._clear_mode_links()
        self.primary_button.text = "RÉINITIALISER LE MOT DE PASSE"
        self.primary_button.unbind(on_release=self.submit)
        self.primary_button.unbind(on_release=self.verify_signup_code)
        self.primary_button.bind(on_release=self.confirm_reset)
        self._set_visible(self.code_input, 44)
        self._set_visible(self.send_code_button, 44)
        self.send_code_button.unbind(on_release=self.request_signup_code)
        self.send_code_button.unbind(on_release=self.request_reset_code)
        self.send_code_button.text = "Envoyer le code de réinitialisation"
        self.send_code_button.bind(on_release=self.request_reset_code)
        self.set_status("Saisissez votre téléphone ou votre e-mail, puis demandez un code.")

    def submit(self, *_args) -> None:
        identity, password = self._identity(), self.password_input.text
        if not identity or not password:
            self.set_status("Saisissez votre identifiant et votre mot de passe.", (0.7, 0.1, 0.1, 1))
            return
        self.set_status("Connexion en cours...")
        ApiClient.request("auth/login/", self._authenticated, self._error, method="POST", payload={"identifier": identity, "password": password})

    def request_signup_code(self, *_args) -> None:
        identity, password = self._identity(), self.password_input.text
        if not identity or not password:
            self.set_status("Saisissez l’identifiant et le mot de passe à créer.", (0.7, 0.1, 0.1, 1))
            return
        endpoint = "auth/request-email-code/" if self._is_email() else "auth/request-code/"
        payload = {"email": identity} if self._is_email() else {"phone": identity}
        self.set_status("Envoi du code d’inscription...")
        ApiClient.request(endpoint, self._code_sent, self._error, method="POST", payload=payload)

    def verify_signup_code(self, *_args) -> None:
        identity, code, password = self._identity(), self.code_input.text.strip(), self.password_input.text
        if not identity or len(code) != 6 or not password:
            self.set_status("Saisissez l’identifiant, le code et le mot de passe.", (0.7, 0.1, 0.1, 1))
            return
        endpoint = "auth/verify-email-code/" if self._is_email() else "auth/verify-code/"
        payload = ({"email": identity, "code": code, "password": password} if self._is_email() else {"phone": identity, "code": code, "password": password})
        self.set_status("Validation de l’inscription...")
        ApiClient.request(endpoint, self._authenticated, self._error, method="POST", payload=payload)

    def request_reset_code(self, *_args) -> None:
        self.set_status("Envoi du code de réinitialisation...")
        ApiClient.request("auth/password-reset/request/", self._code_sent, self._error, method="POST", payload={"identifier": self._identity()})

    def confirm_reset(self, *_args) -> None:
        if not self._identity() or len(self.code_input.text.strip()) != 6 or not self.password_input.text:
            self.set_status("Saisissez l’identifiant, le code et le nouveau mot de passe.", (0.7, 0.1, 0.1, 1))
            return
        ApiClient.request("auth/password-reset/confirm/", self._reset_done, self._error, method="POST", payload={"identifier": self._identity(), "code": self.code_input.text.strip(), "password": self.password_input.text})

    def _code_sent(self, data: Any) -> None:
        dev_code = data.get("dev_code") if isinstance(data, dict) else None
        self.set_status("Code envoyé. Saisissez-le pour continuer." + (f" Code de développement : {dev_code}" if dev_code else ""), PRIMARY)

    def _reset_done(self, _data: Any) -> None:
        self.mode = "login"
        self.primary_button.text = "SE CONNECTER"
        self.primary_button.unbind(on_release=self.confirm_reset)
        self.primary_button.bind(on_release=self.submit)
        self._set_visible(self.code_input, 0, False)
        self._set_visible(self.send_code_button, 0, False)
        self.set_status("Mot de passe modifié. Vous pouvez vous connecter.", PRIMARY)

    def _authenticated(self, data: Any) -> None:
        ApiClient.set_token(data.get("token", ""))
        account = data.get("account", {})
        if account.get("role") == "buyer" and not data.get("profile_configured"):
            profile = self.manager.get_screen("buyer-profile")
            profile.signup_role = "buyer"
            self.manager.current = "buyer-profile"
        else:
            destination = self.next_screen or "home"
            self.next_screen = "home"
            if destination == "home":
                home = self.manager.get_screen("home")
                home.skip_auto_recommendations = True
            self.manager.current = destination

    def _error(self, message: str) -> None:
        self.set_status(message, (0.7, 0.1, 0.1, 1))

    def set_status(self, text: str, color=MUTED) -> None:
        self.status_label.text = text
        self.status_label.color = color

    def continue_without_login(self, *_args) -> None:
        self.manager.current = "home"

import webbrowser
from typing import Any

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

try:
    from ..core import *
except ImportError:
    from core import *


class UserProfileScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_role = "buyer"
        self.build_ui()

    def build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(10))
        root.add_widget(self.make_button("← Retour à l’accueil", self.go_home, height=42, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(self.make_label("Mon profil", size=24, color=PRIMARY, bold=True, height=44))

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        content = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None, padding=(0, dp(4)))
        content.bind(minimum_height=content.setter("height"))

        self.profile_label = self.make_label("Chargement du profil...", size=15, color=TEXT, height=90)
        content.add_widget(self.profile_label)

        content.add_widget(self.make_label("Modifier mes informations", size=18, color=PRIMARY, bold=True, height=36))
        self.full_name_input = TextInput(hint_text="Nom complet", multiline=False, size_hint_y=None, height=dp(42))
        content.add_widget(self.full_name_input)
        self.email_input = TextInput(hint_text="E-mail", multiline=False, size_hint_y=None, height=dp(42))
        content.add_widget(self.email_input)
        self.culture_input = TextInput(hint_text="Culture principale (ex: Cacao, Anacarde, Maïs)", multiline=False, size_hint_y=None, height=dp(42))
        content.add_widget(self.culture_input)

        content.add_widget(self.make_button("Enregistrer mes infos", self.save_profile_info, height=44, color=PRIMARY))
        content.add_widget(self.make_button("Modifier ma région & localité", self.open_buyer_profile, height=44, color=(0.95, 0.48, 0.08, 1)))

        # Section Changement de mot de passe
        content.add_widget(self.make_label("Changer de mot de passe", size=18, color=PRIMARY, bold=True, height=36))
        self.old_pwd_input = TextInput(hint_text="Ancien mot de passe", password=True, multiline=False, size_hint_y=None, height=dp(42))
        content.add_widget(self.old_pwd_input)
        self.new_pwd_input = TextInput(hint_text="Nouveau mot de passe (min 6 car.)", password=True, multiline=False, size_hint_y=None, height=dp(42))
        content.add_widget(self.new_pwd_input)
        content.add_widget(self.make_button("Changer le mot de passe", self.change_password, height=44, color=(0.20, 0.40, 0.60, 1)))

        self.seller_button = self.make_button(
            "Devenir vendeur — choisir un abonnement",
            self.open_seller_space,
            height=48,
            color=(0.11, 0.38, 0.22, 1),
        )
        content.add_widget(self.seller_button)

        self.payment_reference = TextInput(
            hint_text="Référence Paystack après paiement",
            multiline=False,
            size_hint_y=None,
            height=dp(44),
        )
        content.add_widget(self.payment_reference)
        content.add_widget(self.make_button(
            "J’ai payé — activer mon espace vendeur",
            self.verify_seller_payment,
            height=44,
            color=(0.12, 0.50, 0.27, 1),
        ))
        content.add_widget(self.make_button("Déconnexion", self.logout, height=44, color=(0.55, 0.18, 0.12, 1)))

        scroll.add_widget(content)
        root.add_widget(scroll)

        self.status_label = self.make_label("", size=13, color=MUTED, height=40)
        root.add_widget(self.status_label)
        self.add_widget(root)

    def on_pre_enter(self, *args):
        ApiClient.request("auth/me/", self._loaded, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)))

    def _loaded(self, data: Any) -> None:
        account = data.get("account", {})
        profile = data.get("buyer_profile") or data.get("profile") or {}
        self.current_role = account.get("role") or "buyer"
        role_label = "Vendeur" if self.current_role == "seller" else "Acheteur"
        self.profile_label.text = (
            f"Téléphone : {account.get('phone') or profile.get('phone') or 'Non renseigné'}\n"
            f"E-mail : {account.get('email') or profile.get('email') or 'Non renseigné'}\n"
            f"Rôle : {role_label}\n"
            f"Localisation : {profile.get('locality_name', 'Non configurée')}, {profile.get('region_name', '')}"
        )
        if not self.full_name_input.text:
            self.full_name_input.text = profile.get("full_name", "")
        if not self.email_input.text:
            self.email_input.text = account.get("email") or profile.get("email") or ""
        if not self.culture_input.text:
            self.culture_input.text = profile.get("culture_profile", "")

        self.seller_button.disabled = False
        self.seller_button.text = (
            "Ouvrir mon espace vendeur" if self.current_role == "seller"
            else "Devenir vendeur — choisir un abonnement"
        )

    def save_profile_info(self, *_args) -> None:
        payload = {
            "full_name": self.full_name_input.text.strip(),
            "email": self.email_input.text.strip(),
            "culture_profile": self.culture_input.text.strip(),
        }
        self.set_status("Enregistrement de votre profil...")
        ApiClient.request("buyer/me/", self._info_saved, lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)), method="PATCH", payload=payload)

    def _info_saved(self, data: Any) -> None:
        self.set_status("Profil mis à jour avec succès !", PRIMARY)
        self.on_pre_enter()

    def change_password(self, *_args) -> None:
        old_p = self.old_pwd_input.text.strip()
        new_p = self.new_pwd_input.text.strip()
        if not old_p or not new_p:
            self.set_status("Renseignez l'ancien et le nouveau mot de passe.", (0.7, 0.1, 0.1, 1))
            return
        if len(new_p) < 6:
            self.set_status("Le nouveau mot de passe doit comporter au moins 6 caractères.", (0.7, 0.1, 0.1, 1))
            return
        self.set_status("Changement du mot de passe...")
        ApiClient.request(
            "auth/change-password/",
            self._password_changed,
            lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)),
            method="POST",
            payload={"old_password": old_p, "new_password": new_p},
        )

    def _password_changed(self, data: Any) -> None:
        self.old_pwd_input.text = ""
        self.new_pwd_input.text = ""
        self.set_status("Mot de passe modifié avec succès.", PRIMARY)

    def open_seller_space(self, *_args) -> None:
        self.manager.current = "seller" if self.current_role == "seller" else "seller-subscription"

    def start_seller_subscription(self, *_args) -> None:
        if self.current_role == "seller":
            self.set_status("Votre espace vendeur est déjà activé.", PRIMARY)
            return
        self.set_status("Préparation du paiement Paystack...")
        ApiClient.request(
            "payments/subscription/initialize/",
            self._payment_initialized,
            lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)),
            method="POST",
            payload={},
        )

    def _payment_initialized(self, data: Any) -> None:
        reference = data.get("reference", "")
        authorization_url = data.get("authorization_url")
        self.payment_reference.text = reference
        if authorization_url:
            webbrowser.open(authorization_url)
            self.set_status(
                "Le paiement est ouvert dans votre navigateur. Après paiement, revenez ici et validez la référence.",
                PRIMARY,
            )
        else:
            self.set_status("URL Paystack indisponible. Utilisez la référence puis réessayez.", (0.7, 0.1, 0.1, 1))

    def verify_seller_payment(self, *_args) -> None:
        reference = self.payment_reference.text.strip()
        if not reference:
            self.set_status("Saisissez la référence Paystack après le paiement.", (0.7, 0.1, 0.1, 1))
            return
        self.set_status("Vérification du paiement en cours...")
        ApiClient.request(
            "payments/subscription/verify/",
            self._payment_verified,
            lambda error: self.set_status(error, (0.7, 0.1, 0.1, 1)),
            method="POST",
            payload={"reference": reference},
        )

    def _payment_verified(self, data: Any) -> None:
        self.set_status("Paiement confirmé. Votre espace vendeur est maintenant activé.", PRIMARY)
        self.on_pre_enter()

    def open_buyer_profile(self, *_args) -> None:
        self.manager.current = "buyer-profile"

    def logout(self, *_args) -> None:
        ApiClient.clear_token()
        self.manager.current = "login"

    def go_home(self, *_args) -> None:
        home = self.manager.get_screen("home")
        home.skip_auto_recommendations = True
        self.manager.current = "home"


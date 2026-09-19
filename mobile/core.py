import json
import os
import re
import webbrowser
from typing import Any, Callable
from urllib.parse import urlencode

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.network.urlrequest import UrlRequest
from kivy.storage.jsonstore import JsonStore
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput


def get_safe_json_store(path: str) -> JsonStore:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    json.loads(content)
                else:
                    with open(path, "w", encoding="utf-8") as fw:
                        fw.write("{}")
        except Exception:
            try:
                with open(path, "w", encoding="utf-8") as fw:
                    fw.write("{}")
            except Exception:
                pass
    return JsonStore(path)


API_BASE_URL = os.getenv("AGRILINK_API_URL", "http://127.0.0.1:8000/api").rstrip("/")
API_TIMEOUT_SECONDS = float(os.getenv("AGRILINK_API_TIMEOUT", "15"))

try:
    import certifi
    SSL_CA_PATH = certifi.where()
except Exception:
    SSL_CA_PATH = None

SESSION_STORE = get_safe_json_store(os.path.join(os.path.expanduser("~"), ".agrilink_session.json"))
CATEGORY_CACHE_STORE = get_safe_json_store(os.path.join(os.path.expanduser("~"), ".agrilink_categories.json"))
OFFLINE_QUEUE_STORE = get_safe_json_store(os.path.join(os.path.expanduser("~"), ".agrilink_offline.json"))

PRIMARY = (0.11, 0.38, 0.22, 1)
SECONDARY = (0.90, 0.95, 0.90, 1)
TEXT = (0.12, 0.16, 0.13, 1)
MUTED = (0.35, 0.40, 0.36, 1)
WHITE = (1, 1, 1, 1)

Window.clearcolor = WHITE


def extract_results(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and "results" in payload:
        return payload["results"]
    return payload if isinstance(payload, list) else []


def load_category_cache(namespace: str) -> list[dict[str, Any]]:
    """Retourne les catégories précédemment chargées, ou une liste vide hors cache."""
    if not CATEGORY_CACHE_STORE.exists(namespace):
        return []
    try:
        value = CATEGORY_CACHE_STORE.get(namespace).get("items", [])
        return value if isinstance(value, list) else []
    except (KeyError, TypeError, ValueError):
        return []


def save_category_cache(namespace: str, categories: list[dict[str, Any]]) -> None:
    """Enregistre uniquement les catégories valides pour le prochain affichage hors connexion."""
    if isinstance(categories, list):
        CATEGORY_CACHE_STORE.put(namespace, items=categories)


class ApiClient:
    auth_token = SESSION_STORE.get("session").get("token", "") if SESSION_STORE.exists("session") else ""
    access_token = SESSION_STORE.get("session").get("access", "") if SESSION_STORE.exists("session") else ""
    refresh_token = SESSION_STORE.get("session").get("refresh", "") if SESSION_STORE.exists("session") else ""

    @classmethod
    def set_tokens(cls, token: str = "", access: str = "", refresh: str = "") -> None:
        cls.auth_token = token or ""
        cls.access_token = access or ""
        cls.refresh_token = refresh or ""
        if cls.auth_token or cls.access_token:
            SESSION_STORE.put(
                "session",
                token=cls.auth_token,
                access=cls.access_token,
                refresh=cls.refresh_token,
            )
        elif SESSION_STORE.exists("session"):
            SESSION_STORE.delete("session")

    @classmethod
    def set_token(cls, token: str) -> None:
        cls.set_tokens(token=token)

    @classmethod
    def clear_token(cls) -> None:
        cls.set_tokens("", "", "")

    @classmethod
    def queue_offline_action(cls, path: str, method: str, payload: dict[str, Any] | None) -> None:
        if path.lstrip("/").startswith(("payments/", "auth/")):
            return
        import time
        action_id = f"action_{int(time.time() * 1000)}"
        OFFLINE_QUEUE_STORE.put(action_id, path=path, method=method, payload=payload or {})

    @classmethod
    def process_offline_queue(cls) -> None:
        keys = list(OFFLINE_QUEUE_STORE.keys())
        if not keys:
            return
        for key in keys:
            if not OFFLINE_QUEUE_STORE.exists(key):
                continue
            try:
                item = OFFLINE_QUEUE_STORE.get(key)
                OFFLINE_QUEUE_STORE.delete(key)
            except KeyError:
                continue

            path = item.get("path")
            method = item.get("method", "POST")
            payload = item.get("payload")
            if path and not path.lstrip("/").startswith(("payments/", "auth/")):
                cls.request(path, on_success=lambda _res: None, on_error=lambda _err: None, method=method, payload=payload, retries=0)

    @classmethod
    def request(
        cls,
        path: str,
        on_success: Callable[[Any], None],
        on_error: Callable[[str], None],
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        retries: int = 1,
    ) -> None:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if cls.access_token:
            headers["Authorization"] = f"Bearer {cls.access_token}"
        elif cls.auth_token:
            headers["Authorization"] = f"Token {cls.auth_token}"

        ca_cert = SSL_CA_PATH if API_BASE_URL.lower().startswith("https://") else None

        def start(attempt: int = 0):
            def failed(_request, result):
                status_code = getattr(_request, "resp_status", None)
                clean_path = path.lstrip("/")
                if (
                    status_code == 401
                    and cls.refresh_token
                    and not clean_path.startswith("auth/token/refresh")
                    and not clean_path.startswith("auth/login")
                ):
                    def on_refresh_success(_req, refresh_res):
                        new_access = refresh_res.get("access") if isinstance(refresh_res, dict) else None
                        if new_access:
                            cls.set_tokens(token=cls.auth_token, access=new_access, refresh=cls.refresh_token)
                            cls.request(path, on_success, on_error, method=method, payload=payload, retries=retries)
                        else:
                            cls.clear_token()
                            on_error("Session expirée. Veuillez vous reconnecter.")

                    def on_refresh_failure(_req, _res):
                        cls.clear_token()
                        on_error("Session expirée. Veuillez vous reconnecter.")

                    refresh_url = f"{API_BASE_URL}/auth/token/refresh/"
                    refresh_body = json.dumps({"refresh": cls.refresh_token}).encode("utf-8")
                    refresh_headers = {"Content-Type": "application/json", "Accept": "application/json"}
                    UrlRequest(
                        refresh_url,
                        req_body=refresh_body,
                        req_headers=refresh_headers,
                        method="POST",
                        timeout=API_TIMEOUT_SECONDS,
                        on_success=on_refresh_success,
                        on_failure=on_refresh_failure,
                        on_error=on_refresh_failure,
                        ca_file=ca_cert,
                    )
                    return

                if attempt < retries:
                    Clock.schedule_once(lambda _dt: start(attempt + 1), 0.6 * (attempt + 1))
                else:
                    if retries > 0 and method in ["POST", "PUT", "PATCH", "DELETE"]:
                        cls.queue_offline_action(path, method, payload)
                    on_error(f"Erreur API : {result}")

            def errored(_request, error):
                if attempt < retries:
                    Clock.schedule_once(lambda _dt: start(attempt + 1), 0.6 * (attempt + 1))
                else:
                    if retries > 0 and method in ["POST", "PUT", "PATCH", "DELETE"]:
                        cls.queue_offline_action(path, method, payload)
                    on_error(f"API indisponible : {error}")

            def success_handler(request, result):
                if method == "GET":
                    Clock.schedule_once(lambda _dt: cls.process_offline_queue(), 2.0)
                on_success(result)

            UrlRequest(
                f"{API_BASE_URL}/{path.lstrip('/')}",
                req_body=body,
                req_headers=headers,
                method=method,
                timeout=API_TIMEOUT_SECONDS,
                on_success=success_handler,
                on_failure=failed,
                on_error=errored,
                ca_file=ca_cert,
            )


        start()



def responsive_scale() -> float:
    """Retourne un facteur modéré pour garder une lecture confortable sur chaque écran."""
    return max(0.80, min(1.25, Window.width / dp(360)))


class BaseScreen(Screen):
    status_label = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*WHITE)
            self.background_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_background, size=self._update_background)

    def _update_background(self, *_args) -> None:
        self.background_rect.pos = self.pos
        self.background_rect.size = self.size

    def set_status(self, message: str, color=MUTED) -> None:
        if self.status_label:
            self.status_label.text = message
            self.status_label.color = color

    def make_label(self, text: str, size=16, color=TEXT, bold=False, height=None) -> Label:
        base_height = dp(height) if height is not None else dp(34)
        label = Label(
            text=text,
            font_size=dp(size) * responsive_scale(),
            color=color,
            bold=bold,
            halign="left",
            valign="middle",
            padding=(dp(4), dp(3)),
            text_size=(None, None),
            size_hint_y=None,
            height=base_height,
        )

        def resize_text(widget, *_args):
            widget.font_size = dp(size) * responsive_scale()
            widget.text_size = (max(dp(30), widget.width - dp(8)), None)
            widget.height = max(base_height, widget.texture_size[1] + dp(6))

        label.bind(width=resize_text, text=resize_text, texture_size=resize_text)
        Window.bind(size=lambda *_args: resize_text(label))
        return label

    def configure_spinner(self, spinner: Spinner, font_size: float = 13) -> Spinner:
        """Adapte le texte visible d’un Spinner à son conteneur et à l’écran."""
        def resize_spinner(widget, *_args):
            widget.font_size = dp(font_size) * responsive_scale()
            widget.text_size = (max(dp(30), widget.width - dp(16)), max(dp(20), widget.height - dp(8)))
            widget.halign = "center"
            widget.valign = "middle"

        spinner.bind(size=resize_spinner)
        Window.bind(size=lambda *_args: resize_spinner(spinner))
        resize_spinner(spinner)
        return spinner

    def make_button(
        self,
        text: str,
        callback,
        height=44,
        color=PRIMARY,
        text_color=WHITE,
        font_size=15,
        bold=False,
    ) -> Button:
        button = Button(
            text=text,
            size_hint_y=None,
            height=dp(height),
            background_normal="",
            background_color=color,
            color=text_color,
            font_size=dp(font_size) * responsive_scale(),
            bold=bold,
            halign="center",
            valign="middle",
            padding=(dp(8), dp(4)),
            text_size=(None, None),
        )

        def resize_button_text(widget, *_args):
            widget.font_size = dp(font_size) * responsive_scale()
            widget.text_size = (max(dp(30), widget.width - dp(16)), widget.height - dp(8))

        button.bind(width=resize_button_text, height=resize_button_text)
        Window.bind(size=lambda *_args: resize_button_text(button))
        button.bind(on_release=callback)
        return button

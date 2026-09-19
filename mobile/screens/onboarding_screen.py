import json
import os
import re
import webbrowser
from typing import Any
from urllib.parse import urlencode

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

try:
    from ..core import *
except ImportError:
    from core import *

class OnboardingScreen(BaseScreen):
    slides = [
        ("🌾", "Trouvez vos intrants près de chez vous", "Découvrez les vendeurs agricoles disponibles dans votre région et votre localité."),
        ("🤝", "Connectez-vous avec les vendeurs locaux", "Comparez les disponibilités et trouvez rapidement le bon fournisseur."),
        ("📞", "Appelez ou WhatsApppez en 1 clic", "Contactez directement les vendeurs pour vérifier la disponibilité de vos semences, engrais et matériels."),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.slide_index = 0
        self._auto_timer = None
        self.build_ui()

    def build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(14))
        root.add_widget(self.make_label("AgriLink CI", size=28, color=PRIMARY, bold=True, height=54))
        self.illustration = self.make_label("", size=58, color=PRIMARY, height=110)
        self.illustration.halign = "center"
        root.add_widget(self.illustration)
        self.title_label = self.make_label("", size=23, color=TEXT, bold=True, height=78)
        self.title_label.halign = "center"
        root.add_widget(self.title_label)
        self.description_label = self.make_label("", size=15, color=MUTED, height=82)
        self.description_label.halign = "center"
        root.add_widget(self.description_label)
        self.indicator_label = self.make_label("", size=22, color=PRIMARY, height=36)
        self.indicator_label.halign = "center"
        root.add_widget(self.indicator_label)
        self.next_btn = self.make_button("Suivant →", self.next_slide, height=48, color=(0.95, 0.48, 0.08, 1))
        root.add_widget(self.next_btn)
        root.add_widget(self.make_button("Passer", self.finish, height=40, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(Label())
        self.add_widget(root)
        self.render_slide()

    def on_enter(self, *args):
        self.start_auto_slide()

    def on_leave(self, *args):
        self.stop_auto_slide()

    def start_auto_slide(self) -> None:
        self.stop_auto_slide()
        self._auto_timer = Clock.schedule_interval(self._auto_advance, 3.5)

    def stop_auto_slide(self) -> None:
        if self._auto_timer:
            Clock.unschedule(self._auto_timer)
            self._auto_timer = None

    def _auto_advance(self, dt) -> None:
        self.slide_index = (self.slide_index + 1) % len(self.slides)
        self.render_slide()

    def render_slide(self) -> None:
        icon, title, description = self.slides[self.slide_index]
        self.illustration.text = icon
        self.title_label.text = title
        self.description_label.text = description
        dots = " ".join(["●" if i == self.slide_index else "○" for i in range(len(self.slides))])
        self.indicator_label.text = f"{dots}  ({self.slide_index + 1}/{len(self.slides)})"
        if self.slide_index == len(self.slides) - 1:
            self.next_btn.text = "Commencer →"
        else:
            self.next_btn.text = "Suivant →"

    def next_slide(self, *_args) -> None:
        if self.slide_index < len(self.slides) - 1:
            self.slide_index += 1
            self.render_slide()
            self.start_auto_slide()
        else:
            self.finish()

    def finish(self, *_args) -> None:
        self.stop_auto_slide()
        self.manager.current = "login"

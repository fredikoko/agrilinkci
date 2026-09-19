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

class TipsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self) -> None:
        scroll = ScrollView(do_scroll_x=False)
        root = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(12), size_hint_y=None)
        root.bind(minimum_height=root.setter("height"))
        root.add_widget(self.make_button("← Retour à l’accueil", self.go_home, height=42, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(self.make_label("Conseils agricoles", size=24, color=PRIMARY, bold=True, height=48))
        tips = [
            ("Bien choisir ses semences", "Privilégiez des semences adaptées à votre zone et vérifiez leur date et leur qualité."),
            ("Stocker les intrants", "Conservez les produits dans un endroit sec, ventilé et hors de portée des enfants."),
            ("Demander conseil", "Contactez plusieurs vendeurs locaux pour comparer la disponibilité et les recommandations."),
        ]
        for title, text in tips:
            root.add_widget(self.make_label(title, size=18, color=PRIMARY, bold=True, height=34))
            root.add_widget(self.make_label(text, size=14, color=TEXT, height=62))
        root.add_widget(Label(size_hint_y=None, height=dp(20)))
        scroll.add_widget(root)
        self.add_widget(scroll)

    def go_home(self, *_args) -> None:
        self.manager.get_screen("home").skip_auto_recommendations = True
        self.manager.current = "home"

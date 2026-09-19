from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout

try:
    from ..core import *
except ImportError:
    from core import *


class ConseilDiagnosticScreen(BaseScreen):
    cultures = ["Tomate", "Chou", "Piment", "Oignon", "Maïs", "Banane", "Riz", "Cacao", "Autre"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.step = 1
        self.answers = {}
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        root.add_widget(self.make_button("← Conseil agricole", self.go_back, height=42, color=(0.35, 0.45, 0.38, 1)))
        root.add_widget(self.make_label("Diagnostic personnalisé", size=22, color=PRIMARY, bold=True, height=46))
        self.step_label = self.make_label("Étape 1/5 : Type de culture", size=16, color=TEXT, height=36)
        root.add_widget(self.step_label)
        self.question = self.make_label("Quelle culture cultivez-vous actuellement ?", size=18, color=TEXT, height=60)
        root.add_widget(self.question)
        self.options = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(210))
        root.add_widget(self.options)
        navigation = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        navigation.add_widget(self.make_button("Précédent", self.previous_step, height=42, color=(0.35, 0.45, 0.38, 1)))
        navigation.add_widget(self.make_button("Suivant", self.next_step, height=42, color=PRIMARY))
        root.add_widget(navigation)
        root.add_widget(self.make_label("Fonction réservée aux abonnés Conseil Pro (3 000 FCFA/mois).", size=13, color=MUTED, height=38))
        self.add_widget(root)
        self.refresh_options()

    def refresh_options(self):
        self.options.clear_widgets()
        if self.step == 1:
            for culture in self.cultures:
                self.options.add_widget(self.make_button(culture, lambda btn, value=culture: self.select(value), height=40, color=(0.90, 0.95, 0.90, 1), text_color=PRIMARY, font_size=12))
        else:
            self.options.add_widget(self.make_label("Répondez aux questions pour obtenir une recommandation adaptée à votre exploitation.", size=15, color=TEXT, height=90))

    def select(self, value):
        self.answers[self.step] = value
        self.set_status(f"Réponse sélectionnée : {value}")

    def next_step(self, *_args):
        if self.step < 5:
            self.step += 1
            self.step_label.text = f"Étape {self.step}/5"
            self.question.text = "Décrivez votre situation agricole."
            self.refresh_options()
        else:
            self.set_status("Diagnostic enregistré. Votre plan personnalisé sera préparé.")

    def previous_step(self, *_args):
        if self.step > 1:
            self.step -= 1
            self.step_label.text = f"Étape {self.step}/5"
            self.refresh_options()

    def go_back(self, *_args):
        self.manager.current = "conseil"

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from conseil.models import Alerte, Article, CategorieConseil


class Command(BaseCommand):
    help = "Charge des catégories, articles et alertes de démonstration pour l’Espace Conseil."

    def handle(self, *args, **options):
        categories = {}
        for nom, description in [
            ("Légumes", "Conseils pour les cultures maraîchères."),
            ("Cacao", "Bonnes pratiques pour les plantations de cacao."),
            ("Engrais", "Choix et utilisation raisonnée des fertilisants."),
            ("Sol", "Préparation, entretien et amélioration des sols."),
        ]:
            category, _ = CategorieConseil.objects.update_or_create(nom=nom, defaults={"description": description})
            categories[nom] = category

        articles = [
            {
                "titre": "Préparer son sol avant la saison des pluies",
                "resume": "Les étapes essentielles pour obtenir un sol prêt à accueillir vos cultures.",
                "categorie": categories["Sol"],
                "culture": "Tomate",
                "niveau": "DEBUTANT",
                "temps_lecture": 5,
                "contenu": "Commencez par observer le drainage, retirer les débris et ameublir la couche superficielle. Ajoutez ensuite une matière organique bien décomposée et prévoyez des planches légèrement surélevées si la parcelle retient l’eau.",
                "est_epingle": True,
            },
            {
                "titre": "Bien doser un engrais NPK",
                "resume": "Comprendre le dosage et le moment d’application pour limiter les pertes.",
                "categorie": categories["Engrais"],
                "culture": "Chou",
                "niveau": "INTERMEDIAIRE",
                "temps_lecture": 7,
                "contenu": "Le dosage dépend de l’analyse du sol, de la culture et du stade de développement. Respectez l’étiquette du produit, évitez le contact direct avec les tiges et privilégiez une application fractionnée lorsque cela est recommandé.",
                "est_epingle": True,
            },
            {
                "titre": "Surveiller les ravageurs du cacao",
                "resume": "Identifier rapidement les signes de ravageurs et agir avec une méthode adaptée.",
                "categorie": categories["Cacao"],
                "culture": "Cacao",
                "niveau": "EXPERT",
                "temps_lecture": 6,
                "contenu": "Inspectez régulièrement les feuilles, les cabosses et les branches. Retirez les parties fortement atteintes, favorisez l’aération de la plantation et demandez conseil à un technicien avant tout traitement phytosanitaire.",
                "est_epingle": False,
            },
        ]
        for data in articles:
            Article.objects.update_or_create(titre=data["titre"], defaults=data)

        Alerte.objects.get_or_create(
            titre="Période de semis des légumes",
            defaults={
                "message": "Surveillez l’humidité du sol et préparez vos planches avant les prochaines pluies.",
                "type_alerte": "SAISONNIERE",
                "priorite": "MOYENNE",
                "date_debut": timezone.now() - timedelta(days=1),
                "est_active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS("Données de conseil agricole chargées avec succès."))

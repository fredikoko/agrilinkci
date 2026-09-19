from django.core.management.base import BaseCommand
from django.db import transaction

from directory_app.models import Locality, Region, ServiceProvider, ProvidedService, ServiceProviderReview


PROVIDERS_DATA = [
    {
        "name": "AgroMéca Poro",
        "provider_type": ServiceProvider.ProviderType.MECANISATION,
        "region_name": "Poro",
        "locality_name": "Korhogo",
        "intervention_zone": "Région du Poro, Sinématiali, Dikodougou et environs",
        "address": "Route de l’Aéroport, Quartier Résidentiel",
        "phone": "+2250701020304",
        "whatsapp_number": "+2250701020304",
        "description": "Entreprise spécialisée dans la mécanisation agricole dans le nord ivoirien. Parc de 4 tracteurs John Deere 90CV équipés de charrues, herses et semoirs pneumatiques.",
        "years_of_experience": 8,
        "is_available": True,
        "is_verified": True,
        "services": [
            {"title": "Labour profond au tracteur 90CV", "rate": 35000, "unit": "par hectare", "description": "Labour de défoncement avec charrue à disques."},
            {"title": "Hersage et émottage / billonnage", "rate": 20000, "unit": "par hectare", "description": "Affinage du lit de semences pour maïs, coton et riz."},
            {"title": "Semis mécanisé précis (maïs, riz, soja)", "rate": 15000, "unit": "par hectare", "description": "Semoir pneumatique 4 rangs avec espacement calibré."},
        ],
        "reviews": [
            {"rating": 5, "comment": "Excellent travail de labour sur mes 15 hectares de maïs. Travail rapide et bien fait."},
            {"rating": 4, "comment": "Tracteur ponctuel, bon conducteur. Je recommande vivement pour la saison."},
        ],
    },
    {
        "name": "LocAgri Bélier",
        "provider_type": ServiceProvider.ProviderType.LOCATION,
        "region_name": "Bélier",
        "locality_name": "Yamoussoukro",
        "intervention_zone": "District de Yamoussoukro, Tiébissou, Toumodi, Didiévi",
        "address": "Zone industrielle, axe Yamoussoukro-Bouaké",
        "phone": "+2250505060708",
        "whatsapp_number": "+2250505060708",
        "description": "Location de matériels et engins agricoles avec ou sans opérateur qualifié. Matériel récent, entretenu et disponible 7j/7.",
        "years_of_experience": 5,
        "is_available": True,
        "is_verified": True,
        "services": [
            {"title": "Location tracteur avec chauffeur qualifié", "rate": 80000, "unit": "par jour", "description": "Tracteur 75CV + carburant à charge client. Chauffeur expérimenté inclus."},
            {"title": "Location motopompe haut débit 3 pouces", "rate": 12000, "unit": "par jour", "description": "Motopompe diesel pour irrigation maraîchère, livrée avec 20m de tuyaux."},
            {"title": "Location batteuse-vanneuse mobile (riz & maïs)", "rate": 25000, "unit": "par jour", "description": "Capacité 1,5 tonne/heure. Facilement tractable au champ."},
        ],
        "reviews": [
            {"rating": 5, "comment": "La motopompe m'a sauvé mes piments en pleine saison sèche. Matériel propre et fonctionnel."},
        ],
    },
    {
        "name": "PhytoPro Centre",
        "provider_type": ServiceProvider.ProviderType.TRAITEMENT,
        "region_name": "Gbêkê",
        "locality_name": "Bouaké",
        "intervention_zone": "Région de Gbêkê, Bouaké, Béoumi, Sakassou",
        "address": "Quartier Commerce, près du grand marché",
        "phone": "+2250102030405",
        "whatsapp_number": "+2250102030405",
        "description": "Application professionnelle de traitements phytosanitaires avec respect strict des normes de sécurité et d’environnement. Applicateurs agréés.",
        "years_of_experience": 6,
        "is_available": True,
        "is_verified": True,
        "services": [
            {"title": "Pulvérisation phytosanitaire motorisée", "rate": 12000, "unit": "par hectare", "description": "Traitement fongicide et insecticide à l'atomiseur à dos pour grandes parcelles."},
            {"title": "Désherbage chimique raisonné pré/post-levée", "rate": 10000, "unit": "par hectare", "description": "Application d’herbicides sélectifs sans dérive."},
            {"title": "Traitement de vergers d’anacarde & manguiers", "rate": 18000, "unit": "par hectare", "description": "Pulvérisation canopée haute pour lutter contre l'anthracnose."},
        ],
        "reviews": [
            {"rating": 5, "comment": "Équipe très professionnelle, équipement complet avec combinaisons de protection."},
        ],
    },
    {
        "name": "TransAgri Littoral",
        "provider_type": ServiceProvider.ProviderType.TRANSPORT,
        "region_name": "San-Pédro",
        "locality_name": "San-Pédro",
        "intervention_zone": "Région de San-Pédro, Sassandra, Méagui, Soubré",
        "address": "Zone portuaire, Boulevard du Port",
        "phone": "+2250708091011",
        "whatsapp_number": "+2250708091011",
        "description": "Transport et logistique de récoltes agricoles du champ vers les coopératives et les usines. Flotte de camions 10T et 20T tout-terrain.",
        "years_of_experience": 10,
        "is_available": True,
        "is_verified": True,
        "services": [
            {"title": "Transport récolte camion benne 10 tonnes", "rate": 50000, "unit": "par voyage", "description": "Transport sécurisé pour palmier à huile, manioc, régimes de bananes."},
            {"title": "Évacuation bord champ vers magasin coopérative", "rate": 4000, "unit": "par tonne", "description": "Prise en charge directe sur piste villageoise praticable."},
            {"title": "Transport sacs de cacao / café séché", "rate": 600, "unit": "par sac", "description": "Bâchage étanche et bon de pesée fourni au départ."},
        ],
        "reviews": [
            {"rating": 4, "comment": "Camion venu à l'heure convenue sur la piste villageoise. Bon tarif négocié."},
        ],
    },
    {
        "name": "AquaForage Daloa",
        "provider_type": ServiceProvider.ProviderType.IRRIGATION,
        "region_name": "Haut-Sassandra",
        "locality_name": "Daloa",
        "intervention_zone": "Haut-Sassandra, Daloa, Issia, Vavoua, Zoukougbeu",
        "address": "Quartier Lobia, Carrefour Gaz",
        "phone": "+2250506070809",
        "whatsapp_number": "+2250506070809",
        "description": "Études hydrogéologiques, forages maraîchers et installation complète de réseaux d’irrigation goutte-à-goutte et aspersion.",
        "years_of_experience": 7,
        "is_available": True,
        "is_verified": True,
        "services": [
            {"title": "Forage agricole pour exploitation maraîchère", "rate": 1500000, "unit": "forfait", "description": "Forage tubé jusqu'à 45m avec essai de débit garanti."},
            {"title": "Installation réseau goutte-à-goutte (1 hectare)", "rate": 400000, "unit": "par hectare", "description": "Goutteurs autorégulants avec filtration à disques et vanne principale."},
            {"title": "Maintenance et détartrage réseau irrigation", "rate": 35000, "unit": "par intervention", "description": "Débouchage canalisations et test pression de pompe."},
        ],
        "reviews": [
            {"rating": 5, "comment": "Forage d'eau réussi à 38m. Débit parfait pour mes 2 hectares de tomates."},
        ],
    },
    {
        "name": "Coopérative Main d’Œuvre Sud",
        "provider_type": ServiceProvider.ProviderType.MAIN_DOEUVRE,
        "region_name": "Sud-Comoé",
        "locality_name": "Aboisso",
        "intervention_zone": "Sud-Comoé, Aboisso, Bonoua, Adiaké",
        "address": "Route internationale, face gare routière",
        "phone": "+2250105090204",
        "whatsapp_number": "+2250105090204",
        "description": "Groupement de travailleurs agricoles qualifiés pour chantiers saisonniers : préparation de sol, désherbage, taille d’hévéa et récoltes.",
        "years_of_experience": 4,
        "is_available": True,
        "is_verified": False,
        "services": [
            {"title": "Équipe de désherbage manuel (5 ouvriers)", "rate": 25000, "unit": "par jour", "description": "Équipe outillée avec machettes et dabas, encadrée par un chef d'équipe."},
            {"title": "Récolte manuelle de manioc et igname", "rate": 30000, "unit": "par hectare", "description": "Arrachage soigné sans blessure des tubercules et mise en tas bord champ."},
            {"title": "Saignée et récolte d’hévéa (au mois)", "rate": 80000, "unit": "par mois", "description": "Saigneur expérimenté, respect des panneaux d'écorce."},
        ],
        "reviews": [],
    },
]


class Command(BaseCommand):
    help = "Peuple la base de données avec des prestataires de services agricoles réalistes"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Création des prestataires de services agricoles...")
        created_count = 0
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first()

        for data in PROVIDERS_DATA:
            region = Region.objects.filter(name=data["region_name"]).first()
            if not region:
                self.stdout.write(f"Région non trouvée: {data['region_name']}, ignoré.")
                continue
            locality = Locality.objects.filter(name=data["locality_name"], region=region).first()
            if not locality:
                locality = Locality.objects.filter(region=region).first()
            if not locality:
                self.stdout.write(f"Localité non trouvée pour {data['name']}, ignoré.")
                continue

            provider, created = ServiceProvider.objects.update_or_create(
                name=data["name"],
                defaults={
                    "provider_type": data["provider_type"],
                    "region": region,
                    "locality": locality,
                    "intervention_zone": data["intervention_zone"],
                    "address": data["address"],
                    "phone": data["phone"],
                    "whatsapp_number": data["whatsapp_number"],
                    "description": data["description"],
                    "years_of_experience": data["years_of_experience"],
                    "is_available": data["is_available"],
                    "is_verified": data["is_verified"],
                    "approval_status": ServiceProvider.ApprovalStatus.APPROVED,
                    "approved_by": admin_user,
                    "is_active": True,
                },
            )

            # Prestations
            for s_data in data.get("services", []):
                ProvidedService.objects.update_or_create(
                    provider=provider,
                    title=s_data["title"],
                    defaults={
                        "rate": s_data["rate"],
                        "unit": s_data["unit"],
                        "description": s_data.get("description", ""),
                        "is_available": True,
                    },
                )

            # Avis
            if admin_user:
                for r_data in data.get("reviews", []):
                    ServiceProviderReview.objects.update_or_create(
                        provider=provider,
                        author=admin_user,
                        defaults={
                            "rating": r_data["rating"],
                            "comment": r_data["comment"],
                            "is_published": True,
                        },
                    )

            created_count += 1
            self.stdout.write(self.style.SUCCESS(f"Prestataire configuré : {provider.name} ({provider.get_provider_type_display()})"))

        self.stdout.write(self.style.SUCCESS(f"{created_count} prestataires de services créés ou mis à jour avec succès."))

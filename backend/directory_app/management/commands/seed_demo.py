from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from directory_app.models import Category, Locality, Product, Region, Vendor, VendorProduct


REGIONS = {
    "Abidjan": ["Abidjan"],
    "Agnéby-Tiassa": ["Agboville", "Tiassalé"],
    "Bélier": ["Yamoussoukro", "Didiévi"],
    "Bounkani": ["Bouna", "Nassian"],
    "Cavally": ["Guiglo", "Duékoué"],
    "Gbêkê": ["Bouaké", "Béoumi"],
    "Gôh": ["Gagnoa", "Oumé"],
    "Gontougo": ["Bondoukou", "Tanda"],
    "Grands-Ponts": ["Dabou", "Grand-Lahou"],
    "Guémon": ["Duékoué", "Bangolo"],
    "Hambol": ["Katiola", "Dabakala"],
    "Haut-Sassandra": ["Daloa", "Issia"],
    "Indénié-Djuablin": ["Abengourou", "Agnibilékrou"],
    "La Mé": ["Adzopé", "Alépé"],
    "Lôh-Djiboua": ["Divo", "Lakota"],
    "Marahoué": ["Bouaflé", "Sinfra"],
    "Moronou": ["Bongouanou", "Arrah"],
    "Nawa": ["Soubré", "Buyo"],
    "Poro": ["Korhogo", "Sinématiali"],
    "San-Pédro": ["San-Pédro", "Tabou"],
    "Sud-Comoé": ["Aboisso", "Grand-Bassam"],
    "Tchologo": ["Ferkessédougou", "Ouangolodougou"],
    "Tonkpi": ["Man", "Danané"],
    "Worodougou": ["Séguéla", "Mankono"],
}

CATEGORIES = [
    ("Semences", "semences"),
    ("Engrais", "engrais"),
    ("Pesticides chimiques", "pesticides-chimiques"),
    ("Produits phytosanitaires", "produits-phytosanitaires"),
    ("Matériel agricole", "materiel-agricole"),
]

PRODUCTS = [
    ("Semence de chou", "semence-chou", "semences", "sachet"),
    ("Semence de tomate", "semence-tomate", "semences", "sachet"),
    ("Engrais NPK 15-15-15", "engrais-npk-15-15-15", "engrais", "sac de 50 kg"),
    ("Urée agricole", "uree-agricole", "engrais", "sac de 50 kg"),
    ("Herbicide homologué", "herbicide-homologue", "pesticides-chimiques", "bidon"),
    ("Pulvérisateur manuel", "pulverisateur-manuel", "materiel-agricole", "unité"),
]


class Command(BaseCommand):
    help = "Peuple la base avec un jeu de données AgriLink CI pour démonstration."

    @transaction.atomic
    def handle(self, *args, **options):
        regions = {}
        for region_name, locality_names in REGIONS.items():
            region, _ = Region.objects.get_or_create(
                name=region_name,
                defaults={"code": slugify(region_name)},
            )
            regions[region_name] = region
            for locality_name in locality_names:
                Locality.objects.get_or_create(region=region, name=locality_name)

        categories = {}
        for name, slug in CATEGORIES:
            category, _ = Category.objects.get_or_create(name=name, defaults={"slug": slug})
            categories[slug] = category

        products = {}
        for name, slug, category_slug, unit in PRODUCTS:
            product, _ = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "category": categories[category_slug],
                    "unit": unit,
                },
            )
            products[slug] = product

        bondoukou = Locality.objects.get(name="Bondoukou", region=regions["Gontougo"])
        tanda = Locality.objects.get(name="Tanda", region=regions["Gontougo"])
        bouake = Locality.objects.get(name="Bouaké", region=regions["Gbêkê"])

        vendors = [
            {
                "name": "Coopérative Agricole du Gontougo",
                "vendor_type": Vendor.VendorType.COOPERATIVE,
                "region": regions["Gontougo"],
                "locality": bondoukou,
                "address": "Marché central, Bondoukou",
                "phone": "+225 07 00 00 00 01",
                "whatsapp_number": "+2250700000001",
                "opening_hours": "Lun-Sam : 08h00-18h00",
                "is_verified": True,
                "products": [("semence-chou", 35), ("engrais-npk-15-15-15", 18), ("pulverisateur-manuel", 6)],
            },
            {
                "name": "Agri Services Bondoukou",
                "vendor_type": Vendor.VendorType.RETAILER,
                "region": regions["Gontougo"],
                "locality": bondoukou,
                "address": "Quartier Administratif, Bondoukou",
                "phone": "+225 07 00 00 00 02",
                "whatsapp_number": "+2250700000002",
                "opening_hours": "Lun-Ven : 07h30-17h30",
                "is_verified": True,
                "products": [("semence-tomate", 22), ("uree-agricole", 12), ("herbicide-homologue", 4)],
            },
            {
                "name": "Tanda Intrants & Conseil",
                "vendor_type": Vendor.VendorType.WHOLESALER,
                "region": regions["Gontougo"],
                "locality": tanda,
                "address": "Route de Bondoukou, Tanda",
                "phone": "+225 07 00 00 00 03",
                "whatsapp_number": "+2250700000003",
                "opening_hours": "Lun-Sam : 08h00-19h00",
                "is_verified": False,
                "products": [("engrais-npk-15-15-15", 80), ("uree-agricole", 65), ("herbicide-homologue", 14)],
            },
            {
                "name": "Bouaké Agro Distribution",
                "vendor_type": Vendor.VendorType.WHOLESALER,
                "region": regions["Gbêkê"],
                "locality": bouake,
                "address": "Zone industrielle, Bouaké",
                "phone": "+225 07 00 00 00 04",
                "whatsapp_number": "+2250700000004",
                "opening_hours": "Lun-Sam : 07h00-18h00",
                "is_verified": True,
                "products": [("semence-chou", 90), ("semence-tomate", 55), ("engrais-npk-15-15-15", 120)],
            },
        ]

        for vendor_data in vendors:
            product_data = vendor_data.pop("products")
            vendor_data["approval_status"] = "approved" if vendor_data.get("is_verified") else "pending"
            vendor, _ = Vendor.objects.update_or_create(
                name=vendor_data["name"],
                defaults=vendor_data,
            )
            for product_slug, quantity in product_data:
                VendorProduct.objects.update_or_create(
                    vendor=vendor,
                    product=products[product_slug],
                    defaults={
                        "quantity_available": quantity,
                        "is_available": quantity > 0,
                        "price_note": "Prix à confirmer avec le vendeur",
                    },
                )

        self.stdout.write(self.style.SUCCESS("Jeu de données AgriLink CI chargé avec succès."))

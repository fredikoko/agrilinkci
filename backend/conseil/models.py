from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify
from django.utils import timezone

from directory_app.models import Payment, Product



class CategorieConseil(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icone = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "Catégorie de conseil"
        verbose_name_plural = "Catégories de conseil"

    def __str__(self):
        return self.nom


class ConseilSubscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expirée"
        CANCELLED = "cancelled", "Annulée"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conseil_subscription")
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="conseil_subscriptions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    agronome_chats_used = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE and self.ends_at > timezone.now()


import os

def upload_to_article_image(instance, filename):
    name, ext = os.path.splitext(filename)
    clean_name = slugify(name) or "image"
    return f"conseil/images/{clean_name}{ext.lower()}"

def upload_to_content_image(instance, filename):
    name, ext = os.path.splitext(filename)
    clean_name = slugify(name) or "image"
    return f"conseil/content_images/{clean_name}{ext.lower()}"


class Article(models.Model):
    NIVEAU_CHOICES = [
        ("DEBUTANT", "Débutant"),
        ("INTERMEDIAIRE", "Intermédiaire"),
        ("EXPERT", "Expert"),
    ]

    titre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    contenu = models.TextField()
    resume = models.TextField(max_length=300, help_text="Résumé court pour la carte d’aperçu")
    categorie = models.ForeignKey(CategorieConseil, on_delete=models.CASCADE, related_name="articles")
    culture = models.CharField(max_length=100, blank=True)
    niveau = models.CharField(max_length=20, choices=NIVEAU_CHOICES, default="DEBUTANT")
    image_principale = models.FileField(upload_to=upload_to_article_image, blank=True, null=True)
    est_epingle = models.BooleanField(default=False)
    est_premium = models.BooleanField(default=False)
    est_publie = models.BooleanField(default=False)
    date_publication = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    nombre_vues = models.PositiveIntegerField(default=0)
    nombre_favoris = models.PositiveIntegerField(default=0)
    produits_associes = models.ManyToManyField(Product, blank=True, related_name="articles_conseil")

    class Meta:
        ordering = ["-est_epingle", "-date_publication"]
        indexes = [
            models.Index(fields=["est_publie", "est_epingle"]),
            models.Index(fields=["culture", "niveau"]),
        ]
        verbose_name = "Article agricole"
        verbose_name_plural = "Articles agricoles"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titre)
        super().save(*args, **kwargs)


class ArticleImage(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="images_contenu")
    image = models.FileField(upload_to=upload_to_content_image, help_text="Image à insérer dans l'article")
    legende = models.CharField(max_length=255, blank=True, help_text="Légende ou description sous l'image")
    ordre = models.PositiveSmallIntegerField(default=0, help_text="Ordre d'affichage dans l'article")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ordre", "created_at"]
        verbose_name = "Image du contenu d'article"
        verbose_name_plural = "Images du contenu d'article"

    def __str__(self):
        return f"Image #{self.id} — {self.article.titre}"


class ArticleFavori(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="articles_favoris")
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="favoris_utilisateurs")
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_ajout"]
        constraints = [
            models.UniqueConstraint(fields=["utilisateur", "article"], name="unique_article_favori_par_utilisateur")
        ]


class Alerte(models.Model):
    PRIORITE_CHOICES = [
        ("BASSE", "Basse"),
        ("MOYENNE", "Moyenne"),
        ("HAUTE", "Haute"),
        ("URGENTE", "Urgente"),
    ]
    TYPE_CHOICES = [
        ("SAISONNIERE", "Conseil saisonnier"),
        ("METEO", "Alerte météo"),
        ("RAVAGEUR", "Épidémie de ravageurs"),
        ("FORMATION", "Formation / Événement"),
        ("GENERALE", "Information générale"),
    ]

    titre = models.CharField(max_length=150)
    message = models.TextField()
    region = models.CharField(max_length=100, blank=True)
    localite = models.CharField(max_length=100, blank=True)
    culture = models.CharField(max_length=100, blank=True)
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField(blank=True, null=True)
    priorite = models.CharField(max_length=20, choices=PRIORITE_CHOICES, default="MOYENNE")
    type_alerte = models.CharField(max_length=30, choices=TYPE_CHOICES, default="GENERALE")
    est_active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_debut", "-date_creation"]
        indexes = [models.Index(fields=["est_active", "date_debut"])]
        verbose_name = "Alerte agricole"
        verbose_name_plural = "Alertes agricoles"

    def __str__(self):
        return self.titre

    @property
    def est_en_cours(self):
        maintenant = timezone.now()
        return self.est_active and self.date_debut <= maintenant and (not self.date_fin or maintenant <= self.date_fin)


class AlerteLue(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alertes_lues")
    alerte = models.ForeignKey(Alerte, on_delete=models.CASCADE, related_name="lectures")
    date_lecture = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["utilisateur", "alerte"], name="unique_alerte_lue_par_utilisateur")
        ]
        ordering = ["-date_lecture"]


class FreeArticleUsage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="free_article_usages")
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    year_month = models.CharField(max_length=7, db_index=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "article", "year_month"], name="unique_user_free_article_month")
        ]
        verbose_name = "Utilisation article gratuit"
        verbose_name_plural = "Utilisations articles gratuits"


class ArticleReview(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="article_reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["article", "author"], name="unique_article_review_by_author")
        ]
        verbose_name = "Avis article"
        verbose_name_plural = "Avis articles"




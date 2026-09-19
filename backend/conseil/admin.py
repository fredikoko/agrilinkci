from django.contrib import admin

from .models import Alerte, AlerteLue, Article, ArticleFavori, ArticleImage, CategorieConseil, ConseilSubscription


@admin.register(ConseilSubscription)
class ConseilSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "starts_at", "ends_at", "agronome_chats_used")
    list_filter = ("status",)
    search_fields = ("user__username", "user__email")


@admin.register(CategorieConseil)
class CategorieConseilAdmin(admin.ModelAdmin):
    list_display = ("nom", "icone")
    search_fields = ("nom", "description")


class ArticleImageInline(admin.TabularInline):
    model = ArticleImage
    extra = 1
    fields = ("image", "legende", "ordre", "balise_insertion")
    readonly_fields = ("balise_insertion",)

    def balise_insertion(self, obj):
        if obj.image:
            return f"[IMG:{obj.image.url}]"
        return "Sauvegardez pour générer la balise"
    balise_insertion.short_description = "Balise d'insertion"


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("titre", "categorie", "culture", "niveau", "est_premium", "est_epingle", "est_publie", "date_publication")
    list_filter = ("categorie", "niveau", "est_premium", "est_epingle", "est_publie")
    search_fields = ("titre", "resume", "contenu", "culture")
    prepopulated_fields = {"slug": ("titre",)}
    filter_horizontal = ("produits_associes",)
    inlines = [ArticleImageInline]


@admin.register(ArticleFavori)
class ArticleFavoriAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "article", "date_ajout")
    search_fields = ("utilisateur__username", "article__titre")


@admin.register(Alerte)
class AlerteAdmin(admin.ModelAdmin):
    list_display = ("titre", "type_alerte", "priorite", "region", "est_active", "date_debut", "date_fin")
    list_filter = ("type_alerte", "priorite", "est_active")
    search_fields = ("titre", "message", "region", "localite", "culture")


@admin.register(AlerteLue)
class AlerteLueAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "alerte", "date_lecture")
    search_fields = ("utilisateur__username", "alerte__titre")

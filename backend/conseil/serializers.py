from rest_framework import serializers

from .models import Alerte, Article, ArticleFavori, ArticleImage, ArticleReview, CategorieConseil

class CategorieConseilSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategorieConseil
        fields = ["id", "nom", "description", "icone"]


class ArticleReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = ArticleReview
        fields = ["id", "article", "author", "author_name", "rating", "comment", "created_at", "updated_at"]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def get_author_name(self, obj):
        if hasattr(obj.author, "buyer_profile") and obj.author.buyer_profile and obj.author.buyer_profile.full_name:
            return obj.author.buyer_profile.full_name
        return obj.author.username or f"Utilisateur #{obj.author.id}"

class ArticleImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ArticleImage
        fields = ["id", "image_url", "legende", "ordre"]

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class ArticleListSerializer(serializers.ModelSerializer):
    categorie_nom = serializers.CharField(source="categorie.nom", read_only=True)
    niveau_label = serializers.CharField(source="get_niveau_display", read_only=True)
    image_url = serializers.SerializerMethodField()
    est_favori = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True, default=0.0)
    review_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Article
        fields = [
            "id", "titre", "slug", "resume", "categorie", "categorie_nom", "culture",
            "niveau", "niveau_label", "est_epingle", "est_premium", "image_url",
            "nombre_vues", "nombre_favoris", "average_rating", "review_count",
            "date_publication", "est_favori",
        ]

    def get_image_url(self, obj):
        if not obj.image_principale:
            return None
        request = self.context.get("request")
        url = obj.image_principale.url
        return request.build_absolute_uri(url) if request else url

    def get_est_favori(self, obj):
        user = self.context.get("request").user if self.context.get("request") else None
        return bool(user and user.is_authenticated and obj.favoris_utilisateurs.filter(utilisateur=user).exists())


class ArticleDetailSerializer(ArticleListSerializer):
    produits_associes = serializers.SerializerMethodField()
    images_contenu = ArticleImageSerializer(many=True, read_only=True)
    reviews = ArticleReviewSerializer(many=True, read_only=True)

    class Meta(ArticleListSerializer.Meta):
        fields = ArticleListSerializer.Meta.fields + [
            "contenu", "images_contenu", "date_modification", "produits_associes", "reviews"
        ]

    def get_produits_associes(self, obj):
        return [{"id": product.id, "name": product.name, "slug": product.slug} for product in obj.produits_associes.all()]


class ArticleFavoriSerializer(serializers.ModelSerializer):
    article = ArticleListSerializer(read_only=True)
    article_id = serializers.PrimaryKeyRelatedField(source="article", queryset=Article.objects.all(), write_only=True)

    class Meta:
        model = ArticleFavori
        fields = ["id", "article", "article_id", "date_ajout"]
        read_only_fields = ["id", "date_ajout"]


class AlerteSerializer(serializers.ModelSerializer):
    priorite_label = serializers.CharField(source="get_priorite_display", read_only=True)
    type_label = serializers.CharField(source="get_type_alerte_display", read_only=True)
    est_en_cours = serializers.BooleanField(read_only=True)
    est_lue = serializers.SerializerMethodField()

    class Meta:
        model = Alerte
        fields = [
            "id", "titre", "message", "region", "localite", "culture", "date_debut", "date_fin",
            "priorite", "priorite_label", "type_alerte", "type_label", "est_active", "est_en_cours", "est_lue",
        ]

    def get_est_lue(self, obj):
        user = self.context.get("request").user if self.context.get("request") else None
        return bool(user and user.is_authenticated and obj.lectures.filter(utilisateur=user).exists())


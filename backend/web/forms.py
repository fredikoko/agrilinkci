from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from directory_app.models import (
    Vendor, VendorProduct, StockMovement, VendorReview,
    ServiceProvider, ProvidedService, Region, Locality, Category, Product
)
from conseil.models import ArticleReview

User = get_user_model()


class LoginForm(forms.Form):
    identifier = forms.CharField(
        label="Numéro de téléphone ou Nom d'utilisateur",
        widget=forms.TextInput(attrs={
            "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition",
            "placeholder": "+2250700000000 ou nom_utilisateur",
            "required": True,
        })
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition",
            "placeholder": "••••••••",
            "required": True,
        })
    )


class SignupForm(forms.Form):
    full_name = forms.CharField(
        label="Nom complet",
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition",
            "placeholder": "Ex: Kouamé Yao",
            "required": True,
        })
    )
    phone = forms.CharField(
        label="Numéro de téléphone",
        max_length=30,
        widget=forms.TextInput(attrs={
            "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition",
            "placeholder": "+2250701020304",
            "required": True,
        })
    )
    email = forms.EmailField(
        label="Adresse e-mail (optionnelle)",
        required=False,
        widget=forms.EmailInput(attrs={
            "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition",
            "placeholder": "votre.email@exemple.ci",
        })
    )
    role = forms.ChoiceField(
        label="Votre rôle",
        choices=[("buyer", "Acheteur / Consommateur"), ("seller", "Vendeur / Agriculteur")],
        widget=forms.Select(attrs={
            "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition",
        })
    )
    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        label="Région",
        required=False,
        empty_label="Choisir une région",
        widget=forms.Select(attrs={
            "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition",
            "id": "id_signup_region",
        })
    )
    locality = forms.ModelChoiceField(
        queryset=Locality.objects.all(),
        label="Localité",
        required=False,
        empty_label="Choisir une localité",
        widget=forms.Select(attrs={
            "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition",
            "id": "id_signup_locality",
        })
    )
    password = forms.CharField(
        label="Mot de passe",
        min_length=6,
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition",
            "placeholder": "Au moins 6 caractères",
            "required": True,
        })
    )
    password_confirm = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition",
            "placeholder": "Répétez le mot de passe",
            "required": True,
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("password_confirm")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned_data


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "vendor_type", "region", "locality", "phone", "address", "opening_hours"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "Nom du vendeur ou de la coopérative"}),
            "vendor_type": forms.Select(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none"}),
            "region": forms.Select(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "id": "id_vendor_region"}),
            "locality": forms.Select(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "id": "id_vendor_locality"}),
            "phone": forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "+2250700000000"}),
            "address": forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "Ex: Marché de gros, stand 12"}),
            "opening_hours": forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "Ex: Lun-Sam : 07h00 - 18h00"}),
        }


class VendorProductForm(forms.ModelForm):
    class Meta:
        model = VendorProduct
        fields = ["product", "quantity_available", "alert_threshold", "price_note"]
        widgets = {
            "product": forms.Select(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none"}),
            "quantity_available": forms.NumberInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "min": 0}),
            "alert_threshold": forms.NumberInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "min": 0}),
            "price_note": forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "Ex: 500 FCFA / kg, 15 000 FCFA / sac"}),
        }


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ["movement_type", "quantity", "reason"]
        widgets = {
            "movement_type": forms.Select(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none"}),
            "quantity": forms.NumberInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "min": 1}),
            "reason": forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "Ex: Récolte du jour, Vente directe, Perte..."}),
        }


class VendorReviewForm(forms.ModelForm):
    class Meta:
        model = VendorReview
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.Select(choices=[(5, "⭐⭐⭐⭐⭐ - Excellent"), (4, "⭐⭐⭐⭐ - Très bon"), (3, "⭐⭐⭐ - Moyen"), (2, "⭐⭐ - Passable"), (1, "⭐ - Décevant")], attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none"}),
            "comment": forms.Textarea(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "rows": 3, "placeholder": "Partagez votre avis sur la qualité des produits et le service..."}),
        }


class ArticleReviewForm(forms.ModelForm):
    class Meta:
        model = ArticleReview
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.Select(choices=[(5, "⭐⭐⭐⭐⭐ (5/5)"), (4, "⭐⭐⭐⭐ (4/5)"), (3, "⭐⭐⭐ (3/5)"), (2, "⭐⭐ (2/5)"), (1, "⭐ (1/5)")], attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none"}),
            "comment": forms.Textarea(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "rows": 3, "placeholder": "Ce conseil vous a-t-il été utile ? Vos remarques..."}),
        }


class ServiceProviderForm(forms.ModelForm):
    class Meta:
        model = ServiceProvider
        fields = ["name", "provider_type", "description", "phone", "whatsapp_number", "region", "locality", "address", "intervention_zone"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "Nom de l'entreprise ou du prestataire"}),
            "provider_type": forms.Select(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none"}),
            "description": forms.Textarea(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "rows": 3, "placeholder": "Présentation des matériels, prestations et zone de couverture..."}),
            "phone": forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "+2250700000000"}),
            "whatsapp_number": forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "+2250700000000"}),
            "region": forms.Select(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "id": "id_prov_region"}),
            "locality": forms.Select(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "id": "id_prov_locality"}),
            "address": forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "Point de repère ou base technique"}),
            "intervention_zone": forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "Ex: Abidjan, Dabou, Tiassalé..."}),
        }


class ProvidedServiceForm(forms.ModelForm):
    class Meta:
        model = ProvidedService
        fields = ["title", "description", "rate", "unit"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "Ex: Labour de terrain avec tracteur"}),
            "description": forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "Détails de la prestation"}),
            "rate": forms.NumberInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "Tarif en FCFA"}),
            "unit": forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "Ex: par hectare, par jour, forfait"}),
        }


class UserProfileForm(forms.Form):
    full_name = forms.CharField(label="Nom complet", max_length=150, widget=forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none"}))
    email = forms.EmailField(label="Adresse e-mail", required=False, widget=forms.EmailInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none"}))
    culture_profile = forms.CharField(label="Cultures d'intérêt (séparées par des virgules)", required=False, widget=forms.TextInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "placeholder": "Ex: Manioc, Tomate, Cacao, Piment"}))
    region = forms.ModelChoiceField(queryset=Region.objects.all(), required=False, empty_label="Toutes régions", widget=forms.Select(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "id": "id_profile_region"}))
    locality = forms.ModelChoiceField(queryset=Locality.objects.all(), required=False, empty_label="Toutes localités", widget=forms.Select(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none", "id": "id_profile_locality"}))


class PasswordChangeWebForm(forms.Form):
    old_password = forms.CharField(label="Ancien mot de passe", widget=forms.PasswordInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none"}))
    new_password = forms.CharField(label="Nouveau mot de passe", min_length=6, widget=forms.PasswordInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none"}))
    confirm_password = forms.CharField(label="Confirmer le nouveau mot de passe", widget=forms.PasswordInput(attrs={"class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none"}))

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("new_password")
        p2 = cleaned_data.get("confirm_password")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Les nouveaux mots de passe ne correspondent pas.")
        return cleaned_data

# Structure modulaire de l’application Kivy

`main.py` assemble uniquement le `ScreenManager`. Les services partagés et chaque écran sont séparés dans des fichiers dédiés.

- `core.py` : thème blanc, constantes, composants communs et `ApiClient`.
- `screens/onboarding_screen.py` : onboarding.
- `screens/login_screen.py` : connexion OTP.
- `screens/buyer_profile_screen.py` : localisation acheteur.
- `screens/home_screen.py` : accueil personnalisé.
- `screens/vendor_list_screen.py` : liste générale des vendeurs.
- `screens/results_screen.py` : résultats issus des filtres et de la recherche.
- `screens/vendor_detail_screen.py` : fiche vendeur.
- `screens/contact_screen.py` : appel et WhatsApp.
- `screens/advanced_search_screen.py` : recherche avancée.
- `screens/favorites_screen.py` : favoris.
- `screens/tips_screen.py` : conseils agricoles.
- `screens/user_profile_screen.py` : profil utilisateur.
- `screens/seller_screen.py` : inscription vendeur, abonnement Paystack et défilement.

Depuis le dossier `mobile`, lancer `python main.py`.

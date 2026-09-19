# Notifications FCM et forfaits AgriLink CI

## Configuration Railway

Définir les variables suivantes dans le service backend :

| Variable | Valeur attendue | Usage |
|---|---|---|
| `FIREBASE_CREDENTIALS_JSON` | JSON minifié du compte de service Firebase | Authentification de l’Admin SDK pour l’envoi FCM |
| `DJANGO_DEBUG` | `false` | Activer les réglages de production |
| `DJANGO_SECRET_KEY` | Clé aléatoire longue | Sécuriser Django |
| `DJANGO_ALLOWED_HOSTS` | Domaine Railway, séparé par des virgules | Autoriser les hôtes |
| `DATABASE_URL` | URL PostgreSQL Railway | Base de production |

Le JSON Firebase ne doit pas être commité dans le dépôt. Dans Railway, le contenu peut être collé en une seule ligne dans la variable d’environnement. Si la variable est absente ou invalide, les notifications sont tout de même enregistrées en base, mais aucun envoi FCM ne sera tenté.

## API mobile

Après authentification, l’application peut enregistrer un appareil avec `POST /api/notifications/device/` et le corps `{"token":"TOKEN_FCM","platform":"android"}`. Les notifications persistées sont récupérées avec `GET /api/notifications/`. Une notification peut être marquée comme lue avec `POST /api/notifications/<id>/read/`.

Un vendeur Pro approuvé peut publier une promotion avec `POST /api/notifications/promote/`, en envoyant `{"title":"...","body":"..."}`. Le backend vérifie l’abonnement actif et applique un quota de **15 promotions par mois**. Les promotions sont enregistrées pour les utilisateurs actifs et envoyées aux appareils FCM enregistrés.

## Règles Free et Pro

Un vendeur vérifié peut créer sa fiche et gérer son stock. Le forfait gratuit est limité à **10 produits distincts**. Un abonnement vendeur actif est identifié par `SellerSubscription.is_active`; il débloque le catalogue illimité, le badge `Vendeur Pro`, la priorité dans les résultats et l’envoi de promotions.

La migration `0009_appnotification_notificationdevice_promotionquota.py` doit être appliquée en production avec `python manage.py migrate` avant d’utiliser les endpoints de notifications.

## Vérifications locales

Les contrôles effectués sont `python3 -m compileall -q backend mobile` et `python3 manage.py check`. Le système Django doit également être démarré avec Firebase Admin installé via `firebase-admin` en production.

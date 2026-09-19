# AgriLink CI

AgriLink CI est un prototype d’annuaire intelligent de distributeurs d’intrants agricoles en Côte d’Ivoire. Le projet est organisé en deux parties complémentaires : une API REST développée avec Django et Django REST Framework, ainsi qu’une application mobile Kivy destinée aux acheteurs et aux vendeurs.

> **Périmètre du MVP.** Le prototype permet de consulter les régions et localités, rechercher des vendeurs par zone ou produit, afficher leur stock, appeler un vendeur ou ouvrir WhatsApp, créer une fiche vendeur et créer un profil acheteur via l’API. Les données fournies par `seed_demo` sont un jeu de démonstration et ne constituent pas encore un référentiel géographique officiel exhaustif.

## Architecture

| Composant | Technologie | Responsabilité |
| --- | --- | --- |
| Backend | Django 5.x + Django REST Framework | Modèles métier, API JSON, filtres, administration |
| Base locale | SQLite | Développement et démonstration rapide |
| Client mobile | Kivy | Recherche, fiche vendeur, appel, WhatsApp, inscription vendeur |
| Compilation mobile | Buildozer | Génération d’un paquet Android |
| Données | Commande `seed_demo` | Chargement des régions, localités, catégories, produits et vendeurs de démonstration |

Le modèle de données sépare les régions et les localités des catégories et produits. Un vendeur possède plusieurs lignes de stock par l’intermédiaire de `VendorProduct`, ce qui permet d’indiquer la quantité, la disponibilité et une note de prix sans figer le catalogue.

## Démarrage du backend

Depuis le dossier `backend`, créez l’environnement virtuel et installez les dépendances :

```bash
cd backend
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

Appliquez ensuite les migrations et chargez le jeu de données de démonstration :

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
```

Lancez l’API en local :

```bash
.venv/bin/python manage.py runserver 0.0.0.0:8000
```

Les principaux points d’entrée sont les suivants :

| Route | Méthodes | Usage |
| --- | --- | --- |
| `/api/health/` | GET | Vérifier que l’API fonctionne |
| `/api/regions/` | GET | Lister les régions |
| `/api/regions/{id}/localities/` | GET | Lister les localités d’une région |
| `/api/categories/` | GET | Lister les catégories d’intrants |
| `/api/products/` | GET | Rechercher dans le catalogue produit |
| `/api/vendors/` | GET, POST, PATCH | Rechercher ou créer une fiche vendeur |
| `/api/vendors/{id}/` | GET | Consulter une fiche vendeur et son stock |
| `/api/vendors/suggestions/` | GET | Obtenir des suggestions par région/localité |
| `/api/stock/` | GET, POST, PATCH, DELETE | Gérer les lignes de stock |
| `/api/buyer-profiles/` | GET, POST, PATCH | Créer ou consulter un profil acheteur |

Exemples de recherche :

```text
/api/vendors/?locality=1&available=true
/api/vendors/?region=8&search=semence%20de%20chou
/api/vendors/?category_slug=semences&ordering=-stock
/api/vendors/suggestions/?region=8&locality=1
```

L’interface d’administration est disponible à l’adresse `/admin/`. Pour créer un administrateur local :

```bash
.venv/bin/python manage.py createsuperuser
```

## Démarrage de l’application Kivy

Installez Kivy dans un environnement compatible avec votre système, puis lancez l’application :

```bash
cd mobile
python3 -m pip install kivy requests
python3 main.py
```

Par défaut, l’application utilise `http://127.0.0.1:8000/api`. Pour un téléphone physique, remplacez cette adresse par l’adresse IP locale de l’ordinateur qui exécute Django. Vous pouvez aussi fournir une variable d’environnement avant le lancement :

```bash
AGRILINK_API_URL=http://192.168.1.20:8000/api python3 main.py
```

Sur l’émulateur Android standard, l’hôte de la machine est généralement accessible via `10.0.2.2`. Sur un appareil physique, le téléphone et l’ordinateur doivent être connectés au même réseau Wi-Fi et le serveur Django doit écouter sur `0.0.0.0`.

## Compilation Android

Le fichier `mobile/buildozer.spec` est déjà préparé. Après installation de Buildozer et de ses dépendances système, exécutez :

```bash
cd mobile
buildozer android debug
```

Avant la compilation, mettez à jour `API_BASE_URL` dans `main.py` ou adaptez le mécanisme de configuration pour utiliser une URL publique HTTPS du backend. Une adresse `127.0.0.1` ne désigne pas le serveur Django lorsqu’elle est utilisée depuis un téléphone.

## Tests

La suite de tests couvre la santé de l’API, le filtrage par localité, la recherche par produit, le détail d’une fiche vendeur et la création d’un profil acheteur :

```bash
cd backend
.venv/bin/python manage.py test directory_app -v 2
```

La syntaxe Python du client Kivy peut être vérifiée sans ouvrir une fenêtre graphique :

```bash
python3 -m py_compile mobile/main.py
```

## Prochaines étapes recommandées

La prochaine version devrait ajouter une authentification par téléphone ou adresse e-mail, une validation des vendeurs par un administrateur, une base PostgreSQL avec recherche géographique plus précise, la notation des vendeurs, les alertes de disponibilité, un cache hors ligne Kivy et un référentiel officiel des régions et localités. Il faudra également remplacer les coordonnées de démonstration par des contacts vérifiés avant toute mise en production.

## Authentification par numéro de téléphone

L’authentification utilise un code OTP à usage unique. Le même parcours sert aux acheteurs et aux vendeurs, mais le compte conserve un rôle (`buyer` ou `seller`). Le numéro est normalisé au format international E.164, le code expire par défaut après cinq minutes, un défi ne peut être tenté que cinq fois et une nouvelle demande est limitée pendant soixante secondes.

| Route | Méthode | Données principales | Résultat |
| --- | --- | --- | --- |
| `/api/auth/request-code/` | POST | `phone`, `role` | Envoie un code SMS et retourne sa durée de validité |
| `/api/auth/verify-code/` | POST | `phone`, `code`, `role` | Crée ou retrouve le compte et retourne un token DRF |
| `/api/auth/me/` | GET | Header `Authorization: Token ...` | Retourne le numéro et le rôle authentifiés |

### Développement local sans fournisseur SMS

Par défaut, `SMS_PROVIDER=console`. Le code est écrit dans les logs Django et, lorsque `DJANGO_DEBUG=true`, il est aussi retourné dans la réponse afin de tester l’application Kivy sans compte SMS payant :

```bash
cd backend
export SMS_PROVIDER=console
export DJANGO_DEBUG=true
.venv/bin/python manage.py runserver 0.0.0.0:8000
```

Cette configuration ne doit pas être utilisée en production, car le code OTP ne doit jamais être exposé dans une réponse HTTP ou dans des logs accessibles.

### Production avec Twilio Verify

Créez un service Verify dans la console Twilio, puis configurez les variables suivantes avant de démarrer Django :

```bash
export SMS_PROVIDER=twilio
export DJANGO_DEBUG=false
export DJANGO_SECRET_KEY="une-cle-secrete-longue-et-aleatoire"
export DJANGO_ALLOWED_HOSTS="api.exemple.ci"
export TWILIO_ACCOUNT_SID="AC..."
export TWILIO_AUTH_TOKEN="..."
export TWILIO_VERIFY_SERVICE_SID="VA..."
```

Le backend appelle l’API Verify pour envoyer le SMS et vérifie ensuite le code auprès de Twilio. La documentation officielle décrit un service Verify réutilisable, l’envoi avec le canal SMS et la vérification séparée du code [1]. Les identifiants doivent rester uniquement dans les variables d’environnement du serveur et ne doivent jamais être inclus dans l’application Kivy.

### Alternative Vonage

Vonage Verify peut être branché en ajoutant une classe équivalente à `TwilioVerifyProvider`. Son flux officiel initialise une vérification via `/v2/verify`, reçoit un identifiant de demande, puis valide le code via `/v2/verify/{request_id}` ; il permet également de définir un secours vocal après le SMS [2]. Le choix dépendra de la couverture, du prix et de la délivrabilité observés pour les opérateurs ivoiriens.

### Utilisation côté Kivy

L’écran « Connexion AgriLink CI » permet de sélectionner « Acheteur » ou « Vendeur », de demander le code, puis de valider celui-ci. Après validation, Kivy conserve le token en mémoire et l’envoie dans l’en-tête `Authorization`. La création ou modification d’une fiche vendeur et de son stock exige un compte vendeur dont le numéro est vérifié.

### Références

[1]: https://www.twilio.com/docs/verify/api "Twilio Verify API"
[2]: https://developer.vonage.com/en/verify/getting-started "Vonage Verify API — Getting Started"

## Abonnement vendeur avec Paystack

L’inscription vendeur est maintenant conditionnée à un abonnement actif. Le vendeur doit d’abord se connecter par SMS avec le rôle « Vendeur », initialiser le paiement Paystack, terminer le paiement dans la page de checkout, puis vérifier la référence Paystack depuis l’application Kivy. Le backend bloque ensuite les créations et modifications de fiches vendeurs lorsque l’abonnement n’est pas actif.

Paystack est appelé uniquement depuis Django : la clé secrète ne doit jamais être placée dans Kivy. Le flux utilise une référence unique, une initialisation serveur, une vérification serveur par référence et un webhook signé. Le montant local est configurable par `PAYSTACK_SUBSCRIPTION_AMOUNT`, sa durée par `PAYSTACK_SUBSCRIPTION_DAYS` et la devise par `PAYSTACK_CURRENCY`. Le multiplicateur `PAYSTACK_AMOUNT_MULTIPLIER` doit correspondre à l’unité attendue par la devise activée dans votre compte Paystack.

| Route | Méthode | Rôle |
| --- | --- | --- |
| `/api/payments/subscription/initialize/` | POST authentifié | Créer une transaction Paystack et retourner l’URL de checkout |
| `/api/payments/subscription/verify/` | POST authentifié | Vérifier la référence et activer l’abonnement |
| `/api/payments/subscription/status/` | GET authentifié | Consulter l’état et la date d’expiration |
| `/api/payments/paystack/webhook/` | POST public signé | Recevoir les événements Paystack et synchroniser le paiement |

Pour activer Paystack en test :

```bash
export PAYSTACK_SECRET_KEY="sk_test_..."
export PAYSTACK_PUBLIC_KEY="pk_test_..."
export PAYSTACK_CURRENCY="XOF"
export PAYSTACK_SUBSCRIPTION_AMOUNT="5000"
export PAYSTACK_AMOUNT_MULTIPLIER="1"
export PAYSTACK_SUBSCRIPTION_DAYS="30"
export PAYSTACK_BASE_URL="https://api.paystack.co"
```

Paystack documente l’initialisation d’une transaction avec une clé secrète côté serveur et la vérification par référence [3]. Les cartes sont disponibles sur les comptes Paystack, tandis que les autres canaux dépendent du pays et de l’éligibilité du compte ; la documentation indique que le mobile money est disponible pour les entreprises en Côte d’Ivoire [4]. Les abonnements récurrents Paystack ne doivent pas être supposés disponibles pour tous les moyens mobiles : pour ce MVP, le paiement initial active une période locale de 30 jours [5].

Le webhook doit être configuré dans le tableau de bord Paystack avec l’URL publique `https://votre-domaine/api/payments/paystack/webhook/`. En développement local, utilisez un tunnel HTTPS ou testez l’activation avec la route de vérification et les clés de test.

### Références Paystack

[3]: https://paystack.com/docs/api/transaction/ "Paystack Transaction API"
[4]: https://paystack.com/docs/payments/payment-channels/ "Paystack Payment Channels"
[5]: https://paystack.com/docs/payments/subscriptions/ "Paystack Subscriptions"

## Authentification acheteur et recommandations locales

Les acheteurs disposent maintenant d’un parcours complet par numéro de téléphone et code OTP. Après validation du code, un acheteur est orienté vers son profil pour renseigner sa région et sa localité. Le profil est lié au compte authentifié et ne peut pas être remplacé par un autre utilisateur.

L’application Kivy appelle ensuite `/api/buyer/recommendations/`. Le backend renvoie d’abord les vendeurs de la localité de l’acheteur, puis les vendeurs actifs de la même région. Les vendeurs vérifiés sont prioritaires à l’intérieur de chaque zone. Si le profil n’est pas encore configuré, l’application redirige l’acheteur vers l’écran de localisation.

| Route | Méthode | Utilisation |
| --- | --- | --- |
| `/api/auth/request-code/` | POST public | Demander le code SMS avec `role=buyer` |
| `/api/auth/verify-code/` | POST public | Valider le code et obtenir le token REST |
| `/api/buyer/me/` | GET, PATCH, PUT authentifié | Lire ou enregistrer la région et la localité de l’acheteur |
| `/api/buyer/recommendations/` | GET authentifié | Obtenir les vendeurs de la localité puis de la région |
| `/api/vendors/` | GET public | Rechercher manuellement dans l’annuaire général |

Exemple de configuration du profil acheteur :

```json
{
  "full_name": "M. Koko",
  "region": 1,
  "locality": 3
}
```

Le token reçu après OTP doit être envoyé dans l’en-tête `Authorization: Token <token>`. Les routes `buyer/me` et `buyer/recommendations` exigent un compte acheteur avec numéro vérifié.

## Notifications push pour les nouvelles commandes

AgriLink CI contient maintenant un flux de commandes avec notification ciblée du vendeur. Un acheteur authentifié crée une commande via `POST /api/orders/`. Django enregistre la commande, puis déclenche l’envoi d’une notification au vendeur après validation de la transaction locale. Les tokens d’appareil du vendeur sont enregistrés via `POST /api/notifications/devices/`.

| Route | Méthode | Fonction |
| --- | --- | --- |
| `/api/notifications/devices/` | POST authentifié vendeur | Enregistrer ou réactiver un token FCM Android |
| `/api/notifications/devices/` | GET authentifié vendeur | Consulter ses appareils enregistrés |
| `/api/orders/` | POST authentifié acheteur | Créer une commande et notifier le vendeur |
| `/api/orders/` | GET authentifié | Voir les commandes de l’acheteur ou du vendeur connecté |
| `/api/orders/{id}/` | PATCH vendeur destinataire | Mettre à jour le statut de la commande |

### Configuration Firebase côté Django

Créez un projet Firebase, activez Firebase Cloud Messaging et téléchargez le compte de service. Conservez le fichier JSON uniquement sur le serveur Django, puis définissez :

```bash
export FIREBASE_SERVICE_ACCOUNT_FILE="/chemin/securise/firebase-service-account.json"
```

Installez ensuite les dépendances :

```bash
cd backend
.venv/bin/pip install -r requirements.txt
```

Le service `directory_app/notifications.py` utilise Firebase Admin pour envoyer une notification contenant le type `new_order`, l’identifiant de la commande et l’identifiant du vendeur. Les tokens invalides sont désactivés afin de ne plus solliciter des appareils supprimés.

### Côté Kivy/Android

Le fichier `mobile/buildozer.spec` demande `pyjnius` et la permission `POST_NOTIFICATIONS`. Après obtention du token FCM par le composant Android, le client peut l’enregistrer avec :

```bash
export AGRILINK_FCM_TOKEN="token-fcm-de-test"
```

Le client Kivy appelle alors automatiquement `POST /api/notifications/devices/` lorsqu’un vendeur ouvre son espace. Pour une vraie compilation Android, il faut encore relier le token retourné par Firebase Messaging au pont Android/PyJNIus et inclure la configuration Firebase de l’application Android. Ne placez jamais le compte de service Firebase dans l’APK.

En arrière-plan, Android peut afficher la notification dans la barre système ; au premier plan, l’application doit traiter le message reçu. Cette distinction est documentée par Firebase [6] [7].

### Références Firebase

[6]: https://firebase.google.com/docs/cloud-messaging/send/v1-api "Firebase Cloud Messaging HTTP v1 API"
[7]: https://firebase.google.com/docs/cloud-messaging/android/receive-messages "Receive messages in Android apps"

## Déploiement du backend Django sur Railway

Le backend est préparé pour Railway avec PostgreSQL, Gunicorn, WhiteNoise, migrations automatiques et endpoint de santé. Railway détecte le fichier `requirements.txt` situé à la racine ; celui-ci inclut les dépendances de `backend/requirements.txt`. Le fichier `railway.json` configure le healthcheck `/api/health/` et la commande de démarrage.

### Déploiement recommandé

Créez un projet Railway, ajoutez un service PostgreSQL, puis ajoutez le dépôt GitHub contenant `agri_link_ci`. Dans les variables du service Django, ajoutez au minimum :

```text
DJANGO_SECRET_KEY=<clé longue et aléatoire>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=<domaine Railway du service>
DJANGO_CSRF_TRUSTED_ORIGINS=https://<domaine Railway du service>
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

La référence `${{Postgres.DATABASE_URL}}` doit correspondre au nom du service PostgreSQL Railway. Railway fournit automatiquement `PORT`; Gunicorn écoute cette variable sur `0.0.0.0`.

Pour activer les services externes en production, ajoutez également les variables Twilio, Paystack et Firebase documentées dans `backend/.env.example`. Les clés secrètes doivent être enregistrées dans les variables Railway et non dans GitHub ou dans l’APK Kivy.

### Contrôles après déploiement

Après le premier déploiement, vérifiez `https://<domaine>/api/health/`, puis exécutez le peuplement de démonstration uniquement si nécessaire :

```bash
python backend/manage.py seed_demo
```

La commande de démarrage exécute automatiquement `migrate`, `collectstatic` puis Gunicorn. En production, utilisez de préférence un service ou une tâche séparée pour `seed_demo`; ne chargez pas de données de démonstration à chaque redémarrage.

### Domaine et application Kivy

Après avoir généré le domaine public Railway, remplacez la valeur par défaut `AGRILINK_API_URL` dans l’application Kivy par `https://<domaine>/api`. L’URL doit être accessible depuis le téléphone Android. Pour la production, activez aussi `DJANGO_ALLOWED_HOSTS` et `DJANGO_CSRF_TRUSTED_ORIGINS` avec le domaine réellement utilisé.

Le guide officiel Railway confirme l’usage de PostgreSQL, WhiteNoise et d’un fichier `requirements.txt` pour une application Django [8]. Railway documente également les healthchecks, qui permettent de vérifier qu’un nouveau déploiement répond correctement avant sa mise en service [9].

### Références Railway

[8]: https://docs.railway.com/guides/django "Railway — Deploy a Django App"
[9]: https://docs.railway.com/deployments/healthchecks "Railway — Healthchecks"

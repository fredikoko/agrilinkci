# 🚀 Guide Complet de Mise en Production — AgriLink CI

Ce document constitue le guide officiel et exhaustif pour le déploiement en production de l'écosystème **AgriLink CI** (Backend API Django, Base de données, Cache, Passerelle de paiement Chariow, Stockage Cloud et Application Mobile Kivy).

---

## 📋 Table des Matières

1. [Architecture Globale du Système](#1-architecture-globale-du-système)
2. [Prérequis & Comptes Tiers](#2-prérequis--comptes-tiers)
3. [Matrice Complète des Variables d'Environnement](#3-matrice-complète-des-variables-denvironnement)
4. [Déploiement Backend Option A : Railway (Recommandé / PaaS)](#4-déploiement-backend-option-a--railway-recommandé--paas)
5. [Déploiement Backend Option B : Serveur Dédié / VPS (Ubuntu, Nginx, Gunicorn)](#5-déploiement-backend-option-b--serveur-dédié--vps-ubuntu-nginx-gunicorn)
6. [Configuration Détaillée des Services Tiers](#6-configuration-détaillée-des-services-tiers)
   - [A. Passerelle de Paiement Chariow](#a-passerelle-de-paiement-chariow)
   - [B. Notifications Push Firebase (FCM)](#b-notifications-push-firebase-fcm)
   - [C. SMS OTP (Twilio Verify / Vonage)](#c-sms-otp-twilio-verify--vonage)
   - [D. Stockage Persistant des Médias (AWS S3 / Cloudflare R2)](#d-stockage-persistant-des-médias-aws-s3--cloudflare-r2)
7. [Compilation et Déploiement de l'Application Mobile Kivy (Android)](#7-compilation-et-déploiement-de-lapplication-mobile-kivy-android)
8. [Checklist Finale de Sécurité & Go-Live](#8-checklist-finale-de-sécurité--go-live)
9. [Maintenance, Sauvegardes & Monitoring](#9-maintenance-sauvegardes--monitoring)

---

## 1. Architecture Globale du Système

L'infrastructure d'AgriLink CI est conçue pour la haute disponibilité, la sécurité et l'évolutivité :

```mermaid
graph TD
    ClientMobile["📱 Application Mobile Kivy (Android/iOS)"] -->|HTTPS / REST API + JWT| ReverseProxy["🛡️ Nginx / Railway Edge Router"]
    ReverseProxy -->|WSGI| Gunicorn["⚙️ Gunicorn (Workers Django)"]
    
    subgraph "Backend Django (AgriLink Core)"
        Gunicorn --> AppCore["Django 5.2 / REST Framework"]
        AppCore --> Signals["Cache Invalidation Signals"]
    end

    subgraph "Données & Performance"
        AppCore --> DB[("🐘 PostgreSQL")]
        AppCore --> Cache[("⚡ Redis Cache")]
        AppCore --> Storage["☁️ Stockage Médias (S3 / Cloudflare R2)"]
    end

    subgraph "Services Tiers"
        AppCore --> Chariow["💳 Chariow Payments (OM, MoMo, Wave, CB)"]
        Chariow -->|Webhook Pulse HMAC-SHA256| AppCore
        AppCore --> Firebase["🔔 Firebase Cloud Messaging (FCM)"]
        AppCore --> Twilio["📲 Twilio / Vonage (SMS OTP)"]
        AppCore --> Sentry["📈 Sentry (Observabilité)"]
    end
```

---

## 2. Prérequis & Comptes Tiers

Avant de démarrer le déploiement, assurez-vous de disposer des éléments suivants :

| Service | Utilité | Prérequis / Liens |
| :--- | :--- | :--- |
| **Nom de domaine** | Accès HTTPS à l'API | Un nom de domaine avec accès DNS (ex: `api.agrilink.ci`) |
| **Hébergement Backend** | Hébergement Django | Compte [Railway.app](https://railway.app) ou serveur VPS (Ubuntu 22.04/24.04) |
| **Compte Chariow** | Encaissement Mobile Money & CB | Compte marchand sur [chariow.com](https://chariow.com) |
| **Projet Firebase** | Notifications Push temps réel | Projet configuré sur [Firebase Console](https://console.firebase.google.com) |
| **Fournisseur SMS** | Authentification par code OTP | Compte Twilio (Verify Service) ou Vonage API |
| **Stockage Cloud** | Images des produits et profils | Bucket AWS S3, Cloudflare R2 ou Supabase Storage |
| **Compte Google Play** | Publication application mobile | Console Google Play Developer (25 $ à vie) |

---

## 3. Matrice Complète des Variables d'Environnement

Créez le fichier de configuration de production ou injectez ces variables dans votre panneau d'hébergement :

```ini
# ==============================================================================
# SÉCURITÉ DJANGO & CORE
# ==============================================================================
DJANGO_SECRET_KEY=cle-tres-longue-aleatoire-et-secrete-d-au-moins-50-caracteres!
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=api.agrilink.ci,agrilink-production.up.railway.app
DJANGO_CSRF_TRUSTED_ORIGINS=https://api.agrilink.ci,https://agrilink-production.up.railway.app
DJANGO_HSTS_SECONDS=31536000

# ==============================================================================
# BASE DE DONNÉES (POSTGRESQL)
# ==============================================================================
# Format : postgresql://<user>:<password>@<host>:<port>/<database>
DATABASE_URL=postgresql://agrilink_user:motdepasse_robuste@postgres.railway.internal:5432/railway

# ==============================================================================
# CACHE REDIS
# ==============================================================================
REDIS_URL=redis://default:motdepasse_redis@redis.railway.internal:6379

# ==============================================================================
# PASSERELLE DE PAIEMENT CHARIOW (https://chariow.com / https://chariow.dev)
# ==============================================================================
CHARIOW_API_KEY=sk_live_votre_cle_secrete_chariow
CHARIOW_WEBHOOK_SECRET=whsec_votre_cle_secrete_webhook_pulse
CHARIOW_BASE_URL=https://api.chariow.com/v1
CHARIOW_CURRENCY=XOF
CHARIOW_SELLER_PRODUCT_ID=prd_vendeur_mensuel_id
CHARIOW_CONSEIL_PRODUCT_ID=prd_conseil_mensuel_id
CHARIOW_CONSEIL_ANNUAL_PRODUCT_ID=prd_conseil_annuel_id
CHARIOW_SUBSCRIPTION_AMOUNT=5000
CHARIOW_SUBSCRIPTION_DAYS=30
CHARIOW_CALLBACK_URL=https://api.agrilink.ci/api/payments/subscription/status/

# ==============================================================================
# NOTIFICATIONS PUSH FIREBASE (FCM)
# ==============================================================================
# Le JSON du compte de service Firebase doit être MINIFIÉ sur une seule ligne :
FIREBASE_CREDENTIALS_JSON={"type":"service_account","project_id":"agrilink-ci",...}

# ==============================================================================
# AUTHENTIFICATION SMS OTP
# ==============================================================================
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_VERIFY_SERVICE_SID=VAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Alternative Vonage :
# SMS_PROVIDER=vonage
# VONAGE_API_KEY=xxxxxxxx
# VONAGE_API_SECRET=xxxxxxxx

# ==============================================================================
# STOCKAGE DES MÉDIAS (S3 / CLOUDFLARE R2)
# ==============================================================================
AWS_ACCESS_KEY_ID=votre_cle_acces_s3_ou_r2
AWS_SECRET_ACCESS_KEY=votre_cle_secrete_s3_ou_r2
AWS_STORAGE_BUCKET_NAME=agrilink-media-prod
AWS_S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
AWS_S3_REGION_NAME=auto

# ==============================================================================
# E-MAILS TRANSACTIONNELS (SMTP)
# ==============================================================================
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.votre_cle_api_sendgrid
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=AgriLink CI <contact@agrilink.ci>

# ==============================================================================
# OBSERVABILITÉ & LOGS
# ==============================================================================
DJANGO_LOG_LEVEL=INFO
SENTRY_DSN=https://xxxxxxxx@o0.ingest.sentry.io/0
SENTRY_TRACES_SAMPLE_RATE=0.1
```

---

## 4. Déploiement Backend Option A : Railway (Recommandé / PaaS)

Le projet contient déjà la configuration native pour Railway (`railway.json` et `Procfile`).

### Étape 4.1 : Créer le projet Railway
1. Rendez-vous sur [Railway.app](https://railway.app) et connectez-vous avec GitHub.
2. Cliquez sur **New Project** > **Deploy from GitHub repo**.
3. Sélectionnez votre dépôt : `fredikoko/agrilinkci`.

### Étape 4.2 : Ajouter la Base PostgreSQL et Redis
1. Dans le canvas de votre projet, cliquez sur **New** > **Database** > **Add PostgreSQL**.
2. Cliquez sur **New** > **Database** > **Add Redis**.
3. Railway injecte automatiquement les variables d'environnement `${{Postgres.DATABASE_URL}}` et `${{Redis.REDIS_URL}}`.

### Étape 4.3 : Configurer le Service Web Django
1. Cliquez sur le service Django AgriLink dans Railway.
2. Allez dans l'onglet **Variables** et ajoutez toutes les variables de la section 3.
3. Vérifiez les liaisons automatiques :
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
   - `REDIS_URL` = `${{Redis.REDIS_URL}}`
4. Allez dans **Settings** > **Networking** > **Generate Domain** (ex: `agrilink-production.up.railway.app`) ou associez votre domaine personnalisé (`api.agrilink.ci`).

### Étape 4.4 : Démarrage Automatique
Railway utilise le fichier `railway.json` présent à la racine :
```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": { "builder": "NIXPACKS" },
  "deploy": {
    "startCommand": "cd backend && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120",
    "healthcheckPath": "/api/health/",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE"
  }
}
```
Railway va automatiquement :
1. Construire l'image Python avec Nixpacks.
2. Appliquer les migrations de base de données (`migrate`).
3. Compiler les fichiers statiques WhiteNoise (`collectstatic`).
4. Lancer Gunicorn sur le port dynamique `$PORT`.
5. Valider la santé du service via `GET /api/health/`.

### Étape 4.5 : Initialisation des données (One-Off)
Depuis le dashboard Railway, ouvrez l'onglet **View Logs** ou la console **CLI** et exécutez :
```bash
# Pour créer le superutilisateur administrateur :
cd backend && python manage.py createsuperuser

# (Optionnel) Pour charger les régions et localités de Côte d'Ivoire :
cd backend && python manage.py seed_demo
```

---

## 5. Déploiement Backend Option B : Serveur Dédié / VPS (Ubuntu, Nginx, Gunicorn)

Si vous déployez sur un VPS (OVH, Hetzner, AWS EC2, DigitalOcean) sous Ubuntu 22.04/24.04 LTS :

### Étape 5.1 : Préparation du Système
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git nginx postgresql postgresql-contrib redis-server certbot python3-certbot-nginx
```

### Étape 5.2 : Configuration de la Base de Données PostgreSQL
```bash
sudo -u postgres psql
```
```sql
CREATE DATABASE agrilink_prod;
CREATE USER agrilink_user WITH ENCRYPTED PASSWORD 'VOTRE_MOT_DE_PASSE_SECURISE';
GRANT ALL PRIVILEGES ON DATABASE agrilink_prod TO agrilink_user;
ALTER DATABASE agrilink_prod OWNER TO agrilink_user;
\q
```

### Étape 5.3 : Installation du Projet
```bash
sudo mkdir -p /var/www/agrilink
sudo chown -R $USER:$USER /var/www/agrilink
cd /var/www/agrilink
git clone https://github.com/fredikoko/agrilinkci.git .

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Créez le fichier `/var/www/agrilink/backend/.env` avec les variables de la section 3, puis exécutez :
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_demo
python manage.py createsuperuser
```

### Étape 5.4 : Configuration de Gunicorn avec Systemd
Créez le service systemd `/etc/systemd/system/agrilink.service` :
```ini
[Unit]
Description=Gunicorn daemon for AgriLink CI
After=network.target postgresql.service redis-server.service

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/var/www/agrilink/backend
EnvironmentFile=/var/www/agrilink/backend/.env
ExecStart=/var/www/agrilink/backend/.venv/bin/gunicorn \
          --access-logfile /var/log/agrilink/gunicorn-access.log \
          --error-logfile /var/log/agrilink/gunicorn-error.log \
          --workers 3 \
          --timeout 120 \
          --bind 127.0.0.1:8000 \
          config.wsgi:application

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Activez et démarrez le service :
```bash
sudo mkdir -p /var/log/agrilink
sudo systemctl daemon-reload
sudo systemctl enable agrilink
sudo systemctl start agrilink
sudo systemctl status agrilink
```

### Étape 5.5 : Configuration de Nginx et Certificat SSL (HTTPS)
Créez le fichier `/etc/nginx/sites-available/agrilink` :
```nginx
server {
    server_name api.agrilink.ci;

    client_max_body_size 25M;

    location /static/ {
        alias /var/www/agrilink/backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location /media/ {
        alias /var/www/agrilink/backend/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

Activez le site et générez le certificat SSL gratuit Let's Encrypt :
```bash
sudo ln -s /etc/nginx/sites-available/agrilink /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Activation du SSL automatique
sudo certbot --nginx -d api.agrilink.ci
```

---

## 6. Configuration Détaillée des Services Tiers

### A. Passerelle de Paiement Chariow

1. **Création des Produits sur Chariow :**
   - Connectez-vous à votre tableau de bord [chariow.com](https://chariow.com).
   - Créez vos produits :
     - **Abonnement Vendeur Pro (Mensuel)** : Prix `5 000 FCFA`, type numérique/abonnement. Copiez son ID (ex: `prd_vendeur_mensuel`).
     - **Abonnement Conseil Pro (Mensuel)** : Prix `3 000 FCFA` (ex: `prd_conseil_mensuel`).
     - **Abonnement Conseil Pro (Annuel)** : Prix `29 000 FCFA` (ex: `prd_conseil_annuel`).
2. **Récupération des Clés API :**
   - Allez dans **Paramètres** > **Clés API**.
   - Copiez la clé secrète de production `sk_live_...` dans la variable `CHARIOW_API_KEY`.
3. **Configuration du Webhook (Pulse) :**
   - Allez dans **Paramètres** > **Webhooks / Pulses** > **Ajouter un endpoint**.
   - URL de destination : `https://api.agrilink.ci/api/payments/chariow/webhook/` (doit impérativement être en HTTPS).
   - Événements sélectionnés : `successful.sale`, `sale.completed`.
   - Copiez le secret du webhook (`whsec_...`) dans la variable `CHARIOW_WEBHOOK_SECRET`.

### B. Notifications Push Firebase (FCM)

1. Ouvrez [Firebase Console](https://console.firebase.google.com).
2. Rendez-vous dans **Paramètres du projet** (icône d'engrenage) > **Comptes de service**.
3. Sélectionnez le SDK Firebase Admin Python et cliquez sur **Générer une nouvelle clé privée**.
4. Un fichier JSON est téléchargé sur votre machine.
5. **Minification sur une seule ligne :**
   En PowerShell sous Windows :
   ```powershell
   (Get-Content -Raw "chemin\vers\serviceAccountKey.json" | ConvertFrom-Json | ConvertTo-Json -Compress)
   ```
   Ou sous Linux :
   ```bash
   jq -c . serviceAccountKey.json
   ```
6. Copiez la chaîne JSON résultante dans la variable d'environnement `FIREBASE_CREDENTIALS_JSON`.

### C. SMS OTP (Twilio Verify / Vonage)

Pour éviter les limitations du mode développement :
1. Créez un service sur [Twilio Verify](https://console.twilio.com/).
2. Définissez la durée du code à 10 minutes.
3. Renseignez `SMS_PROVIDER=twilio`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, et `TWILIO_VERIFY_SERVICE_SID`.

### D. Stockage Persistant des Médias (AWS S3 / Cloudflare R2)

En production, les conteneurs éphémères (comme Railway) ne conservent pas les images téléversées sur disque local. Il est indispensable d'utiliser S3 ou Cloudflare R2 :
1. Créez un bucket privé : `agrilink-media-prod`.
2. Configurez la règle CORS du bucket :
   ```json
   [
     {
       "AllowedHeaders": ["*"],
       "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
       "AllowedOrigins": ["*"],
       "ExposeHeaders": ["ETag"]
     }
   ]
   ```
3. Renseignez les variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, et `AWS_S3_ENDPOINT_URL`. Django utilise automatiquement `S3Boto3Storage` dès que ces variables sont détectées.

---

## 7. Compilation et Déploiement de l'Application Mobile Kivy (Android)

L'application mobile est prête pour Android grâce à Buildozer (`mobile/buildozer.spec`).

### Étape 7.1 : Configuration de l'URL d'API de Production
Dans `mobile/core.py`, vérifiez ou configurez l'URL cible de production :
```python
API_BASE_URL = os.getenv("AGRILINK_API_URL", "https://api.agrilink.ci/api/")
```

### Étape 7.2 : Environnement de Build Linux / WSL
Buildozer nécessite un environnement Linux (Ubuntu 22.04 recommandé ou WSL2 sous Windows) :
```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
pip3 install --upgrade buildozer Cython
```

### Étape 7.3 : Génération du Keystore de Signature Android
Générez votre clé de signature de production (à conserver précieusement et en lieu sûr) :
```bash
keytool -genkey -v -keystore agrilink-release.keystore -alias agrilink_key -keyalg RSA -keysize 2048 -validity 10000
```

### Étape 7.4 : Compilation du Fichier AAB (Android App Bundle pour Google Play)
```bash
cd mobile
export P4A_RELEASE_KEYSTORE=agrilink-release.keystore
export P4A_RELEASE_KEYALIAS=agrilink_key
export P4A_RELEASE_KEYSTORE_PASSWD="votre_mot_de_passe"
export P4A_RELEASE_KEYALIAS_PASSWD="votre_mot_de_passe"

# Compilation Release :
buildozer android release
```
Le fichier `.aab` généré dans `bin/` est prêt à être téléversé sur la **Google Play Console** dans l'onglet **Production**.

---

## 8. Checklist Finale de Sécurité & Go-Live

Avant d'ouvrir l'accès aux utilisateurs finaux, validez chaque point :

- [ ] **HTTPS actif partout** : Certificat SSL valide avec redirection automatique HTTP -> HTTPS.
- [ ] **`DJANGO_DEBUG=false`** : Vérifiez qu'aucune page de debug Django ne s'affiche en cas d'erreur 404/500.
- [ ] **Endpoint Health** : `curl https://api.agrilink.ci/api/health/` renvoie `{"status": "ok", "db": "ok", "cache": "ok"}` avec HTTP 200.
- [ ] **Clés secrètes protégées** : Aucune clé sensible (`SECRET_KEY`, `CHARIOW_API_KEY`, mots de passe BDD) n'est présente dans le code Git ou dans l'application mobile.
- [ ] **Throttling activé** : Les limites de débit sur l'authentification (OTP à 5/h par IP) protègent contre les attaques par force brute.
- [ ] **Paiement Chariow en réel** : Effectuez un test avec un compte marchand réel (transaction de 100 FCFA ou montant test) et validez la réception du webhook Pulse.
- [ ] **Tests automatisés validés** : Exécutez `python manage.py test directory_app conseil` (32 tests OK).

---

## 9. Maintenance, Sauvegardes & Monitoring

### Sauvegardes Automatiques PostgreSQL
Sur Railway, les snapshots quotidiens sont activés par défaut.
Sur VPS, configurez un cron quotidien avec `pg_dump` :
```bash
0 3 * * * pg_dump -U agrilink_user -h localhost agrilink_prod | gzip > /var/backups/agrilink/db_$(date +\%Y\%m\%d).sql.gz
```

### Surveillance des Logs en Direct
- **Sur Railway :** Dashboard > Projet > Service Django > **Deploy Logs** ou **HTTP Logs**.
- **Sur VPS :**
  ```bash
  journalctl -u agrilink.service -f
  tail -f /var/log/agrilink/gunicorn-error.log
  tail -f /var/log/nginx/error.log
  ```

### Observabilité Sentry
Dès qu'une exception non interceptée survient en production, Sentry capture la trace complète, l'utilisateur concerné et l'environnement sans impacter le client.

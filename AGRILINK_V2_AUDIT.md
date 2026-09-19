# Audit d’écart AgriLink CI V2

## Synthèse

Le projet possède déjà une base Django REST et un mobile Kivy fonctionnels avec authentification OTP, vendeurs, catalogue, stock simple, abonnements Paystack, Conseil Pro, notifications FCM et analytics vendeur. Le cahier des charges joint décrit cependant une V2 plus large, notamment avec JWT, limitation des abus, états vendeur détaillés, traçabilité des stocks, évaluations, cache Redis, tâches asynchrones, stockage externe, supervision et une marketplace transactionnelle.

La contrainte produit existante est conservée : **aucune commande en ligne ne sera réintroduite automatiquement**, car les exigences historiques du projet privilégient le contact direct téléphone/WhatsApp. Les modules panier, commandes et paiement de commandes devront donc rester optionnels jusqu’à validation explicite.

## État comparatif

| Domaine | État actuel observé | Écart V2 | Priorité |
|---|---|---|---|
| Authentification | OTP téléphone/e-mail et Token DRF | Access/refresh tokens, révocation et sessions appareils | Haute |
| Protection anti-abus | Limites OTP métier présentes | Rate limiting par IP/utilisateur et connexion | Haute |
| Paiements | Paystack vendeur/Conseil et webhook | Idempotence renforcée, journal d’événement et validation uniforme | Haute |
| Vendeurs | Fiche pending/approved/rejected et gestion propriétaire | DRAFT, UNDER_REVIEW, SUSPENDED et transitions admin | Haute |
| Produits | Catalogue global et stocks vendeur | Images, prix structurés, disponibilité et serializers séparés | Moyenne |
| Stocks | Quantité disponible et saisie manuelle | Entrées/sorties, seuils, historique et contrôle de stock négatif | Haute |
| Recherche | Filtres région/localité/catégorie et tri Pro | Prix, disponibilité, rayon géographique et pagination robuste | Moyenne |
| Géolocalisation | Latitude/longitude sur vendeurs/localités | Recherche par distance/PostGIS | Moyenne |
| Avis | Non identifié dans les modèles actuels | Notes, commentaires, unicité par transaction et modération | Moyenne |
| Favoris | Favoris d’articles Conseil | Favoris vendeurs/produits en plus | Moyenne |
| Conseil | Premium et favoris limités | Comptabilisation mensuelle des articles premium | Haute |
| Notifications | FCM et e-mail/SMS abonnement | Traitement asynchrone avec file de tâches | Haute |
| Cache | Non identifié dans les dépendances | Redis pour référentiels et recherches fréquentes | Moyenne |
| Stockage | Fichiers locaux non structurant | Stockage objet externe et validation d’images | Moyenne |
| API | Routes `/api/...` existantes | Version `/api/v2/` et format de réponse standardisé | Moyenne |
| Mobile | Écrans modulaires et ApiClient | Session persistante, cache local, retry et mode faible connexion | Haute |
| Administration | Admin Django des modèles principaux | Tableau de bord métier, audit et modération étendus | Moyenne |
| Observabilité | Logs Django classiques et health check Railway | logs structurés, Sentry, vérification DB/Redis | Haute |
| Tests | 13 tests backend existants | couverture sécurité, stocks, paiements, webhooks et Conseil | Haute |
| CI/CD | Pas de pipeline identifié | GitHub Actions, lint, audit dépendances et tests | Moyenne |

## Ordre recommandé d’implémentation

La première étape de la V2 doit renforcer les fondations sans casser les parcours actuels : sécuriser les permissions et les paiements, ajouter les états vendeur et l’historique de stock, puis traiter les notifications asynchrones et les performances. Le mobile sera ensuite adapté à la persistance de session et aux réseaux instables.

Les commandes en ligne, le panier, les commandes et le paiement d’une commande sont volontairement placés dans une phase séparée. Leur activation nécessite une confirmation fonctionnelle, car elle modifierait la règle actuelle « pas de commande en ligne ».

## Premiers fichiers prioritaires

- `backend/directory_app/models.py` pour les états vendeur, l’historique de stock, les favoris et les avis ;
- `backend/directory_app/views.py` et `serializers.py` pour les permissions par propriété et les réponses publiques/privées ;
- `backend/directory_app/paystack_service.py` et `payment_views.py` pour l’idempotence Paystack ;
- `backend/conseil/views.py` et ses modèles pour le quota premium mensuel ;
- `backend/config/settings.py` et `requirements.txt` pour Redis, cache et observabilité ;
- `mobile/core.py` pour le stockage de session, les retries, le cache et la gestion de connexion faible ;
- `Procfile`, `railway.json`, `.gitignore` et la documentation de production pour les contrôles de déploiement.

## Décision de périmètre

La V2 sera construite par phases vérifiables. Chaque phase devra conserver les tests existants, créer les migrations nécessaires et documenter les variables de production. Les secrets, bases locales, caches, médias et fichiers compilés resteront exclus du dépôt et des archives de livraison.

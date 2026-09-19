# AgriLink CI V2 — Progression

## Fonctionnalités intégrées dans cette itération

Cette itération a suivi les priorités de sécurité, fiabilité, marketplace et expérience mobile du cahier des charges.

| Fonctionnalité | Implémentation |
|---|---|
| Limitation anti-abus | Throttles DRF dédiés aux demandes OTP, vérifications OTP, connexion et récupération de compte |
| Déconnexion sécurisée | `POST /api/auth/logout/` supprime le token DRF du compte |
| Session mobile | Token conservé dans un stockage JSON local Kivy, suppression lors de la déconnexion |
| Réseau instable | Timeout configurable et une relance contrôlée des requêtes mobiles |
| Stock fiable | Seuil d’alerte, mouvements entrée/sortie/correction et blocage des sorties supérieures au stock |
| Audit stock | `StockMovement` conserve les quantités avant/après, le vendeur et la date |
| Favoris vendeurs | `vendor-favorites/` avec contrôle d’unicité et accès privé par utilisateur |
| Favoris produits | `product-favorites/` avec contrôle d’unicité et accès privé par utilisateur |
| Avis vendeurs | `vendor-reviews/`, note de 1 à 5, commentaire, publication et modération admin |
| Indicateurs vendeurs | Note moyenne et nombre d’avis agrégés en base dans les listes publiques |
| Paiements idempotents | Une vérification Paystack répétée ne prolonge plus deux fois un abonnement déjà activé |
| Documentation | Audit complet V2 dans `AGRILINK_V2_AUDIT.md` |

## Routes principales ajoutées

```text
POST   /api/auth/logout/
GET    /api/stock-movements/
POST   /api/stock-movements/
GET    /api/vendor-favorites/
POST   /api/vendor-favorites/
DELETE /api/vendor-favorites/{id}/
GET    /api/product-favorites/
POST   /api/product-favorites/
DELETE /api/product-favorites/{id}/
GET    /api/vendor-reviews/
POST   /api/vendor-reviews/
PATCH  /api/vendor-reviews/{id}/
DELETE /api/vendor-reviews/{id}/
```

## Migrations

Les migrations ajoutées dans cette itération sont :

```text
directory_app/migrations/0012_vendorproduct_alert_threshold_stockmovement.py
directory_app/migrations/0013_productfavorite_vendorfavorite_vendorreview.py
```

## Vérifications réalisées

Les commandes suivantes passent dans l’environnement de développement :

```bash
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test directory_app conseil
cd ..
python3 -m compileall -q backend mobile
```

## Fonctionnalités volontairement non activées automatiquement

Le cahier des charges décrit un panier, des commandes et le paiement de commandes. Le projet historique demande explicitement de ne pas proposer de commande en ligne et de conserver le contact direct téléphone/WhatsApp. Ces modules restent donc hors activation tant qu’une validation fonctionnelle explicite n’est pas donnée.

Les prochaines étapes recommandées sont l’ajout d’un vrai quota mensuel Conseil Pro, l’activation optionnelle de Redis/Celery pour les notifications, l’ajout d’un stockage objet externe pour les images, puis l’observabilité et la CI/CD.

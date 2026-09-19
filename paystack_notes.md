# Notes Paystack vérifiées

## Paiement transactionnel

Documentation officielle : https://paystack.com/docs/api/transaction/

Le backend doit initialiser une transaction avec la clé secrète côté serveur, conserver la référence retournée et rediriger l’utilisateur vers l’URL d’autorisation. Après le retour de paiement, le serveur doit appeler l’endpoint de vérification par référence et contrôler au minimum le statut `success`, la référence, le montant attendu et la devise avant d’activer l’abonnement.

## Abonnements récurrents

Documentation officielle : https://paystack.com/docs/payments/subscriptions/

Paystack propose des plans avec une période et un montant, puis une création d’abonnement via un plan. La documentation précise que les abonnements récurrents supportent les cartes et le prélèvement direct au Nigeria ; il ne faut donc pas promettre un renouvellement automatique par mobile money en Côte d’Ivoire sans confirmation de l’éligibilité du compte Paystack. Pour le MVP ivoirien, le flux recommandé est un paiement initial via les canaux disponibles sur le compte, suivi d’une activation pour une durée définie côté application.

## Décision MVP

Créer un `Payment` local avec une référence unique, le montant attendu, la devise, le statut et la réponse Paystack minimale. Créer un `SellerSubscription` avec `starts_at`, `ends_at`, `status` et l’utilisateur vendeur. Le vendeur ne peut créer ou activer sa fiche qu’après une vérification serveur réussie. Ajouter un webhook signé pour synchroniser les événements Paystack, tout en conservant la vérification par référence comme source de confirmation immédiate.

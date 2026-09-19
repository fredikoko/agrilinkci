# Tableau de bord financier administrateur

## Accès

Le tableau de bord est réservé aux comptes Django administrateurs (`is_staff=True`) :

```text
GET /api/admin/financial-dashboard/?days=30
```

Le paramètre `days` accepte une période comprise entre 1 et 365 jours. La réponse utilise la structure `success/data` et regroupe les indicateurs financiers de la période demandée.

## Indicateurs

| Groupe | Indicateurs |
|---|---|
| Paiements | paiements réussis, montant encaissé, paiements échoués et paiements en attente |
| Abonnements vendeurs | abonnements actifs, expirés, revenus et nombre de paiements |
| Abonnements Conseil Pro | abonnements actifs, expirés, revenus et nombre de paiements |
| Ventes enregistrées | transactions, unités vendues, chiffre d’affaires calculé avec quantité × prix unitaire |
| Meilleurs vendeurs | classement par chiffre d’affaires avec unités et nombre de transactions |

Les paiements sont sélectionnés à partir de leur statut serveur `success` et de leur date de paiement. Le mobile ne fournit jamais les totaux financiers de ce tableau de bord.

## Tests ajoutés

Le fichier `backend/directory_app/test_v2_finance.py` couvre :

- la vérification idempotente d’un paiement Paystack déjà réussi, sans nouvel appel Paystack et sans prolongation de l’abonnement ;
- une sortie de stock valide et le blocage d’une sortie supérieure à la quantité disponible ;
- une entrée de stock et la conservation de l’historique des mouvements ;
- la protection du tableau financier contre les utilisateurs non administrateurs ;
- la présence des métriques d’abonnement pour un administrateur.

La suite complète `directory_app` et `conseil` comporte désormais 16 tests et passe avec succès.

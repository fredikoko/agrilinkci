# Notes Chariow vérifiées

## Passerelle de paiement Chariow

Documentation officielle : [https://chariow.dev](https://chariow.dev)
Plateforme : [https://chariow.com](https://chariow.com)

Chariow est une solution de paiement optimisée pour l'Afrique de l'Ouest, supportant le Mobile Money (Orange Money, MTN MoMo, Wave, Moov) et les cartes bancaires (Visa, Mastercard).

### 1. Initiation d'un paiement (`POST /v1/checkout`)
- Authentification : `Authorization: Bearer <CHARIOW_API_KEY>`
- URL : `https://api.chariow.com/v1/checkout`
- Corps de la requête :
  - `product_id` : ID du produit créé sur votre boutique Chariow (ex: `prd_vendeur_mensuel`, `prd_conseil_mensuel`).
  - `email` ou `customer_email` : Adresse e-mail du client.
  - `first_name`, `last_name`, `phone` : Coordonnées du client.
  - `metadata` : Dictionnaire de données personnalisées (`reference`, `purpose`, `user_id`).
- Réponse :
  - `step: "payment"`
  - `payment.checkout_url` : URL sécurisée vers laquelle rediriger l'utilisateur pour procéder au règlement.

### 2. Vérification d'une vente (`GET /v1/sales`)
- Recherche par référence ou ID de transaction : `GET /v1/sales?search=<reference>` ou `GET /v1/sales/<sale_id>`
- Statuts de succès : `completed`, `settled`.

### 3. Webhooks & Notifications d'événements (Pulses)
- Header de signature : `x-chariow-signature` (HMAC-SHA256 calculé sur le corps brut avec le secret webhook).
- Headers contextuels : `x-pulse-id`, `x-pulse-delivery-id`, `x-pulse-event` (ex: `successful.sale`, `sale.completed`).
- Le webhook permet la synchronisation asynchrone et idempotente en temps réel.

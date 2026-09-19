# Notifications d’abonnement vendeur

Le backend envoie une notification dans l’application et tente également un envoi par e-mail et par SMS lorsque cela est possible.

## Événements

| Événement | Notification |
|---|---|
| Paiement confirmé | Confirmation de l’activation et date de fin du plan |
| Sept jours avant l’échéance | Rappel de renouvellement |
| Un jour avant l’échéance | Rappel urgent de renouvellement |
| Après l’échéance | Confirmation de l’expiration et retour aux limites gratuites |

Le service ne crée pas de doublons pour les rappels d’expiration déjà envoyés.

## E-mail

En production, configurez les variables suivantes dans Railway :

```text
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=votre-compte-smtp
EMAIL_HOST_PASSWORD=votre-mot-de-passe-smtp
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
DEFAULT_FROM_EMAIL=no-reply@agrilink.ci
```

L’adresse utilisée est celle du compte, puis celle du compte d’authentification ou du profil acheteur si nécessaire.

## SMS

Pour les SMS transactionnels Twilio, configurez :

```text
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_MESSAGING_SERVICE_SID=MG...
```

Si aucun Messaging Service n’est utilisé, configurez plutôt :

```text
TWILIO_FROM_NUMBER=+...
```

Le numéro du vendeur doit être enregistré au format international. En développement, l’absence de configuration Twilio ne bloque pas le paiement : l’événement est tout de même conservé dans les notifications internes et l’échec SMS est journalisé.

## Vérification Paystack

La confirmation est déclenchée après la vérification serveur du paiement, que celle-ci arrive par l’endpoint de vérification mobile ou par le webhook Paystack. Le webhook reste idempotent grâce à la référence de paiement persistée.

## Alerte automatique d’expiration

La commande Django à exécuter une fois par jour est :

```bash
cd backend
python manage.py check_seller_subscriptions
```

Configurez cette commande avec le planificateur quotidien de votre hébergeur Railway, par exemple à 08:00 UTC. Une autre possibilité consiste à l’exécuter via un cron externe sécurisé qui appelle une tâche protégée, mais la commande Django reste la méthode recommandée pour conserver le contrôle dans le backend.

La commande marque les abonnements échus comme `expired`, envoie l’alerte d’expiration et envoie les rappels lorsque l’abonnement arrive à 7 jours ou 1 jour de son échéance.

## Fichiers concernés

- `backend/directory_app/subscription_notifications.py`
- `backend/directory_app/management/commands/check_seller_subscriptions.py`
- `backend/directory_app/paystack_service.py`
- `backend/directory_app/models.py`
- `backend/config/settings.py`
- `backend/directory_app/migrations/0011_alter_appnotification_kind.py`

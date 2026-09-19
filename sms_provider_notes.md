# Notes de comparaison des fournisseurs SMS OTP

## Twilio Verify
Source officielle : https://www.twilio.com/docs/verify/api

Le flux documenté utilise un service Verify réutilisable. L’application envoie une vérification avec `channel: sms` et le numéro au format international E.164, puis vérifie le code avec une requête séparée. La documentation indique aussi des canaux complémentaires comme l’appel vocal, l’e-mail et WhatsApp, ainsi que des fonctions de limitation et de prévention de la fraude.

## Vonage Verify
Source officielle : https://developer.vonage.com/en/verify/getting-started

Le flux documenté commence par un POST sur `/v2/verify`, avec un workflow pouvant tenter le SMS puis l’appel vocal en secours. La validation se fait avec un POST sur `/v2/verify/{request_id}` et le code reçu par l’utilisateur. L’API prend également en charge plusieurs canaux et la personnalisation du workflow.

## Décision de conception proposée

Pour AgriLink CI, isoler le fournisseur derrière une classe `SmsProvider` et conserver uniquement un identifiant de transaction OTP côté serveur. Ne jamais stocker le code en clair. En développement, utiliser un fournisseur `ConsoleSmsProvider` qui écrit le code dans les logs ou renvoie un code de test explicitement activé ; en production, brancher Twilio Verify ou Vonage Verify via variables d’environnement. Le numéro doit être normalisé et validé en E.164 avant l’appel externe. Ajouter une expiration courte, un nombre maximal d’essais et une limitation par numéro et adresse IP.

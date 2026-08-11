# Critique du projet, risques et pistes d'amélioration

## 1. Risque légal — à lire en premier

Scraper des sites marchands français viole quasi systématiquement leurs conditions
générales d'utilisation, même sans contournement technique agressif. Ce n'est pas
bloquant pour un usage personnel/petit groupe, mais :

- Ne jamais scraper pour revendre l'information, ni pour de l'achat automatisé
  ("botting" de stock) — c'est là que le risque juridique et de blocage devient sérieux.
- Rester sur un usage perso/petit serveur privé plutôt qu'un service ouvert à grande
  échelle : plus le volume de requêtes et d'utilisateurs grandit, plus le risque
  (technique et légal) grandit avec.
- Le contournement actif d'un antibot (Playwright pour "passer" une protection) est une
  zone grise : c'est toléré en usage perso raisonnable, mais garder à l'esprit que le
  but ici est *rester discret et ne pas nuire*, pas *maximiser l'agressivité du scrape*.

Ce projet est cadré comme un outil de veille personnelle, pas un outil de sniping/achat
automatique — voir le "Hors périmètre" du [PRD](PRD.md). Le garder ainsi.

## 2. Playwright partout = coût CPU/RAM, hébergement payant assumé

Décision : pas de fallback HTTP par site, Playwright partout pour tous les sites, sans
exception — priorité à la robustesse anti-détection sur la légèreté. L'objectif n'est
plus "léger" mais "pas inutilement lourd" : hébergement prévu sur Railway ou Render
(payant), donc du budget CPU/RAM est disponible.

Reste important malgré tout :
- Réutiliser un même contexte navigateur entre cycles au lieu de relancer Chromium à
  chaque scrape (noté dans ARCHITECTURE.md) — ça reste la principale source d'économie
  et évite de payer pour rien, indépendamment du budget disponible.
- Surveiller la RAM réelle en usage prolongé pour dimensionner le plan Railway/Render
  (les plans hobby ont des limites de RAM assez basses — un navigateur headless par
  site actif en simultané peut dépasser un plan gratuit/starter rapidement).
- Railway/Render : vérifier que l'image de déploiement peut installer les dépendances
  système de Chromium (`playwright install --with-deps`) — c'est souvent le point de
  friction n°1 pour déployer Playwright sur ces plateformes (buildpack vs Docker).

## 3. Grammaire de filtre en texte libre = risque d'ambiguïté

`contient "30" ou contient "ans" et contient "coffret"` est ambigu sans parenthèses
explicites (priorité ET/OU pas universellement évidente pour un utilisateur non
technique). Recommandation :
- Exiger des parenthèses dès qu'il y a un mélange ET/OU dans une même expression, et
  rejeter avec un message clair plutôt que deviner une priorité.
- Fournir `/filtre test "texte item fictif"` (déjà dans TASKS.md phase 3) pour que
  l'utilisateur valide son filtre avant de le laisser tourner en prod.

## 4. Un item "change" — bien définir ce qui redéclenche une alerte

Le PRD dit : rupture→dispo ou changement de prix redéclenche une alerte. Attention à
un piège classique : un site qui fait fluctuer légèrement l'affichage (ex: prix barré
vs prix promo, format de dispo qui change sans changement réel) peut générer du bruit.
→ Normaliser strictement les valeurs de prix/dispo dans chaque adapter avant comparaison,
pas de comparaison sur le texte brut de la page.

## 5. Un seul point de panne : le bot process

Tout (scheduler, scraper, bot Discord) tourne dans un seul process asyncio. Une
exception non catchée dans un adapter ne doit jamais tuer tout le bot. Recommandation
dès la phase 4 : chaque tâche de scraping par site doit être isolée (try/except large
autour de `fetch_items`, log de l'erreur dans le salon log, le site repasse juste en
erreur/backoff) — jamais de crash global à cause d'un site qui a changé sa page HTML.

## 6. Suggestions d'amélioration (au-delà du MVP)

- **Snapshot d'image** : stocker une miniature de l'item au moment de l'alerte (au cas
  où l'image change/disparaît ensuite), utile pour l'historique.
- **Historique consultable** (`/stats`, backlog v2) : nombre de matchs par profil sur
  les 7 derniers jours, utile pour ajuster un filtre trop large/trop strict.
- **Alerte de santé** : si un site n'a renvoyé aucun item depuis longtemps alors qu'il
  en renvoyait avant, c'est probablement l'adapter qui est cassé (le site a changé son
  HTML) plutôt qu'une vraie absence de stock — vaut une alerte distincte dans le salon
  log ("adapter Auchan : 0 items depuis 2h, vérifier").
- **Mode "dry-run" global** : lancer le bot sans notifier réellement (juste logger ce
  qui aurait matché), pratique pour valider un nouvel adapter ou un nouveau filtre sans
  spammer le salon alerte.

## 7. Questions tranchées

- Usage strictement personnel/privé, un seul serveur Discord, pas d'exposition
  publique — confirmé.
- Hébergement : Railway ou Render, payant si nécessaire — donc pas de contrainte dure
  de budget RAM/CPU, juste éviter le gaspillage évident (voir §2).
- Hébergement : **Render, type de service "Background Worker"** — adapté nativement à
  un process sans serveur HTTP (contrairement à un service web classique, pas de
  spin-down à contourner). Render Disks pour le volume persistant.
- Déploiement via **Dockerfile** (pas de buildpack natif) — nécessaire pour maîtriser
  l'installation des dépendances système de Chromium
  (`playwright install --with-deps chromium`), point de friction connu des buildpacks
  auto-détectés.
- **Commande `/pause`** confirmée au scope : coupe immédiatement tout scraping (tous
  sites), utile si un site commence visiblement à bloquer/CAPTCHA en boucle. Ajoutée à
  TASKS.md phase 6.

## 8. Questions encore ouvertes (à trancher avant/pendant l'implémentation)

- Le stockage SQLite + fichiers config JSON doit vivre sur un Render Disk monté sur un
  chemin persistant — à configurer avant la mise en prod, sinon la config et
  l'historique de dédup repartent de zéro à chaque redeploy.

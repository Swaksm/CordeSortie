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

## 2. Playwright partout = tension avec "léger et performant"

Le choix (validé) d'utiliser Playwright sur tous les sites est le plus robuste face à
l'antibot, mais c'est objectivement le choix le plus lourd en CPU/RAM parmi les options
possibles. Pistes pour limiter l'impact :
- Réutiliser un même contexte navigateur entre cycles au lieu de relancer Chromium à
  chaque scrape (déjà noté dans ARCHITECTURE.md — c'est important, pas optionnel).
- Si un site s'avère ne pas avoir d'antibot après test réel, envisager de repasser cet
  adapter en HTTP simple (httpx) pour lui — l'interface `SiteAdapter` le permet sans
  changer le reste du système.
- Surveiller la RAM réelle en usage prolongé avant de multiplier les sites actifs.

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

## 7. Questions encore ouvertes (à trancher avant/pendant l'implémentation)

- Un seul serveur Discord au départ (assumé dans le PRD) — confirmé ?
- Le bot doit-il être hébergé en continu (VPS/Raspberry Pi maison) ? Ça conditionne le
  budget RAM/CPU réellement disponible pour Playwright.
- Faut-il une commande d'urgence `/pause` qui coupe tout scraping immédiatement (utile
  si un site commence visiblement à bloquer/CAPTCHA en boucle) ?

# Tâches — CordeSortie

Cocher au fur et à mesure. Garder ce fichier synchronisé avec l'état réel du code —
c'est la référence pour savoir où on en est, pas la conversation.

## Phase 0 — Setup projet

- [x] Cadrage (PRD, architecture, liste de sites) — `docs/`
- [x] Init git
- [x] Squelette Python (`requirements.txt`, structure de dossiers)
- [x] `.env.example` (token Discord, chemins config)
- [x] CI GitHub Actions (`.github/workflows/ci.yml`) : lint (`ruff`) + tests
      (`pytest`, matrice Python 3.12/3.13) avec couverture de code (`pytest-cov`,
      branch coverage, seuil `--cov-fail-under=35` pour ne pas casser le build sur
      la couverture actuelle réelle ~39%, faible car adapters/commandes Discord
      nécessitent un vrai navigateur/serveur Discord). Rapport de couverture
      affiché dans le résumé de run GitHub et exporté en artefact XML.

## Phase 1 — Bot Discord de base

- [x] Connexion bot, enregistrement des slash commands (squelette vide)
- [x] ~~Commande `/config set-channel <role: config|alerte|log> <#salon>`~~
      **simplifiée en Phase 7** en `/config set-log-channel` : les rôles "config" et
      "alerte" n'ont jamais été lus nulle part dans le code (dead code découvert en
      revue) — les alertes vont dans le salon dédié par profil depuis longtemps, et
      aucune commande n'a jamais utilisé de "salon config". Seul "log" servait.
- [x] Persistance de la config de base dans `data/<guild_id>/config.json`
- [x] Commande `/config show` (affiche la config actuelle en éphémère)

## Phase 2 — Stockage

- [x] Schéma SQLite (`seen_items`, `scrape_runs`)
- [x] Migration/init DB au démarrage
- [x] Fonctions de dédup (clé stable par item)

## Phase 3 — Moteur de filtres

- [x] Grammaire de filtre : `contient`, `ET`, `OU`, `NON`, parenthèses
- [x] Parser + évaluateur, avec tests unitaires sur des cas ambigus
- [x] Support `prix_min` / `prix_max` / `only_available`
- [x] Commandes `/filtre add`, `/filtre list`, `/filtre remove`, `/filtre test <texte>`
      (mode dry-run pour valider un filtre sur un item fictif)
- [x] Salon d'alerte dédié auto-créé par profil (`<pseudo>-<nom du filtre>`, regroupés
      dans une catégorie "Alertes" — séparée de "CordeSortie" qui ne contient que les
      salons de pilotage du bot), supprimé automatiquement avec le profil
- [x] Salon "cordesortie-aide" (hors plan initial) : documentation des commandes
      générée depuis les commandes réellement enregistrées (`bot.tree.walk_commands`),
      pas un texte maintenu à la main — régénérée à chaque connexion, découpée en
      plusieurs messages épinglés si ça dépasse la limite Discord (jamais tronquée)
- [x] Commande `/sites` (hors plan initial) : liste les sites supportés et leur statut
      réel (dérivé de `REGISTRY`, pas d'une doc à maintenir à part)

## Phase 4 — Scraper engine

- [x] Interface `SiteAdapter` + registre de sites disponibles
- [x] Setup Playwright (contexte navigateur partagé, gestion cookies)
- [x] Premier adapter (Carrefour) — testé en direct sur le site, 30 items, prix
      et titres corrects
- [x] Normalisation `Item` (titre, prix, dispo, url, image)
- [x] Adapter JouéClub (hors plan initial, ajouté car dispo web fiable) — testé en
      direct, 26 items dont 6 correctement détectés indisponibles
- [x] Commande `/filtre dry-run` (hors plan initial) : scrape en direct les sites
      d'un profil et applique le moteur de filtres dessus, sans alerter ni toucher
      à la dédup — pont manuel entre scraper et filtres en attendant le scheduler
      (Phase 5). Testé bout en bout : 30 matchs corrects sur carrefour + joueclub.
- [x] Adapter Leclerc — testé en direct, 42 items, prix corrects (pas de vraie
      détection de rupture, comme Carrefour)
- [x] Adapter Auchan — testé en direct, 30 items, 17 dispo/13 rupture correctement
      détectés via microdonnées schema.org (`meta[itemprop=availability]`)
- [x] ~~Adapter Fnac~~ **abandonné** : bloqué par un CAPTCHA Datadome dès la
      première requête (voir docs/SITES.md) — pas d'adapter, contourner un CAPTCHA
      n'est pas fait ici

## Phase 5 — Scheduler & anti-détection

- [x] Boucle asyncio par (serveur, site) — `SchedulerManager`, une tâche par site
      actif, recalculées à chaque `/filtre add|remove` (pas de polling périodique)
- [x] Plancher dur 60s codé en dur (`_HARD_FLOOR_SECONDS`, indépendant de la config)
- [x] Jitter sur l'intervalle de scrape (±15%) et sur le log
- [x] Backoff exponentiel + jitter sur erreurs/blocages détectés (jusqu'à 60 min max)
- [x] Intervalle configurable par profil via `/filtre add interval_minutes` (pas de
      commande séparée `/config set-interval` — le profil suffit, cf. décision
      ARCHITECTURE.md §5)
- [x] Détection explicite de page de challenge/captcha (`BlockedError`, domaines
      Datadome/hCaptcha/Cloudflare connus) → log + backoff du site concerné
- [x] Testé en direct : scheduler tourne, scrape 4 sites/minute, `scrape_runs`
      correctement peuplée

## Phase 6 — Alertes & log

- [x] Notifier : embed Discord pour chaque item matché, envoyé dans le salon d'alerte
      dédié du profil (`profile.alert_channel_id`)
- [x] Anti-doublon scopé par profil (`alert_channel_id`), pas juste par site — deux
      profils qui matchent le même item sont notifiés indépendamment (voir
      `tests/test_storage.py`)
- [x] Notification si prix change ou item redevient disponible
- [x] Flux d'évènements en direct dans le salon log (hors plan initial, demandé en
      plus du résumé périodique) : création/suppression de filtre, résultat concis
      de chaque cycle de scrape (`log_event()` dans `notifier.py`)
- [x] Log périodique (salon log), intervalle configurable indépendamment du scrape
      (`config.log_interval_minutes`)
- [x] Gestion des erreurs remontées dans le log (site down, adapter cassé, blocage)
- [x] Commande `/pause` + `/resume` : coupe/reprend immédiatement tout scraping
- [x] Testé en direct sur Discord : alerte reçue pour un filtre large
      (`contient("pokemon")`), confirmée que la dédup empêche le spam au cycle
      suivant

## Phase 7 — Durcissement / qualité

- [x] Tests sur le moteur de filtres (cas AND/OR/NOT imbriqués) — `tests/test_filters.py`
- [x] Tests sur le scheduler (jitter respecte le plancher, backoff fonctionne,
      plafonne) — `tests/test_scheduler.py`, logique de délai extraite dans
      `_compute_delay_seconds()` pour être testable sans event loop réel
- [x] Gestion propre de l'arrêt : `bot.close()` vérifié — ferme la DB, arrête
      Playwright (aucun process Chromium orphelin), annule les tâches du
      scheduler (`tests/test_bot_lifecycle.py`). Découvert au passage : mes
      propres redémarrages de test laissaient tourner plusieurs instances du
      bot en parallèle (outil de gestion de process, pas un bug du bot) —
      nettoyé, à surveiller en usage réel.
- [ ] Revue anti-détection avant mise en prod longue durée (voir RISKS.md)
- [x] Documentation utilisateur finale (README : installation, création du bot
      Discord, premiers pas, commandes, déploiement)
- [x] Revue complète du code : bugs trouvés et corrigés — rôles de salon "config"/
      "alerte" morts (supprimés, cf. Phase 1), `/filtre list` sans garde-fou de
      longueur (pouvait planter sur beaucoup de profils), scheduler qui pouvait
      mourir silencieusement sur une config corrompue, sites dupliqués dans
      `/filtre add` non dédupliqués, formulation "Filtres prix (prix >= X)"
      redondante, mise à jour inutile du message info quand rien ne change,
      `refresh_guild()` non protégé pouvant laisser une interaction en suspens.
      Tous corrigés, 30 tests toujours verts, testé en direct sur Discord.

## Phase 8 — Déploiement (reporté)

Décision (2026-08-12) : déploiement mis en pause, priorité à fiabiliser le bot en
local d'abord. Aucune option gratuite pérenne trouvée pour un Background Worker +
disque persistant : Render (aucun tier gratuit pour ça), Railway (trial épuisé,
passage payant nécessaire), Oracle Cloud Always Free (vrai gratuit à vie, mais
capacité ARM saturée au moment de l'essai — à retenter plus tard). Le `Dockerfile`
est prêt et testé, indépendant de la plateforme choisie in fine.

- [x] `Dockerfile` (build + import testés en local avec Docker, y compris Playwright)
- [x] Repo GitHub créé et code poussé (nécessaire pour connecter n'importe quelle
      plateforme de déploiement)
- [ ] Choisir la plateforme définitive (Render / Railway / Oracle Cloud / auto-hébergé)
- [ ] Service créé, connecté au repo, `DISCORD_TOKEN` en variable d'environnement
- [ ] Volume/disque persistant monté sur `/data`

## Phase 9 — Améliorations post-revue (2026-08-12)

- [x] `/filtre edit` : modifier un profil existant sans le supprimer/recréer
      (expression, sites, prix, dispo, intervalle). Limite connue : impossible
      d'effacer price_min/price_max une fois posés (None = "inchangé" dans cette
      commande) — remove + add si besoin.
- [x] Salon d'alerte privé (`/filtre add private:true`) : visible uniquement par le
      créateur (les admins voient toujours tout via la permission Administrator,
      indépendamment des overwrites). Affiché avec 🔒 dans `/filtre list`.
- [x] `/stats` : stats de scrape sur une fenêtre de temps (défaut 24h) + total
      d'alertes historique par profil (`Database.count_seen_items`).
- [x] `/filtre pause name:X` / `/filtre resume name:X` : pause un seul profil (le
      site continue d'être scrapé si un autre profil actif le cible aussi).
      Distinct de `/pause` global. Affiché avec ⏸️ dans `/filtre list`.
- [x] Cap de longueur de nom de salon (100 car. Discord) : déjà couvert par
      `slugify()` (tronque à 90) depuis la Phase 3 — verrouillé par tests
      (`tests/test_alert_channels.py`).

37 tests au total, testé en direct sur Discord (config existante restée compatible,
aucun reset nécessaire — tous les nouveaux champs ont des valeurs par défaut).

## Backlog / v2 (hors MVP)

- [ ] Multi-serveur Discord avec configs isolées
- [ ] Intervalle de scrape par site (plutôt que global)
- [ ] Interface web de configuration

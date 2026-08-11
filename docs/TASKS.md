# Tâches — CordeSortie

Cocher au fur et à mesure. Garder ce fichier synchronisé avec l'état réel du code —
c'est la référence pour savoir où on en est, pas la conversation.

## Phase 0 — Setup projet

- [x] Cadrage (PRD, architecture, liste de sites) — `docs/`
- [x] Init git
- [x] Squelette Python (`requirements.txt`, structure de dossiers)
- [x] `.env.example` (token Discord, chemins config)
- [ ] CI minimale (lint + un test qui importe le package) — optionnel mais utile tôt

## Phase 1 — Bot Discord de base

- [x] Connexion bot, enregistrement des slash commands (squelette vide)
- [x] Commande `/config set-channel <role: config|alerte|log> <#salon>`
- [x] Persistance de la config de base (channels) dans `data/<guild_id>/config.json`
- [x] Commande `/config show` (affiche la config actuelle dans le salon config)

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
      dans une catégorie "CordeSortie"), supprimé automatiquement avec le profil

## Phase 4 — Scraper engine

- [ ] Interface `SiteAdapter` + registre de sites disponibles
- [ ] Setup Playwright (contexte navigateur partagé, gestion cookies)
- [ ] Premier adapter (Carrefour recommandé comme site de validation, voir SITES.md)
- [ ] Normalisation `Item` (titre, prix, dispo, url, image)
- [ ] Adapters Auchan, Leclerc, Fnac

## Phase 5 — Scheduler & anti-détection

- [ ] Boucle asyncio par site, plancher dur 60s codé en dur (pas contournable via config)
- [ ] Jitter sur l'intervalle de scrape
- [ ] Backoff exponentiel + jitter sur erreurs/blocages détectés
- [ ] Commande `/config set-interval <site|profil> <minutes>` avec validation du plancher
- [ ] Détection explicite de page de challenge/captcha → log + pause du site concerné

## Phase 6 — Alertes & log

- [ ] Notifier : embed Discord pour chaque item matché, envoyé dans le salon d'alerte
      dédié du profil (`profile.alert_channel_id`)
- [ ] Anti-doublon (ne pas re-notifier un item inchangé)
- [ ] Notification si prix change ou item redevient disponible
- [ ] Log périodique (salon log), intervalle configurable indépendamment du scrape
- [ ] Gestion des erreurs remontées dans le log (site down, adapter cassé)
- [ ] Commande `/pause` : coupe immédiatement tout scraping (tous sites)

## Phase 7 — Durcissement / qualité

- [ ] Tests sur le moteur de filtres (cas AND/OR/NOT imbriqués)
- [ ] Tests sur le scheduler (jitter respecte le plancher, backoff fonctionne)
- [ ] Gestion propre de l'arrêt (SIGINT/SIGTERM) — fermer proprement Playwright
- [ ] Revue anti-détection avant mise en prod longue durée (voir RISKS.md)
- [ ] Documentation utilisateur finale (README : comment inviter le bot, premiers pas)

## Phase 8 — Déploiement Render

- [x] `Dockerfile` (build + import testés en local avec Docker)
- [x] Repo GitHub créé et code poussé (nécessaire pour connecter Render)
- [ ] Service Render "Background Worker" créé, connecté au repo
- [ ] `DISCORD_TOKEN` configuré en variable d'environnement Render (jamais commité)
- [ ] Render Disk monté sur `/data` (doit matcher `DATA_DIR=/data` du Dockerfile)
- [ ] Mettre à jour le Dockerfile avec `playwright install --with-deps chromium`
      une fois la Phase 4 (scraper) codée

## Backlog / v2 (hors MVP)

- [ ] Multi-serveur Discord avec configs isolées
- [ ] Intervalle de scrape par site (plutôt que global)
- [ ] Interface web de configuration
- [ ] Historique/statistiques consultables via commande (`/stats`)
- [ ] Salon d'alerte par profil en privé (visible uniquement par le créateur du
      filtre + les admins) au lieu de visible par tout le serveur

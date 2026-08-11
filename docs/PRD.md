# PRD — CordeSortie

## 1. Objectif

Un bot Discord (en local pour l'instant, déploiement cloud reporté — voir
[TASKS.md Phase 8](TASKS.md)) qui surveille en continu des sites marchands français à
la recherche d'items Pokémon (cartes, coffrets, produits dérivés...) correspondant à
des critères définis par l'utilisateur, et notifie sur Discord dès qu'un item
disponible matche ces critères.

Usage strictement personnel/privé : un seul serveur Discord, pas d'exposition publique.

Priorités du projet, par ordre :
1. **Fiable** — ne pas rater une alerte, ne pas spammer de faux positifs.
2. **Discret** — ne jamais se faire bloquer par les antibots des sites cibles.
3. **Simple/intuitif** — un utilisateur non technique doit pouvoir configurer ses
   filtres sans toucher à du code.
4. **Pas inutilement lourd** — pas de sur-ingénierie ; le budget CPU/RAM n'est pas la
   contrainte principale (hébergement payant assumé), mais on évite le gaspillage
   évident (ex : relancer un navigateur entier à chaque cycle de scrape).

## 2. Utilisateurs cibles

Un seul serveur Discord privé, avec un ou plusieurs utilisateurs qui définissent des
filtres et reçoivent les alertes. Pas de multi-serveur au MVP (voir backlog v2).

## 3. Fonctionnalités

### 3.1 Filtres

L'utilisateur définit un ou plusieurs **profils de filtre**, chacun composé de :

- Une **expression logique** sur le texte de l'item (titre + description), combinant des
  conditions `contient "X"` avec `ET` / `OU`, avec parenthésage possible pour des cas
  du type `(contient "30" OU contient "ans") ET contient "boite"`.
- Une **liste de sites** à surveiller pour ce profil, choisie parmi la liste supportée
  (voir [SITES.md](SITES.md)) — un profil peut cibler un seul site ou plusieurs.
- Des **filtres additionnels optionnels** :
  - Prix min / prix max.
  - Disponibilité uniquement (par défaut : oui — n'alerter que si l'item est en stock).
- Un nom de profil (pour le retrouver/l'éditer/le supprimer).

Chaque profil est indépendant : un item peut déclencher plusieurs alertes s'il matche
plusieurs profils.

### 3.2 Salons Discord

Salons auto-gérés par le bot, répartis en deux catégories Discord :

**Catégorie "Alertes"** :
- Un **salon par profil de filtre**, auto-créé à la création du profil (`<pseudo>-<nom
  du filtre>`), auto-supprimé avec lui. Un message par item matché (embed : titre,
  prix, site, lien, image), plus un message épinglé récapitulant les critères du
  profil. Évite que les alertes de plusieurs filtres se mélangent.

**Catégorie "CordeSortie"** (pilotage du bot) :
- **Salon info** (`📊-info-N-filtres`) : tableau de bord, renommé avec le nombre de
  filtres actifs, message épinglé listant tous les profils.
- **Salon aide** (`cordesortie-aide`) : documentation de toutes les commandes,
  générée depuis le code (jamais désynchronisée), régénérée à chaque connexion.
- **Salon log** (assigné via `/config set-log-channel`, un seul, pas auto-créé) :
  flux en direct (création/suppression de filtre, résultat de chaque cycle de
  scrape) **et** un récapitulatif périodique toutes les *N* minutes (configurable).
  Sert à vérifier que le bot est vivant sans lire les logs serveur.

### 3.3 Sites supportés

Liste initiale à choisir dans un ensemble prédéfini (extensible) : Auchan, Leclerc,
Carrefour, Fnac, et autres à définir — voir [SITES.md](SITES.md) pour le détail et
l'état d'implémentation de chaque adapter. L'utilisateur choisit, par profil de filtre,
quels sites de cette liste surveiller.

### 3.4 Rythme de scrape

- Intervalle **configurable par l'utilisateur**, en minutes.
- **Plancher dur à 1 minute** — toute valeur en dessous est refusée par le bot avec un
  message d'erreur explicite.
- L'intervalle réellement appliqué est **jitteré** : ± quelques secondes/pourcentage
  autour de la valeur choisie, pour ne jamais scraper à un rythme parfaitement
  périodique (voir [ARCHITECTURE.md](ARCHITECTURE.md#anti-détection)).
- L'intervalle peut être différent par site (un site plus permissif peut être scrapé
  plus souvent qu'un site sensible), configuration à affiner en phase 2.

### 3.5 Anti-doublon

Un item déjà alerté ne doit pas re-déclencher une alerte tant que rien n'a changé
(même item, même dispo, même prix). Si le prix change ou l'item redevient disponible
après une rupture, une nouvelle alerte est légitime.

## 4. Hors périmètre (MVP)

- Achat automatique de l'item (pas d'auto-checkout — hors sujet et à haut risque légal).
- Multi-serveur Discord avec configs isolées (v2 potentielle).
- Interface web de configuration (tout passe par Discord + fichier config pour le MVP).

## 5. Critères de succès

- Le bot tourne plusieurs jours sans se faire bloquer par un antibot.
- Une alerte arrive en moins de `intervalle + quelques secondes` après la mise en ligne
  réelle d'un item matchant.
- Configurer un nouveau filtre prend moins d'une minute via les commandes Discord.

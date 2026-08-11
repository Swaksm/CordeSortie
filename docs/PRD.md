# PRD — CordeSortie

## 1. Objectif

Un bot Discord auto-hébergé qui surveille en continu des sites marchands français à la
recherche d'items Pokémon (cartes, coffrets, produits dérivés...) correspondant à des
critères définis par l'utilisateur, et notifie sur Discord dès qu'un item disponible
matche ces critères.

Priorités du projet, par ordre :
1. **Fiable** — ne pas rater une alerte, ne pas spammer de faux positifs.
2. **Discret** — ne jamais se faire bloquer par les antibots des sites cibles.
3. **Simple/intuitif** — un utilisateur non technique doit pouvoir configurer ses
   filtres sans toucher à du code.
4. **Léger** — pas de sur-ingénierie, empreinte CPU/RAM raisonnable.

## 2. Utilisateurs cibles

Un serveur Discord (potentiellement plusieurs à terme, mais le MVP vise **un serveur**),
avec un ou plusieurs utilisateurs qui définissent des filtres et reçoivent les alertes.

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

Trois rôles de salon, configurables (un salon Discord = un rôle, assignable via commande) :

- **Salon config** : lecture/écriture de la configuration (liste des filtres actifs,
  sites, intervalle de scrape). Reflète l'état du fichier de config lisible.
- **Salon alerte** : un message par item matché, avec titre, prix, site, lien direct,
  et si possible une image.
- **Salon log** : toutes les *N* minutes (configurable), un récapitulatif : nombre de
  scrapes effectués, nombre d'items vus, nombre de matchs, erreurs éventuelles
  (site down, adapter cassé, etc.). Sert à vérifier que le bot est vivant sans avoir à
  lire les logs serveur.

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

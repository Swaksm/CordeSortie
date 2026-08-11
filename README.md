# CordeSortie

Bot Discord de veille sur des items Pokémon en vente sur des sites marchands français
(Auchan, Leclerc, Carrefour, Fnac, ...), avec filtres configurables par l'utilisateur
et alertes en temps quasi réel dans Discord.

*CordeSortie* : la corde qui te sort de la galère de surveiller les sites toi-même.

## Statut

En phase de cadrage — pas encore de code. Voir la documentation :

- [docs/PRD.md](docs/PRD.md) — fonctionnalités et périmètre
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — design technique
- [docs/SITES.md](docs/SITES.md) — sites cibles et leur statut
- [docs/TASKS.md](docs/TASKS.md) — roadmap détaillée
- [docs/RISKS.md](docs/RISKS.md) — critique, risques, pistes d'amélioration
- [CLAUDE.md](CLAUDE.md) — guide pour contribuer avec Claude Code

## Stack

Python 3.12+, discord.py, Playwright, SQLite. Détails dans
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Usage prévu

Outil de veille personnelle, pas un outil d'achat automatique. Voir la section
"Risque légal" de [docs/RISKS.md](docs/RISKS.md) avant tout déploiement à plus grande
échelle.

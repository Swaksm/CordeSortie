# Sites cibles

Liste des enseignes envisagées pour le scraping d'items Pokémon. Statut à mettre à
jour au fur et à mesure de l'implémentation de chaque adapter.

| Site      | Statut adapter | Antibot connu               | Notes |
|-----------|-----------------|------------------------------|-------|
| Auchan    | À faire         | À évaluer                   | Recherche produit via leur moteur de recherche interne. |
| Leclerc   | À faire         | À évaluer                   | Multi-magasins (e.leclerc) — vérifier si stock est national ou par magasin. |
| Carrefour | À faire         | À évaluer                   | Historiquement protégé (Akamai/Datadome selon les périodes) — commencer par ce site pour valider l'approche Playwright. |
| Fnac      | À faire         | À évaluer                   | Souvent une cible prioritaire pour les produits Pokémon (forte demande = forte protection anti-bot probable). |
| Autre ?   | —               | —                            | Compléter (Cultura, Micromania, Cdiscount, TF1 Games, sites officiels Pokémon Center EU...) selon les besoins. |

## Ajouter un nouveau site

1. Vérifier manuellement la structure de la page produit/recherche et la présence
   d'un antibot (ouvrir les devtools réseau, chercher Cloudflare/Datadome/Akamai dans
   les headers de réponse).
2. Créer `scraper/adapters/<site>.py` implémentant `SiteAdapter`.
3. Ajouter une entrée dans le tableau ci-dessus avec le statut réel.
4. Tester en isolation (`python -m cordesortie.scraper.adapters.<site>`) avant de
   l'activer dans un profil de filtre en production.

## Notes anti-détection par site

À documenter au fur et à mesure des observations réelles (ex : "Carrefour bloque après
X requêtes/minute même avec Playwright", "Fnac nécessite un cookie de consentement
cookies avant d'accéder au moteur de recherche"). Ce fichier doit rester à jour car ces
comportements évoluent dans le temps côté sites.

# Sites cibles

Liste des enseignes envisagées pour le scraping d'items Pokémon. Statut à mettre à
jour au fur et à mesure de l'implémentation de chaque adapter.

| Site      | Statut adapter | Antibot connu               | Notes |
|-----------|-----------------|------------------------------|-------|
| Carrefour | **Fait**        | Aucun rencontré en test      | Recherche `?q=pokemon`, cartes `article[data-testid=<EAN>]`. Le moteur de recherche exclut déjà les produits indisponibles côté API (`displayUnavailable=false`) → tous les items renvoyés sont marqués `available=True`, pas de vraie détection de rupture pour ce site. Sélecteurs relevés le 2026-08-11. |
| JouéClub  | **Fait**        | Aucun rencontré en test      | Recherche `?searchText=pokemon`. Vraie disponibilité en ligne exposée (`.product__stockIcon-card`, statut "Web" vs "En magasin"). Sélecteurs relevés le 2026-08-12. |
| Leclerc   | **Fait**        | Aucun rencontré en test      | Recherche `/recherche?q=pokemon`, cartes `article[data-product-card]` (`data-ean` = clé stable). Aucun marqueur de rupture trouvé sur les cartes → `available=True` toujours, pas de vraie détection de rupture. Sélecteurs relevés le 2026-08-12. |
| Auchan    | **Fait**        | Aucun rencontré en test      | Recherche `/recherche?text=pokemon`, cartes `article.product-thumbnail`. Microdonnées schema.org (`meta[itemprop=price]`, classe CSS `outOfStock`) → **vraie détection de rupture fiable**, comme JouéClub. Sélecteurs relevés le 2026-08-12. |
| Fnac      | **Bloqué**      | **Datadome (CAPTCHA)**       | Bloqué dès la première requête, même en Playwright avec UA réaliste — redirection immédiate vers une page CAPTCHA `geo.captcha-delivery.com`. Pas d'adapter : contourner un CAPTCHA activement n'est pas quelque chose qu'on fait ici. Reste dans `SUPPORTED_SITES` mais absent de `REGISTRY` (ne renverra jamais d'item). |
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

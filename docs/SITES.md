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
| Cultura   | **Fait**        | Aucun rencontré en test      | Recherche `/search/results?search_query=pokemon`, cartes `article.one-card--product` (`data-product-sku` = clé stable). Vend aussi via des vendeurs marketplace en plus de son propre stock : seul le prix Cultura (`div.price`) est retenu, pas le "+N neufs dès X€" du marketplace qui peut être plus élevé. Disponibilité textuelle (`en stock Cultura` vs `Précommande...`/`Dispo sous N jours...`) → vraie détection de rupture/précommande. Sélecteurs relevés le 2026-08-28. |
| King Jouet | **Bloqué**     | **Datadome (CAPTCHA)**       | Même blocage que Fnac : `page.goto()` renvoie un 403 avec un iframe CAPTCHA `geo.captcha-delivery.com` dès la première requête en Playwright headless (fonctionne dans un navigateur avec session/cookies déjà établis, ce qui a d'abord induit en erreur lors du repérage manuel des sélecteurs — à vérifier systématiquement avec un contexte Playwright *neuf*, pas juste visuellement). Pas d'adapter. Reste dans `SUPPORTED_SITES`, absent de `REGISTRY`. |
| Intermarché | **Écarté**    | —                            | Catalogue et prix par magasin (nécessite de choisir une adresse/un magasin avant tout accès produit) — pas de recherche nationale unifiée comme Leclerc/Carrefour/Auchan. Ne rentre pas dans le modèle d'adapter actuel (un profil = une recherche nationale). |
| Système U | **Écarté**      | —                            | Même limitation qu'Intermarché : e-commerce (Courses U) organisé par magasin, pas de catalogue national. |
| Cora      | **Écarté**      | —                            | Racheté par Carrefour (2024) — le site redirige entièrement vers carrefour.fr, déjà couvert par l'adapter Carrefour. |
| Géant Casino | **Écarté**   | —                            | Redirige vers "PetitCasino" (format supérette de proximité) — plus de catalogue jouet/hypermarché national à scraper. |
| Maxi Toys | **Écarté**      | —                            | Fusionné avec King Jouet (même groupe) — le site redirige vers king-jouet.com, donc bloqué par le même Datadome, sans intérêt d'adapter séparé. |
| Autre ?   | —               | —                            | Compléter (Micromania, Cdiscount, TF1 Games, sites officiels Pokémon Center EU...) selon les besoins. |

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

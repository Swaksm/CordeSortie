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
| Ludifolie | **Fait**        | Aucun rencontré en test      | Recherche `/recherche?controller=search&s=pokemon` (PrestaShop). Cartes `.product-miniature[data-id-product]`, microdonnées schema.org (`itemprop=price/availability`) → **vraie détection de rupture fiable**, comme Auchan. Sélecteurs relevés le 2026-08-30. |
| Micromania | **Fait**       | Aucun rencontré en test      | Recherche via l'URL Salesforce Commerce Cloud `/on/demandware.store/Sites-Micromania-Site/fr_FR/Search-Show?q=pokemon` (deviner l'URL à la main échoue, `/notfound` — passer par un vrai clic sur le raccourci "POKEMON" du moteur de recherche pour l'obtenir). Cartes `.product-tile[data-pid]`, microdonnées schema.org → vraie détection de rupture. Sélecteurs relevés le 2026-08-30. |
| La Taverne de Dream | **Fait** | Aucun rencontré en test | Boutique Shopify (thème Dawn), catégorie Pokémon dédiée (`/collections/pokemon-nouveau-site`) plutôt qu'une recherche plein texte. Cartes `li.grid__item`, clé stable = slug d'URL (pas d'ID numérique exposé). Pas de vraie détection de rupture (juste un badge visuel "Épuisé" si présent). Sélecteurs relevés le 2026-08-30. |
| Comptoir des Écoliers | **Instable** | — | WooCommerce standard (`li.product`, classes `instock`/`outofstock`), sélecteurs propres et adapter écrit (`adapters/comptoirdesecoliers.py`) — mais le site **recharge la page en plein milieu du scrape** de façon reproductible (2/2 essais), invalidant les handles Playwright en cours d'extraction et faisant planter `page.close()` après coup. Volontairement absent de `REGISTRY` : pas un antibot dur, mais trop imprévisible pour les cycles réguliers. Repéré/testé le 2026-08-30. |
| Philibert | **Instable**   | —                            | Le moteur de recherche est un widget tiers (Doofinder) qui se re-render de façon imprévisible pendant la frappe automatisée (testé avec `press_sequentially`, `fill()`, et `page.keyboard.type` — 3 approches différentes, 3 résultats différents, jamais la bonne recherche). Prix/dispo exposés proprement une fois sur la page de résultats (`data-value`, `data-availability`), mais impossible d'y arriver de façon fiable. Adapter écrit (`adapters/philibert.py`) mais absent de `REGISTRY`. Testé le 2026-08-30. |
| Outpost Brussels | **Bloqué** | **Cloudflare**            | Page "Un instant…" (vérification de sécurité Cloudflare) dès la première requête. Pas d'adapter. Testé le 2026-08-30. |
| Dracaustore | **Fait**       | Aucun rencontré en test      | Boutique Shopify (thème plus ancien, pas Dawn), recherche `/search?type=product&q=pokemon`. Cartes `.grid-item.search-result`, clé stable = slug d'URL. Aucun marqueur de rupture trouvé → `available=True` toujours, comme Carrefour/Leclerc. Sélecteurs relevés le 2026-08-30. |
| Amazon FR | **Écarté**      | —                            | Écarté d'entrée sans test : anti-bot réputé bien plus agressif qu'un simple CAPTCHA (détection IP), et prix marketplace multi-vendeurs hors du contrôle du site — hors du cadre "prix constructeur" du projet. |
| La Grande Récré | **Écarté**  | —                            | Le domaine ne résout plus (`la-grande-recre.fr` et `grandrecre.fr` échouent) — probablement discontinué, même groupe (Ludendo) que Maxi Toys qui a aussi disparu. |
| Autre ?   | —               | —                            | Compléter (Cdiscount, TF1 Games, sites officiels Pokémon Center EU...) selon les besoins. |

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

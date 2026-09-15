# Données terrain

## Introduction

Le rôle du module de données terrain (data/) est de prendre une Bounding Box (BBox) géographique et de collecter les données exploitables en lien avec celle-ci.

## Organisation du code dans data/

- data/
    - Elevation/
        - client_opentopography.py
        - parser_elevation.py
        - structures_elevation.py
    - OverPass/
        - client_overpass.py
        - queries_overpass.py
        - raster_overpass.py
        - search_overpass_raster.py
        - structures_op.py
    - data_fetcher.py
    - disk_cache.py
    - structures_communes.py

## structures_communes.py

###  class BBox ''Bounding box'':
- La BBox est défini à sa base par 4 coordonnées (S, W, N, E), formant une boite rectangulaire.
- Est une @dataclass **mutable** qui sert de **conteneur** pour les données qui la concerne :
    
    - dem_data : les données d'élévations relative à cette BBox (np.ndarray), le plus utilisées des attributs. Sert pour la rasterisation de OSM, A*, et élévation du tracé, visualisation.
    - osm_features : cache des données OpenStreetMap relative à cette BBox (geojson), usage interne à OverPass
    - raster_osm : version rasterisé du cache geojson. permet de construire la grille des multiplicateurs
    - osm_mult : chemin critique dans le routage, une des entrées de a_star, représente les multiplicateurs de terrain pour chaque case du raster.
    - cost_grid : visualisation de la grille des costs pour une BBox données. ne fait pas aprtie du pipeline principal. usage : debug/visualisation

    - les champs de données ont le champ *compare* a false. une comparaison de deux BBox ne compare que les coordonnées.

### fonctions rowcol_to_latlon et latlon_to_rowcol

- wrappers pour les fonction rasterio de conversions rangées/colonnes <-> coordonnées
- raison principale est que rasterio utilise lon/lat comme convention et le projet utilisais lat/lon, alors un wrapper permettait de ne pas se tromper.

## data_fetcher.py ''le pipeline d'acquisition des données'' 

### fonction fetch_terrain

- prend 3 arguments 
    - la BBox que l'ont veut remplir, 
    - le type de DEM que l'ont veut du API d'élévation (par défaut sur COP30, ne pas toucher pour l'instant). Classe définit dans structures_elevation.py
    - le dictionnaire des poids associés à chaque feature OSM.
- retourne None (effet de bord sur la BBox en argument)

- Effectue un pipeline en 3 étapes : 
    - remplir le champ dem_data, soit par le cache soit par le API de opentopography
    - obtenir les données geojson du OverPass API en lien avec cette BBox et les rasterisé sur le même format que le dem_data
    - construire la grille des multiplicateurs de terrain OSM
    - imprimé les temps pour chaque étape partielle et la fonction totale.

### fonction fetch_parsed_dem
- va chercher les bytes de dem en cache ou par le API de opentopography. 
- les convertis/retourne en DEMdata(structure_elevation.py) un dataclass qui sert de conteneur pour les données relevant du dem.

## Elevation/ sous module d'élévation

### structures_elevation.py

#### class DEMType (Enum)
- énumère les collections de DEM disponibles chez OpenTopography : SRTMGL1 (30m), SRTMGL3 (90m), AW3D30 (30m), COP30 (30m), COP90 (90m), NASADEM (30m).
- le projet utilise COP30 partout, les autres sont là pour pouvoir changer de source sans toucher au code.

#### class DEMdata (NamedTuple)
- conteneur **immuable** du résultat du parsing, 4 champs :
    - array : grille 2D numpy des élévations en mètres (les cases sans données sont des np.nan(not a number))
    - transform : l'objet Affine de rasterio qui fait le lien case <-> coordonnées (voir plus bas)
    - slope : grille 2D des pentes, **en radians**
    - aspect : grille 2D des orientations de pente, **en degrés** (0 = nord, sens horaire)
- les 4 grilles ont exactement la même shape, donc un tuple (row, col) désigne la même case partout.
 
### client_opentopography.py

- Ce fichier sert de lien avec l'API d'élévation, il retourne du GeoTIFF soit des bytes, le parsing est fait par le parser (voir plus bas). Les clés API sont lues dans le .env

#### fonction get_dem(demtype, bbox) -> bytes

- Cette fonction reçoit une BBox en argument ainsi qu'un DEMtype (par défaut COP30 pour l'ensemble du projet).  

1. On vérifie la cache pour voir si on a une partie ou la totalité de la zone demandée en cache. 

2. Si on a la **couverture complête** en cache, retourner les données.

3. Si on a une **couverture partielle** de la zone et que les zones manquantes font moins que **_SLIVER_TOLERANCE_DEG** on considère qu'un appel API nevaut pas la peine et on utilise le cache tel quel.

4. Si une des zones manquantes est sous la taille de **_MIN_FETCH_DEG**, l'API refuserait l'appel, alors on jette la couverture partielle et on fait une requête complête.

5. **couverture partielle**, Si on a une partie de la zone demandée en cache et que els zones manquantes sont assez grandes pour être demandé au API, on fait les demandes en parallêle.

6. Une fois les zones manquantes téléchargées, chacune est sauvegardée au cache **individuellement**, puis toutes les tuiles (cache + nouvelles) sont fusionnées et découpées exactement sur la BBox demandée.

- Note sur l'étape 5 : chaque zone manquante est élargie de **_FETCH_OVERLAP_DEG** (~3-4 pixels) avant d'être demandée, pour qu'elle chevauche ses voisines. Sans ça, une frontière mal alignée sur la grille native laisse une couture de nodata à la fusion, et cette couture devient un mur infranchissable pour A*.

#### fonction _fetch_from_api

- construit la requête GET vers OpenTopography avec le demtype, les 4 coordonnées, outputFormat=GTiff et une clé API.
- **rotation des clés** : sur une erreur 429 (quota dépassé) ou 401 (clé invalide), on passe simplement à la clé suivante. Les timeouts et erreurs de connexion, eux, remontent tout de suite parce que changer de clé n'y changerait rien.
- si toutes les clés sont épuisées, lève une HTTPError.

#### fonctions _merge_dem_bytes et _crop_to_bbox

- _merge_dem_bytes : ouvre chaque bloc de bytes en mémoire (MemoryFile) et les assemble avec rasterio.merge. Le nodata=-9999 est passé **explicitement**, sinon la fusion ne reconnaît pas toujours les pixels manquants et laisse des coutures entre tuiles adjacentes.
- _crop_to_bbox : découpe le raster fusionné pile sur la BBox demandée. C'est ce qui garantit que la grille retournée correspond exactement à la BBox, peu importe combien de tuiles ont servi à la construire.

### parser_elevation.py

- Ce fichier convertit les bytes GeoTIFF en structure exploitable (DEMdata). Un GeoTIFF contient à la fois les valeurs d'élévation (grille de pixels) et les métadonnées géographiques (coin supérieur gauche, taille des pixels, système de coordonnées).

#### le transform (Affine)

- 6 nombres qui décrivent la géométrie du raster, c'est le lien entre une case (row, col) et une coordonnée (lat, lon) :
    - a : largeur d'un pixel en longitude (deg/pixel), positif vers l'est
    - b : rotation colonne -> ligne, ~toujours 0
    - c : longitude du coin haut-gauche
    - d : rotation ligne -> colonne, ~toujours 0
    - e : hauteur d'un pixel en latitude (deg/pixel), **négatif** parce que les rangées descendent vers le sud
    - f : latitude du coin haut-gauche
- les rotations sont nulles parce que les DEM sont alignés sur le nord. C'est ce qui permet les conversions simples des wrappers de structures_communes.py.

#### fonction parse_dem_data(data) -> DEMdata

1. Ouvre le GeoTIFF en mémoire avec rasterio et lit la **bande 1**. Un DEM n'a qu'une seule bande, et la convention géospatiale numérote à partir de 1.
2. Récupère le transform du fichier.
3. Remplace la valeur nodata du fichier par np.nan.
4. Filtre les valeurs absurdes : tout ce qui dépasse 9000 m (plus haut que l'Everest) ou descend sous -500 m devient nan.
5. Calcule slope et aspect, puis assemble le DEMdata.

- peut lever rasterio.errors.RasterioIOError si les données sont corrompues ou invalides.

#### fonction _compute_slope
P.S cette fonction n'est plus utilisé pour le pipeline principal car elle ne permet pas de distinguer une montée d'une descente.
Comparaison_visuelle.py s'en sert pour des fin de visualisation et les tests de cost_grid également. On pourrait potentiellement rendre son calcul paresseux pour ne pas le faire à chaque parse du DEM.

- retourne un tuple (slope, aspect), les deux en même temps parce que l'aspect se déduit des mêmes gradients.
- le vrai problème à régler ici : **un pixel n'a pas la même taille en mètres partout sur la planète**.
    - 1 degré de **latitude** vaut ~111 320 m, constant partout -> un scalaire.
    - 1 degré de **longitude** vaut 111 320 * cos(latitude), donc ça rétrécit en montant vers les pôles -> un vecteur, une valeur par rangée du raster.

1. Calculer la latitude de chaque rangée à partir du transform (f + e * index de la rangée).
2. Convertir la taille des pixels en mètres : hauteur = |e| * 111320 (scalaire), largeur = |a| * (vecteur des m/deg de lon), remis en colonne pour le broadcast numpy.
3. np.gradient sur la grille d'élévation, ce qui donne dz_drow (variation nord-sud) et dz_dcol (variation est-ouest), en mètres par pixel.
4. Diviser par la taille réelle des pixels pour obtenir de vraies pentes rise/run : dz_dy et dz_dx.
5. Pythagore sur chaque couple : magnitude = sqrt(dz_dx² + dz_dy²), puis arctan pour passer en **radians**.

#### fonction _compute_aspect
P.S l'aspect n'est jamais utilisé dans le pipeline, lors de la cocneption du fichier parser_elevation.py il semblait potentiellement utile et la fonction n'avait que deux lignes. on pourrait aussi rendre son calcul paresseux. 

- l'aspect est la **direction vers laquelle la pente descend**.
- formule : (90 - degrés(arctan2(-dz_dy, dz_dx))) % 360, ce qui convertit la convention mathématique (0 = est, sens antihoraire) vers la convention boussole (0 = nord, sens horaire).
- utilité : combiné à la direction de déplacement, l'aspect permet de savoir si un pas monte ou descend, donc d'obtenir une pente **signée**. 

#### fonctions elevation_at et max_elevation

- elevation_at(dem, lat, lon) : convertit lat/lon en row/col avec le transform du DEM et retourne l'élévation à cette case.
- max_elevation(array) : le maximum de la grille, un simple array.max() qui aplatit le 2D tout seul.

## OverPass/ sous module OpenStreetMap

### queries_overpass.py

- ne contient que des fonctions qui retournent des **strings de requête OverpassQL**, une par type de feature (query_trail, query_road, query_hydro, query_vegetation, query_cliff...etc).
- chaque requête cible les 3 types d'objets OSM pertinents : node (point), way (ligne ou polygone), relation (regroupement).
- **query_all_features** concatène toutes les requêtes en une seule grosse requête. On fait **1 seul appel API** pour toute la BBox au lieu d'un appel par feature. Overpass est un service public gratuit, on limite la pression sur l'API et on évite une vingtaine d'allers-retours réseau.
- il y a aussi des helpers de requête par id (node/way/relation/area) et par BBox, surtout utilisées à des fins de debug.

### structures_op.py

#### osm_dtype

- un **structured array numpy** : un dtype composé de 19 champs booléens (trail, road, water, water_small, water_crossing, bridge, ford, vegetation, wetland, peak, cliff, ridge, valley, arete, scree, bare_rock, glacier, border, building).
- concrètement, chaque case du raster OSM est un amalgame de 19 flags. Une case peut donc être à la fois "vegetation" et "trail", ce qui exprime le comportement voulu : soit que les features se superposent dans la réalité.
- c'est ce dtype qui définit le contrat entre data/ et cost_model/ : les poids sont donnés par nom de champ.

#### _FEATURE_FILTERS

- dict qui associe chaque champ du osm_dtype à une **fonction de classification** (lambda) qui prend les tags OSM d'un feature et retourne un booléen.
- rôle : après le fetch groupé, on a un gros paquet de features mélangées. Ces filtres redistribuent chaque feature dans le bon champ.
- pattern typique : re.search sur un tag ("highway", "natural", "waterway"...) avec les mêmes mots-clés que la requête correspondante.
- **doit être gardé synchronisé avec queries_overpass.py**. Si on ajoute un mot-clé à une requête sans l'ajouter au filtre, le feature est téléchargé mais jamais rasterisé, et rien ne le signale.

#### _FEATURE_QUERIES

- ancienne table de mapping champ -> fonction de requête, du temps où on faisait un appel API par feature. **Inutilisée** depuis le passage à query_all_features(queries_overpass.py), gardée comme référence.

### client_overpass.py

- Ce fichier sert de lien avec l'API OpenStreetMap. Deux différences importantes avec le client d'élévation :
    - Overpass fonctionne en **POST**, pas en GET.
    - le format [out:geojson] n'est **pas** supporté par l'API. On demande du [out:json] et la conversion en GeoJSON est faite côté client avec la librairie osm2geojson.
- les serveurs Overpass exigent un User-Agent identifiable, sinon ils répondent 406 (not acceptable).

#### fonction get_data(query, bbox, verbosity, response_format) -> dict

- retourne une FeatureCollection GeoJSON.
- la verbosity (geom par défaut) détermine le niveau de détail géométrique retourné par le serveur.
- la logique de couverture cache est **exactement la même que get_dem** : couverture complète -> cache, lamelles négligeables -> cache, sous-bbox trop petite -> requête complète, couverture partielle -> fetch parallèle des zones manquantes puis fusion.
- deux différences : pas d'élargissement des zones manquantes (les features vectorielles ne souffrent pas du problème de couture des rasters), et la fusion se fait par déduplication d'ids plutôt que par rasterio.merge.

#### fonction _fetch_from_api

- assemble la requête finale : le préfixe [out:json][timeout:...][bbox:...] + la query + le suffixe "out {verbosity};".
- **fallback sur 3 endpoints** (overpass-api.de, kumi.systems, private.coffee) : on essaie chacun à tour de rôle et on garde la première réponse valide. Les instances publiques sont souvent saturées, c'est ce qui rend le module fiable en pratique.
- piège propre à Overpass : le serveur peut répondre **200 OK avec une erreur cachée** dans un champ "remark" (timed out, out of memory). _remark_error détecte ça par regex et traite la réponse comme un échec. Sans cette vérification, on rasterise du vide sans s'en rendre compte.
- si les 3 endpoints échouent, lève OverpassRemarkError avec le détail de chaque échec.

#### gestion des échecs partiels

- contrairement au DEM, get_data collecte les échecs zone par zone (as_completed + try/except) au lieu de planter au premier.
- les zones réussies sont quand même **sauvegardées au cache**, et l'exception est levée seulement après. Le travail n'est donc pas perdu : un retry repart avec plus de couverture que le tour précédent.

### raster_overpass.py

- c'est l'étape qui transforme des géométries vectorielles (lignes, polygones, points) en grille de flags exploitable par le routage.
- la résolution est de **1 arc-seconde (1/3600 de degré, ~30 m)**, choisie pour s'imbriquer 1:1 avec le DEM COP30.

#### fonction rasterize_bbox (la fonction principale)

- ne calcule **pas** sa propre grille : elle reprend directement le transform et la shape du bbox.dem_data.
- conséquence essentielle : la case (row, col) du raster OSM est **exactement** la case (row, col) du DEM. Pas de rééchantillonnage, pas de décalage, pas d'interpolation entre les deux sources.
- c'est aussi pourquoi fetch_terrain doit remplir dem_data **avant** de rasteriser.

#### fonction _fill_raster_grid

- si bbox.osm_features est vide, fait l'appel API (query_all_features) puis **trie** les features dans les 19 champs via _FEATURE_FILTERS, et garde le résultat dans la BBox.
- si osm_features est déjà rempli, réutilise directement le contenu de la BBox, sans appel réseau.
- la rasterisation se fait en deux phases :
    - **phase 1 (parallèle)** : chaque champ est rasterisé indépendamment dans son propre thread (_mark_feature), ce qui produit un masque booléen. Les threads ne touchent jamais la grille partagée.
    - **phase 2 (série)** : le thread principal récupère les résultats au fur et à mesure (as_completed) et applique chaque masque avec un |=. Chaque masque est libéré dès qu'il est appliqué, ce qui limite la mémoire.
- séparer les deux phases évite toute course de données sur la grille, tout en gardant le parallélisme là où il coûte cher (le calcul rasterio).
- une exception sur un champ est attrapée et imprimée : un feature qui échoue ne fait pas tomber toute la rasterisation.

#### fonction _mark_feature

- extrait les géométries GeoJSON du champ, appelle rasterio.features.rasterize et retourne un masque booléen.
- **all_touched=True** est requis : sans ça, les géométries Point (les nodes OSM comme les sommets) et les lignes très fines peuvent ne marquer aucun pixel.

### search_overpass_raster.py

- utilitaires de lecture sur un raster déjà construit. Ne font pas partie du pipeline d'acquisition, et nécessitent que bbox.osm_features soit rempli.
- row_to_lat / col_to_lon : conversion approximative case -> coordonnées à partir des coins de la BBox. À ne pas confondre avec les wrappers de structures_communes.py qui passent par le transform et sont la version exacte.
- get_cell_names(bbox, row, col, field) : retourne les noms (tag 'name' ou 'ref') des features d'un champ qui touchent une case précise. Fonctionne en rasterisant chaque feature sur une mini-grille 1x1 alignée sur la case.
- get_field_names_in_bbox(bbox, field) : tous les noms d'un champ dans la BBox, sans filtre spatial.
- get_all_names_in_cell(bbox, row, col) : get_cell_names pour les 19 champs d'un coup, retourne un dict champ -> noms.
- usage : donner des noms lisibles au tracé ("vous traversez la rivière X"), et debug.

## disk_cache.py ''le module central de cache''

- pourquoi : les deux API sont lents (de quelques secondes à quelques dizaines de secondes) et à quota limité. Sans cache, chaque itération de développement et chaque recalcul d'itinéraire recoûte un appel réseau complet. Également, une cache permet au programme de fonctionner hors-ligne pour des zones pré déterminées
- architecture : les **fichiers** vont sur le disque dans cache/ à la racine du projet (GeoTIFF pour le DEM, JSON pour l'OSM), et un **index SQLite** (cache/index.db) garde une rangée par fichier avec son type, ses 4 coordonnées, sa signature et sa date.
- la connexion SQLite est unique (singleton _get_conn) et toutes les écritures passent par un threading.Lock, parce que les fetchs sont parallèles.

### les clés

- _dem_key : nom lisible construit avec le demtype et les 4 coordonnées arrondies à 4 décimales -> dem_COP30_45.5_-72.4_45.51_-72.39.tif. L'arrondi fait qu'une BBox redemandée avec une différence infime retombe sur le même fichier.
- _osm_key : impossible de mettre la requête brute dans un nom de fichier (beaucoup trop longue), donc on hache query|bbox|verbosity|format en **md5**. Ça donne un nom court, déterministe et ***pratiquement*** unique.
- _osm_query_hash : hache la requête **sans la bbox**. C'est ce qui permet de retrouver des tuiles cachées avec une géométrie différente mais la même requête, donc de faire du matching spatial. Ce hash est stocké dans la colonne demtype de l'index, colonne réutilisée pour les deux types.

### la couverture partielle

- c'est le coeur du module. Plutôt que de répondre "cache hit / cache miss", on répond à la question **"quelle partie de cette BBox est déjà sur disque ?"**.

1. find_overlapping_dem_tiles / find_overlapping_osm_tiles : requête SQL de chevauchement de rectangles (west < est demandé ET east > ouest demandé, pareil en latitude). Au passage, toute entrée dont le fichier a disparu du disque est supprimée de l'index.
2. _group_contiguous_tiles : **union-find** sur les tuiles. Deux tuiles sont unies si leurs rectangles se touchent ou se chevauchent, ce qui donne des groupes connexes fusionnables chacun en un seul raster. La compression de chemin garde l'opération quasi linéaire.
3. get_partial_dem_coverage : pour chaque groupe, fusionne les GeoTIFF avec rasterio.merge et retourne (bytes, région couverte).
4. _compute_uncovered_bboxes : calcule la liste **minimale** de rectangles manquants.
    - construit une grille de coordonnées à partir de toutes les latitudes et longitudes qui apparaissent (bordures de la requête + bordures des zones couvertes).
    - pour chaque cellule de cette grille, teste si son centre est couvert.
    - fusionne horizontalement les cellules non couvertes consécutives d'une même bande de latitude. Ça évite de générer une nuée de micro-requêtes là où une seule bande suffit.

- query_dem_cache_coverage / query_osm_cache_coverage sont les points d'entrée utilisés par les clients. Ils retournent (données couvertes, bboxes manquantes). Si rien n'est en cache, la zone manquante est simplement la BBox complète.

### important : la fusion se fait en mémoire, pas sur le disque

- quand plusieurs tuiles cachées sont collées ou se chevauchent, elles **sont** fusionnées automatiquement, mais uniquement en RAM (MemoryFile), le temps de l'appel.
- le résultat fusionné n'est **jamais** repassé à save_dem ni réindexé. Les fichiers d'origine restent sur le disque, séparés, un par sous-bbox téléchargée.
- deux conséquences :
    - la fusion est refaite **au complet à chaque appel** sur la même zone. Plus on accumule de tuiles sur une région, plus chaque lecture ouvre et fusionne de fichiers. C'est du CPU/IO local, pas du réseau, mais ça ne diminue jamais tout seul.
    - il n'existe aucune compaction du cache. Seules les entrées dont le fichier a disparu du disque sont purgées de l'index.
- côté OSM c'est encore plus direct : pas de groupement du tout, query_osm_cache_coverage charge toutes les tuiles qui chevauchent et les passe à _merge_geojson.

### la fusion GeoJSON

- _merge_geojson : concatène des FeatureCollections en **dédupliquant par id de feature**.
- nécessaire parce que les tuiles OSM se chevauchent souvent et qu'un même chemin peut apparaître dans plusieurs réponses. Sans déduplication il serait rasterisé plusieurs fois (sans changer le résultat, mais en coûtant du temps) et les noms retournés par search_overpass_raster seraient dupliqués.








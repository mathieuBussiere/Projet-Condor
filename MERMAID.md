# Pipeline complet - Projet Condor

```mermaid
flowchart TD
    USER["Utilisateur\nclic depart + clic arrivee"]

    FT["fetch_terrain(bbox)\n(1/4) DEM  (2/4) OSM\n(3/4) cost_grid  (3.5/4) osm_mult"]

    subgraph DATA["Acquisition des donnees"]
        DEM["OpenTopography API\nGET COP30 GeoTIFF\n-> parse_dem_data\n-> DEMdata slope/aspect/array/transform"]
        OSM["Overpass API\nGET GeoJSON\n-> _FEATURE_FILTERS\n-> rasterize_bbox\n-> Raster OSM NxM"]
    end

    subgraph COST["Construction grille de cout - cost_grid.py"]
        COSTG["build_cost_grid\nTobler x multiplicateurs OSM\ncost_grid - visualisation seulement"]
        OSM_MULT["build_multiplicateurs_osm\nmultiplicateurs OSM seulement\nosm_mult - routage A*"]
    end

    subgraph ASTAR["Pathfinding - a_star.py"]
        CONV["lat/lon -> row/col\nlatlon_to_rowcol_affine"]
        SEARCH["a_star - cout par arrete\npente signee : dz / dist_m\nTobler directionnelle x osm_mult\nheuristique euclidienne en heures"]
        TRACE["reconstruction chemin\n-> traduire row/col -> lat/lon"]
    end

    subgraph API["API + UI"]
        EP["POST /api/v1/path/calculate\nPathService.calculate_path"]
        FRONT["React - Leaflet\npolyline Trajectory sur la carte\n+ StatPanel + Export"]
    end

    USER --> EP
    EP -->|BBox| FT
    FT --> DEM & OSM
    DEM --> COSTG & OSM_MULT
    OSM --> COSTG & OSM_MULT
    OSM_MULT --> CONV
    DEM -.->|dem_data.array| SEARCH
    CONV --> SEARCH --> TRACE --> EP --> FRONT
```

# Pipeline de donnees - Projet Condor

```mermaid
flowchart TD
    BBOX["BBox\nlat/lon min-max"]

    subgraph DEM["Branche DEM - Elevation"]
        OT["OpenTopography API\nGET COP30 GeoTIFF"]
        PARSE["parse_dem_data\nGeoTIFF -> array numpy"]
        SLOPE["_compute_slope\ngradient -> pente en rad"]
        ASPECT["_compute_aspect\ndirection de la pente"]
        DEMDATA["DEMdata(NamedTuple)\narray | slope | aspect | transform"]
    end

    subgraph OSM["Branche OSM - Features terrain"]
        OV["Overpass API\nGET GeoJSON"]
        FILTER["_FEATURE_FILTERS\nclassifie les features par type"]
        RASTER["_mark_feature x N threads\nGeoJSON -> masque booleen 30m"]
        OSMGRID["Raster OSM\narray structure NxM dtype osm_dtype\ntrail | road | water | bridge | ..."]
    end

    subgraph COSTGRID["Construction de la grille de cout"]
        TOBLER["_vitesse_cost_grid\nTobler -> cout de base par cellule\n30m / vitesse km/h"]
        MULTIELEV["_multiplicateur_elevation\nx si altitude > 2500m"]
        MULTIWEIGHTS["_compute_multiplicateurs\neau=inf  sentier x0.7  vegetation x2.0\nroute x0.5  marecage x3.5  falaise=inf"]
        FINAL["cost_grid - visualisation\narray NxM float\ncout Tobler x OSM en heures/cellule"]
        OSM_MULT["osm_mult - routage\narray NxM float\nbuild_multiplicateurs_osm\nmultiplicateurs OSM seulement"]
    end

    BBOX --> OT
    BBOX --> OV

    OT --> PARSE
    PARSE --> SLOPE
    PARSE --> ASPECT
    SLOPE --> DEMDATA
    ASPECT --> DEMDATA

    OV --> FILTER
    FILTER --> RASTER
    RASTER --> OSMGRID

    DEMDATA -->|slope| TOBLER
    TOBLER --> MULTIELEV
    DEMDATA -->|array elevation| MULTIELEV
    MULTIELEV --> MULTIWEIGHTS
    OSMGRID --> MULTIWEIGHTS
    MULTIWEIGHTS --> FINAL
    OSMGRID --> OSM_MULT
```

# Parsing des donnees d'elevation - parser_elevation.py

```mermaid
flowchart TD
    IN["GeoTIFF bytes\nopentopography"]
    RASTERIO["rasterio.open\nlire band 1 -> array 2D float\nlire transform Affine"]
    CLEAN["Nettoyage\nnodata -> NaN\n>9000m ou <-500m -> NaN"]

    subgraph STEP1["Etape 1 - Taille reelle d un degre"]
        LAT_CONST["m_per_deg_lat = 111 320 m/deg\nCONSTANTE - latitude presque invariable"]
        LAT_VEC["lats = f + e x [0,1,2...N]\nVECTEUR de latitudes, une par row"]
        LON_VEC["m_per_deg_lon = 111 320 x cos(lats)\nVECTEUR - longitude retrecit vers les poles"]
    end

    subgraph STEP2["Etape 2 - Taille d un pixel en metres"]
        PIX_H["pixel_h_m = |e| x m_per_deg_lat\nSCALAIRE - hauteur uniforme"]
        PIX_W["pixel_l_m = |a| x m_per_deg_lon\nMATRICE 2D - largeur varie selon la row"]
    end

    subgraph STEP3["Etape 3 - Gradient d elevation"]
        GRAD["np.gradient array\ndz_drow - variation N->S  m/pixel\ndz_dcol - variation O->E  m/pixel"]
    end

    subgraph STEP4["Etape 4 - Rise / Run"]
        DZ_DY["dz_dy = dz_drow / pixel_h_m\npente verticale  m/m"]
        DZ_DX["dz_dx = dz_dcol / pixel_l_m\npente horizontale  m/m"]
    end

    subgraph STEP5["Etape 5 - Magnitude + angle"]
        PYTH["magnitudes = sqrt(dz_dx^2 + dz_dy^2)\nPythagore 2D -> pente combinee  m/m"]
        ARCTAN["slope = arctan magnitudes\nangle en radians"]
        ASPECT["aspect = 90 - arctan2(-dz_dy, dz_dx) mod 360\ndirection de la pente  0deg=N"]
    end

    OUT["DEMdata\narray  slope  aspect  transform"]

    IN --> RASTERIO --> CLEAN
    CLEAN --> STEP1
    STEP1 --> STEP2
    CLEAN --> STEP3
    STEP2 --> STEP4
    STEP3 --> STEP4
    STEP4 --> STEP5
    STEP5 --> OUT
```

# Rasterisation Overpass - raster_overpass.py

```mermaid
flowchart TD
    BBOX["BBox\nlat/lon min-max"]

    subgraph FETCH["Etape 1 - Fetch GeoJSON  client_overpass.get_data()"]
        QUERY["Construction requete OverpassQL\n(out:json)(timeout:60)(bbox:...)\nout geom;"]
        EP1["overpass-api.de"]
        EP2["overpass.kumi.systems\nfailover si EP1 echoue"]
        EP3["overpass.openstreetmap.ru\nfailover si EP2 echoue"]
        CONV["osm2geojson.json2geojson()\nJSON Overpass -> FeatureCollection GeoJSON"]
        CACHE["bbox.osm_features <- cache du resultat"]
    end

    subgraph FILTER["Etape 2 - Classification  _FEATURE_FILTERS  (1 passe)"]
        FN["Pour chaque feature\nexamine les OSM tags (properties)"]
        T1["trail\npath|footway|track|bridleway"]
        T2["road\nmotorway|trunk|primary..."]
        T3["water\nwaterway river/stream OR natural=water"]
        T4["water_crossing\nbridge+highway OR ford OR stepping_stones"]
        T5["bridge / ford"]
        T6["vegetation\nwood|forest|farmland|meadow..."]
        T7["wetland\nmarsh|bog|swamp|fen..."]
        T8["peak / cliff / ridge / valley\narete / scree / bare_rock / border"]
        CLASSIFIED["bbox.osm_features\ndict[16 champs -> list GeoJSON features]"]
    end

    subgraph THREAD["Etape 3 - Rasterisation parallele  ThreadPoolExecutor max_workers=4"]
        GRID0["grid = np.zeros shape dtype=osm_dtype\n16 champs bool  NxM  tout False"]
        SUBMIT["executor.submit(_mark_feature, field, ...)\n16 futures  4 workers max en simultane"]
        SHAPES["shapes = [feat.geometry for feat in feat_list]"]
        RASTERIO["rasterio.features.rasterize\nshapes -> uint8 mask NxM\nall_touched=True  transform Affine"]
        LOCK["_grid_lock  threading.Lock\ngrid[field] |= mask.astype bool\nOR atomique thread-safe"]
    end

    OUT["Raster OSM  bbox.raster_osm\narray NxM  dtype=osm_dtype\n16 masques bool 30m/pixel\naligne sur le DEM"]

    BBOX --> QUERY
    QUERY --> EP1 --> EP2 --> EP3
    EP1 & EP2 & EP3 --> CONV --> CACHE

    CACHE --> FN
    FN --> T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8
    T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8 --> CLASSIFIED

    CLASSIFIED --> GRID0 --> SUBMIT --> SHAPES --> RASTERIO --> LOCK --> OUT
```

# Construction de la grille de cout - cost_grid.py + weights.py

```mermaid
flowchart TD
    DEM["DEMdata\nslope_rad NxM  |  elevation NxM"]
    OSM["Raster OSM\narray NxM osm_dtype"]

    subgraph STEP1["Etape 1 - Cout de base  _vitesse_cost_grid()"]
        TAN["s = tan(slope_rad)"]
        EXP["W = 6 x exp(-3.5 x |s + 0.05|)\nvitesse Tobler km/h - optimum a pente -5%"]
        BASE["base = 0.030 km / W\ncout en heures  array NxM float"]
    end

    subgraph STEP2["Etape 2 - Multiplicateur altitude  _multiplicateur_elevation()"]
        CHKELEV{"max(elevation) > 2500 m ?"}
        DELTA["delta = max(0, elevation - 2500)\nm au-dessus du seuil"]
        MULTIELEV["mult = 1.0 + 0.0002 x delta\nlineaire, toujours >= 1.0"]
        APPLYELEV["base = base x mult"]
    end

    subgraph STEP3["Etape 3 - Poids terrain  build_weights()  +  DEFAULT_WEIGHTS"]
        DEFAULT["DEFAULT_WEIGHTS\ntrail=0.7  road=0.5  water=inf  cliff=inf\nvegetation=2.0  wetland=3.5  scree=1.8  ..."]
        CONTRAINTES["contraintes user\nmax_couvert | eviter_routes | eviter_traverse_eau"]
        BUILDW["surcharge le poids cible\nexemple max_couvert -> vegetation = 0.6"]
        WFINAL["weights  dict[str, float]"]
    end

    subgraph STEP4["Etape 4 - Multiplicateurs OSM  _compute_multiplicateurs()"]
        ONES["multiplicateurs = np.ones NxM"]
        LOOP["Pour chaque (feature, weight) dans weights"]
        ACTIF["actif = osm[feature]  masque booleen"]
        SUPPRESS["_SUPPRESSED_BY - gestion de conflits\nwater masque la ou water_crossing present\nactif and= ~osm(override)"]
        APPLYM["multiplicateurs[actif] *= weight"]
    end

    CHKOSM{"osm et weights\nfournis ?"}
    FINAL["cost_grid - visualisation\nNxM float - cout Tobler x OSM en heures/cellule\ninf = cellule infranchissable"]
    OSM_MULT["osm_mult - routage\nNxM float - multiplicateurs OSM seulement\nbuild_multiplicateurs_osm"]

    DEM -->|slope| TAN --> EXP --> BASE
    BASE --> CHKELEV
    DEM -->|elevation| CHKELEV
    CHKELEV -->|oui| DELTA --> MULTIELEV --> APPLYELEV --> CHKOSM
    CHKELEV -->|non| CHKOSM

    DEFAULT --> BUILDW
    CONTRAINTES --> BUILDW
    BUILDW --> WFINAL

    CHKOSM -->|oui| ONES
    WFINAL --> LOOP
    ONES --> LOOP --> ACTIF
    OSM --> ACTIF
    ACTIF --> SUPPRESS --> APPLYM --> FINAL
    APPLYM --> OSM_MULT

    CHKOSM -->|non, base directement| FINAL
```

# Pipeline API - exemple  avec compare call 
```mermaid
sequenceDiagram
    autonumber
    actor Client as 💻 Interface React (UI)
    participant EP as 🔌 Couche Endpoint<br/>(v1/endpoints/path.py)
    participant SC as 📋 Couche Schéma<br/>(src/api/schemas/path.py)
    participant SV as 🧠 Couche Service<br/>(services/compare_path.py)
    participant AL as 🧮 Moteurs Mathématiques<br/>(similaritymeasures / A*)

    %% 1. Arrivée de la requête HTTP
    Client->>EP: POST /api/v1/path/compare<br/>(UploadFile, bbox string, points string)
    note over EP: Le routeur HTTP intercepte le payload entrant

    %% 2. Validation par les Schémas
    EP->>SC: Injecte les paramètres de formulaire dans les schémas
    activate SC
    note over SC: Validation du format via<br/>RouteComparisonRequest &<br/>RouteComparisonMetadata
    SC-->>EP: Objets de données structurellement valides
    deactivate SC

    %% 3. Traitement par la couche Service
    EP->>SV: RouteComparisonService.parse_trail_file(file_name, content)
    activate SV
    note over SV: Utilise gpxpy ou pandas pour convertir<br/>le fichier brut en List[tuple] (lat, lng)
    SV-->>EP: Points de trace de référence standardisés

    EP->>SV: RouteComparisonService.compare(path_algo, path_ref, ...)
    note over SV: Aligne la trace de référence via distance géodésique<br/>Égalise la densité des points avec NumPy
    
    %% 4. Calculs Mathématiques Lourds
    SV->>AL: Exécute les mesures de similarité
    note over AL: similaritymeasures.frechet_dist()<br/>similaritymeasures.dtw()<br/>ratio_effort()
    AL-->>SV: Résultats des métriques (Fréchet, DTW, Effort)
    
    note over SV: Normalise les scores & génère :<br/>"score" & "verdict"
    SV-->>EP: Retourne un dictionnaire de résultats
    deactivate SV

    %% 5. Validation de la réponse sortante
    EP->>SC: Associe le dictionnaire de sortie à la structure de réponse
    activate SC
    note over SC: Valide la structure finale via<br/>RouteComparisonResponse
    SC-->>EP: Objet de réponse typé (sécurisé)
    deactivate SC

    %% 6. Retour Final
    EP-->>Client: 200 OK (Payload JSON avec Scores & Métriques)
```

# Pipeline Pathfinding - Projet Condor
# Pipeline UI/UX - Projet Condor
# Pipeline UI Condor

```mermaid
graph TD
    A["main.tsx<br/>Point d'entrée"] --> B["App.tsx<br/>Composant racine"]
    
    B --> C["Gestion d'état"]
    B --> D["Hooks"]
    B --> E["Composants"]
    
    C --> C1["État de route<br/>départ, arrivée, itinéraires"]
    C --> C2["Trajectoire<br/>points, distance, durée"]
    C --> C3["Métriques de comparaison<br/>frechet, dtw, effortRatio"]
    C --> C4["État UI<br/>chargement, erreur, loading"]
    C --> C5["État météo<br/>météo, statut météo"]
    C --> C6["Contraintes<br/>éviter eau, pente max"]
    
    D --> D1["useRoute<br/>Gestion itinéraire"]
    D --> D2["useBbox<br/>Calcul zone"]
    D --> D3["useWeather<br/>Récupération météo"]
    
    D1 --> D1A["handleMapClick"]
    D1 --> D1B["routeReset"]
    
    E --> E1["Composant Barre latérale"]
    E --> E2["Composant Carte"]
    
    E1 --> E1A["Liste waypoints"]
    E1 --> E1B["Panneau contraintes"]
    E1 --> E1C["Panneau météo"]
    E1 --> E1D["Panneau statistiques"]
    E1 --> E1E["Panneau comparaison"]
    
    E2 --> E2A["Gestionnaire clics carte"]
    E2 --> E2B["Couche trajectoire"]
    E2 --> E2C["Couche marqueurs"]
    E2 --> E2D["Couche météo"]
    E2 --> E2E["Contrôles styles"]
    
    C1 --> F["Gestionnaires d'événements"]
    C2 --> F
    C3 --> F
    C4 --> F
    C5 --> F
    C6 --> F
    
    F --> F1["optimiserItinéraire"]
    F --> F2["comparerTrajectoire"]
    F --> F3["changeFile"]
    F --> F4["récupérerMétéo"]
    F --> F5["réinitialiser"]
    
    F1 --> API1["calculeTrajectoire<br/>pathService.ts"]
    F2 --> API2["compareRoute<br/>compareRouteService.ts"]
    F4 --> API3["API Météo"]
    
    API1 --> R1["Points d'itinéraire"]
    API1 --> R2["Distance & Durée"]
    
    API2 --> R3["Score comparaison"]
    API2 --> R4["Métriques<br/>Frechet, DTW, Effort"]
    
    API3 --> R5["Données météo"]
    
    R1 --> U["Mise à jour UI"]
    R2 --> U
    R3 --> U
    R4 --> U
    R5 --> U
    
    U --> E1
    U --> E2
    
    style A fill:#4f46e5,color:#fff
    style B fill:#7c3aed,color:#fff
    style E1 fill:#ec4899,color:#fff
    style E2 fill:#06b6d4,color:#fff
    style F1 fill:#10b981,color:#fff
    style F2 fill:#10b981,color:#fff
    style F4 fill:#10b981,color:#fff
    style API1 fill:#f59e0b,color:#fff
    style API2 fill:#f59e0b,color:#fff
    style API3 fill:#f59e0b,color:#fff
```

## Résumé du pipeline UI

**Point d'entrée** → `main.tsx` initialise React et affiche `App.tsx`

**Couche état** → `App.tsx` gère :
- État de route (points de départ/arrivée)
- Données de trajectoire (points, distance, durée)
- Métriques de comparaison (Frechet, DTW, ratio d'effort)
- Météo et contraintes
- États de chargement/erreur UI

**Couche hooks** → Logique réutilisable :
- `useRoute` - gère la sélection d'itinéraire
- `useBbox` - calcule la zone délimitée
- `useWeather` - récupère les données météo

**Couche composants** → Deux conteneurs principaux :
- **Barre latérale** - contrôles UI, statistiques, comparaisons
- **Carte** - carte interactive avec couches

**Gestionnaires d'événements** → Déclenchés par actions utilisateur :
- Optimisation itinéraire → appel API → mise à jour points
- Comparaison trajectoire → appel API → mise à jour métriques
- Récupération météo → appel API → mise à jour couche
- Réinitialisation → efface tous les états

**Couche API** → Services backend :
- `pathService.ts` - calcul d'itinéraire
- `compareRouteService.ts` - comparaison de trajectoire
- API Météo - données météorologiques

**Affichage** → L'état mis à jour revient aux composants pour l'actualisation UI


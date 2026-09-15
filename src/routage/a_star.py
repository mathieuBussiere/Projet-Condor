"""
Implémentation de l'algorithme de chemin A* et A* bidirectionnel.
"""
import math
import heapq
import time
from dataclasses import dataclass

from similaritymeasures import similaritymeasures

from data.structures_communes import BBox, latlon_to_rowcol_affine, rowcol_to_latlon
from data.data_fetcher import fetch_terrain
import numpy as np

from routage.simplify import simplifier_rdp

# Physique du cout (Tobler + altitude) : source de verite unique, partagee
# avec cost_model.cost_grid pour que la carte de cout affichee corresponde
# a ce que le routage calcule reellement. Voir cost_model/physique.py.
from cost_model.physique import (
    CELL_SIZE_M,
    CELL_DIAG_M,
    VITESSE_MAX_KMH,
    difficulte_altitude,
    vitesse_tobler_radians,
    vitesse_tobler_ratio,
)

_CELL_SIZE_M = CELL_SIZE_M
_MAX_SPEED_KMH = VITESSE_MAX_KMH
_H_SCALE = _CELL_SIZE_M / 1000.0 / _MAX_SPEED_KMH

# Alias retro-compatibles : ces helpers vivent maintenant dans physique.py
_tobler_depuis_radians = vitesse_tobler_radians
_tobler_depuis_ratio = vitesse_tobler_ratio

# Fonction qui trouve les voisins d'une cellule (node).
def voisins(node):
    """
    args :
        node: La cellule dont nous voulons trouver ces voisins.

    return :
        Les voisins prêt de la cellule actuelle.
    """
    x, y = node
    return [
        (x+1,y),(x-1,y),(x,y+1),(x,y-1),
        (x+1,y+1),(x-1,y-1),(x+1,y-1),(x-1,y+1)
    ]

# Heuristique de l'algorithme A*. Calcule une estimation du coût restant pour d'un point (a, b)
# au point final. On utilise le calcul euclidien où tous les mouvements sont permit (vol d'oiseau).
def heuristique(a, b):
    """
    args :
        a: Coordonnée X d'un point.
        b: Coordonnée Y d'un point.

    return :
        Une estimation du coût d'un point (a, b) jusqu'à l'objectif.
    """

    """
      Chebyshev distance: max(abs(dr), abs(dc))
      ceci est mieux pour le pathfinding dans une grille avec 8 direction de mouvement, car il prend en compte les mouvements diagonaux qui sont plus rapides que les mouvements orthogonaux.
    """

    dr = abs(a[0] - b[0])
    dc = abs(a[1] - b[1])
    diagonal_moves = min(dr, dc)
    straight_moves = abs(dr - dc)
    raw = diagonal_moves + straight_moves
    return raw * 0.8


def calculer_cout_tobler(
    chemin_latlon: list[tuple[float, float]],
    dem_array: np.ndarray,
    transform,
) -> float:
    """
    Calcule le coût Tobler réel (en heures) d'un chemin en lat/lon.

    Paramètres :
        chemin_latlon — liste de (lat, lon) ex: sortie de traduire_colrow_vers_latlon()
        dem_array     — grille d'élévation (metres)
        transform     — transform affine rasterio de la bbox

    Retourne :
        coût total en heures selon la hiking function de Tobler
    """
    if len(chemin_latlon) < 2:
        return 0.0

    total_h = 0.0

    for i in range(1, len(chemin_latlon)):
        lat1, lon1 = chemin_latlon[i - 1]
        lat2, lon2 = chemin_latlon[i]

        # coord  sur grille
        r1, c1 = latlon_to_rowcol_affine(transform, lat1, lon1)
        r2, c2 = latlon_to_rowcol_affine(transform, lat2, lon2)

        # Borner aux dimensions de la grille
        r1 = min(max(r1, 0), dem_array.shape[0] - 1)
        c1 = min(max(c1, 0), dem_array.shape[1] - 1)
        r2 = min(max(r2, 0), dem_array.shape[0] - 1)
        c2 = min(max(c2, 0), dem_array.shape[1] - 1)

        # Distance horizontale Haversine pour la
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = (math.sin(dphi / 2) ** 2
             + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
        dist_m = 6_371_000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        if dist_m < 0.1:
            continue

        # Pente ratio dz/dist
        dz = float(dem_array[r2, c2]) - float(dem_array[r1, c1])
        slope = dz / dist_m

        # Coût Tobler en heures
        speed = _tobler_depuis_ratio(slope)
        total_h += (dist_m / 1000.0) / speed

    return total_h

    # en termes de tuiles
    # return diagonal_moves + straight_moves

# Calcule le coût de déplacement physique entre `current` et `v`.
def cout_arrete(current, v, osm_mult: np.ndarray, dem_array: np.ndarray, inverse: bool = False):
    """
    args :
        current: Cellule de départ du déplacement (row, col).
        v: Cellule d'arrivée du déplacement (row, col).
        osm_mult: Grille des multiplicateurs de difficulté.
        dem_array: Grille des élévations.
        inverse: Si True, calcule le coût du déplacement physique inverse
            (v -> current) plutôt que (current -> v). C'est ce qu'il faut
            utiliser dans la recherche backward de l'A* bidirectionnel,
            car le coût n'est pas symétrique (la pente signée distingue
            monter et descendre).

    return :
        Le coût de l'arête en heures, ou None si le déplacement est impossible.
    """
    cr, cc = current
    r, c = v

    # step 1. check pour impossibilite
    # le mult s'applique a la destination du deplacement PHYSIQUE reel :
    # current -> v en mode normal, donc destination = v (r,c)
    # v -> current en mode inverse (backward), donc destination = current (cr,cc)
    if not inverse:
        mult = osm_mult[r][c]
    else:
        mult = osm_mult[cr][cc]
    if math.isinf(mult):
        return None

    # step 2. calcule la slope signee, déplacement physique réel :
    # current -> v (cas normal) ou
    # v -> current si inverse = True (cas backward)
    if not inverse:
        dz = dem_array[r, c] - dem_array[cr, cc]
    else:
        dz = dem_array[cr, cc] - dem_array[r, c]

    is_diagonal = (r != cr) and (c != cc)
    dist_m = (CELL_DIAG_M if is_diagonal else CELL_SIZE_M)

    slope = dz / dist_m
    if math.isnan(slope):
        return None

    # step 3. vitesse de tobler (pente en ratio dz/dist)
    speed = vitesse_tobler_ratio(slope)

    # step 4. penalite d'altitude (manque d'O2, cf. difficulte_altitude)
    # s'applique a la destination du deplacement PHYSIQUE reel, comme mult
    if not inverse:
        alt_dest = float(dem_array[r, c])
    else:
        alt_dest = float(dem_array[cr, cc])
    alt_mult = difficulte_altitude(alt_dest)

    # step 5. cout de l'arrete en heures
    time_h = (dist_m / 1000) / speed
    edge_cost = time_h * mult * alt_mult  # <- applique les penalites

    return edge_cost


# Fonction A*. Elle trouve le meilleur chemin.
def a_star(start, goal, osm_mult: np.ndarray, dem_array: np.ndarray):
    """
    args :
        start: Le début du chemin.
        goal: L'objectif du chemin.
        osm_mult: Une grille des multiplicateurs de difficulte de la grille
        dem_array: la grille des elevations de chaque

    return :
        Le meilleur chemin entre un point de départ et un point final.
        calcul la difficulte d'un move dynamiquement
    """
    shape = dem_array.shape
    open_list = []
    heapq.heappush(open_list, (0, start))

    g = {start: 0}
    parent = {start: None}
    closed_set = set()

    while open_list:
        _, current = heapq.heappop(open_list)
        if current in closed_set:
            continue

        closed_set.add(current)

        if current == goal:
            break

        # Pour chaque voisin
        for v in voisins(current):

            r, c = v

            if r < 0 or r >= shape[0] or c < 0 or c >= shape[1]:
                continue

            if v in closed_set:
                continue

            # impossibilite, pente signee, Tobler et penalite d'altitude :
            # tout est dans cout_arrete, seule source de verite, partagee
            # avec la recherche bidirectionnelle via relaxer_voisins.
            edge_cost = cout_arrete(current, v, osm_mult, dem_array)
            if edge_cost is None:
                continue

            tentative = g[current] + edge_cost

            if v not in g or tentative < g[v]:
                g[v] = tentative
                # heuristique convertis en heures (unite de g())
                f = tentative + heuristique(v, goal) * _H_SCALE
                heapq.heappush(open_list, (f, v))
                parent[v] = current
    # gerer le cas goal innateignable (MARC)
    if goal not in parent:
        return []

    # reconstruction
    path = []
    c = goal

    while c:
        path.append(c)
        c = parent.get(c)

    return path[::-1]

# Cette fonction est équivalente à la boucle for v in Voisins(current)
def relaxer_voisins(current, shape, osm_mult, dem_array, g, parent, open_list, g_heap, closed_set,
                      objectif_heuristique, inverse, g_autre_sens, meilleur_cout):
    """
    Relâche les voisins de `current` pour une direction de recherche donnée
    (forward si inverse = False, backward si inverse = True).

    Factorise la boucle de relaxation des voisins, identique dans son
    fonctionnement à celle de `a_star`, mais paramétrée par direction.

    À chaque voisin amélioré, vérifie aussi s'il est déjà connu de l'autre
    sens (g_autre_sens) pour mettre à jour le meilleur chemin trouvé jusqu'à
    présent : c'est ce qui permet de capter une "rencontre" dès qu'elle
    existe, et pas seulement quand un nœud est fermé des deux côtés.

    En plus du tas principal `open_list` (trié par f, pilote l'exploration),
    on alimente `g_heap`, un tas auxiliaire trié par g, pour permettre à
    l'appelant de lire le g minimal en O(log n) (condition d'arrêt) au lieu
    de scanner tout le tas en O(n) à chaque itération.

    return :
        Le meilleur_cout mis à jour (et le nœud de rencontre associé, ou None).
    """
    meilleur_noeud = None

    for v in voisins(current):
        r, c = v

        if r < 0 or r >= shape[0] or c < 0 or c >= shape[1]:
            continue

        if v in closed_set:
            continue

        edge_cost = cout_arrete(current, v, osm_mult, dem_array, inverse=inverse)
        if edge_cost is None:
            continue

        tentative = g[current] + edge_cost

        if v not in g or tentative < g[v]:
            g[v] = tentative
            f = tentative + heuristique(v, objectif_heuristique) * _H_SCALE
            heapq.heappush(open_list, (f, v))
            heapq.heappush(g_heap, (tentative, v))
            parent[v] = current

        # le voisin est connu de l'autre sens -> chemin candidat via v
        if v in g_autre_sens and g[v] + g_autre_sens[v] < meilleur_cout:
            meilleur_cout = g[v] + g_autre_sens[v]
            meilleur_noeud = v

    return meilleur_cout, meilleur_noeud


def simplifier_chemin(path):
    """
    Filtre le chemin en retirant tous les points alignés inutiles,
    ainsi que le point de départ et le point d'arrivée.
    """
    if len(path) <= 2:
        return []

    chemin_simplifie = []

    for i in range(1, len(path) - 1):
        prev = path[i - 1]
        curr = path[i]
        nxt = path[i + 1]

        # Calcul des vecteurs de direction
        dr1 = curr[0] - prev[0]
        dc1 = curr[1] - prev[1]

        dr2 = nxt[0] - curr[0]
        dc2 = nxt[1] - curr[1]

        # Si les directions diffèrent (produit en croix non nul), c'est un virage
        if dr1 * dc2 != dc1 * dr2:
            chemin_simplifie.append(curr)

    return chemin_simplifie

def calculer_distance_frechet(
    chemin_algo_latlon: list,
    chemin_humain_latlon: list,
) -> float:
    """
    Calcule la distance de Fréchet discrète en mètres entre deux trajectoires.

    Gère le problème de densité : si A* a 50 points et le GPX en a 2000,
    le chemin sparse est interpolé à la même densité avant le calcul.
    """
    if not chemin_algo_latlon or not chemin_humain_latlon:
        return float('inf')

    p = np.array(chemin_algo_latlon,    dtype=np.float64)  # (N, 2)  ← A*
    q = np.array(chemin_humain_latlon,  dtype=np.float64)  # (M, 2)  ← référence GPX

    # Resample le chemin le plus court à la densité du plus long
    target_n = max(len(p), len(q))
    p = _interpolate_path(p, target_n)
    q = _interpolate_path(q, target_n)

    # Cap pour éviter des calculs trop longs sur de très longues traces
    MAX_PTS = 500
    if target_n > MAX_PTS:
        idx = np.linspace(0, target_n - 1, MAX_PTS, dtype=int)
        p = p[idx]
        q = q[idx]

    frechet_deg = float(similaritymeasures.frechet_dist(p, q))

    # Degrés → mètres
    avg_lat = (p[:, 0].mean() + q[:, 0].mean()) / 2.0
    m_per_deg_lat = 111_132.0
    m_per_deg_lon = 111_132.0 * np.cos(np.radians(avg_lat))
    frechet_meters = frechet_deg * (m_per_deg_lat + m_per_deg_lon) / 2.0

    return frechet_meters


def _interpolate_path(path: np.ndarray, target_n: int) -> np.ndarray:
    """Resample a path array (N, 2) to target_n points via linear interpolation."""
    if len(path) >= target_n:
        return path
    t_old = np.linspace(0, 1, len(path))
    t_new = np.linspace(0, 1, target_n)
    return np.column_stack([
        np.interp(t_new, t_old, path[:, 0]),
        np.interp(t_new, t_old, path[:, 1]),
    ])

def g_min(g_heap, g, closed_set):
    """
    Retourne le g minimal parmi les nœuds encore "ouverts" (pas fermés),
    en O(log n) amorti, via suppression paresseuse des entrées obsolètes
    de g_heap (nœuds fermés, ou entrées dépassées par une meilleure valeur
    de g trouvée depuis).
    """
    while g_heap:
        cout, n = g_heap[0]
        if n in closed_set or g.get(n) != cout:
            heapq.heappop(g_heap)
            continue
        return cout
    return math.inf

# Fonction qui traduit les coordonées des points de colrow vers latlon
def traduire_colrow_vers_latlon(chemin, transform):
    chemin_traduit = []

    for point in chemin:
        chemin_traduit.append(rowcol_to_latlon(transform, point[0], point[1]))

    return chemin_traduit

def snap_to_traversable(
    row_col: tuple,
    osm_mult: np.ndarray,
    max_radius: int = 20
) -> tuple:
    """
    si la position passe sur une cellule infranchissable, on cherche la cellule la plus proche qui est franchissable
    utile quand on mets le pt départ/arrivée sur une zone infranchissable
    """
    r, c = row_col
    if not np.isinf(osm_mult[r, c]):
        return row_col

    for radius in range(1, max_radius + 1):
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                if abs(dr) != radius and abs(dc) != radius:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < osm_mult.shape[0] and 0 <= nc < osm_mult.shape[1]:
                    if not np.isinf(osm_mult[nr, nc]):
                        print(f"  [snap] {row_col} → ({nr},{nc}) (radius {radius})")
                        return (nr, nc)
    return row_col  # fallback

def _decimer_pas_m(chemin_latlon, pas_m=CELL_SIZE_M):
    """
    Décime un chemin lat/lon pour que les points consécutifs soient espacés
    d'au moins pas_m mètres (extrémités toujours conservées).

    Nécessaire avant calculer_cout_tobler : un GPX dense (points aux ~5 m)
    lu contre un DEM à 30 m attribue tout le dénivelé d'une cellule à un
    micro-segment au franchissement de chaque frontière de cellule, ce qui
    crée des pentes fictives de 50-100 % et gonfle le coût de ~2x.
    """
    if len(chemin_latlon) < 3:
        return list(chemin_latlon)
    out = [chemin_latlon[0]]
    for p in chemin_latlon[1:-1]:
        lat1, lon1 = out[-1]
        lat2, lon2 = p
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = (math.sin(dphi / 2) ** 2
             + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
        if 6_371_000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)) >= pas_m:
            out.append(p)
    out.append(chemin_latlon[-1])
    return out


def ratio_effort(chemin_algo, chemin_reference, dem_array, transform):
    """
    < 1.0 → A* trouve un chemin moins difficile que la référence
    = 1.0 → effort identique
    > 1.0 → A* est plus dur que le sentier humain
    """
    cout_algo = calculer_cout_tobler(_decimer_pas_m(chemin_algo), dem_array, transform)
    cout_ref  = calculer_cout_tobler(_decimer_pas_m(chemin_reference), dem_array, transform)
    if cout_ref == 0.0:
        # référence dégénérée (ex. boucle tronquée à un point) : pas de ratio calculable
        return float("inf")
    return cout_algo / cout_ref


def comparer_chemins(chemin_algo, chemin_ref):
    p = np.array(chemin_algo)
    q = np.array(chemin_ref)

    # DTW — moins sensible aux outliers que Fréchet
    dtw, _ = similaritymeasures.dtw(p, q)

    # Fréchet — pire cas de déviation
    frechet = similaritymeasures.frechet_dist(p, q)

    # Area between curves — déviation moyenne intégrée
    area = similaritymeasures.area_between_two_curves(p, q)

    return {
        "frechet_m":   frechet  * 111_132,
        "dtw_m":       dtw      * 111_132,
        "area_m2":     area     * 111_132**2,
    }

def score_qualite_chemin(chemin_algo, chemin_ref, dem_array, transform) -> dict:
    metriques = comparer_chemins(chemin_algo, chemin_ref)
    ratio     = ratio_effort(chemin_algo, chemin_ref, dem_array, transform)

    # Score 0-100 : plus haut = meilleur
    # Fréchet < 500m = bon, > 2000m = mauvais
    score_geo     = max(0, 100 - (metriques["frechet_m"] / 20))
    # Effort ratio < 1 = bonus, > 1.2 = pénalité
    score_effort  = max(0, 100 - max(0, ratio - 1.0) * 200)

    score_final = score_geo * 0.6 + score_effort * 0.4

    return {
        **metriques,
        "ratio_effort":  round(ratio, 3),
        "score_geo":     round(score_geo, 1),
        "score_effort":  round(score_effort, 1),
        "score_final":   round(score_final, 1),
    }

# Méthode principale de l'algorithme de recherche de chemin.
# Elle trouve le chemin en coordonnées row/col et les traduit en lat/lon.
def recherche_meilleur_chemin(osm_mult, dem_array, transform, depart_row_col, arrivee_row_col, bidirectionnel=False):
    """
    args :
        osm_mult: La grille des multiplicateurs de difficulte.
        dem_array: La grille des elevations.
        transform: Le transform affine pour la conversion row/col <-> lat/lon.
        depart_row_col: coordonnée du point de départ en format row/col.
        arrivee_row_col: coordonnée du point de arrivée en format row/col.
        bidirectionnel: non implémenté. Les composants existent (cout_arrete
            avec inverse=True, relaxer_voisins, g_min) mais la fonction pilote
            n'est pas écrite. Passer True lève NotImplementedError plutôt que
            de retourner silencieusement un résultat qui n'a pas été demandé.

    return :
        Le meilleur chemin entre un point de départ et un point final en format lat/lon.
    """
    if bidirectionnel:
        raise NotImplementedError(
            "A* bidirectionnel non implémenté : les composants sont en place "
            "(cout_arrete inverse, relaxer_voisins, g_min), pas la fonction pilote."
        )

    epsilon_m = 5.0
    # On trouve le chemin avec A*
    chemin = a_star(depart_row_col, arrivee_row_col, osm_mult, dem_array)
    print(f"chemin trouvé : {chemin}")
    chemin = simplifier_rdp(chemin, epsilon_m=epsilon_m)
    # On traduit le chemin en coordonnées lat/lon pour l'affichage sur le front-end
    chemin = traduire_colrow_vers_latlon(chemin, transform)
    return chemin
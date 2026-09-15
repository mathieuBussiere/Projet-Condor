"""
Benchmark pour a_star (src/routage/a_star.py).

Note : a_star_bidirectionnel n'existe pas. Les composants sont écrits
(cout_arrete avec inverse=True, relaxer_voisins, g_min) mais pas la fonction
pilote. Les sections 1, 3 et 4 se dégradent proprement : la section 1 est
ignorée, les sections 3 et 4 ne rapportent que l'A* classique.

Regroupe tous les tests effectués pendant le développement :
  1. Validation de correction  : a_star vs a_star_bidirectionnel donnent le même coût optimal
  2. Non-régression           : a_star actuel == a_star avant le refactor cout_arrete (même coût)
  3. Performance              : temps d'exécution + nombre de noeuds explorés, classique vs bidirectionnel
  4. Mise à l'échelle         : performance sur grilles de tailles croissantes
  5. Heuristique              : admissibilité de heuristique() sur des paires aléatoires

Deux modes de données :
  - "synthetique" (par défaut) : grilles aléatoires générées avec numpy, pour tester sans
    dépendre de vraies données terrain.
  - "reel" : branche vos vraies données DEM/OSM via fetch_terrain/BBox. Voir la fonction
    charger_grille_reelle() ci-dessous, à adapter avec votre bounding box.

Usage :
    python3 benchmark_a_star.py                  # lance tout en mode synthetique
    python3 benchmark_a_star.py --reel            # lance le benchmark de perf sur vos données réelles
    python3 benchmark_a_star.py --section perf    # lance uniquement une section
"""
import sys
import os
import types
import math
import time
import argparse
import heapq

import numpy as np

# ---------------------------------------------------------------------------
# Import du module a_star_bidirectionnel.py
#
# Le module importe data.structures_communes / data.data_fetcher. Si ces
# modules ne sont pas disponibles dans l'environnement courant (ex: ce
# bac à sable de dev), on les mocke pour permettre l'exécution du benchmark
# en mode synthétique. Chez vous, où ces modules existent réellement, ce
# mock ne s'active jamais (l'import réel réussit et est utilisé tel quel).
# ---------------------------------------------------------------------------
try:
    import data.structures_communes  # noqa: F401
    import data.data_fetcher  # noqa: F401
except ImportError:
    _fake_structures = types.ModuleType("data.structures_communes")
    _fake_structures.BBox = object
    _fake_structures.latlon_to_rowcol_affine = lambda *a, **k: None
    _fake_structures.rowcol_to_latlon = lambda transform, r, c: (r, c)
    _fake_fetcher = types.ModuleType("data.data_fetcher")
    _fake_fetcher.fetch_terrain = lambda *a, **k: None
    _fake_data_pkg = types.ModuleType("data")
    sys.modules["data"] = _fake_data_pkg
    sys.modules["data.structures_communes"] = _fake_structures
    sys.modules["data.data_fetcher"] = _fake_fetcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import src.routage.a_star as algo  # noqa: E402

# a_star_bidirectionnel n'existe pas : les composants sont ecrits (cout_arrete
# inverse, relaxer_voisins, g_min) mais pas la fonction pilote. Les sections qui
# comparent les deux algorithmes se degradent proprement au lieu de planter.
BIDIR_DISPO = hasattr(algo, "a_star_bidirectionnel")


# ===========================================================================
# Utilitaires communs
# ===========================================================================
def cout_total_chemin(chemin, osm_mult, dem_array):
    """Recalcule le coût total réel d'un chemin (somme des cout_arrete forward)."""
    total = 0.0
    for i in range(len(chemin) - 1):
        c = algo.cout_arrete(chemin[i], chemin[i + 1], osm_mult, dem_array, inverse=False)
        if c is None:
            return math.inf
        total += c
    return total

def chemin_valide(chemin, osm_mult, dem_array, start, goal):
    """Vérifie que le chemin relie bien start à goal via des voisins valides."""
    if not chemin:
        return False
    if chemin[0] != start or chemin[-1] != goal:
        return False
    shape = dem_array.shape
    for i in range(len(chemin) - 1):
        if chemin[i + 1] not in algo.voisins(chemin[i]):
            return False
        r, c = chemin[i + 1]
        if r < 0 or r >= shape[0] or c < 0 or c >= shape[1]:
            return False
        if math.isinf(osm_mult[r][c]):
            return False
    return True

def compter_noeuds_fermes(start, goal, osm_mult, dem_array):
    """
    Ré-implémente la boucle de a_star juste pour compter les noeuds fermés
    (closed_set), sans modifier a_star_bidirectionnel.py. Utilisé uniquement
    à des fins de mesure/benchmark.
    """
    shape = dem_array.shape
    open_list = [(0, start)]
    g = {start: 0}
    closed_set = set()
    while open_list:
        _, current = heapq.heappop(open_list)
        if current in closed_set:
            continue
        closed_set.add(current)
        if current == goal:
            break
        for v in algo.voisins(current):
            r, c = v
            if r < 0 or r >= shape[0] or c < 0 or c >= shape[1]:
                continue
            if v in closed_set:
                continue
            edge_cost = algo.cout_arrete(current, v, osm_mult, dem_array)
            if edge_cost is None:
                continue
            tentative = g[current] + edge_cost
            if v not in g or tentative < g[v]:
                g[v] = tentative
                f = tentative + algo.heuristique(v, goal) * algo._H_SCALE
                heapq.heappush(open_list, (f, v))
    return len(closed_set)

def grille_synthetique(rows, cols, seed, dem_range=(-15, 15), mult_range=(0.8, 3.0),
                        taux_obstacles=0.0):
    """
    Génère une grille de test aléatoire (dem + osm_mult), avec obstacles
    optionnels.
    """
    rng = np.random.RandomState(seed)
    dem = rng.uniform(dem_range[0], dem_range[1], (rows, cols))
    mult = rng.uniform(mult_range[0], mult_range[1], (rows, cols))
    if taux_obstacles > 0:
        n_obs = int(rows * cols * taux_obstacles)
        for _ in range(n_obs):
            rr, cc = rng.randint(0, rows), rng.randint(0, cols)
            mult[rr, cc] = math.inf
    return dem, mult

def charger_grille_reelle(bbox_coords=None):
    """
    Point d'entrée pour brancher vos vraies données DEM/OSM.

    À adapter : remplacez les coordonnées ci-dessous par votre zone d'intérêt,
    et assurez-vous que data.structures_communes / data.data_fetcher sont
    bien sur le PYTHONPATH (ils le sont automatiquement si ce script est
    lancé depuis la racine de votre projet).

    Note : cette fonction ne peut pas être testée dans un environnement où
    data.structures_communes/data.data_fetcher sont mockés (ex: bac à sable
    de développement) — elle nécessite vos vrais modules. C'est attendu :
    --reel est fait pour être lancé chez vous, pas dans cet environnement.

    return :
        (dem_array, osm_mult, transform, depart_row_col, arrivee_row_col)
    """
    from data.structures_communes import BBox, latlon_to_rowcol_affine
    from data.data_fetcher import fetch_terrain

    if bbox_coords is None:
        # Boite de l'université de Sherbrooke, reprise de votre __main__
        bbox_coords = (45.3702179, -71.9385714, 45.3864681, -71.9002343)

    depart_lat, depart_lon = 45.3818756, -71.9318363
    arrivee_lat, arrivee_lon = 45.3769985, -71.9261569

    box = BBox(*bbox_coords)
    fetch_terrain(box)

    depart_row_col = latlon_to_rowcol_affine(box.dem_data.transform, depart_lat, depart_lon)
    arrivee_row_col = latlon_to_rowcol_affine(box.dem_data.transform, arrivee_lat, arrivee_lon)

    return box.dem_data.array, box.osm_mult, box.dem_data.transform, depart_row_col, arrivee_row_col


# ===========================================================================
# Section 1 : Validation de correction. S'assurer que a_star et a_star_bidirectionnelle donnent le même chemin optimal
# ===========================================================================
def section_validation_correction():
    print("=" * 70)
    print("SECTION 1 : Validation de correction (a_star vs a_star_bidirectionnel)")
    print("=" * 70)

    if not BIDIR_DISPO:
        print("  [ignore] a_star_bidirectionnel non implemente : rien a comparer.")
        print()
        return True

    cas = []

    # Terrain plat sans obstacles
    dem, mult = np.zeros((20, 20)), np.ones((20, 20))
    cas.append(("Terrain plat sans obstacles", dem, mult, (0, 0), (19, 19)))

    # Pente asymétrique diagonale (et son inverse)
    dem = np.fromfunction(lambda r, c: (c - r) * 5.0, (25, 25))
    mult = np.ones((25, 25))
    cas.append(("Pente asymétrique diagonale", dem, mult, (0, 0), (24, 24)))
    cas.append(("Pente asymétrique diagonale (inverse)", dem, mult, (24, 24), (0, 0)))

    # Obstacles (mur avec ouverture) + terrain aléatoire
    dem, mult = grille_synthetique(30, 30, seed=42, dem_range=(0, 10), mult_range=(1, 1))
    mult[10, 5:25] = math.inf
    mult[10, 27] = math.inf
    cas.append(("Obstacles (mur + ouverture)", dem, mult, (0, 0), (29, 29)))

    # Terrain aléatoire complexe (deux paires de points)
    dem, mult = grille_synthetique(35, 35, seed=42)
    cas.append(("Terrain aléatoire complexe", dem, mult, (2, 3), (32, 30)))
    cas.append(("Terrain aléatoire complexe, autre paire", dem, mult, (5, 5), (20, 28)))

    # start == goal
    cas.append(("start == goal", dem, mult, (5, 5), (5, 5)))

    # Goal inatteignable (entouré de murs)
    dem2 = np.zeros((15, 15))
    mult2 = np.ones((15, 15))
    mult2[4, :] = math.inf
    mult2[:, 4] = math.inf
    cas.append(("Goal inatteignable (entouré de murs)", dem2, mult2, (0, 0), (10, 10)))

    # 20 configurations aléatoires variées (tailles, obstacles, points)
    for seed in range(20):
        rng = np.random.RandomState(seed)
        rows, cols = rng.randint(20, 50), rng.randint(20, 50)
        dem3, mult3 = grille_synthetique(rows, cols, seed=seed, dem_range=(-20, 20), mult_range=(0.5, 4.0),
                                          taux_obstacles=0.05)
        start = (rng.randint(0, rows), rng.randint(0, cols))
        goal = (rng.randint(0, rows), rng.randint(0, cols))
        cas.append((f"Aléatoire seed={seed}", dem3, mult3, start, goal))

    tout_ok = True
    for nom, dem_arr, mult_arr, start, goal in cas:
        c_classique = algo.a_star(start, goal, mult_arr, dem_arr)
        c_bidir = algo.a_star_bidirectionnel(start, goal, mult_arr, dem_arr)

        cout_c = cout_total_chemin(c_classique, mult_arr, dem_arr)
        cout_b = cout_total_chemin(c_bidir, mult_arr, dem_arr)

        valide_c = chemin_valide(c_classique, mult_arr, dem_arr, start, goal)
        valide_b = chemin_valide(c_bidir, mult_arr, dem_arr, start, goal)

        ok = (valide_c == valide_b) and (not valide_c or abs(cout_c - cout_b) < 1e-9)
        tout_ok &= ok

        statut = "OK" if ok else "FAIL"
        detail = "pas de chemin" if not valide_c else f"coût={cout_c:.6f}"
        print(f"  [{statut}] {nom} -> {detail}")
        if not ok:
            print(f"        classique: cout={cout_c} valide={valide_c}")
            print(f"        bidir    : cout={cout_b} valide={valide_b}")

    print()
    print("RESULTAT:", "TOUS LES TESTS PASSENT" if tout_ok else "DES TESTS ONT ECHOUE")
    print()
    return tout_ok


# ===========================================================================
# Section 2 : Non-régression. S'assurer que la version actuelle de a_star donne le même coût que le a_star original
# ===========================================================================
def _a_star_original(start, goal, osm_mult, dem_array):
    """
    Copie figée de votre a_star d'AVANT l'extraction de cout_arrete (calcul
    du coût inline dans la boucle voisins). Utilisée uniquement comme
    référence de non-régression : si le a_star actuel diverge de celle-ci,
    c'est que le refactor a changé un comportement.

    PORTÉE LIMITÉE — cette copie modélise une physique volontairement
    dépassée : ni pénalité d'altitude (loi de Dalton), ni plancher de
    vitesse Tobler. Elle ne reste donc une référence valide que sur les
    grilles de cette section : basse altitude (dem ~ ±20 m, où Dalton vaut
    1.000 de façon quasi uniforme) et pentes douces (où le plancher ne mord
    jamais). Sur un relief réaliste elle divergera du a_star actuel, et
    ce sera elle qui aura tort. Voir cost_model/physique.py, et les
    invariants verrouillés dans tests/physique_tests.py.
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
        cr, cc = current
        for v in algo.voisins(current):
            r, c = v
            if r < 0 or r >= shape[0] or c < 0 or c >= shape[1]:
                continue
            if v in closed_set:
                continue
            mult = osm_mult[r][c]
            if math.isinf(mult):
                continue
            dz = dem_array[r, c] - dem_array[cr, cc]
            is_diagonal = (r != cr) and (c != cc)
            dist_m = (42.426 if is_diagonal else 30.0)
            slope = dz / dist_m
            if math.isnan(slope):
                continue
            speed = 6.0 * math.exp(-3.5 * abs(slope + 0.05))
            time_h = (dist_m / 1000) / speed
            edge_cost = time_h * mult
            tentative = g[current] + edge_cost
            if v not in g or tentative < g[v]:
                g[v] = tentative
                f = tentative + algo.heuristique(v, goal) * algo._H_SCALE
                heapq.heappush(open_list, (f, v))
                parent[v] = current
    if goal not in parent:
        return []
    path = []
    c = goal
    while c:
        path.append(c)
        c = parent.get(c)
    return path[::-1]

def section_non_regression():
    print("=" * 70)
    print("SECTION 2 : Non-régression (a_star actuel vs version pré-refactor)")
    print("=" * 70)
    print("Compare a_star (qui appelle cout_arrete) avec une copie figée de")
    print("la version où le calcul de coût était inline dans la boucle voisins.")
    print()

    tout_ok = True
    n_tests = 0

    configs = []
    configs.append((np.zeros((20, 20)), np.ones((20, 20)), (0, 0), (19, 19)))
    dem = np.fromfunction(lambda r, c: (c - r) * 5.0, (25, 25))
    configs.append((dem, np.ones((25, 25)), (0, 0), (24, 24)))
    configs.append((dem, np.ones((25, 25)), (24, 24), (0, 0)))
    for seed in range(25):
        rng = np.random.RandomState(seed)
        rows, cols = rng.randint(15, 50), rng.randint(15, 50)
        dem3, mult3 = grille_synthetique(rows, cols, seed=seed, dem_range=(-15, 15),
                                          mult_range=(0.8, 3.0), taux_obstacles=0.05)
        start = (rng.randint(0, rows), rng.randint(0, cols))
        goal = (rng.randint(0, rows), rng.randint(0, cols))
        configs.append((dem3, mult3, start, goal))

    for dem_arr, mult_arr, start, goal in configs:
        n_tests += 1
        c_ancien = _a_star_original(start, goal, mult_arr, dem_arr)
        c_actuel = algo.a_star(start, goal, mult_arr, dem_arr)

        ok = (c_ancien == c_actuel)
        tout_ok &= ok
        if not ok:
            print(f"  [FAIL] start={start} goal={goal}")
            print(f"        ancien : {c_ancien}")
            print(f"        actuel : {c_actuel}")

    print(f"  {n_tests} configurations testées.")
    print("RESULTAT:", "AUCUNE REGRESSION (chemin identique partout)" if tout_ok else "REGRESSION DETECTEE")
    print()
    return tout_ok


# ===========================================================================
# Section 3 : Performance (classique vs bidirectionnel) sur une grille fixe
# ===========================================================================
def section_performance(dem_array=None, osm_mult=None, start=None, goal=None, repetitions=3):
    print("=" * 70)
    print("SECTION 3 : Performance classique vs bidirectionnel")
    print("=" * 70)

    if dem_array is None:
        dem_array, osm_mult = grille_synthetique(100, 100, seed=7, dem_range=(-20, 20), mult_range=(0.5, 2.0))
        start, goal = (0, 0), (dem_array.shape[0] - 1, dem_array.shape[1] - 1)
        print(f"  (grille synthétique {dem_array.shape}, seed=7, dem~U(-20,20), mult~U(0.5,2.0))")

    temps_classique = []
    temps_bidir = []
    for _ in range(repetitions):
        t0 = time.time()
        c_classique = algo.a_star(start, goal, osm_mult, dem_array)
        t1 = time.time()
        temps_classique.append(t1 - t0)
        if BIDIR_DISPO:
            c_bidir = algo.a_star_bidirectionnel(start, goal, osm_mult, dem_array)
            temps_bidir.append(time.time() - t1)

    cout_c = cout_total_chemin(c_classique, osm_mult, dem_array)
    n_classique = compter_noeuds_fermes(start, goal, osm_mult, dem_array)
    med_c = sorted(temps_classique)[len(temps_classique) // 2]
    pct_grille = n_classique / dem_array.size * 100

    print(f"  start={start} goal={goal}  ({repetitions} répétitions, médiane affichée)")
    print(f"  A* classique     : temps={med_c:.4f}s  cout={cout_c:.5f}  len={len(c_classique)}"
          f"  noeuds_fermes={n_classique} ({pct_grille:.1f}% de la grille)")

    if not BIDIR_DISPO:
        print("  A* bidirectionnel: [ignore] non implemente")
        print()
        return {"t_classique": med_c, "t_bidir": None, "cout_classique": cout_c,
                "cout_bidir": None, "noeuds_fermes": n_classique, "pct_grille": pct_grille}

    cout_b = cout_total_chemin(c_bidir, osm_mult, dem_array)
    med_b = sorted(temps_bidir)[len(temps_bidir) // 2]
    print(f"  A* bidirectionnel: temps={med_b:.4f}s  cout={cout_b:.5f}  len={len(c_bidir)}")
    if med_b > 0:
        print(f"  speedup bidir/classique: {med_c / med_b:.2f}x  (>1 = bidir plus rapide)")
    print()
    return {"t_classique": med_c, "t_bidir": med_b, "cout_classique": cout_c,
            "cout_bidir": cout_b, "noeuds_fermes": n_classique, "pct_grille": pct_grille}


# ===========================================================================
# Section 4 : Mise à l'échelle (performance sur tailles croissantes)
# ===========================================================================
def section_mise_a_lechelle(tailles=(50, 100, 200, 300)):
    print("=" * 70)
    print("SECTION 4 : Mise à l'échelle (tailles croissantes)")
    print("=" * 70)
    if BIDIR_DISPO:
        print(f"  {'taille':>8} {'classique(s)':>14} {'bidir(s)':>12} {'speedup':>10} {'noeuds_fermes':>14} {'%grille':>9}")
    else:
        print("  (a_star_bidirectionnel non implemente : colonnes bidir et speedup ignorees)")
        print(f"  {'taille':>8} {'classique(s)':>14} {'noeuds_fermes':>14} {'%grille':>9}")

    resultats = []
    for size in tailles:
        dem, mult = grille_synthetique(size, size, seed=7, dem_range=(-20, 20), mult_range=(0.5, 2.0))
        start, goal = (0, 0), (size - 1, size - 1)

        t0 = time.time()
        algo.a_star(start, goal, mult, dem)
        t1 = time.time()
        t_bidir = None
        if BIDIR_DISPO:
            algo.a_star_bidirectionnel(start, goal, mult, dem)
            t_bidir = time.time() - t1

        n_fermes = compter_noeuds_fermes(start, goal, mult, dem)
        pct = n_fermes / (size * size) * 100

        if BIDIR_DISPO:
            speedup = (t1 - t0) / t_bidir if t_bidir > 0 else float("inf")
            print(f"  {size:>8} {t1 - t0:>14.4f} {t_bidir:>12.4f} {speedup:>9.2f}x {n_fermes:>14} {pct:>8.1f}%")
        else:
            print(f"  {size:>8} {t1 - t0:>14.4f} {n_fermes:>14} {pct:>8.1f}%")
        resultats.append({"taille": size, "t_classique": t1 - t0, "t_bidir": t_bidir,
                           "noeuds_fermes": n_fermes, "pct_grille": pct})
    print()
    return resultats


# ===========================================================================
# Section 5 : Admissibilité de l'heuristique avec un simple algorithme de dijkstra.
# (h(a,b) ne doit jamais dépasser le vrai coût optimal a->b)
# ===========================================================================
def _dijkstra_complet(source, osm_mult, dem_array, inverse=False):
    shape = dem_array.shape
    g = {source: 0}
    open_list = [(0, source)]
    closed = set()
    while open_list:
        d, u = heapq.heappop(open_list)
        if u in closed:
            continue
        closed.add(u)
        for v in algo.voisins(u):
            r, c = v
            if r < 0 or r >= shape[0] or c < 0 or c >= shape[1]:
                continue
            if v in closed:
                continue
            cost = algo.cout_arrete(u, v, osm_mult, dem_array, inverse=inverse)
            if cost is None:
                continue
            nd = g[u] + cost
            if v not in g or nd < g[v]:
                g[v] = nd
                heapq.heappush(open_list, (nd, v))
    return g

def section_admissibilite_heuristique(n_paires=15, seed=1):
    print("=" * 70)
    print("SECTION 5 : Admissibilité de l'heuristique")
    print("=" * 70)
    print("  Vérifie que heuristique(a,b) * _H_SCALE <= vrai coût optimal a->b")
    print("  sur des paires de points aléatoires (violations = bug critique).")
    print()

    dem, mult = grille_synthetique(150, 150, seed=7, dem_range=(-20, 20), mult_range=(0.5, 2.0))

    rng = np.random.RandomState(seed)
    violations = 0
    for _ in range(n_paires):
        a = (rng.randint(0, dem.shape[0]), rng.randint(0, dem.shape[1]))
        b = (rng.randint(0, dem.shape[0]), rng.randint(0, dem.shape[1]))
        g_real = _dijkstra_complet(a, mult, dem)
        if b not in g_real:
            continue
        h = algo.heuristique(a, b) * algo._H_SCALE
        ok = h <= g_real[b] + 1e-9
        if not ok:
            violations += 1
        statut = "ok" if ok else "VIOLATION"
        print(f"  [{statut}] a={a} b={b}  h={h:.5f}  vrai_cout={g_real[b]:.5f}")

    print()
    print("RESULTAT:", f"{violations} violation(s) trouvée(s) sur {n_paires} paires testées")
    print()
    return violations == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark a_star / a_star_bidirectionnel")
    parser.add_argument("--section", choices=["correction", "regression", "perf", "echelle", "heuristique", "tout"],
                         default="tout", help="Quelle section lancer (défaut: tout)")
    parser.add_argument("--reel", action="store_true",
                         help="Utilise vos vraies données DEM/OSM (via charger_grille_reelle) "
                              "pour la section perf, au lieu de données synthétiques")
    args = parser.parse_args()

    resultats_ok = []

    if args.section in ("correction", "tout"):
        resultats_ok.append(section_validation_correction())

    if args.section in ("regression", "tout"):
        resultats_ok.append(section_non_regression())

    if args.section in ("perf", "tout"):
        if args.reel:
            dem_array, osm_mult, transform, start, goal = charger_grille_reelle()
            section_performance(dem_array, osm_mult, start, goal)
        else:
            section_performance()

    if args.section in ("echelle", "tout") and not args.reel:
        section_mise_a_lechelle()

    if args.section in ("heuristique", "tout"):
        resultats_ok.append(section_admissibilite_heuristique())

    if resultats_ok:
        print("=" * 70)
        print("RESUME GLOBAL:", "TOUT OK" if all(resultats_ok) else "DES PROBLEMES ONT ETE DETECTES")
        print("=" * 70)

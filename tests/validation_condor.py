"""
Validation de la validité des tracés produits par le programme.
Comparaison avec alternatives naïves et avec traces réelles.

Pas un pytest (nom sans suffixe _tests) - script CLI autonome.

Trois tracés par cas, tous re-scorés sur les VRAIES grilles (calculer_cout_tobler) :
  1. Condor          : recherche_meilleur_chemin sur les grilles réelles (le produit à valider)
  2. Aveugle terrain : même A*, DEM aplati + multiplicateurs neutralisés (seul l'infranchissable
                       reste bloqué : lac, bâtiment, pente critique) -> plus court chemin
                       franchissable. Prouve que le modèle de coût (pente + terrain) ajoute
                       de la valeur.
  3. Ligne droite    : cas dégénéré, compte les cellules eau/falaise traversées.

Vérité terrain : chaque fichier GPX/CSV déposé dans tests/traces/ devient automatiquement
un cas de validation (bbox = étendue de la trace, départ/arrivée = extrémités), scoré via
RouteComparisonService.compare (Fréchet, DTW, ratio d'effort, score 0-100).

Usage :
    python tests/validation_condor.py                 # tous les cas
    python tests/validation_condor.py --cas UDES      # un seul cas
    python tests/validation_condor.py --liste         # liste les cas disponibles
    python tests/validation_condor.py --sans-figures  # pas de PNG
    python tests/validation_condor.py --superposer rainier_dc rainier_emmons rainier_kautz
                                                      # + figure combinée traces/Condor

Sorties : tests/exports/validation/<cas>.png + resultats.csv + tableau console.
Prérequis : .env avec OPENTOPO_KEY_1 (DEM en cache disque après le premier run).
"""
import sys
import os
import io
import csv
import math
import argparse
import contextlib
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from src.data.structures_communes import BBox, latlon_to_rowcol_affine, rowcol_to_latlon
from src.data.data_fetcher import fetch_terrain
from src.data.Elevation.structures_elevation import DEMType
from cost_model.weights import HIKING_WEIGHTS
from src.routage.a_star import (
    recherche_meilleur_chemin,
    snap_to_traversable,
    calculer_cout_tobler,
    cout_arrete,
    _interpolate_path,
)
from src.api.services.compare_path import RouteComparisonService
from comparaison_visuelle import build_osm_rgb, CATEGORIES

TRACES_DIR = os.path.join(os.path.dirname(__file__), "traces")
EXPORT_DIR = os.path.join(os.path.dirname(__file__), "exports", "validation")
CELL_M = 30.0
MARGE_TRACE_DEG = 0.01          # marge autour de l'étendue d'une trace GPS
MAX_CELLULES = 1_000_000           # garde-fou taille de grille (A* Python)
SEUIL_BOUCLE_M = 50.0            # départ/arrivée plus proches -> trace traitée comme boucle

# Styles des tracés 
STYLES = {
    "condor":   dict(color="#090909", linestyle="--",  linewidth=1.8, label="Condor"),
    "aveugle":  dict(color="#6A4C93", linestyle="-.", linewidth=2.0, label="Aveugle terrain"),
    "droite":   dict(color="#121112", linestyle=":",  linewidth=1.8, label="Ligne droite"),
    "trace":    dict(color="#2F31A5", linestyle="-",  linewidth=5.5, alpha=0.5, label="Trace GPS"),
}

STYLE_LEGENDE = dict(facecolor="#6E6E6E", edgecolor="#1F1F1F",
                     labelcolor="white", framealpha=0.9)

# Rappel des couleurs du fond OSM : (categorie dans CATEGORIES, libelle affiche)
LEGENDE_OSM = [
    ("infrastructure", "Routes / sentiers"),
    ("eau",            "Eau"),
    ("vegetation",     "Végétation"),
]


def _patches_osm():
    """Carrés de couleur des catégories OSM, couleurs tirées de CATEGORIES."""
    couleurs = {nom: couleur for nom, _, couleur in CATEGORIES}
    return [mpatches.Patch(color=couleurs[nom], label=libelle)
            for nom, libelle in LEGENDE_OSM if nom in couleurs]


def _dimensions_bbox(bbox) -> str:
    """Étendue de la zone couverte, ex. « 2.4 km x 5.1 km (12.2 km²) ».

    Largeur mesurée à la latitude médiane (elle rétrécit vers les pôles).
    """
    lat_med = (bbox.sud + bbox.nord) / 2.0
    largeur_km = haversine_m(lat_med, bbox.ouest, lat_med, bbox.est) / 1000.0
    hauteur_km = haversine_m(bbox.sud, bbox.ouest, bbox.nord, bbox.ouest) / 1000.0
    return (f"Zone couverte : {largeur_km:.1f} km x {hauteur_km:.1f} km "
            f"({largeur_km * hauteur_km:.1f} km²)")


def _titre_figure(fig, titre: str, bbox):
    """Titre de la figure + ligne d'étendue de la zone juste en dessous."""
    fig.suptitle(titre, fontsize=13)
    fig.text(0.5, 0.935, _dimensions_bbox(bbox), ha="center", fontsize=9, color="#555555")


def _panneau_elevation(fig, ax, dem):
    """Panneau DEM (shading terrain) + barre de couleurs graduée en mètres."""
    im = ax.imshow(dem, cmap="terrain")
    ax.set_title("Élévation (DEM)", fontsize=10)
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Élévation (m)", fontsize=8)
    cbar.ax.tick_params(labelsize=8)
    return im


@dataclass
class CasValidation:
    nom: str
    bbox_coords: tuple            # (sud, ouest, nord, est)
    depart: tuple                 # (lat, lon)
    arrivee: tuple                # (lat, lon)
    but: str = ""
    trace_reference: list | None = field(default=None, repr=False)  # [(lat, lon), ...]


def charger_cas_traces() -> list[CasValidation]:
    """Un cas (+ retour) par fichier GPX/CSV déposé dans tests/traces/."""
    cas = []
    if not os.path.isdir(TRACES_DIR):
        return cas
    for fname in sorted(os.listdir(TRACES_DIR)):
        if not fname.lower().endswith((".gpx", ".csv")):
            continue
        path = os.path.join(TRACES_DIR, fname)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            contenu = f.read()
        points = RouteComparisonService.parse_trail_file(fname, contenu)
        if len(points) < 2:
            print(f"[!] trace ignorée (illisible ou < 2 points) : {fname}")
            continue
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        sud, nord = min(lats) - MARGE_TRACE_DEG, max(lats) + MARGE_TRACE_DEG
        ouest, est = min(lons) - MARGE_TRACE_DEG, max(lons) + MARGE_TRACE_DEG
        n_cellules = (nord - sud) * 3600 * (est - ouest) * 3600
        if n_cellules > MAX_CELLULES:
            print(f"[!] trace ignorée (grille {n_cellules:.0f} cellules > {MAX_CELLULES}) : {fname}")
            continue
        stem = os.path.splitext(fname)[0][:40]
        bbox_coords = (sud, ouest, nord, est)
        if haversine_m(*points[0], *points[-1]) < SEUIL_BOUCLE_M:
            # Boucle (départ = arrivée) : couper au point le plus éloigné du départ,
            # sinon compare() tronque la référence à un point (coût 0 -> division par 0).
            k = max(range(len(points)), key=lambda i: haversine_m(*points[0], *points[i]))
            if k == 0 or k == len(points) - 1:
                print(f"[!] trace ignorée (boucle dégénérée) : {fname}")
                continue
            cas.append(CasValidation(
                nom=f"TRACE_{stem}_aller",
                bbox_coords=bbox_coords,
                depart=points[0], arrivee=points[k],
                but="vérité terrain : boucle GPS, moitié aller",
                trace_reference=points[:k + 1],
            ))
            cas.append(CasValidation(
                nom=f"TRACE_{stem}_retour",
                bbox_coords=bbox_coords,
                depart=points[k], arrivee=points[-1],
                but="vérité terrain : boucle GPS, moitié retour (pente signée)",
                trace_reference=points[k:],
            ))
        else:
            cas.append(CasValidation(
                nom=f"TRACE_{stem}",
                bbox_coords=bbox_coords,
                depart=points[0], arrivee=points[-1],
                but="vérité terrain : trace GPS enregistrée",
                trace_reference=points,
            ))
            cas.append(CasValidation(
                nom=f"TRACE_{stem}_retour",
                bbox_coords=bbox_coords,
                depart=points[-1], arrivee=points[0],
                but="vérité terrain, direction inverse (pente signée)",
                trace_reference=points,
            ))
    return cas


# ---------------------------------------------------------------------------
# Géométrie
# ---------------------------------------------------------------------------
def haversine_m(lat1, lon1, lat2, lon2) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 6_371_000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def longueur_m(chemin: list) -> float:
    return sum(haversine_m(*chemin[i - 1], *chemin[i]) for i in range(1, len(chemin)))


def densifier(chemin: list, pas_m: float = 10.0) -> np.ndarray:
    """Ré-échantillonne un chemin lat/lon à ~pas_m mètres (réutilise _interpolate_path)."""
    arr = np.asarray(chemin, dtype=float)
    if len(arr) < 2:
        return arr
    target_n = max(len(arr), int(longueur_m(chemin) / pas_m) + 2)
    return _interpolate_path(arr, target_n)


def cellules_du_chemin(chemin: list, transform, shape) -> list[tuple]:
    """Suite de cellules (row, col) traversées, consécutives dédupliquées, bornées."""
    cells = []
    for lat, lon in densifier(chemin):
        r, c = latlon_to_rowcol_affine(transform, lat, lon)
        r = min(max(r, 0), shape[0] - 1)
        c = min(max(c, 0), shape[1] - 1)
        if not cells or cells[-1] != (r, c):
            cells.append((r, c))
    return cells


# ---------------------------------------------------------------------------
# Chargement d'un cas + génération des trois tracés
# ---------------------------------------------------------------------------
def charger_cas(cas: CasValidation) -> dict:
    bbox = BBox(*cas.bbox_coords)
    fetch_terrain(bbox, DEMType.COP30, HIKING_WEIGHTS)
    transform = bbox.dem_data.transform
    dem = bbox.dem_data.array

    ctx = {"bbox": bbox, "transform": transform, "dem": dem}
    for cle, latlon in (("depart", cas.depart), ("arrivee", cas.arrivee)):
        rc = latlon_to_rowcol_affine(transform, *latlon)
        rc = (min(max(rc[0], 0), dem.shape[0] - 1), min(max(rc[1], 0), dem.shape[1] - 1))
        with contextlib.redirect_stdout(io.StringIO()):
            rc_snap = snap_to_traversable(rc, bbox.osm_mult)
        ctx[cle] = rc_snap
        ctx[f"{cle}_latlon"] = rowcol_to_latlon(transform, *rc_snap)
        # distance de snap en mètres (Chebyshev x 30 m, approximation en cellules)
        ctx[f"snap_{cle}_m"] = max(abs(rc_snap[0] - rc[0]), abs(rc_snap[1] - rc[1])) * CELL_M
    return ctx


def route_condor(ctx) -> list:
    bbox = ctx["bbox"]
    with contextlib.redirect_stdout(io.StringIO()):
        return recherche_meilleur_chemin(
            bbox.osm_mult, ctx["dem"], ctx["transform"], ctx["depart"], ctx["arrivee"]
        )


def route_aveugle(ctx) -> list:
    """Même A*, aveuglé : DEM plat + multiplicateurs neutres. Seul l'infranchissable
    (et les trous NaN du DEM, que Condor refuse aussi) reste bloqué -> plus court
    chemin franchissable. Coût constant par cellule => l'heuristique reste admissible."""
    bbox = ctx["bbox"]
    mult_aveugle = np.where(np.isinf(bbox.osm_mult) | np.isnan(ctx["dem"]), np.inf, 1.0)
    dem_plat = np.zeros_like(ctx["dem"], dtype=float)
    with contextlib.redirect_stdout(io.StringIO()):
        return recherche_meilleur_chemin(
            mult_aveugle, dem_plat, ctx["transform"], ctx["depart"], ctx["arrivee"]
        )


def route_ligne_droite(ctx, pas_m: float = 15.0) -> list:
    (lat1, lon1), (lat2, lon2) = ctx["depart_latlon"], ctx["arrivee_latlon"]
    n = max(2, int(haversine_m(lat1, lon1, lat2, lon2) / pas_m) + 1)
    t = np.linspace(0.0, 1.0, n)
    return list(zip(lat1 + t * (lat2 - lat1), lon1 + t * (lon2 - lon1)))


# ---------------------------------------------------------------------------
# Métriques
# ---------------------------------------------------------------------------
def verifier_plausibilite(chemin: list, ctx) -> dict:
    """Vérifications physiques automatiques sur un tracé lat/lon."""
    res = {
        "chemin_vide": not chemin or len(chemin) < 2,
        "cellules_inf": 0, "pct_inf": 0.0, "pct_nan": 0.0,
        "pente_max_pct": 0.0, "pente_p95_pct": 0.0, "ratio_detour": 0.0,
        "plausible": False,
    }
    if res["chemin_vide"]:
        return res

    dem, osm_mult = ctx["dem"], ctx["bbox"].osm_mult
    cells = cellules_du_chemin(chemin, ctx["transform"], dem.shape)

    inf_mask = [np.isinf(osm_mult[r, c]) for r, c in cells]
    nan_mask = [np.isnan(dem[r, c]) for r, c in cells]
    res["cellules_inf"] = int(sum(inf_mask))
    res["pct_inf"] = 100.0 * sum(inf_mask) / len(cells)
    res["pct_nan"] = 100.0 * sum(nan_mask) / len(cells)

    pentes = []
    for i in range(1, len(cells)):
        (r1, c1), (r2, c2) = cells[i - 1], cells[i]
        z1, z2 = float(dem[r1, c1]), float(dem[r2, c2])
        if math.isnan(z1) or math.isnan(z2):
            continue
        dist = CELL_M * math.hypot(r2 - r1, c2 - c1)
        if dist > 0:
            pentes.append(abs(z2 - z1) / dist * 100.0)
    if pentes:
        res["pente_max_pct"] = float(max(pentes))
        res["pente_p95_pct"] = float(np.percentile(pentes, 95))

    dist_directe = haversine_m(*ctx["depart_latlon"], *ctx["arrivee_latlon"])
    res["ratio_detour"] = longueur_m(chemin) / dist_directe if dist_directe > 30 else 1.0

    res["plausible"] = (
        res["cellules_inf"] == 0 # aucune cellule inf
        and res["pct_nan"] < 5.0 # moins de 5 nan cells
        and res["pente_max_pct"] <= 100.0   # ~45 deg, invraisemblable a pied au-dela
        and res["ratio_detour"] <= 5.0 # longueur du trace ne depasse pas 5x le chemin vol d'oiseau
    )
    return res


PENALITE_INF = 1.0        # cellule infranchissable comptée x5 au lieu de bloquer

def cout_condor_h(chemin: list, ctx, penalite_inf: float | None = None) -> float:
    """Coût que l'A* optimise réellement : Tobler x multiplicateurs OSM x altitude.

    Re-score un tracé lat/lon avec cout_arrete (la source de vérité du modèle
    de coût). Retourne inf si le tracé traverse une arête infranchissable.
    Condor doit être le plus bas des trois tracés - sinon, bug d'optimalité.

    penalite_inf : remplace le multiplicateur des cellules infranchissables au lieu
    de bloquer. Réservé à la trace GPS de référence, qui passe là où le raster dit
    « impossible » (falaise rasterisée large, pont non tagué) : un coût infini
    rendrait la ligne de référence inutilisable comme point de comparaison.
    """
    osm_mult = ctx["bbox"].osm_mult
    if penalite_inf is not None:
        osm_mult = np.where(np.isinf(osm_mult), penalite_inf, osm_mult)
    cells = cellules_du_chemin(chemin, ctx["transform"], ctx["dem"].shape)
    total = 0.0
    for i in range(1, len(cells)):
        c = cout_arrete(cells[i - 1], cells[i], osm_mult, ctx["dem"])
        if c is None:
            return float("inf")
        total += c
    return total


CORRIDOR_M = 60.0                # tolérance "le tracé suit le GPX" (2 cellules)


def pct_dans_corridor(chemin: list, trace: list | None) -> float | str:
    """% du tracé à moins de CORRIDOR_M mètres de la trace GPX de référence.

    100 % = le tracé suit le même chemin que la trace ; une valeur basse
    signifie qu'il rejoint l'arrivée par un autre itinéraire.
    """
    if trace is None or not chemin or len(chemin) < 2 or len(trace) < 2:
        return ""
    p = densifier(chemin)
    q = densifier(trace)
    # projection plane locale (mètres), suffisante à l'échelle d'une bbox de rando
    lat0 = math.radians(float(np.mean(p[:, 0])))
    m_lat, m_lon = 111_132.0, 111_132.0 * math.cos(lat0)
    p_xy = np.column_stack([p[:, 0] * m_lat, p[:, 1] * m_lon])
    q_xy = np.column_stack([q[:, 0] * m_lat, q[:, 1] * m_lon])
    # distance min de chaque point du tracé à la trace (broadcast N x M)
    d_min = np.sqrt(((p_xy[:, None, :] - q_xy[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
    return round(100.0 * float((d_min <= CORRIDOR_M).mean()), 1)


def metriques_route(nom_cas, nom_route, chemin, ctx, trace=None) -> dict:
    plaus = verifier_plausibilite(chemin, ctx)
    row = {
        "cas": nom_cas, "route": STYLES[nom_route]["label"],
        "cout_tobler_h": round(calculer_cout_tobler(chemin, ctx["dem"], ctx["transform"]), 3)
                         if not plaus["chemin_vide"] else float("nan"),
        "cout_condor_h": round(cout_condor_h(chemin, ctx), 3)
                         if not plaus["chemin_vide"] else float("nan"),
        "longueur_km": round(longueur_m(chemin) / 1000.0, 2) if not plaus["chemin_vide"] else 0.0,
        "dans_corridor_pct": pct_dans_corridor(chemin, trace),
        **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in plaus.items()},
        "snap_depart_m": ctx["snap_depart_m"], "snap_arrivee_m": ctx["snap_arrivee_m"],
        "frechet_m": "", "dtw_m": "", "score": "", "verdict": "",
    }
    if trace is not None and not plaus["chemin_vide"]:
        cmp = RouteComparisonService.compare(
            chemin, trace, ctx["dem"], ctx["transform"],
            ctx["depart_latlon"], ctx["arrivee_latlon"],
        )
        row["frechet_m"] = cmp["metrics"]["frechet_distance_meters"]
        row["dtw_m"] = cmp["metrics"]["dtw_corridor_deviation_meters"]
        row["score"] = cmp["score"]
        row["verdict"] = cmp["verdict"]
    return row


# ---------------------------------------------------------------------------
# Figure : 2 panneaux (OSM | DEM), les tracés superposés
# ---------------------------------------------------------------------------
def _tracer_routes(ax, routes: dict, ctx):
    shape = ctx["dem"].shape
    ordre = ["trace", "droite", "aveugle", "condor"]  # trace dessous, Condor dessus
    for nom in ordre:
        chemin = routes.get(nom)
        if not chemin or len(chemin) < 2:
            continue
        rc = np.array([latlon_to_rowcol_affine(ctx["transform"], lat, lon) for lat, lon in chemin])
        rc[:, 0] = np.clip(rc[:, 0], 0, shape[0] - 1)
        rc[:, 1] = np.clip(rc[:, 1], 0, shape[1] - 1)
        ax.plot(rc[:, 1], rc[:, 0], **STYLES[nom])
    (r1, c1), (r2, c2) = ctx["depart"], ctx["arrivee"]
    ax.plot(c1, r1, "o", color="white", markeredgecolor="#1F1F1F", markersize=9, zorder=5)
    ax.plot(c2, r2, "*", color="white", markeredgecolor="#1F1F1F", markersize=13, zorder=5)


def figure_cas(nom_cas: str, routes: dict, ctx, output_dir: str):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
    _titre_figure(fig, f"Validation des tracés - {nom_cas}", ctx["bbox"])

    ax1.imshow(build_osm_rgb(ctx["bbox"].raster_osm, CATEGORIES))
    ax1.set_title("Terrain OSM", fontsize=10)
    _panneau_elevation(fig, ax2, ctx["dem"])

    for ax in (ax1, ax2):
        _tracer_routes(ax, routes, ctx)
        ax.set_xticks([]), ax.set_yticks([])
    handles = [plt.Line2D([], [], **{k: v for k, v in STYLES[n].items()})
               for n in ("condor", "aveugle", "droite") if routes.get(n)]
    if routes.get("trace"):
        handles.append(plt.Line2D([], [], **{k: v for k, v in STYLES["trace"].items()}))
    handles += _patches_osm()
    ax1.legend(handles=handles, loc="best", fontsize=9, **STYLE_LEGENDE)

    os.makedirs(output_dir, exist_ok=True)
    out = os.path.join(output_dir, f"{nom_cas}.png")
    plt.tight_layout(rect=(0, 0, 1, 0.92))   # place pour le titre + la ligne d'étendue
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"      figure -> {out}")


# Figures superposées : une couleur par voie, trace GPS pleine, Condor pointillé
COULEURS_SUPERPOSITION = ["#E810B6", "#E08A00", "#2E5FA3", "#2A9D5C", "#6A4C93", "#1F1F1F"]
COULEURS_CONDOR_SUPERPOSITION = ["#090909", "#084B5C", "#763B08"]   # pointillé Condor, une couleur par voie


def figure_superposition(elements: list[tuple], nom_figure: str, output_dir: str,
                         titre: str | None = None):
    """Superpose plusieurs couples (trace GPS, tracé Condor) sur une bbox commune.

    elements : [(nom_cas, trace_latlon, condor_latlon), ...] - condor peut être None.
    Purement visuel : aucune métrique recalculée, tableau et CSV inchangés.
    La bbox union peut dépasser MAX_CELLULES : aucun A* n'est relancé ici.
    """
    tous_points = [p for _, trace, _ in elements for p in trace]
    lats = [p[0] for p in tous_points]
    lons = [p[1] for p in tous_points]
    bbox = BBox(min(lats) - MARGE_TRACE_DEG, min(lons) - MARGE_TRACE_DEG,
                max(lats) + MARGE_TRACE_DEG, max(lons) + MARGE_TRACE_DEG)
    fetch_terrain(bbox, DEMType.COP30, HIKING_WEIGHTS)
    transform, dem = bbox.dem_data.transform, bbox.dem_data.array

    def en_pixels(chemin):
        rc = np.array([latlon_to_rowcol_affine(transform, lat, lon) for lat, lon in chemin])
        rc[:, 0] = np.clip(rc[:, 0], 0, dem.shape[0] - 1)
        rc[:, 1] = np.clip(rc[:, 1], 0, dem.shape[1] - 1)
        return rc

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
    _titre_figure(fig, titre or f"Superposition - {nom_figure}", bbox)
    ax1.imshow(build_osm_rgb(bbox.raster_osm, CATEGORIES))
    ax1.set_title("Terrain OSM", fontsize=10)
    _panneau_elevation(fig, ax2, dem)

    handles = []
    for i, (nom, trace, condor) in enumerate(elements):
        couleur = COULEURS_SUPERPOSITION[i % len(COULEURS_SUPERPOSITION)]
        couleur_condor = COULEURS_CONDOR_SUPERPOSITION[i % len(COULEURS_CONDOR_SUPERPOSITION)]
        court = nom.removeprefix("TRACE_").removesuffix("_aller")
        for ax in (ax1, ax2):
            rc = en_pixels(trace)
            (ligne,) = ax.plot(rc[:, 1], rc[:, 0], color=couleur, linewidth=5.0, alpha=0.7,
                               label=f"{court} - GPS")
            if ax is ax1:
                handles.append(ligne)
            if condor and len(condor) >= 2:
                rc = en_pixels(condor)
                (ligne,) = ax.plot(rc[:, 1], rc[:, 0], color=couleur_condor,
                                   linewidth=1.8, linestyle="--",
                                   label=f"{court} - Condor")
                if ax is ax1:
                    handles.append(ligne)
    handles += _patches_osm()
    for ax in (ax1, ax2):
        ax.set_xticks([]), ax.set_yticks([])
    ax1.legend(handles=handles, loc="best", fontsize=9, **STYLE_LEGENDE)

    os.makedirs(output_dir, exist_ok=True)
    out = os.path.join(output_dir, f"{nom_figure}.png")
    plt.tight_layout(rect=(0, 0, 1, 0.92))   # place pour le titre + la ligne d'étendue
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nfigure superposée -> {out}")


# ---------------------------------------------------------------------------
# Exécution
# ---------------------------------------------------------------------------
COLONNES_CONSOLE = [
    ("route", 16), ("plausible", 9), ("cout_condor_h", 13), ("cout_tobler_h", 13), ("longueur_km", 11),
    ("cellules_inf", 12), ("pente_max_pct", 13), ("dans_corridor_pct", 17),
    ("frechet_m", 10), ("dtw_m", 8), ("score", 6),
]


def executer_cas(cas: CasValidation, sans_figures: bool) -> tuple[list[dict], dict]:
    print(f"\n=== {cas.nom} - {cas.but}")
    ctx = charger_cas(cas)
    print(f"    grille {ctx['dem'].shape[0]}x{ctx['dem'].shape[1]}, "
          f"snap départ {ctx['snap_depart_m']:.0f} m / arrivée {ctx['snap_arrivee_m']:.0f} m")

    routes = {
        "condor": route_condor(ctx),
        "aveugle": route_aveugle(ctx),
        "droite": route_ligne_droite(ctx),
        "trace": cas.trace_reference,
    }
    lignes = []
    for nom in ("condor", "aveugle", "droite"):
        lignes.append(metriques_route(cas.nom, nom, routes[nom], ctx, cas.trace_reference))
    if routes["trace"] and len(routes["trace"]) >= 2:
        # Référence GPS : seuls les coûts bruts ont un sens (plausibilité et
        # comparaison la feraient se juger elle-même).
        l = metriques_route(cas.nom, "trace", routes["trace"], ctx)
        l["cout_condor_h"] = round(cout_condor_h(routes["trace"], ctx, PENALITE_INF), 3)
        lignes.append({k: l[k] for k in ("cas", "route", "cout_condor_h",
                                         "cout_tobler_h", "longueur_km", "pente_max_pct")})

    ref = lignes[0]["cout_tobler_h"]   # Condor, toujours en tête
    for l in lignes:
        v = l["cout_tobler_h"]
        l["delta_pct_vs_condor"] = round(100.0 * (v - ref) / ref, 1) if ref and not math.isnan(v) else ""

    if not sans_figures:
        figure_cas(cas.nom, routes, ctx, EXPORT_DIR)
    return lignes, routes


def imprimer_tableau(lignes: list[dict]):
    entete = "cas".ljust(34) + "".join(nom.ljust(w + 1) for nom, w in COLONNES_CONSOLE)
    print("\n" + entete)
    print("-" * len(entete))
    for l in lignes:
        cells = l["cas"][:33].ljust(34)
        for nom, w in COLONNES_CONSOLE:
            cells += str(l.get(nom, ""))[:w].ljust(w + 1)
        print(cells)


def main():
    parser = argparse.ArgumentParser(description="Validation des tracés Condor")
    parser.add_argument("--cas", help="nom (ou début de nom) d'un cas à exécuter seul")
    parser.add_argument("--sans-figures", action="store_true")
    parser.add_argument("--liste", action="store_true", help="liste les cas et quitte")
    parser.add_argument("--superposer", metavar="TRACE", nargs="+",
                        help="superpose ces traces (et leurs tracés Condor, sens aller) "
                             "sur une même carte, ex. --superposer rainier_dc rainier_emmons rainier_kautz")
    args = parser.parse_args()

    tous = charger_cas_traces()
    if not tous:
        print(f"[!] aucune trace GPX/CSV valide dans {TRACES_DIR}")
        return 2
    if args.liste:
        for c in tous:
            print(f"  {c.nom.ljust(40)} {c.but}")
        return 0
    if args.cas:
        tous = [c for c in tous if c.nom.upper().startswith(args.cas.upper())]
        if not tous:
            print(f"[!] aucun cas ne correspond à « {args.cas} » (voir --liste)")
            return 2

    voulu = [t.lower().removeprefix("trace_") for t in (args.superposer or [])]

    def a_superposer(nom_cas: str) -> bool:
        stem = nom_cas.lower().removeprefix("trace_").removesuffix("_aller")
        return stem in voulu and not nom_cas.endswith("_retour")

    if voulu and not args.cas:
        tous = [c for c in tous if a_superposer(c.nom)]
        if not tous:
            print(f"[!] aucun cas ne correspond à --superposer {' '.join(voulu)} (voir --liste)")
            return 2

    lignes = []
    superposition = []           # (nom, trace GPS, tracé Condor) pour --superposer
    for cas in tous:
        try:
            l, routes = executer_cas(cas, args.sans_figures)
            lignes.extend(l)
            if a_superposer(cas.nom):
                superposition.append((cas.nom, cas.trace_reference, routes["condor"]))
        except Exception as e:
            print(f"[!] échec du cas {cas.nom} : {e}")
            lignes.append({"cas": cas.nom, "route": "ERREUR", "plausible": False, "verdict": str(e)})

    if voulu and len(superposition) < len(voulu):
        trouves = {n.lower().removeprefix("trace_").removesuffix("_aller") for n, _, _ in superposition}
        print(f"[!] traces à superposer introuvables : {', '.join(sorted(set(voulu) - trouves))}")
    if superposition and not args.sans_figures:
        prefixe = os.path.commonprefix(voulu).rstrip("_-") or "traces"
        try:
            figure_superposition(superposition, f"SUPERPOSITION_{prefixe}", EXPORT_DIR,
                                 titre=f"Traces GPS et tracés Condor - {prefixe}")
        except Exception as e:
            print(f"[!] figure superposée échouée : {e}")

    imprimer_tableau(lignes)

    os.makedirs(EXPORT_DIR, exist_ok=True)
    out_csv = os.path.join(EXPORT_DIR, "resultats.csv")
    champs = sorted({k for l in lignes for k in l})
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=champs)
        w.writeheader()
        w.writerows(lignes)
    print(f"\nCSV -> {out_csv}")

    non_plausibles = [l for l in lignes if l["route"] == "Condor" and not l.get("plausible")]
    return 1 if non_plausibles else 0


if __name__ == "__main__":
    sys.exit(main())

"""
fichier de comparaison visuelle OSM et DEM

pas un pytest
"""
import numpy as np
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cost_model.weights import HIKING_WEIGHTS, DEFAULT_WEIGHTS
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LogNorm
from src.data.structures_communes import BBox
from src.data.data_fetcher import fetch_terrain
from src.data.Elevation.structures_elevation import DEMType
from src.data.OverPass.raster_overpass import rasterize_bbox
from dataclasses import dataclass
from src.cost_model.cost_grid import build_cost_grid

"""
classe permettant de preconfigure des zones.
"""
@dataclass
class LocationConfig:
    name: str
    bbox: BBox
    demtype: DEMType = DEMType.COP30
    marker: tuple[int, int] | None = None   # (row, col) pixel
    marker_label: str = ""
"""

bbox
: 
{sud: 47.59122307928162, ouest: -70.67358112335206, nord: 47.635248770310454, est: -70.6141176223755}
end
: 
{lat: 47.62409936387735, lng: -70.62526702880861}
start
: 
{lat: 47.602372485714724, lng: -70.66243171691896}
"""
ORFORD = LocationConfig(
    name="Mont Orford",
    bbox=BBox(45.1, -72.4, 45.5, -71.9),
    marker=(677, 570),
    marker_label="Sommet Mont Orford (853 m)"
)

ORFORD_ZOOM = LocationConfig(
    name="Mont Orford (zoom)",
    # centre sur le sommet du mont Orford (45.3131, -72.2153), ~5 km x 5 km
    bbox=BBox(45.2911, -72.2551, 45.3351, -72.1755),
    marker=None,
    marker_label="Sommet Mont Orford (853 m)"
)

GROSMORNE = LocationConfig(
    name="Gros Morne National Park",
    bbox=BBox(49.2391, -58.3236, 50.16088765239024, -57.1453),
    marker=None,
    marker_label="none"
)


EVEREST = LocationConfig(
    name="Mont Everest",
    bbox=BBox(27.6294397, 86.0995530, 28.7010582, 87.9116620),
    marker=None,
    marker_label="Sommet Mont Everest"
)

FORILLONS = LocationConfig(
    name = "forillons",
    bbox=BBox(48.721568566681285, -64.32749176025392, 48.88373483101803, -64.13426971435548),
    marker=None,
    marker_label="rien for now"
)

MARAIS = LocationConfig(
    name="Marais",
    bbox=BBox(45.3659329263845, -71.80221496107276, 45.39353272377899, -71.7748886537344),
    marker=None,
    marker_label="Marais a l'est de Sherbrooke"
)

VC = LocationConfig(
    name="vc",
    bbox=BBox(46.92034491685944, -71.56540489196779, 46.94197142783448, -71.51898765563966),
    marker=None,
    marker_label=""
)

VALCATRAZ = LocationConfig(
    name="Valcatraz",
    bbox=BBox(46.915622079120794, -71.62660217285158, 46.94282542217977, -71.56688117980958),
    marker=None,
    marker_label=""
)

VALCATRAZ2 = LocationConfig(
    name="Valcatraz2",
    bbox=BBox(46.89409472613639, -71.64751731147682, 47.00756569360364, -71.48491965522682),
    marker=None,
    marker_label=""
)

COTOPAXI = LocationConfig(
    name="Cotopaxi",
    bbox=BBox(-0.7326320885029514, -78.48263740539552, -0.6328157849265642, -78.36908340454103),
    marker=None,
    marker_label="Volcan Cotopaxi"
    )

MTSTJOSEPH = LocationConfig(
    name="Sentier_du_Mont_SaintJoseph",
    bbox=BBox(45.3702179, -71.9385714, 45.3864681, -71.9002343),
    marker=None,
    marker_label="Sentier_du_Mont_SaintJoseph"
)

UDES = LocationConfig(
    name="UdeS",
    bbox=BBox(45.3702179, -71.9385714, 45.3864681, -71.9002343),
    marker=None,
    marker_label="uds"
)

SHERB = LocationConfig(
    name="sherb",
    bbox=BBox(45.35114175704128, -71.81687164306642, 45.41501066311106,-71.75040435791017),
    marker_label="none"

)

"""MONTAGNE = LocationConfig(
    name="montagne",

)"""

DEBUG = LocationConfig(
    name="debug",
    bbox=BBox(45.3646,-71.9019, 45.3736, -71.8929),
    marker=None,
    marker_label = "none"
)
#liste des panels actifs
PANELS = ["dem", "slope", "osm", "cost"]

# Categories (ordre : les premieres sont ecrasees par les suivantes)
CATEGORIES = [
    ("terrain",        ["peak","cliff","ridge","valley","arete","scree","bare_rock","border"],
                        (0.6, 0.4, 0.2)),   # brun
    ("glacier",        ["glacier"],
                        (0.8, 0.95, 1.0)),  # bleu glacé
    ("vegetation",     ["vegetation","wetland"],
                        (0.2, 0.7, 0.2)),   # vert
    ("eau",            ["water","water_crossing","bridge","ford"],
                        (0.2, 0.5, 0.9)),   # bleu
    ("infrastructure", ["trail","road"],
                        (1.0, 0.0, 0.6)),  # magenta
]


# ===== construction de l'image RGB pour l'OSM =============
# Fond : gris pour les cellules vides
def build_osm_rgb(osm, categories=CATEGORIES):
    h, w = osm.shape
    rgb = np.full((h, w, 3), 0.70)
    for _label, fields, color in categories:
        mask = np.zeros((h, w), dtype=bool)
        for field in fields:
            mask |= osm[field]
        rgb[mask] = color
    return rgb

def plot_panel(ax, fig, dem, osm, panel, location, categories=CATEGORIES, osm_mult=None):
    if panel == "dem":
        im = ax.imshow(dem.array, cmap="terrain")
        ax.set_title("DEM - Elevation (m)")
        fig.colorbar(im, ax=ax, label="Élévation (m)", fraction=0.03)

    elif panel == "slope":
        im = ax.imshow(np.degrees(dem.slope), cmap="RdYlGn_r")
        ax.set_title("Pente (degrees)")
        fig.colorbar(im, ax=ax, label="Pente (°)", fraction=0.03)

    elif panel == "osm":
        ax.imshow(build_osm_rgb(osm, categories))
        ax.set_title("OSM - Features")
        patches = [mpatches.Patch(color=(0.70,)*3, label="vide")]
        patches += [mpatches.Patch(color=c, label=lbl) for lbl, _, c in categories]
        ax.legend(handles=patches, loc="lower right", fontsize=8)

    elif panel == "cost":
        cost = build_cost_grid(dem, osm, HIKING_WEIGHTS, osm_mult=osm_mult)
        cost_display = np.where(np.isinf(cost), np.nan, cost)  # inf → nan (gris)

        # Échelle log : le coût couvre maintenant ~3 ordres de grandeur
        # (Dalton monte à ×12 en haute altitude, les poids OSM multiplient
        # encore). Une échelle linéaire figée à 0–3 saturerait tout le haut
        # de la montagne en rouge uniforme, sans aucun contraste.
        # Percentiles 1/99 pour ignorer les outliers de bordure.
        finis = cost_display[np.isfinite(cost_display)]
        if finis.size and finis.max() > finis.min() > 0:
            norm = LogNorm(vmin=np.percentile(finis, 1), vmax=np.percentile(finis, 99))
            im = ax.imshow(cost_display, cmap="RdYlGn_r", norm=norm)
            ax.set_title("Modèle de coût (échelle log)")
            fig.colorbar(im, ax=ax, label="Coût (h / cellule, log)", fraction=0.03)
        else:  # grille dégénérée (tout NaN, ou coût constant) : log impossible
            im = ax.imshow(cost_display, cmap="RdYlGn_r")
            ax.set_title("Modèle de coût")
            fig.colorbar(im, ax=ax, label="Coût (h / cellule)", fraction=0.03)

    if location.marker:
        row, col = location.marker
        ax.plot(col, row, 'r+', markersize=14, markeredgewidth=2,
                label=location.marker_label)
        ax.legend(loc="upper right", fontsize=8)

def run_comparison(location, panels=PANELS, categories=CATEGORIES,
                   output_path="exports/visual_comparison.png"):
    print(f"Chargement DATA - {location.name}...")
    bbox_0 = location.bbox
    fetch_terrain(bbox_0)

    dem = bbox_0.dem_data
    total = dem.array.size
    nan_count = int(np.isnan(dem.array).sum())
    valid = total - nan_count
    print(f"[DEM DEBUG] shape={dem.array.shape}  NaN={nan_count}/{total} ({nan_count/total:.0%})")
    if valid > 0:
        print(f"[DEM DEBUG] elevation min={np.nanmin(dem.array):.1f}m  max={np.nanmax(dem.array):.1f}m")
    else:
        print("[DEM DEBUG] TOUTES les valeurs sont NaN — l'array est vide")

    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    fig.suptitle(f"Comparaison — {location.name}", fontsize=14)

    for ax, panel in zip(axes.flatten(), panels):
        plot_panel(ax, fig, bbox_0.dem_data, bbox_0.raster_osm, panel, location, categories, osm_mult=bbox_0.osm_mult)

    for ax in axes.flatten()[len(panels):]:  # cacher les axes vides si < 4 panels
        ax.set_visible(False)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Sauvegardé -> {output_path}")
    plt.show()

if __name__ == "__main__":
    run_comparison(
        location=UDES,
        panels=PANELS,
        categories=CATEGORIES,
        output_path="exports/visual_comparison.png"
    )

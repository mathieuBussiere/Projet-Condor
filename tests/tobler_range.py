"""
Script standalone pour visualiser la fonction de vitesse Tobler et
la distribution réelle des pentes signées (celles que franchit l'A*)
dans une bounding box.
Lancer avec : python tests/tobler_range.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from src.data.structures_communes import BBox
from src.data.data_fetcher import fetch_terrain
from src.cost_model.cost_grid import _vitesse_tobler, _DIMENSION_CELL
from src.cost_model.physique import CELL_SIZE_M, CELL_DIAG_M


VALCATRAZ = BBox(46.915622079120794, -71.62660217285158, 46.94282542217977, -71.56688117980958)

BBOX = VALCATRAZ
NOM  = "Valcatraz"


def pentes_signees(dem_array: np.ndarray) -> np.ndarray:
    """
    args :
        dem_array : raster d'altitudes (m)

    return :
        array 1d des pentes signees (ratio dz/dist) de toutes les aretes

    Reproduit ce que calcule l'A* dans cout_arrete (routage/a_star.py) :
    difference d'altitude entre deux cellules voisines divisee par la
    distance reellement parcourue, 30 m en orthogonal et 42.426 m en
    diagonal. Le signe distingue montee et descente, contrairement a
    dem_data.slope qui est une magnitude (sqrt de somme de carres, donc
    toujours >= 0) et ne peut pas illustrer l'asymetrie de Tobler.

    Chaque arete est comptee dans ses deux sens, parce que l'A* peut la
    franchir dans les deux : la distribution est donc symetrique par
    construction. C'est voulu - ce sont les COUTS lus sur cette plage qui
    sont asymetriques, pas les pentes disponibles.
    """
    aretes = [
        (dem_array[:, 1:]   - dem_array[:, :-1],   CELL_SIZE_M),  # est-ouest
        (dem_array[1:, :]   - dem_array[:-1, :],   CELL_SIZE_M),  # nord-sud
        (dem_array[1:, 1:]  - dem_array[:-1, :-1], CELL_DIAG_M),  # diagonale \
        (dem_array[1:, :-1] - dem_array[:-1, 1:],  CELL_DIAG_M),  # diagonale /
    ]
    pentes = np.concatenate([(dz / dist).ravel() for dz, dist in aretes])
    pentes = pentes[~np.isnan(pentes)]
    return np.concatenate([pentes, -pentes])


def main():
    print(f"Chargement DEM - {NOM}...")
    fetch_terrain(BBOX)

    s_flat = pentes_signees(BBOX.dem_data.array)

    print(f"\n--- Distribution des pentes signees dans {NOM} ---")
    print(f"  min      : {s_flat.min():+.4f}  ({s_flat.min()*100:+.1f}%)")
    print(f"  max      : {s_flat.max():+.4f}  ({s_flat.max()*100:+.1f}%)")
    print(f"  p5 / p95 : {np.percentile(s_flat, 5)*100:+.1f}% / {np.percentile(s_flat, 95)*100:+.1f}%")
    print(f"  mediane de |s| : {np.median(np.abs(s_flat))*100:.1f}%")
    print(f"  aretes   : {len(s_flat)} (chacune comptee dans ses 2 sens)")

    s_range  = np.linspace(-1.0, 1.0, 500)
    vitesses = _vitesse_tobler(np.arctan(s_range))
    couts    = _DIMENSION_CELL / vitesses * 60
    s_opt    = -0.05

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    ax = axes[0]
    ax.plot(s_range * 100, vitesses, color="steelblue")
    ax.axvline(s_opt * 100, color="red", linestyle="--", label=f"optimum s={s_opt}")
    ax.axvline(s_flat.min() * 100, color="green", linestyle=":", label=f"min bbox")
    ax.axvline(s_flat.max() * 100, color="orange", linestyle=":", label=f"max bbox")
    ax.set_xlabel("s (%, rise/run × 100)")
    ax.set_ylabel("Vitesse (km/h)")
    ax.set_title("Tobler — vitesse vs pente")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    ax.hist(s_flat * 100, bins=80, color="steelblue", alpha=0.75)
    ax.axvline(s_opt * 100, color="red", linestyle="--", label="optimum")
    ax.set_xlabel("s (%, rise/run × 100)")
    ax.set_ylabel("Nombre d'arêtes")
    ax.set_title(f"Distribution des pentes signées - {NOM}")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    ax = axes[2]
    ax.plot(s_range * 100, couts, color="darkorange")
    ax.axvline(s_opt * 100, color="red", linestyle="--", label="optimum")
    ax.axvline(s_flat.min() * 100, color="green", linestyle=":", label="min bbox")
    ax.axvline(s_flat.max() * 100, color="orange", linestyle=":", label="max bbox")
    ax.set_xlabel("s (%, rise/run × 100)")
    ax.set_ylabel("Coût (min / cellule 30m)")
    ax.set_title("Coût de traversée par cellule")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.suptitle(f"Tobler - range de s ({NOM})", fontsize=12)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()

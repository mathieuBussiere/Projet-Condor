"""
fichier d'implementation de la grille de cout .

probablement le fichier le plus importants du projet.

on veut ici utiliser le data recolter des sources pour construire une grille de cout de traverse.

l'idee est la suivante : 
    1.le cout de base = temps pour traverser une cellule (30mx30m) a la vitesse donnee par la "Toblers hiking function"
    2.multiplicateurs de terrain modulaires

    cost d'une cellule = base_cost * multiplicateurs
"""
import numpy as np
from  src.data.structures_communes import BBox
from src.data.Elevation.structures_elevation import DEMdata
from src.data.structures_communes import latlon_to_rowcol_affine, rowcol_to_latlon
from .weights import DEFAULT_WEIGHTS, _SUPPRESSED_BY, build_weights
# Physique du cout (Tobler + altitude) : source de verite unique, partagee
# avec routage.a_star pour que la carte de cout affichee corresponde a ce
# que le routage calcule reellement. Voir physique.py.
from .physique import (
    CELL_SIZE_KM,
    cout_traverse_grille,
    difficulte_altitude_grille,
    vitesse_tobler_grille,
)

_DIMENSION_CELL = CELL_SIZE_KM  # 30m en km, meme unite que vitesse tobler (km/h) -> resultat en heures


# les None en ce moment sont pour les tests
def build_cost_grid(dem: DEMdata,
                    osm: np.ndarray|None,
                    weights: dict[str, float]|None,
                    osm_mult: np.ndarray|None = None,
                    ) -> np.ndarray:
    # base cost
    base = _vitesse_cost_grid(dem.slope)
    # debug
    row, col = np.unravel_index(np.argmax(base), base.shape)
    #print(f"\n Tobler max : {base[row, col]}\n pos : {row}, {col}")

    # facteur elevation : meme fonction que le routage (loi de Dalton).
    # Pas de garde-fou sur un seuil ici : contrairement a l'ancien modele
    # lineaire, Dalton est continu et mord des les basses altitudes. Le
    # garde-fou `np.max(dem.array) > 2500` etait de toute facon casse : un
    # seul NaN dans le DEM rend np.max NaN, et NaN > 2500 vaut False, donc
    # le multiplicateur sautait silencieusement.
    base = base * difficulte_altitude_grille(dem.array)

    # multiplicateurs selon les features osm
    if osm_mult is not None:
        return base * osm_mult
    elif osm is not None and weights is not None:
        multiplicateurs = _compute_multiplicateurs(osm, weights)
        final_cost = base * multiplicateurs

        # debug
        masked = np.where(np.isinf(final_cost), -np.inf, final_cost)
        row, col = np.unravel_index(np.argmax(masked), final_cost.shape)
        #print(f"\n final max : {final_cost[row, col]}\n pos : {row, col}")

        return final_cost
    else :
        return base

def _vitesse_tobler(slope_rad : float) -> float:
    """
    Tobler's hiking function :
        formule exponentielle develope par Waldo Tobler en 1993.
        elle sert a estimer la vitesse de marche d'un humain sur une pente.
        Formule -> W = 6 * exp(-3.5 * |S + 0.05|)
        W = vitesse en km/h
        S = slope(vertical rise/horizontal distance)
        exp() = fonction exponentielle

        slope optimale -> la fonction demontre que la slope optimale est -5%

    Delegue a physique.vitesse_tobler_grille (source de verite unique).
    Attention : contrairement a l'ancienne version locale, la vitesse est
    desormais bornee par un plancher (0.1 km/h), ce qui borne le cout d'une
    cellule a 0.3 h au lieu de le laisser exploser en terrain vertical.
    """
    return vitesse_tobler_grille(slope_rad)


def _vitesse_cost_grid(slope_rad : np.ndarray) -> np.ndarray:
    """cost = distance/vitesse = 30m/vitesse de tobler"""
    return cout_traverse_grille(slope_rad)

def _compute_multiplicateurs(osm : np.ndarray, weights : dict[str, float])-> np.ndarray:
    # set le grid to 1.0
    multiplicateurs = np.ones(osm.shape, dtype=float)

    for feature, weight in weights.items():
        if feature not in osm.dtype.names:
            continue
        actif = osm[feature]
        # eviter conflits (ex : un pont rend une cellule avec water franchissable)
        if feature in _SUPPRESSED_BY:
            for override in _SUPPRESSED_BY[feature]:
                actif = actif & ~osm[override] # masque les cellules overriden
        multiplicateurs[actif] *= weight
    
    # debug
    masked = np.where(np.isinf(multiplicateurs), -np.inf, multiplicateurs)
    row, col = np.unravel_index(np.argmax(masked), multiplicateurs.shape)
    #print(f"\n max multi (sans inf) : {multiplicateurs[row, col]}\n pos : {row, col}")
    return multiplicateurs


def _multiplicateur_elevation(elevation: np.ndarray) -> np.ndarray:
    """
    Conserve comme alias retro-compatible. L'ancien modele lineaire
    (seuil 2500 m, +0.02 %/m) est remplace par la loi de Dalton, la meme
    que celle utilisee par le routage : voir physique.difficulte_altitude.
    """
    return difficulte_altitude_grille(elevation)


def build_multiplicateurs_osm(raster_osm : np.ndarray, weights : dict[str, float]) -> np.ndarray:
    if raster_osm is None or weights is None:
        return np.ones_like(raster_osm, dtype=float) if raster_osm is not None else None
    return _compute_multiplicateurs(raster_osm, weights)



"""
Physique commune du modele de cout : Tobler (pente -> vitesse) et
altitude (rarefaction de l'O2 -> multiplicateur de difficulte).

Source de verite unique. Avant ce module, Tobler etait reimplemente a
5 endroits avec des semantiques divergentes (avec ou sans plancher de
vitesse), ce qui faisait que le scoring des chemins (calculer_cout_tobler)
n'utilisait pas la meme physique que le routage qui les avait produits.

Deux familles d'API, parce que les deux consommateurs ont des contraintes
opposees :
  - scalaire (math)  -> routage.a_star, appele par voisin dans la boucle
                        chaude ; math.exp est ~3.5x plus rapide que np.exp
                        sur un scalaire.
  - vectorisee (numpy) -> cost_model.cost_grid, applique sur la grille entiere.

Unites : pente en ratio (dz/dist) ou en radians selon la fonction, vitesse
en km/h, altitude en metres, cout en heures.
"""
import math

import numpy as np

# --- Geometrie de la grille ---
CELL_SIZE_M = 30.0
CELL_DIAG_M = 42.426  # diagonale d'une cellule 30x30
CELL_SIZE_KM = CELL_SIZE_M / 1000.0  # meme unite que la vitesse Tobler (km/h) -> cout en heures

# --- Tobler's hiking function ---
# W = 6 * exp(-3.5 * |S + 0.05|), Waldo Tobler 1993.
# W = vitesse (km/h), S = pente en ratio (rise/run). L'optimum est a S = -5%.
VITESSE_MAX_KMH = 6.0
PENTE_OPTIMALE = -0.05
# Plancher de vitesse : borne le cout d'une cellule a CELL_SIZE_KM / 0.1 = 0.3 h.
# Sans lui, la vitesse tend vers 0 quand la pente explose et le cout aussi. 
# L'infranchissable s'exprime déja avec osm_mult = inf
PLANCHER_VITESSE_KMH = 0.1

# Constante nécéssaire au calcul d,altitude -> difficulte ---
_P0 = 760.0       # pression au niveau de la mer (mmHg)
_FIO2 = 0.209     # fraction d'O2 dans l'air inspire
_PH2O = 47.0      # pression de vapeur d'eau des voies aeriennes (mmHg, quasi constante)
_H_BARO = 8000.0  # hauteur d'echelle de l'atmosphere (m)
DURETE_ALT = 2.0  # levier de tuning : 1 = Dalton pur (trop clement), 2 = ressenti haute altitude
_PIO2_MER = _FIO2 * (_P0 - _PH2O)  # PiO2 au niveau de la mer ~= 149 mmHg


def vitesse_tobler_ratio(slope_ratio: float) -> float:
    """Vitesse de marche (km/h). Entree : pente en ratio dz/dist (0.12 = 12%)."""
    return max(
        VITESSE_MAX_KMH * math.exp(-3.5 * abs(slope_ratio - PENTE_OPTIMALE)),
        PLANCHER_VITESSE_KMH,
    )


def vitesse_tobler_radians(slope_rad: float) -> float:
    """Vitesse de marche (km/h). Entree : pente en radians (depuis dem.slope)."""
    return vitesse_tobler_ratio(math.tan(slope_rad))


def vitesse_tobler_grille(slope_rad: np.ndarray) -> np.ndarray:
    """Vitesse de marche (km/h) sur une grille. Entree : pentes en radians."""
    s = np.tan(slope_rad)
    return np.maximum(
        VITESSE_MAX_KMH * np.exp(-3.5 * np.abs(s - PENTE_OPTIMALE)),
        PLANCHER_VITESSE_KMH,
    )


def cout_traverse_grille(slope_rad: np.ndarray) -> np.ndarray:
    """Cout de base (heures) pour traverser une cellule, sur une grille."""
    return CELL_SIZE_KM / vitesse_tobler_grille(slope_rad)


def difficulte_altitude(altitude_m: float, durete: float = DURETE_ALT) -> float:
    """
    Multiplicateur de difficulte du au manque d'oxygene en altitude.

    Modelise le mal aigu des montagnes via la chaine physique :
      - loi barometrique : Pb(h) = P0 * exp(-h / H)   -> pression totale
      - loi de Dalton    : PiO2 = FiO2 * (Pb - PH2O)  -> pression partielle
                                                         d'O2 inspire
      - multiplicateur   : (PiO2 au niveau de la mer / PiO2 a l'altitude) ** durete

    `durete` est le levier de game design : 1 correspond au Dalton pur
    (physiquement exact mais trop clement), 2 assume une difficulte jugee arbitrairement plus aproprie

    Continue et sans seuil
    Valeurs de controle (durete=2) :
        0 m -> 1.00, 2500 m -> 1.96, 5500 m -> 4.53,
        8000 m -> 9.40, 8848 m -> 12.16.
    """
    pb = _P0 * math.exp(-altitude_m / _H_BARO)
    pio2 = _FIO2 * max(pb - _PH2O, 1e-6)  # ~23 000 m, Pb - PH2O passe negatif
    return (_PIO2_MER / pio2) ** durete


def difficulte_altitude_grille(elevation_m: np.ndarray, durete: float = DURETE_ALT) -> np.ndarray:
    """
    Version vectorisee de difficulte_altitude, sur une grille d'elevations.
    Les NaN du DEM se propagent en NaN (cellule sans donnee).
    """
    pb = _P0 * np.exp(-elevation_m / _H_BARO)
    pio2 = _FIO2 * np.maximum(pb - _PH2O, 1e-6)
    return (_PIO2_MER / pio2) ** durete

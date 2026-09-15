"""
Tests de la physique du modele de cout (cost_model/physique.py).

Verrouille les invariants qui ont justifie l'extraction du module :
Tobler etait reimplemente a 5 endroits avec des semantiques divergentes
(avec/sans plancher de vitesse, en ratio ou en radians), et l'altitude
avait deux modeles incompatibles (Dalton pour le routage, lineaire pour
la grille de cout). Ces tests echouent si les implementations redivergent.

Fonctions pures : aucun reseau, aucune fixture.
"""
import math

import numpy as np
import pytest

from cost_model.physique import (
    CELL_SIZE_KM,
    DURETE_ALT,
    PENTE_OPTIMALE,
    PLANCHER_VITESSE_KMH,
    VITESSE_MAX_KMH,
    cout_traverse_grille,
    difficulte_altitude,
    difficulte_altitude_grille,
    vitesse_tobler_grille,
    vitesse_tobler_radians,
    vitesse_tobler_ratio,
)

# Pentes en ratio (dz/dist) couvrant descente raide -> montee raide.
_PENTES = (-0.8, -0.5, -0.05, 0.0, 0.12, 0.3, 0.7)


# ---------------------------------------------------------------- Tobler

@pytest.mark.parametrize("s", _PENTES)
def test_ratio_et_radians_coherents(s):
    """
    Le piege historique : cost_grid travaillait en radians (avec np.tan),
    a_star en ratio dz/dist. Les deux doivent decrire la meme physique,
    donc ratio(x) == radians(atan(x)).
    """
    assert vitesse_tobler_ratio(s) == pytest.approx(vitesse_tobler_radians(math.atan(s)))


def test_scalaire_et_vectorise_coherents():
    """La version numpy (cost_grid) doit coller a la version math (a_star)."""
    rads = np.arctan(np.array(_PENTES))
    attendu = [vitesse_tobler_radians(r) for r in rads]
    assert vitesse_tobler_grille(rads) == pytest.approx(attendu)


@pytest.mark.parametrize("s", _PENTES)
def test_formule_historique_preservee(s):
    """
    Hors plancher, on doit retrouver exactement la formule de Tobler 1993 :
    W = 6 * exp(-3.5 * |S + 0.05|).
    """
    attendu = VITESSE_MAX_KMH * math.exp(-3.5 * abs(s + 0.05))
    if attendu < PLANCHER_VITESSE_KMH:
        pytest.skip("le plancher mord, la formule brute ne s'applique plus")
    assert vitesse_tobler_ratio(s) == pytest.approx(attendu)


def test_optimum_a_moins_5_pourcent():
    """Tobler demontre que la vitesse est maximale a -5% de pente."""
    assert vitesse_tobler_ratio(PENTE_OPTIMALE) == pytest.approx(VITESSE_MAX_KMH)
    for s in (-0.3, -0.2, -0.1, 0.0, 0.1, 0.2):
        assert vitesse_tobler_ratio(s) <= vitesse_tobler_ratio(PENTE_OPTIMALE)


@pytest.mark.parametrize("s", (5.0, 22.6, 100.0))
def test_plancher_borne_le_cout_en_terrain_vertical(s):
    """
    Sans plancher, la vitesse tend vers 0 et le cout d'une cellule explose
    (~1e32 h sur une falaise), ce qui noyait les couts reels dans du bruit
    numerique. L'infranchissable se dit avec osm_mult = inf, pas comme ca.
    """
    assert vitesse_tobler_ratio(s) == pytest.approx(PLANCHER_VITESSE_KMH)
    cout_max = CELL_SIZE_KM / PLANCHER_VITESSE_KMH
    assert cout_traverse_grille(np.arctan(np.array([s])))[0] == pytest.approx(cout_max)
    assert cout_max == pytest.approx(0.3)


#  Altitude

# Valeurs de reference de la chaine loi barometrique -> loi de Dalton, a durete=2.
_CONTROLE_DALTON = [(0, 1.00), (2500, 1.96), (5500, 4.53), (8000, 9.40), (8848, 12.16)]


@pytest.mark.parametrize("altitude_m, attendu", _CONTROLE_DALTON)
def test_valeurs_de_controle_dalton(altitude_m, attendu):
    assert difficulte_altitude(altitude_m) == pytest.approx(attendu, abs=0.01)


def test_niveau_de_la_mer_est_neutre():
    assert difficulte_altitude(0.0) == pytest.approx(1.0)


def test_croissance_stricte_avec_altitude():
    altitudes = [0, 500, 1000, 2500, 4000, 5500, 7000, 8848]
    valeurs = [difficulte_altitude(h) for h in altitudes]
    assert valeurs == sorted(valeurs)
    assert len(set(valeurs)) == len(valeurs)


def test_dalton_scalaire_et_vectorise_coherents():
    hs = np.array([float(h) for h, _ in _CONTROLE_DALTON])
    attendu = [difficulte_altitude(h) for h in hs]
    assert difficulte_altitude_grille(hs) == pytest.approx(attendu)


def test_nan_du_dem_se_propage():
    """Une cellule sans donnee doit rester sans donnee, pas devenir 1.0."""
    res = difficulte_altitude_grille(np.array([np.nan, 2500.0]))
    assert np.isnan(res[0])
    assert res[1] == pytest.approx(1.96, abs=0.01)


def test_un_nan_ne_contamine_pas_les_autres_cellules():
    """
    Regression : le garde-fou `np.max(dem.array) > 2500` de cost_grid rendait
    NaN des qu'un seul trou existait dans le DEM, et `NaN > 2500` etant False,
    la penalite d'altitude sautait sur TOUTE la grille.
    """
    res = difficulte_altitude_grille(np.array([np.nan, 8848.0, 0.0]))
    assert res[1] == pytest.approx(12.16, abs=0.01)
    assert res[2] == pytest.approx(1.0)


def test_durete_1_donne_le_dalton_pur():
    """A durete=1, l'Everest ne coute que ~3.5x : exact, mais trop clement."""
    assert difficulte_altitude(8848, durete=1.0) == pytest.approx(3.49, abs=0.02)


def test_durete_est_bien_un_exposant():
    for h in (2500, 5500, 8848):
        pur = difficulte_altitude(h, durete=1.0)
        assert difficulte_altitude(h, durete=DURETE_ALT) == pytest.approx(pur ** DURETE_ALT)


def test_tres_haute_altitude_ne_casse_pas():
    """
    Au-dela de ~23 000 m, Pb - PH2O passe negatif et la formule cassait
    (racine d'un negatif / division par zero). Hors des elevations
    terrestres, mais la fonction ne doit pas exploser.
    """
    for h in (19_000, 25_000, 100_000):
        v = difficulte_altitude(h)
        assert math.isfinite(v) and v > 0
    assert np.all(np.isfinite(difficulte_altitude_grille(np.array([19e3, 25e3, 1e5]))))


# Coherence routage / viz

def test_routage_et_grille_de_cout_partagent_la_meme_physique():
    """
    on verifie que la grille de cout dans comparaison visuelle fait les mêmes calculs que a_star
    """
    from cost_model.cost_grid import _multiplicateur_elevation, _vitesse_tobler
    from routage.a_star import difficulte_altitude as dalton_routage

    for h in (0.0, 1200.0, 2500.0, 5500.0, 8848.0):
        assert _multiplicateur_elevation(np.array([h]))[0] == pytest.approx(dalton_routage(h))

    rads = np.arctan(np.array(_PENTES))
    assert _vitesse_tobler(rads) == pytest.approx([vitesse_tobler_radians(r) for r in rads])

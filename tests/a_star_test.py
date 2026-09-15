"""
Test de l'algorithme A*
"""

import pytest
from data.structures_communes import BBox
from data.data_fetcher import fetch_terrain
from data.Elevation.structures_elevation import DEMType
from routage.a_star import RechercherMeilleurChemin
from data.structures_communes import latlon_to_rowcol_affine


# bounding box de test.
@pytest.fixture(scope="module")
def box():
    b = BBox(45.3550771, -72.0021626, 45.4356587, -71.8142473)
    fetch_terrain(b)
    return b

def test_Astar(box):
    depart = latlon_to_rowcol_affine(box.dem_data.transform, 45.38, -71.93)
    arrivee = latlon_to_rowcol_affine(box.dem_data.transform, 45.37, -71.92)
    chemin = RechercherMeilleurChemin(box.cost_grid, box.dem_data.transform, depart, arrivee)
    assert isinstance(chemin, list)
    assert len(chemin) > 0
"""
premier jet de fichier test pour opentopography API

autheur(s) : marc-emile scholer
date de creation : 08-05-26
"""
import numpy as np
import requests
from data.structures_communes import BBox
from data.Elevation.structures_elevation import DEMType, DEMdata
from data.Elevation.parser_elevation import parse_dem_data, elevation_at, max_elevation
import data.Elevation.client_opentopography as client
import pytest

# zone autour du sommet du mont orford
_BOX2 = BBox(45.1,-72.4,45.5,-71.9)

# coordonnees du sommet du mont orford (source: OSM lat=45.3118401 lon=-72.2417821)
_SOMMET_LAT = 45.3118401
_SOMMET_LON = -72.2417821

# elevation du sommet est 853, 
# mais on peut donner du jeu a l'algo un peu pour l'instant
_ELEVATION_ORFORD = 840

# 1 seul call API, you learn something everyday
@pytest.fixture(scope="module")
def dem_bytes():
    return client.get_dem(DEMType.COP30,_BOX2)

# parser le data 1 seule fois
@pytest.fixture(scope="module")
def dem_data(dem_bytes):
    return parse_dem_data(dem_bytes)
 
# verifier que l'ont recoit quelque chose
def test_get_bytes_from_dem(dem_bytes):
    assert isinstance(dem_bytes, bytes)
    assert len(dem_bytes) > 0

# tester le parser
def test_parse_dem(dem_data):
    assert isinstance(dem_data,DEMdata)
    print(f"ARRAY :\n{dem_data.array}\nTRANSFORM :\n {dem_data.transform}\n")

# get elevation au sommet
def test_get_elevation(dem_data):
    
    res = elevation_at(dem_data, _SOMMET_LAT, _SOMMET_LON)

    assert res > _ELEVATION_ORFORD

# test get max elevation dans une zone
def test_max_elevation(dem_data):

    res = max_elevation(dem_data.array)

    assert res > _ELEVATION_ORFORD

    print(f"{res}")

# tests de slope 
def test_slope_shape(dem_data):
    assert dem_data.array.shape == dem_data.slope.shape

def test_slope_range(dem_data):
    valid = dem_data.slope[~np.isnan(dem_data.slope)]
    assert np.all(valid >= 0.0)
    assert np.all(valid <= 90.0)


# tests d'aspects 
def test_aspect_shape(dem_data):
    assert dem_data.slope.shape == dem_data.aspect.shape

def test_aspect_range(dem_data):
    valid = dem_data.slope[~np.isnan(dem_data.slope)]
    assert np.all(valid >= 0.0)
    assert np.all(valid <= 360.0)


# ============================================================
# SONDE : trouver le vrai minimum de bbox accepte par OpenTopography
# appelle _fetch_from_api directement -> contourne le cache ET l'expansion
# de fetch_terrain (_MIN_BBOX_HALF_DEG). Lancer avec -s pour voir le tableau.
# ============================================================

# tailles totales de bbox (en degres) a tester, de la plus grande a la plus petite
# plancher mesure pour COP30 : ~0.0035 deg OK / 0.0030 deg KO (~12 px)
_PROBE_SIZES_DEG = [0.10, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001, 0.0005]


def _probe_bbox(size_deg: float) -> BBox:
    """bbox carree de cote size_deg centree sur le sommet du mont orford."""
    half = size_deg / 2
    return BBox(
        _SOMMET_LAT - half, _SOMMET_LON - half,
        _SOMMET_LAT + half, _SOMMET_LON + half,
    )


def test_probe_min_bbox_opentopography():
    """
    Fait varier la taille de bbox et reporte la plus petite acceptee par l'API.
    N'echoue jamais : c'est exploratoire. Resultats imprimes (pytest -s).
    """
    results = []
    smallest_ok = None
    for size in _PROBE_SIZES_DEG:
        bbox = _probe_bbox(size)
        try:
            data = client._fetch_from_api(DEMType.COP30, bbox)
            ok = isinstance(data, bytes) and len(data) > 0
            results.append((size, "OK" if ok else "VIDE", len(data) if ok else 0, ""))
            if ok:
                smallest_ok = size
        except requests.exceptions.HTTPError as e:
            code = getattr(e.response, "status_code", "?") if e.response is not None else "?"
            results.append((size, "HTTP", 0, f"{code}: {str(e)[:60]}"))
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError) as e:
            results.append((size, "RESEAU", 0, str(e)[:60]))

    print("\n\n=== Sonde minimum bbox OpenTopography (COP30, centre = mont Orford) ===")
    print(f"{'cote (deg)':>12} | {'~metres':>8} | {'statut':>6} | {'octets':>8} | detail")
    print("-" * 72)
    for size, statut, nbytes, detail in results:
        print(f"{size:>12.4f} | {size*111320:>8.0f} | {statut:>6} | {nbytes:>8} | {detail}")
    print(f"\n-> plus petite bbox acceptee : {smallest_ok} deg "
          f"({smallest_ok*111320:.0f} m de cote)" if smallest_ok else "\n-> aucune taille acceptee")
    print(f"-> seuil actuel _MIN_BBOX_HALF_DEG => bbox forcee a {2*0.05:.2f} deg de cote\n")





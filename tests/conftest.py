"""
fichier pour la configuration des fichiers de test
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
#add comment

import pytest
from data.structures_communes import BBox
from data.data_fetcher import fetch_terrain
from data.Elevation.structures_elevation import DEMType

# region mont orford
_BOX2 = BBox(45.1, -72.4, 45.5, -71.9)
# coordonnees du sommet du mont orford (source: OSM lat=45.3118401 lon=-72.2417821)
_SOMMET_ORF_LAT = 45.3118401
_SOMMET_ORF_LON = -72.2417821
# region Chimborazo

# region Himalaya (enorme)
_BOX3 = BBox(27.6294397, 86.0995530, 28.7010582, 87.9116620)
# coordonnees du sommet du Mont Everest (source: OSM)
_SOMMET_WORLD_LAT = 27.9881399
_SOMMET_WORLD_LON = 86.9249751

# region Jungle...

@pytest.fixture(scope="session")
def bbox():
    return _BOX3


@pytest.fixture(scope="session")
def terrain(bbox):
    print("\nChargement de la Bounding Box...\n")
    fetch_terrain(bbox)
    #print(f"\n\nICI transform----->>>>>\n{bbox.dem_data.transform}")
    return bbox


@pytest.fixture(scope="session")
def dem(terrain):
    #print(f"{terrain.dem_data}")
    return terrain.dem_data


@pytest.fixture(scope="session")
def raster_osm(terrain):
    return terrain.raster_osm

@pytest.fixture(scope="session")
def sommet():
    """Coordonnees (lat, lon) du sommet de reference pour les tests d'alignement."""
    return _SOMMET_WORLD_LAT, _SOMMET_WORLD_LON
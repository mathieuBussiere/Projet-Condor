"""
definitions et structures de classes, types et autre dans opentopography api

"""
from typing import NamedTuple
from enum import Enum
import numpy as np
import rasterio

class DEMType(Enum):
    """
    types de DEM (DIGITAL ELEVATION MODEL) disponibles via opentopography.
    """
    SRTMGL1 = "SRTMGL1"   # SRTM GL1 - 30m
    SRTMGL3 = "SRTMGL3"   # SRTM GL3 - 90m
    AW3D30  = "AW3D30"    # ALOS World 3D - 30m
    COP30   = "COP30"     # Copernicus DEM - 30m (main one en ce moment@)
    COP90   = "COP90"     # Copernicus DEM - 90m
    NASADEM = "NASADEM"   # NASA DEM - 30m

# classe pour contenir l'association d'un array 2D numpy d'elevation 
# + le transform pour recuperer les coordonnes d'une case donnes
class DEMdata(NamedTuple):
    # 2d array dans ce cas ci
    array : np.ndarray 
    # un transform qui preserve les lignes droite (contrairement a un transform qui peut les courber)
    transform : rasterio.transform.Affine 
    """
    le transforme entrepose 6 chiffres : 
    [pixel_width : combien de deg de lon un right step ajoute
    pixel_height : combien de deg de lat un down step ajoute
    top_left_lon : longitude du top left corner
    top_left_lat : latitude du top left corner
    row_rotation : changement de la latitude pendant le deplacemkent sur une range
    col_rotation : "miroir mais pour colonne", sont presque toujours de 0 parce que les dem sont alignes vers le nord]
    """
    # raster de la slope (radians)
    slope : np.ndarray

    aspect : np.ndarray
   
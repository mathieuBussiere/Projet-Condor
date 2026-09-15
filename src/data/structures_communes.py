"""
fichier de description des structures communes entre les api
"""
import rasterio.transform
from rasterio.transform import Affine
# module dataclass fournis automatiquement un constructeur, des methodes speciales de comparaison et d'impression
from dataclasses import dataclass, field
from .Elevation.structures_elevation import DEMdata
import numpy as np


"""
wrappers de la conversion rasterio, 
la raison est que la convention du projet est lat,lon pas lon,lat

P.S -> utilisez le TRANSFORM du dem_data de la bbox
"""
def rowcol_to_latlon(transform: Affine, row: int, col: int) -> tuple[float, float]:
    """convertit row, col en lat, lon centre de la cellule."""
    lon, lat = rasterio.transform.xy(transform, row, col)
    return float(lat), float(lon)

def latlon_to_rowcol_affine(transform: Affine, lat: float, lon: float) -> tuple[int, int]:
    """convertit lat, lon en row, col pour tout raster rasterio."""
    row, col = rasterio.transform.rowcol(transform, lon, lat)
    return int(row), int(col)


@dataclass
class BBox:
    """
    Bounding box (bbox) : notion importantes dans overpass
    delimite une zone : tuple[sud,ouest,nord,est]
    """
    sud: float
    ouest: float
    nord: float
    est: float

    # dem 
    dem_data: DEMdata | None = None

    # cache du geoJSON OSM de la bbox
    osm_features: dict[str, list] = field(
        default_factory=dict, # utilise un dict par bbox (default = partage)
        repr=False, # apparait pas lorsque print(bbox)
        compare=False) # compare compare seulement les grids, pas les features
    
    # raster osm de la bbox
    raster_osm : np.ndarray = field(
        default=None,
        repr=False,
        compare=False) 
    
    # multiplicateurs osm
    osm_mult : np.ndarray = field(default=None, 
                                  repr=False, 
                                  compare=False)
     
    # cost grid de la bbox
    cost_grid: np.ndarray =  field(
        default=None,
        repr=False,
        compare=False)
    
    

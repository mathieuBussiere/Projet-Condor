"""
Fichier de rasterization de overpass/openstreetmap.

on veut que la resolution du raster soit 30m pour imbriquer 1:1 avec le raster dem
la resolution du dem est a 30m -> taille des pixels = 1 arc-seconde ou 1/3600 degree
chaque cellule du raster est un osm_dtype avec des flags booleens pour represente les feature OSM.
"""
import numpy as np
import rasterio.features
import rasterio.transform
from rasterio.transform import Affine
from concurrent.futures import ThreadPoolExecutor, as_completed
from .structures_op import osm_dtype, _FEATURE_QUERIES, _FEATURE_FILTERS
from .queries_overpass import query_all_features
from . import client_overpass
from ..structures_communes import BBox

# resolution 1 arc-seconde
# 1 degre de latitude = 111 320m ish constant sur toute la planete
# -> 30 m = 1/3600 deg
# en longitude l'affaire se corce car la longueur varie sur la planete selon le cosinus de la latitude
# ce probleme sera interessant a surmonter + tard dans la grille de cout 
PIXEL_SIZE_DEG_LON = 1/3600
PIXEL_SIZE_DEG_LAT = 1/3600

# maximum de threads simultanee
MAX_WORKERS = 4



"""
RASTERISATION DE DATA OSM POUR UNE BBOX DONNE
RESOLUTION 30M
"""


"""
Etape 1 : calculer la grille raster a partir d'une bbox

defi : convertir une zone defini par 4 coordonnees decimales en array 2d numpy 
avec une resolution a 30m 
"""

def _create_raster_grid(shape: tuple[int, int]) -> np.ndarray:
    """
    cree un array vide aligne 1:1 avec le dem (1 arc-seconde) 
    a partir d'une bbox
    dtype = osm_dtype
    """
    return np.zeros(shape, dtype=osm_dtype)


"""
Etape 2 : remplir la grille raster

defi : verifier chaque element d'une bbox donnee et ajuster 
       le osm_dtype de la cellule correspondante a cet element

       c'est le bon moment de faire du parallelisme !!!!!!
"""

def _mark_feature(field: str,
                  feat_list: list,
                  transform,
                  n_rows: int,
                  n_cols: int) -> tuple[str, np.ndarray | None]:
    """
    calcule le masque rasterise pour un feature OSM.
    retourne (field, mask) sans toucher a la grille.
    """
    shapes = [feat["geometry"] for feat in feat_list if feat.get("geometry")]

    if not shapes:
        return field, None

    # all_touched=True requis pour les geometries Point (nodes OSM comme les peaks)
    mask = rasterio.features.rasterize(
        ((geom, 1) for geom in shapes),
        out_shape=(n_rows, n_cols),
        transform=transform,
        dtype=np.uint8,
        all_touched=True,
    )
    return field, mask.astype(bool)



def _fill_raster_grid(bbox: BBox, grid: np.ndarray, transform: Affine) -> None:
    # fetch une seule fois le geoJSON de la bbox, sinon reutilise le cache si deja present
    if not bbox.osm_features:
        data = client_overpass.get_data(query_all_features(), bbox=bbox, response_format="geojson")
        all_feats = data.get("features", [])
        bbox.osm_features = {
            field: [f for f in all_feats
                    if f.get("geometry") and filter_fn(
                        (f.get("properties") or {}).get("tags") or {}
                    )]
                    for field, filter_fn in _FEATURE_FILTERS.items()
        }

    n_rows, n_cols = grid.shape

    # phase 1 (parallel) : rasterize chaque feature independamment, sans toucher la grille
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_mark_feature, field, shapes, transform, n_rows, n_cols): field
            for field, shapes in bbox.osm_features.items()
        }
        # phase 2 (serie) : as_completed est itere dans le main thread
        # les |= sont en serie, chaque masque est libere des qu'il est applique
        for future in as_completed(futures):
            field = futures[future]
            try:
                _, mask = future.result()
                if mask is not None:
                    grid[field] |= mask
            except Exception as e:
                print(f"[raster_overpass] {field}: {e}")


# la fonction culminante !!!!
# prend une BBox et rasterise son contenu !!!!!!
def rasterize_bbox(bbox: BBox) -> np.ndarray:
    transform = bbox.dem_data.transform
    shape = bbox.dem_data.array.shape[:2]
    grid = _create_raster_grid(shape)
    _fill_raster_grid(bbox, grid, transform)
    return grid



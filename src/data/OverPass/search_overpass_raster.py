"""
Fonctions de recherche dans un raster OSM deja rasterise.
Necessite que bbox.osm_features soit rempli (via rasterize_bbox ou fill_raster_grid).
"""
import numpy as np
import rasterio.features
import rasterio.transform
from .structures_op import osm_dtype
from ..structures_communes import BBox
from .raster_overpass import PIXEL_SIZE_DEG_LAT, PIXEL_SIZE_DEG_LON
from ..structures_communes import latlon_to_rowcol_affine


def row_to_lat(bbox: BBox, row: int) -> float:
    """latitude au centre de la cellule (row 0 = nord)"""
    return bbox.nord - row * PIXEL_SIZE_DEG_LAT


def col_to_lon(bbox: BBox, col: int) -> float:
    """longitude au centre de la cellule (col 0 = ouest)"""
    return bbox.ouest + col * PIXEL_SIZE_DEG_LON


def get_cell_names(bbox: BBox, row: int, col: int, field: str) -> list[str]:
    """
    retourne les noms (tag 'name' ou 'ref') des features OSM du champ `field`
    qui intersectent la cellule (row, col).
    """
    feats = (bbox.osm_features or {}).get(field, [])
    if not feats:
        return []

    cell_lat       = bbox.nord - row * PIXEL_SIZE_DEG_LAT
    cell_lon       = bbox.ouest + col * PIXEL_SIZE_DEG_LON
    lat_nord_cell  = cell_lat + 0.5 * PIXEL_SIZE_DEG_LAT
    lat_sud_cell   = cell_lat - 0.5 * PIXEL_SIZE_DEG_LAT
    lon_ouest_cell = cell_lon - 0.5 * PIXEL_SIZE_DEG_LON
    lon_est_cell   = cell_lon + 0.5 * PIXEL_SIZE_DEG_LON

    transform = rasterio.transform.from_bounds(
        lon_ouest_cell, lat_sud_cell, lon_est_cell, lat_nord_cell, 1, 1
    )

    names = []
    for feat in feats:
        geom = feat.get("geometry")
        if not geom:
            continue
        tags = (feat.get("properties") or {}).get("tags") or {}
        name = tags.get("name") or tags.get("ref")
        if not name:
            continue
        mask = rasterio.features.rasterize(
            [(geom, 1)], out_shape=(1, 1), transform=transform, dtype=np.uint8
        )
        if mask[0, 0]:
            names.append(name)

    return names


def get_field_names_in_bbox(bbox: BBox, field: str) -> list[str]:
    """retourne les noms de tous les features OSM du champ `field` dans la bbox."""
    feats = (bbox.osm_features or {}).get(field, [])
    names = []
    for feat in feats:
        tags = (feat.get("properties") or {}).get("tags") or {}
        name = tags.get("name") or tags.get("ref")
        if name:
            names.append(name)
    return names


def get_all_names_in_cell(bbox: BBox, row: int, col: int) -> dict[str, list[str]]:
    """get_cell_names() pour tous les fields d'une cellule."""
    res = {}
    for field in osm_dtype.names:
        names = get_cell_names(bbox, row, col, field)
        if names:
            res[field] = names
    return res

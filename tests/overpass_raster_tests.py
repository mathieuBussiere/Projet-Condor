"""
tests d'integration pour le raster OSM

autheur(s) : marc-emile scholer
date de creation : 13-05-26
"""
from data.OverPass.search_overpass_raster import (get_cell_names,
                                                  get_all_names_in_cell,
                                                  get_field_names_in_bbox)
from data.OverPass.structures_op import osm_dtype
from data.structures_communes import latlon_to_rowcol_affine

# verifier la taille de la grille
def test_raster_shape(raster_osm):
    n_rows, n_cols = raster_osm.shape
    assert n_rows > 0 and n_cols > 0
    print(f"shape: ({n_rows}, {n_cols})")


# verifier le contenu des cellules
def test_raster_dtype(raster_osm):
    assert raster_osm.dtype == osm_dtype


def test_peak_in_raster(raster_osm, bbox, dem, sommet):
    
    peaks = bbox.osm_features.get("peak", [])
    
    lat_sommet, lon_sommet = sommet
    # peak osm le plus pret du sommet de ref
    sommet_feat = min(peaks, key= lambda f: abs(f["geometry"]["coordinates"][1] - lat_sommet)
                                            + abs(f["geometry"]["coordinates"][0] - lon_sommet))
    osm_lon, osm_lat = sommet_feat["geometry"]["coordinates"]
    row, col = latlon_to_rowcol_affine(dem.transform, osm_lat, osm_lon)
    assert raster_osm[row, col]["peak"], f"peak attendu en ({row}, {col})"

def test_field_names_in_bbox(raster_osm, bbox):
    assert raster_osm is not None
    peaks = get_field_names_in_bbox(bbox, "peak")
    assert len(peaks) > 0, f"aucun peak nomme dans la bbox"


def test_print_names_at_sommet(raster_osm, bbox, dem, sommet):
    lat, lon = sommet
    row, col = latlon_to_rowcol_affine(dem.transform, lat, lon)
    print(f"PEAKS  : {get_cell_names(bbox, row, col, 'peak')}")
    print(f"ALL    : {get_all_names_in_cell(bbox, row, col)}")


    

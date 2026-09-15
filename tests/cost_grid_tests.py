"""
tests de la grille de couts
"""

import pytest
from data.structures_communes import rowcol_to_latlon, latlon_to_rowcol_affine
from cost_model.cost_grid import build_cost_grid
from cost_model.weights import DEFAULT_WEIGHTS

TOLERANCE = 0.5 / 3600  # demi-pixel (1 arc-seconde)

def test_rowcol_to_latlon_top_left(dem, bbox):
    """(0, 0) doit pointer vers le coin nord-ouest de la bbox."""
    lat, lon = rowcol_to_latlon(dem.transform, 0, 0)
    assert abs(lat - bbox.nord) < TOLERANCE, f"lat attendu ~{bbox.nord}, obtenu {lat}"
    assert abs(lon - bbox.ouest) < TOLERANCE, f"lon attendu ~{bbox.ouest}, obtenu {lon}"

def test_latlon_to_rowcol_top_left(dem, bbox):
    """Le coin nord-ouest doit mapper vers (0, 0)."""
    row, col = latlon_to_rowcol_affine(dem.transform, bbox.nord, bbox.ouest)
    assert row == 0, f"row attendu 0, obtenu {row}"
    assert col == 0, f"col attendu 0, obtenu {col}"

def test_round_trip(dem, bbox):
    """Aller-retour (row,col) -> (lat,lon) -> (row,col) doit etre stable."""
    row_in, col_in = 10, 15
    lat, lon = rowcol_to_latlon(dem.transform, row_in, col_in)
    row_out, col_out = latlon_to_rowcol_affine(dem.transform, lat, lon)
    assert row_out == row_in and col_out == col_in, "round-trip instable"

def test_grid(dem, raster_osm):
    print("\ndebut test_grid...\n")
    print(f"BASE GRID :\n {build_cost_grid(dem, None, None)}\n")
    print(f"WEIGHTED GRID :\n {build_cost_grid(dem, raster_osm, DEFAULT_WEIGHTS)}\n")


"""
fichier test d'alignement des raster DEM et OSM
"""
import rasterio.transform

from data.structures_communes import BBox
from data.OverPass.raster_overpass import PIXEL_SIZE_DEG_LAT, PIXEL_SIZE_DEG_LON
from data.structures_communes import latlon_to_rowcol_affine

def test_dem_resolution(dem):
    """resolution DEM doit etre 1/3600 deg"""
    assert abs(dem.transform.a - PIXEL_SIZE_DEG_LON) < 1e-6
    assert abs(abs(dem.transform.e) - PIXEL_SIZE_DEG_LAT) < 1e-6


def test_shape_match(raster_osm, dem):
    """OSM et DEM doivent avoir le meme shape"""
    assert raster_osm.shape == dem.array.shape, (
        f"OSM {raster_osm.shape} != DEM {dem.array.shape}"
    )
    print(f"shape commune: {raster_osm.shape}")


def test_slope_shape_match(dem, raster_osm):
    """slope raster doit avoir le meme shape que le raster OSM"""
    assert dem.slope.shape == raster_osm.shape, (
        f"slope {dem.slope.shape} != OSM {raster_osm.shape}"
    )


def test_aspect_shape_match(dem, raster_osm):
    """aspect raster doit avoir le meme shape que le raster OSM"""
    assert dem.aspect.shape == raster_osm.shape, (
        f"aspect {dem.aspect.shape} != OSM {raster_osm.shape}"
    )


def test_extent_match(dem, bbox):
    """DEM doit couvrir la bbox demandee (tolerance 1 pixel)"""
    rows, cols = dem.array.shape
    dem_top_lat = dem.transform.f
    dem_top_lon = dem.transform.c
    dem_px_lat  = abs(dem.transform.e)
    dem_px_lon  = dem.transform.a
    dem_sud = dem_top_lat - rows * dem_px_lat
    dem_est = dem_top_lon + cols * dem_px_lon
    tol = PIXEL_SIZE_DEG_LAT + 1e-6
    assert abs(dem_top_lat - bbox.nord) < tol,  f"Nord:  DEM={dem_top_lat} bbox={bbox.nord}"
    assert abs(dem_top_lon - bbox.ouest) < tol, f"Ouest: DEM={dem_top_lon} bbox={bbox}"
    assert abs(dem_sud - bbox.sud) < tol,       f"Sud:   DEM={dem_sud} bbox={bbox.sud}"
    assert abs(dem_est - bbox.est) < tol,       f"Est:   DEM={dem_est} bbox={bbox.est}"
    print(f"DEM extent  : N={dem_top_lat}  O={dem_top_lon}  S={dem_sud}  E={dem_est}")
    print(f"bbox extent : N={bbox.nord}   O={bbox.ouest}  S={bbox.sud}  E={bbox.est}")


def test_pixel_alignment(dem, bbox, sommet):
    """DEM et OSM retournent le meme (row, col) pour le sommet de reference (±1 pixel).

    latlon_to_rowcol utilise round(); rasterio.transform.rowcol utilise floor().
    L'ecart max est 0 pixel
    """
    lat, lon = sommet
    dem_row, dem_col = rasterio.transform.rowcol(dem.transform, lon, lat)
    osm_row, osm_col = latlon_to_rowcol_affine(dem.transform, lat, lon)    
    assert abs(dem_row - osm_row) == 0, f"row: DEM={dem_row}  OSM={osm_row}"
    assert abs(dem_col - osm_col) == 0, f"col: DEM={dem_col}  OSM={osm_col}"
    print(f"Sommet -> DEM=({dem_row}, {dem_col})  OSM=({osm_row}, {osm_col})")


def test_peak_dans_cellule_dem(dem, raster_osm, bbox, sommet):
    peaks = (bbox.osm_features or {}).get("peak", [])
    assert peaks, "Aucun peak dans osm_features['peak']"

    lat, lon = sommet
    def dist(f):
        c = f["geometry"]["coordinates"]
        return abs(c[1] - lat) + abs(c[0] - lon)
    sommet_feat = min(peaks, key=dist)

    osm_lon, osm_lat = sommet_feat["geometry"]["coordinates"]
    print(f"\ncoordonnees OSM reelles : lat={osm_lat}  lon={osm_lon}")

    # OSM convention (round) — same as rasterize
    osm_row, osm_col = latlon_to_rowcol_affine(dem.transform, osm_lat, osm_lon)    # DEM convention (floor)
    dem_row, dem_col = rasterio.transform.rowcol(dem.transform, osm_lon, osm_lat)
    print(f"\ncellule OSM : ({osm_row}, {osm_col})  DEM : ({dem_row}, {dem_col})")

    assert raster_osm[osm_row, osm_col]["peak"], (
        f"\npeak absent en cellule OSM ({osm_row},{osm_col})"
    )
    assert abs(dem_row - osm_row) == 0, f"row: DEM={dem_row}  OSM={osm_row}"
    assert abs(dem_col - osm_col) == 0, f"col: DEM={dem_col}  OSM={osm_col}"
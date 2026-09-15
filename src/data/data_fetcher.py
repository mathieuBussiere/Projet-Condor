"""
contexte : 
effectuer un fetch simultanee pour toute les sources de data (DEM + OSM pour l'instant)
"""
import time
import numpy as np
from .structures_communes import BBox
from .Elevation.client_opentopography import get_dem
from .Elevation.structures_elevation import DEMType, DEMdata
from .Elevation.parser_elevation import parse_dem_data
from .OverPass.raster_overpass import rasterize_bbox
from cost_model.cost_grid import build_multiplicateurs_osm
from cost_model.weights import DEFAULT_WEIGHTS

_MIN_BBOX_HALF_DEG = 0.0045 # distance minimum du centre a une extremite
# -> bbox totale mini de 0.009 deg (~1 km). Plancher OpenTopo COP30 mesure ~0.0035 deg
# (~12 px), on garde ~2.6x de marge. cf. tests/opentopography_tests.py::test_probe_min_bbox

def fetch_parsed_dem(demtype : DEMType, bbox : BBox) -> DEMdata:
   bytes_of_data = get_dem(demtype, bbox)
   return parse_dem_data(bytes_of_data)

def fetch_terrain(bbox : BBox,
                  demtype : DEMType = DEMType.COP30,
                  weights : dict[str, float] = DEFAULT_WEIGHTS
                  ) -> None:
   # expand la bbox a une taille minimum pour que DEM et OSM soient alignes
   # modifie la bbox en place (reference) donc tout le pipeline utilise la meme bbox elargie
   mid_lat = (bbox.sud + bbox.nord) / 2
   mid_lon = (bbox.ouest + bbox.est) / 2
   half_lat = max((bbox.nord - bbox.sud) / 2, _MIN_BBOX_HALF_DEG)
   half_lon = max((bbox.est - bbox.ouest) / 2, _MIN_BBOX_HALF_DEG)
   bbox.sud   = max(mid_lat - half_lat, -90.0)
   bbox.nord  = min(mid_lat + half_lat,  90.0)
   bbox.ouest = max(mid_lon - half_lon, -180.0)
   bbox.est   = min(mid_lon + half_lon, 180.0)

   t0 = time.time()

   print("[1/3] fetching DEM...")
   dem = fetch_parsed_dem(demtype, bbox)
   bbox.dem_data = dem
   print(f"      done in {time.time()-t0:.1f}s")

   t1 = time.time()
   print("[2/3 rasterizing OSM...")
   bbox.raster_osm = rasterize_bbox(bbox)
   print(f"      done in {time.time()-t1:.1f}s")

   t3 = time.time()
   print("[3/3] building osm multipliers...")
   bbox.osm_mult = build_multiplicateurs_osm(bbox.raster_osm, weights)
   print(f"      done in {time.time()-t3:.1f}s")

   print(f"      total: {time.time()-t0:.1f}s")
   

   






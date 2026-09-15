"""
Path service for calculating optimized terrain trajectories.
"""
import time
import traceback
import uuid

import numpy as np
from geopy.distance import geodesic

from src.api.schemas.path import Coordinate, PathRequest, PathResponse
from src.data.data_fetcher import fetch_terrain
from src.data.structures_communes import BBox, latlon_to_rowcol_affine
from src.routage.a_star import (
    snap_to_traversable,
    recherche_meilleur_chemin,
)
from src.data.Elevation.structures_elevation import DEMType
from src.cost_model.weights import HIKING_WEIGHTS, DEFAULT_WEIGHTS


class PathService:
    @staticmethod
    def _bbox_from_request(data: PathRequest) -> BBox:
        return BBox(
            sud=data.bbox.sud,
            ouest=data.bbox.ouest,
            nord=data.bbox.nord,
            est=data.bbox.est,
        )

    @staticmethod
    def _elevation_stats(
        points: list[Coordinate],
        dem_array: np.ndarray,
        transform,
    ) -> tuple[float | None, float | None]:
        """
        Samples the DEM at each point of the path and returns
        (max_elevation_m, avg_elevation_m).
        """
        if not points:
            return None, None

        grid_h, grid_w = dem_array.shape
        elevations = []

        for point in points:
            r, c = latlon_to_rowcol_affine(transform, point.lat, point.lng)
            r = min(max(r, 0), grid_h - 1)
            c = min(max(c, 0), grid_w - 1)
            elevations.append(float(dem_array[r, c]))

        return round(max(elevations), 1), round(float(np.mean(elevations)), 1)

    @staticmethod
    def calculate_path(data: PathRequest) -> PathResponse:
        if data.bbox is None:
            raise ValueError("Bounding box (bbox) requise.")

        bbox = PathService._bbox_from_request(data)
        fetch_terrain(bbox, DEMType.COP30, HIKING_WEIGHTS)

        if bbox.dem_data is None or bbox.osm_mult is None:
            raise ValueError("Échec du chargement des matrices de terrain.")

        transform = bbox.dem_data.transform
        trajectory_id = f"TRJ-{uuid.uuid4().hex[:6].upper()}"

        # Calcul et sécurisation des ancrages sur la grille
        start_grid = latlon_to_rowcol_affine(transform, data.start.lat, data.start.lng)
        end_grid = latlon_to_rowcol_affine(transform, data.end.lat, data.end.lng)
        start_grid = snap_to_traversable(start_grid, bbox.osm_mult)
        end_grid = snap_to_traversable(end_grid, bbox.osm_mult)

        grid_h, grid_w = bbox.osm_mult.shape
        print(f"[{trajectory_id}] Grid size: {grid_h}x{grid_w}")

        if not (0 <= start_grid[0] < grid_h and 0 <= start_grid[1] < grid_w):
            raise ValueError(f"Départ hors zone d'analyse: {start_grid}")
        if not (0 <= end_grid[0] < grid_h and 0 <= end_grid[1] < grid_w):
            raise ValueError(f"Arrivée hors zone d'analyse: {end_grid}")

        start_tuple = (data.start.lat, data.start.lng)
        end_tuple = (data.end.lat, data.end.lng)
        distance_km = geodesic(start_tuple, end_tuple).kilometers
        duration_minutes = (distance_km / 5.0) * 60
        path_points = []

        try:
            t0 = time.time()
            print(f"[{trajectory_id}] Calcul de la trajectoire optimale via A*...")
            a_star_latlon_path = recherche_meilleur_chemin(
                bbox.osm_mult, bbox.dem_data.array, transform, start_grid, end_grid
            )
            print(f"[{trajectory_id}] A* complété avec succès en {time.time() - t0:.2f}s ({len(a_star_latlon_path)} points)")
            path_points = [Coordinate(lat=lat, lng=lng) for lat, lng in a_star_latlon_path]
        except Exception as e:
            print(f"[-] ERROR : Échec critique du routage. Fallback en ligne droite appliqué. Motifs : {e}")
            traceback.print_exc()
            path_points = [
                Coordinate(lat=data.start.lat, lng=data.start.lng),
                Coordinate(lat=data.end.lat, lng=data.end.lng),
            ]

        max_elevation_m, avg_elevation_m = PathService._elevation_stats(
            path_points, bbox.dem_data.array, transform
        )

        return PathResponse(
            trajectory_id=trajectory_id,
            start=data.start,
            end=data.end,
            bbox=data.bbox,
            points=path_points,
            distance_km=round(distance_km, 2),
            time=round(duration_minutes, 1),
            grid_shape=bbox.osm_mult.shape,
            grid_computed=True,
            max_elevation_m=max_elevation_m,
            avg_elevation_m=avg_elevation_m,
        )
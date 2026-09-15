"""
Service engine for parsing reference tracks and scoring algorithmic path accuracy.
"""
import io
from typing import List, Dict, Any
import gpxpy
import numpy as np
import pandas as pd
import similaritymeasures
from geopy.distance import geodesic

from src.routage.a_star import ratio_effort


class RouteComparisonService:
    @staticmethod
    def parse_trail_file(file_name: str, file_content: str) -> List[tuple]:
        """
        Détermine le format du fichier à partir de son extension
        et extrait la liste des coordonnées (lat, lon) depuis le contenu brut.
        """
        if file_name.lower().endswith('.gpx'):
            return RouteComparisonService._parse_gpx(file_content)
        elif file_name.lower().endswith('.csv'):
            return RouteComparisonService._parse_csv(file_content)
        return []

    @staticmethod
    def _parse_gpx(file_content: str) -> List[tuple]:
        points = []
        try:
            # gpxpy accepte directement une chaîne de caractères XML brute
            gpx = gpxpy.parse(file_content)
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        points.append((point.latitude, point.longitude))
        except Exception as e:
            print(f"[-] Erreur de lecture GPX : {e}")
        return points

    @staticmethod
    def _parse_gpx(file_content: str) -> List[tuple]:
        points = []
        try:
            gpx = gpxpy.parse(file_content)

            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        points.append((point.latitude, point.longitude))

            if not points:
                for route in gpx.routes:
                    for point in route.points:
                        points.append((point.latitude, point.longitude))

            if not points:
                for waypoint in gpx.waypoints:
                    points.append((waypoint.latitude, waypoint.longitude))

            if not points:
                print(
                    "[-] GPX Parsing Warning: File parsed successfully, but contained 0 tracks, routes, or waypoints.")

        except Exception as e:
            print(f"[-] Critical GPX XML Engine Error: {e}")

        return points

    @staticmethod
    def _parse_csv(file_content: str) -> List[tuple]:
        try:
            df = pd.read_csv(io.StringIO(file_content), sep=None, engine='python')

            if df.empty:
                print("[-] CSV Parsing Warning: The uploaded file is completely empty.")
                return []

            # Normalize headers to lowercase and strip hidden spaces
            df.columns = df.columns.str.strip().str.lower()

            lat_col = next((c for c in df.columns if c in ['lat', 'latitude']), None)
            lng_col = next((c for c in df.columns if c in ['lng', 'lon', 'longitude']), None)

            # If columns aren't found, print out exactly what Pandas saw
            if not lat_col or not lng_col:
                print(f"[-] CSV Mapping Failed! Columns found by Pandas: {list(df.columns)}")
                return []

            # Drop rows where coordinates are missing (NaN)
            df = df.dropna(subset=[lat_col, lng_col])

            points = list(zip(df[lat_col].astype(float), df[lng_col].astype(float)))
            return points

        except Exception as e:
            print(f"[-] Global Pandas CSV Engine breakdown: {e}")
            return []

    @classmethod
    def compare(
        cls,
        path_algo: List[tuple],
        path_ref_raw: List[tuple],
        dem_array: np.ndarray,
        transform,
        start_tuple: tuple,
        end_tuple: tuple
    ) -> Dict[str, Any]:
        """Runs geospatial analysis and returns metric discrepancy stats."""
        # Alignement dynamique de la trace de référence selon le départ/arrivée réels
        idx_start = min(range(len(path_ref_raw)), key=lambda i: geodesic(path_ref_raw[i], start_tuple).meters)
        idx_end = min(range(len(path_ref_raw)), key=lambda i: geodesic(path_ref_raw[i], end_tuple).meters)

        if idx_start <= idx_end:
            path_ref = path_ref_raw[idx_start:idx_end + 1]
        else:
            path_ref = path_ref_raw[idx_end:idx_start + 1][::-1]

        p = np.array(path_algo, dtype=np.float64)
        q = np.array(path_ref, dtype=np.float64)

        # Égalisation des densités de points
        target_n = min(max(len(p), len(q)), 2000)
        if len(p) < target_n:
            p = np.column_stack([np.interp(np.linspace(0, 1, target_n), np.linspace(0, 1, len(p)), p[:, 0]),
                                 np.interp(np.linspace(0, 1, target_n), np.linspace(0, 1, len(p)), p[:, 1])])
        if len(q) < target_n:
            q = np.column_stack([np.interp(np.linspace(0, 1, target_n), np.linspace(0, 1, len(q)), q[:, 0]),
                                 np.interp(np.linspace(0, 1, target_n), np.linspace(0, 1, len(q)), q[:, 1])])

        # Projection métrique plane locale pour éviter les distorsions de calcul euclidien
        avg_lat = (p[:, 0].mean() + q[:, 0].mean()) / 2.0
        m_per_deg_lat = 111132.0
        m_per_deg_lon = 111132.0 * np.cos(np.radians(avg_lat))

        p_meters = np.column_stack([p[:, 1] * m_per_deg_lon, p[:, 0] * m_per_deg_lat])
        q_meters = np.column_stack([q[:, 1] * m_per_deg_lon, q[:, 0] * m_per_deg_lat])

        # Calcul mathématique des écarts géométriques
        frechet_m = float(similaritymeasures.frechet_dist(p_meters, q_meters))
        dtw_val, _ = similaritymeasures.dtw(p_meters, q_meters)
        dtw_m = float(dtw_val) / len(p_meters)

        # % du tracé algo à moins de CORRIDOR_M mètres de la référence :
        # la trace humaine est l'étalon, cette métrique mesure directement
        # "est-ce qu'on suit le même chemin". Distance min par blocs pour
        # borner la mémoire du broadcast N x M (jusqu'à 2000 x 2000 points).
        corridor_hits = 0
        for i in range(0, len(p_meters), 256):
            bloc = p_meters[i:i + 256]
            d_min = np.sqrt(((bloc[:, None, :] - q_meters[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
            corridor_hits += int((d_min <= cls.CORRIDOR_M).sum())
        corridor_pct = 100.0 * corridor_hits / len(p_meters)

        # Évaluation de l'effort physiologique
        effort_ratio = ratio_effort(path_algo, path_ref, dem_array, transform)

        # Génération des scores normalisés (0-100).
        # Barème centré sur la fidélité à la trace humaine (la référence) :
        #  - corridor (60 %) : suit-on le même chemin que la référence
        #  - géométrie (20 %) : écart MOYEN (DTW), moins indulgent que le pire cas Fréchet
        #  - effort (20 %) : pénalise uniquement un tracé PLUS DUR que l'humain (ratio > 1)
        score_corridor = corridor_pct
        score_geo = max(0.0, min(100.0, 100.0 - dtw_m * 0.5))
        score_effort = max(0.0, min(100.0, 100.0 - max(0.0, effort_ratio - 1.0) * 200.0))
        score_final = round(score_corridor * 0.6 + score_geo * 0.2 + score_effort * 0.2, 1)

        return {
            "score": score_final,
            "verdict": cls._get_verdict(score_final),
            "metrics": {
                "frechet_distance_meters": round(frechet_m, 1),
                "dtw_corridor_deviation_meters": round(dtw_m, 1),
                "tobler_effort_ratio": round(effort_ratio, 3),
                "corridor_percent": round(corridor_pct, 1),
            }
        }

    # Tolérance "même chemin" : ~2 cellules DEM (30 m)
    CORRIDOR_M = 60.0

    @staticmethod
    def _get_verdict(score: float) -> str:
        if score >= 90: return "Excellent — Tracé très fidèle au sentier"
        if score >= 70: return "Bon — Corridor similaire avec déviations mineures"
        if score >= 50: return "Acceptable — Itinéraire divergent mais cohérent"
        return "Faible — Écart critique par rapport au tracé de référence"
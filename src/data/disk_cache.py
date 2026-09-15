"""
module central de cache

autheur : marc-emile scholer
date : 2026-06-04
"""
import io
import sqlite3
import hashlib
import json
import threading
from pathlib import Path
from datetime import datetime, timezone

import rasterio
from rasterio.merge import merge as rasterio_merge
from rasterio.io import MemoryFile


# cache directory at project root
CACHE_DIRECTORY = Path(__file__).parent.parent.parent/ "cache"


_conn: sqlite3.Connection | None = None
_db_lock = threading.Lock()

def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = init_db()
    return _conn



def init_db(cache_dir : Path = CACHE_DIRECTORY) -> sqlite3.Connection:
    """
    initialisation de la db sqlite3
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cache_dir/ "index.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
                id        TEXT PRIMARY KEY,
                type      TEXT,
                south     REAL,
                west      REAL,
                north     REAL,
                east      REAL,
                demtype   TEXT,
                meta      TEXT,
                cached_on TEXT )"""
        )
    conn.commit()
    return conn

def _dem_key(demtype_value: str, bbox) -> str:
    """fonction de creation des noms de fichier de type DEM(GeoTiff)"""
    s = round(bbox.sud, 4)
    w = round(bbox.ouest, 4)
    n = round(bbox.nord, 4)
    e = round(bbox.est, 4)
    return f"dem_{demtype_value}_{s}_{w}_{n}_{e}.tif"
    
def _osm_key(query: str, bbox_str: str, verbosity: str, response_format: str) -> str:
    """
    fonction de creation des noms de fichier de type OSM(GeoJSON)
    ici utilise le raw string de la query serait impossible(trop long)
    md5 produit un hash hexadecimal deterministe, compact et PRATIQUEMENT unique
    """
    raw = f"{query}|{bbox_str}|{verbosity}|{response_format}"
    hash_osm = hashlib.md5(raw.encode()).hexdigest()
    return f"osm_{hash_osm}.json"

# !!!! get la box exact si on l'a, delete les stale entry
def get_cached_dem(
        demtype_value : str, 
        bbox) -> bytes | None: 
    # nom du
    key = _dem_key(demtype_value, bbox)
    with _db_lock:
        row = _get_conn().execute(
            "SELECT id FROM cache WHERE id = ? AND type = 'dem'", (key,)
        ).fetchone()
        if row is None:
            return None
        path = CACHE_DIRECTORY / key

        if not path.exists():
            _get_conn().execute("DELETE FROM cache WHERE id = ?", (key,))
            _get_conn().commit()
            return None

    return path.read_bytes()

# zone critique !
# save un dem en cache
def save_dem(
        demtype_value : str,
        bbox, data: bytes) -> None:
    key = _dem_key(demtype_value, bbox)
    (CACHE_DIRECTORY / key).write_bytes(data)
    with _db_lock:
        _get_conn().execute(
            """INSERT OR REPLACE INTO cache
                   (id, type, south, west, north, east, demtype, meta, cached_on)
               VALUES (?, 'dem', ?, ?, ?, ?, ?, NULL, ?)""",
            (key, bbox.sud, bbox.ouest, bbox.nord, bbox.est, demtype_value,
             datetime.now(timezone.utc).isoformat()),
        )
        _get_conn().commit()


def find_overlapping_dem_tiles(
        demtype_value: str, 
        bbox) -> list[tuple[str, float, float, float, float]]:
    """
    retourne [(key, south, west, north, east)] pour toutes les tuiles DEM en cache
    qui overlap la bbox demandee.
    delete automatiquement les entrees dont le fichier est absent.
    """
    with _db_lock:
        rows = _get_conn().execute(
            """SELECT id, south, west, north, east FROM cache
               WHERE type    = 'dem'
                 AND demtype = ?
                 AND west    < ?
                 AND east    > ?
                 AND south   < ?
                 AND north   > ?""",
            (demtype_value, bbox.est, bbox.ouest, bbox.nord, bbox.sud),
        ).fetchall()

        valid: list[tuple[str, float, float, float, float]] = []
        stale: list[str] = []
        for key, south, west, north, east in rows:
            if (CACHE_DIRECTORY / key).exists():
                valid.append((key, south, west, north, east))
            else:
                stale.append(key)

        if stale:
            _get_conn().executemany("DELETE FROM cache WHERE id = ?", [(k,) for k in stale])
            _get_conn().commit()

    return valid

def _group_contiguous_tiles(
    tiles: list[tuple[str, float, float, float, float]]
    ) -> list[list[tuple[str, float, float, float, float]]]:
    """
    Utilise union find pour grouper les tuiles connexes
    2 tuiles sont dans le meme groupe si leur bbox se touche ou overlap
    retourne les groupes de tuiles connexes
    """
    # parent[i] = i 
    n = len(tiles)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]  # path compression
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        _, si, wi, ni, ei = tiles[i]
        for j in range(i + 1, n):
            _, sj, wj, nj, ej = tiles[j]
            if wi <= ej and ei >= wj and si <= nj and ni >= sj:
                union(i, j)

    groups: dict[int, list] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(tiles[i])
    return list(groups.values())


def get_partial_dem_coverage(
        demtype_value: str, 
        bbox) -> list[tuple[bytes, tuple[float, float, float, float]]] | None:
    """
    Agrege les tuiles DEM en cache qui chevauchent la bbox demandee.
    Retourne une liste de (data_bytes, (south, west, north, east)) - une entree
    par region contigue trouvee. Retourne None si aucune tuile.
    """
    tiles = find_overlapping_dem_tiles(demtype_value, bbox)
    if not tiles:
        return None

    # resultat = liste de box 
    results: list[tuple[bytes, tuple[float, float, float, float]]] = []
    # pour tout le data en cache
    for group in _group_contiguous_tiles(tiles):
        # trouve la zone couverte en 1 passe
        keys_col, souths, wests, norths, easts = zip(*group)
        covered = (min(souths), min(wests), max(norths), max(easts))

        datasets = [rasterio.open(CACHE_DIRECTORY / key) for key in keys_col]
        try:
            merged_array, merged_transform = rasterio_merge(datasets, nodata=-9999)
            profile = datasets[0].profile.copy()
            profile.update(
                height=merged_array.shape[1],
                width=merged_array.shape[2],
                transform=merged_transform,
                nodata=-9999,
            )
            with MemoryFile() as mem:
                with mem.open(**profile) as dst:
                    dst.write(merged_array)
                results.append((mem.read(), covered))
        finally:
            for ds in datasets:
                ds.close()

    return results

def _compute_uncovered_bboxes(
    query_s: float, query_w: float, query_n: float, query_e: float,
    covered: list[tuple[float, float, float, float]],
    ) -> list[tuple[float, float, float, float]]:
    """
    avec argument donne la queried bbox et une liste de rectangles couverts (s,w,n,e) par le cache,
    retourne la liste minimale de bboxes rectangulaires non couvertes.
    Utilise une grille de coordonnees + fusion horizontale par bande de latitude.
    """
    clipped = []
    for s, w, n, e in covered:
        cs, cw, cn, ce = max(s, query_s), max(w, query_w), min(n, query_n), min(e, query_e)
        if cs < cn and cw < ce:
            clipped.append((cs, cw, cn, ce))

    lats = sorted({query_s, query_n} | {r[0] for r in clipped} | {r[2] for r in clipped})
    lons = sorted({query_w, query_e} | {r[1] for r in clipped} | {r[3] for r in clipped})

    result: list[tuple[float, float, float, float]] = []
    for i in range(len(lats) - 1):
        cell_s, cell_n = lats[i], lats[i + 1]
        mid_lat = (cell_s + cell_n) / 2
        merge_w = merge_e = None
        for j in range(len(lons) - 1):
            cell_w, cell_e = lons[j], lons[j + 1]
            mid_lon = (cell_w + cell_e) / 2
            is_covered = any(
                s <= mid_lat <= n and w <= mid_lon <= e
                for s, w, n, e in clipped
            )
            if is_covered:
                if merge_w is not None:
                    result.append((cell_s, merge_w, cell_n, merge_e))
                    merge_w = merge_e = None
            else:
                if merge_w is None:
                    merge_w = cell_w
                merge_e = cell_e
        if merge_w is not None:
            result.append((cell_s, merge_w, cell_n, merge_e))

    return result


def query_dem_cache_coverage(demtype_value: str,
                      bbox,
) -> tuple[
    list[tuple[bytes, tuple[float, float, float, float]]],
    list[tuple[float, float, float, float]],
]:
    """
    Verifie la couverture du cache pour la bbox demandee.
    Retourne un tuple:
      - donnees couvertes : [(data_bytes, (south, west, north, east)), ...]
      - bboxes manquantes : [(south, west, north, east), ...]
    """
    covered_data = get_partial_dem_coverage(demtype_value, bbox)

    if not covered_data:
        return [], [(bbox.sud, bbox.ouest, bbox.nord, bbox.est)]

    covered_regions = [region for _, region in covered_data]
    missing = _compute_uncovered_bboxes(
        bbox.sud, bbox.ouest, bbox.nord, bbox.est, covered_regions
    )
    return covered_data, missing

def _osm_query_hash(query: str, verbosity: str, response_format: str) -> str:
    """hash deterministe de la query (sans bbox) pour le matching spatial OSM."""
    return hashlib.md5(f"{query}|{verbosity}|{response_format}".encode()).hexdigest()


def save_osm(query: str,
             bbox_str: str,
             verbosity: str,
             response_format: str,
             data: dict) -> None:
    key = _osm_key(query, bbox_str, verbosity, response_format)
    query_hash = _osm_query_hash(query, verbosity, response_format)
    parts = bbox_str.split(",") if bbox_str else []
    south, west, north, east = (float(p) for p in parts) if len(parts) == 4 else (None, None, None, None)
    (CACHE_DIRECTORY / key).write_text(json.dumps(data), encoding="utf-8")
    
    # zone critique !
    with _db_lock:
        _get_conn().execute(
            """INSERT OR REPLACE INTO cache
                   (id, type, south, west, north, east, demtype, meta, cached_on)
               VALUES (?, 'osm', ?, ?, ?, ?, ?, ?, ?)""",
            (key, south, west, north, east, query_hash, bbox_str,
             datetime.now(timezone.utc).isoformat()),
        )
        _get_conn().commit()


def find_overlapping_osm_tiles(
    query: str, bbox, verbosity: str, response_format: str
) -> list[tuple[str, float, float, float, float]]:
    """
    Retourne [(key, south, west, north, east)] pour toutes les tuiles OSM en cache
    qui overlap la bbox demandee et correspondent a la meme query.
    Delete automatiquement les entrees dont le fichier est absent.
    """
    query_hash = _osm_query_hash(query, verbosity, response_format)
    with _db_lock:
        rows = _get_conn().execute(
            """SELECT id, south, west, north, east FROM cache
               WHERE type    = 'osm'
                 AND demtype = ?
                 AND south IS NOT NULL
                 AND west    < ?
                 AND east    > ?
                 AND south   < ?
                 AND north   > ?""",
            (query_hash, bbox.est, bbox.ouest, bbox.nord, bbox.sud),
        ).fetchall()

        valid: list[tuple[str, float, float, float, float]] = []
        stale: list[str] = []
        for key, south, west, north, east in rows:
            if (CACHE_DIRECTORY / key).exists():
                valid.append((key, south, west, north, east))
            else:
                stale.append(key)

        if stale:
            _get_conn().executemany("DELETE FROM cache WHERE id = ?", [(k,) for k in stale])
            _get_conn().commit()

    return valid


def _merge_geojson(collections: list[dict]) -> dict:
    """Fusionne des FeatureCollections GeoJSON en dedupliquant par feature id."""
    seen_ids: set = set()
    merged_features = []
    for collection in collections:
        for feat in collection.get("features", []):
            fid = feat.get("id")
            if fid is None or fid not in seen_ids:
                if fid is not None:
                    seen_ids.add(fid)
                merged_features.append(feat)
    return {"type": "FeatureCollection", "features": merged_features}


def query_osm_cache_coverage(
    query: str,
    bbox,
    verbosity: str,
    response_format: str,
) -> tuple[dict | None, list[tuple[float, float, float, float]]]:
    """
    Verifie la couverture du cache OSM pour la bbox demandee.
    Retourne un tuple:
      - GeoJSON fusionne des tuiles couvertes (None si aucune)
      - bboxes manquantes : [(south, west, north, east), ...]
    """
    tiles = find_overlapping_osm_tiles(query, bbox, verbosity, response_format)

    if not tiles:
        return None, [(bbox.sud, bbox.ouest, bbox.nord, bbox.est)]

    covered_regions = []
    collections = []
    for key, south, west, north, east in tiles:
        collections.append(json.loads((CACHE_DIRECTORY / key).read_text(encoding="utf-8")))
        covered_regions.append((south, west, north, east))

    merged = _merge_geojson(collections)
    missing = _compute_uncovered_bboxes(
        bbox.sud, bbox.ouest, bbox.nord, bbox.est, covered_regions
    )
    return merged, missing


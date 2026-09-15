
"""
Client pour l'API OpenTopography.
autheur(s) : marc-emile scholer
date de creation : 07-05-26
"""
import requests
import os
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from rasterio.merge import merge as rasterio_merge
from rasterio.io import MemoryFile
from ..structures_communes import BBox
from .structures_elevation import DEMType
from ..disk_cache import save_dem, query_dem_cache_coverage
import rasterio.windows

load_dotenv()

# endpoints api
_ENDPOINT = "https://portal.opentopography.org/API/globaldem"
_TIMEOUT = 100
_API_KEYS = [
    os.getenv("OPENTOPO_KEY_1"),
    os.getenv("OPENTOPO_KEY_2"),
   # os.getenv("OPENTOPO_KEY_3"),
]

_MIN_FETCH_DEG = 0.005      # taille minimum d'une sous-bbox avant de fallback sur la bbox complete
                            # (plancher OpenTopo COP30 ~0.0035 deg / ~12 px, on garde une marge)
_SLIVER_TOLERANCE_DEG = 0.002  # lamelles plus petites que ca sont negligeables (manque ~200m de bord)
_FETCH_OVERLAP_DEG = 0.001  # ~3-4 px COP30 : on elargit chaque sous-bbox manquante pour qu'elle
                            # chevauche les tuiles voisines. Sinon les frontieres non alignees sur
                            # la grille native laissent une couture de nodata a la fusion (mur A*)


def _fetch_from_api(demtype: DEMType, bbox: BBox) -> bytes:
    for key in _API_KEYS:
        parametres = {
            "demtype": demtype.value,
            "south": bbox.sud,
            "west": bbox.ouest,
            "north": bbox.nord,
            "east": bbox.est,
            "outputFormat": "GTiff",
            "API_Key": key,
        }
        try:
            request = requests.get(_ENDPOINT, params=parametres, timeout=_TIMEOUT)
            request.raise_for_status()
            return request.content
        except requests.exceptions.HTTPError as e:
            if request.status_code in (429, 401):
                continue
            raise e
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError) as e:
            raise e
    raise requests.exceptions.HTTPError("Toutes les keys sont épuisées")


def _merge_dem_bytes(all_bytes: list[bytes]) -> bytes:
    mem_files = [MemoryFile(b) for b in all_bytes]
    datasets = [mf.open() for mf in mem_files]
    try:
        # nodata=-9999 explicite : sinon la fusion peut ne pas reconnaitre les
        # pixels manquants et laisser des coutures entre tuiles adjacentes
        merged_arr, merged_transform = rasterio_merge(datasets, nodata=-9999)
        profile = datasets[0].profile.copy()
        profile.update(
            height=merged_arr.shape[1],
            width=merged_arr.shape[2],
            transform=merged_transform,
            nodata=-9999,
        )
        with MemoryFile() as out:
            with out.open(**profile) as dst:
                dst.write(merged_arr)
            return out.read()
    finally:
        for ds in datasets:
            ds.close()
        for mf in mem_files:
            mf.close()

def _crop_to_bbox(raw: bytes, bbox: BBox) -> bytes:
    with MemoryFile(raw) as mem:
        with mem.open() as src:
            window = rasterio.windows.from_bounds(bbox.ouest, bbox.sud, bbox.est, bbox.nord, src.transform)
            nodata = src.nodata if src.nodata is not None else -9999
            data = src.read(window=window, boundless=True, fill_value=nodata)
            transform = src.window_transform(window)
            profile = src.profile.copy()
            profile.update(height=data.shape[1], width=data.shape[2], transform=transform, nodata=nodata)
        with MemoryFile() as out:
            with out.open(**profile) as dst:
                dst.write(data)
            return out.read()


def get_dem(demtype: DEMType, bbox: BBox) -> bytes:
    """
    Retourne le data elevation model pour la bbox donne, prend les donnes cached en priorite, fallback sur API
    args :
        demtype : la collection de data que l'ont veut utiliser
        bbox : une bounding box pour l'ensemble du data

    return :
        fichier binaire GeoTIFF exploitable avec une librairie comme rasterio

    peut lever :
        requests.exceptions.Timeout: requete trop longue
        requests.exceptions.ConnectionError: pas de connexion au serveur
        requests.exceptions.HTTPError: erreur HTTP (429 trop de requetes, 504 surcharge, 406 not acceptable)
    """
    print("[DEM : verifier couverture cache...]")
    covered_data, missing_bboxes = query_dem_cache_coverage(demtype.value, bbox)

    if not missing_bboxes:
        print("[DEM : couverture complete en cache]")
        all_bytes = [data for data, _ in covered_data]
        raw = all_bytes[0] if len(all_bytes) == 1 else _merge_dem_bytes(all_bytes)
        return _crop_to_bbox(raw, bbox)

    #helper pour check si bbox trop petite
    def _is_too_small(b):
        sub_s, sub_w, sub_n, sub_e = b
        return (sub_n - sub_s) < _MIN_FETCH_DEG or (sub_e - sub_w) < _MIN_FETCH_DEG

    # lamelles negligeables (ex: bbox legerement decalee) : on crop le cache sans re-fetch
    if covered_data and all(
        (sub_n - sub_s) < _SLIVER_TOLERANCE_DEG or (sub_e - sub_w) < _SLIVER_TOLERANCE_DEG
        for sub_s, sub_w, sub_n, sub_e in missing_bboxes
    ):
        print("[DEM : lamelles negligeables, utilisation du cache]")
        all_bytes = [data for data, _ in covered_data]
        raw = all_bytes[0] if len(all_bytes) == 1 else _merge_dem_bytes(all_bytes)
        return _crop_to_bbox(raw, bbox)

    # si une sous-bbox est trop petite, on ignore le cache partiel et on requete la bbox complete
    # (la bbox complete a deja une taille minimum garantie par fetch_terrain)
    if any(_is_too_small(b) for b in missing_bboxes):
        print("[DEM : sous-bbox trop petite, requete complete...]")
        covered_data = []
        missing_bboxes = [(bbox.sud, bbox.ouest, bbox.nord, bbox.est)]

    if covered_data:
        print(f"[DEM : couverture partielle - {len(missing_bboxes)} zone(s) manquante(s)]")
        # on elargit chaque sous-bbox manquante pour qu'elle recouvre les tuiles voisines
        # (cachees ou autres bandes) : evite les coutures de nodata a la fusion
        missing_bboxes = [
            (max(s - _FETCH_OVERLAP_DEG, -90.0), max(w - _FETCH_OVERLAP_DEG, -180.0),
             min(n + _FETCH_OVERLAP_DEG, 90.0), min(e + _FETCH_OVERLAP_DEG, 180.0))
            for s, w, n, e in missing_bboxes
        ]
    else:
        print("[DEM : aucune donnee en cache, appel API...]")

    # helper pour aller fetch une sub bbox
    def _fetch_sub(bbox_tuple: tuple) -> tuple[BBox, bytes]:
        sub_s, sub_w, sub_n, sub_e = bbox_tuple
        sub_bbox = BBox(sud=sub_s, ouest=sub_w, nord=sub_n, est=sub_e)
        print(f"[DEM : fetching ({sub_s:.4f},{sub_w:.4f}) -> ({sub_n:.4f},{sub_e:.4f})]")
        return sub_bbox, _fetch_from_api(demtype, sub_bbox)

    with ThreadPoolExecutor(max_workers=len(missing_bboxes)) as ex:
        fetched_pairs = list(ex.map(_fetch_sub, missing_bboxes))

    newly_fetched: list[bytes] = []
    for sub_bbox, data in fetched_pairs:
        save_dem(demtype.value, sub_bbox, data)
        newly_fetched.append(data)

    all_bytes = [data for data, _ in covered_data] + newly_fetched
    return _crop_to_bbox(all_bytes[0] if len(all_bytes) == 1 else _merge_dem_bytes(all_bytes), bbox)

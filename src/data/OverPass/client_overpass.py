"""
Client pour l'API overpass de OpenStreetmap.
autheur(s) : marc-emile scholer
date de creation : 07-05-26

Overpass fonctionne avec des requetes http de type POST.
Note: [out:geojson] n'est pas supporte par l'API — la conversion GeoJSON est faite via osm2geojson du cote client.
"""
import requests
import osm2geojson
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

from ..structures_communes import BBox
from ..disk_cache import save_osm, query_osm_cache_coverage, _merge_geojson


# endpoints api
_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

_RE_ERREURS = re.compile(r"error|timed out|out of memory", re.IGNORECASE)

_CONNECT_TIMEOUT = 8
_OVERPASS_TIMEOUT = 180
_READ_TIMEOUT = 200
# serveurs overpass exigent une identification, sinon erreur 406 (not acceptable)
_HEADERS = {"User-Agent": "CodeNameCondor/0.1 (student project; contact schm2805@usherbrooke.ca)"}

_MIN_FETCH_DEG = 0.005  # Overpass n'a pas de minimum reel ; aligne sur le seuil DEM pour coherence
_SLIVER_TOLERANCE_DEG = 0.002

class OverpassRemarkError(requests.exceptions.HTTPError):
    pass


def _remark_error(data: dict) -> str | None:
    remark = data.get("remark") or ""
    return remark if _RE_ERREURS.search(remark) else None


def _fetch_from_api(
    query: str, bbox: BBox, verbosity: str, response_format: str
) -> dict:
    bbox_settings = f"[bbox:{bbox.sud},{bbox.ouest},{bbox.nord},{bbox.est}]"
    query_complete = f"[out:json][timeout:{_OVERPASS_TIMEOUT}]{bbox_settings};\n{query}\nout {verbosity};"
    errors = []
    for endpoint in _ENDPOINTS:
        try:
            r = requests.post(
                endpoint,
                data={"data": query_complete},
                headers=_HEADERS,
                timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
            )
            r.raise_for_status()
            data = r.json()
            remark = _remark_error(data)
            if remark:
                errors.append(f"{endpoint}: OverpassRemarkError: {remark}")
                continue
            return osm2geojson.json2geojson(data) if response_format == "geojson" else data
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError) as e:
            errors.append(f"{endpoint}: {type(e).__name__}: {e}")
    raise OverpassRemarkError(
        "Tous les serveurs Overpass ont echoue :\n  " + "\n  ".join(errors)
    )


def _is_too_small(b):
    sub_s, sub_w, sub_n, sub_e = b
    return (sub_n - sub_s) < _MIN_FETCH_DEG or (sub_e - sub_w) < _MIN_FETCH_DEG


def get_data(
    query: str,
    bbox: BBox = None,
    verbosity: str = "geom",
    response_format: str = "geojson",
) -> dict:
    """
    args :
        query: en langage OverPassQL (sans prefixe [out:...])
        verbosity : details du retour (geom, body, tags, skel...)
        response_format : format de reponse ("geojson" ou "json")

    return :
        FeatureCollection GeoJSON si response_format="geojson", sinon dict JSON Overpass

    peut lever :
        requests.exceptions.Timeout: requete trop longue
        requests.exceptions.ConnectionError: pas de connexion au serveur
        requests.exceptions.HTTPError: erreur HTTP (429 trop de requetes, 504 surcharge, 406 not acceptable...etc.)
    """
    if bbox is None:
        return _fetch_from_api(query, BBox(0, 0, 0, 0), verbosity, response_format)

    print("[OSM : verifier couverture cache...]")
    cached_data, missing_bboxes = query_osm_cache_coverage(query, bbox, verbosity, response_format)

    if not missing_bboxes:
        print("[OSM : couverture complete en cache]")
        return cached_data

    # lamelles negligeables (ex: bbox legerement decalee) : on retourne le cache sans re-fetch
    if cached_data and all(
        (sub_n - sub_s) < _SLIVER_TOLERANCE_DEG or (sub_e - sub_w) < _SLIVER_TOLERANCE_DEG
        for sub_s, sub_w, sub_n, sub_e in missing_bboxes
    ):
        print("[OSM : lamelles negligeables, utilisation du cache]")
        return cached_data

    # ici on evite d'avoir une sous bbox trop petite en fallback sur la bbox complete qui a deja une taille minimum
    if any(_is_too_small(b) for b in missing_bboxes):
        print("[OSM : sous-bbox trop petite, requete complete...]")
        cached_data = None
        missing_bboxes = [(bbox.sud, bbox.ouest, bbox.nord, bbox.est)]

    if cached_data:
        print(f"[OSM : couverture partielle - {len(missing_bboxes)} zone(s) manquante(s)]")
    else:
        print("[OSM : aucune donnee en cache, appel API...]")

    def _fetch_sub(bbox_tuple: tuple) -> tuple[str, dict]:
        sub_s, sub_w, sub_n, sub_e = bbox_tuple
        sub_bbox = BBox(sud=sub_s, ouest=sub_w, nord=sub_n, est=sub_e)
        print(f"[OSM : fetching ({sub_s:.4f},{sub_w:.4f}) -> ({sub_n:.4f},{sub_e:.4f})]")
        return f"{sub_s},{sub_w},{sub_n},{sub_e}", _fetch_from_api(query, sub_bbox, verbosity, response_format)

    reussites: list[tuple[str, dict]] = []
    echecs: list[str] = []
    with ThreadPoolExecutor(max_workers=len(missing_bboxes)) as ex:
        futures = {ex.submit(_fetch_sub, b): b for b in missing_bboxes}
        for future in as_completed(futures):
            sub_s, sub_w, sub_n, sub_e = futures[future]
            try:
                reussites.append(future.result())
            except requests.exceptions.RequestException as err:
                echecs.append(
                    f"({sub_s:.4f},{sub_w:.4f}) -> ({sub_n:.4f},{sub_e:.4f}) : {err}"
                )

    newly_fetched: list[dict] = []
    for sub_bbox_str, data in reussites:
        save_osm(query, sub_bbox_str, verbosity, response_format, data)
        newly_fetched.append(data)

    if echecs:
        raise OverpassRemarkError(
            f"{len(echecs)}/{len(missing_bboxes)} zone(s) OSM non recuperee(s) :\n  "
            + "\n  ".join(echecs)
        )

    all_collections = ([cached_data] if cached_data else []) + newly_fetched
    return all_collections[0] if len(all_collections) == 1 else _merge_geojson(all_collections)

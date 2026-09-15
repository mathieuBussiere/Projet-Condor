"""
definitions et structures de classes, types et autre dans loverpass api

"""
import numpy as np
import re
from .queries_overpass import *

"""
Structured arrays : numpy supporte des datatypes structure dans les array
pratique ici pour enumerer les attributs
"""
osm_dtype = np.dtype([
    ("trail", bool),
    ("road", bool),
    ("water", bool),
    ("water_small", bool),
    ("water_crossing", bool),
    ("bridge", bool),
    ("ford", bool),
    ("vegetation", bool),
    ("wetland", bool),
    ("peak", bool),
    ("cliff", bool),
    ("ridge", bool),
    ("valley", bool),
    ("arete", bool),
    ("scree", bool),
    ("bare_rock", bool),
    ("glacier", bool),
    ("border", bool),
    ("building", bool)
])


"""
mapping des champs osm_dtype -> query correspondante 

!!---UNUSED---!!
"""
_FEATURE_QUERIES: list[tuple[str, callable]] = [
    ("trail",          query_trail),
    ("road",           query_road),
    ("water",          query_hydro),
    ("water_small",    query_hydro),
    ("water_crossing", query_water_crossing),
    ("bridge",         query_bridge),
    ("ford",           query_natural_water_crossing),
    ("vegetation",     query_vegetation),
    ("wetland",        query_wetland),
    ("peak",           query_peaks),
    ("cliff",          query_cliff),
    ("ridge",          query_ridge),
    ("valley",         query_valley),
    ("arete",          query_arete),
    ("scree",          query_scree),
    ("bare_rock",      query_bare_rock),
    ("glacier",        query_glacier),
    ("border",         query_border),
    ("building",       query_building),
]


"""
Map des features avec leur fonction de recherche, doit etre garder a jour

pattern : 

"feature" : lambda p (properties de osm_features) :
                bool(re.search(r"kw1|kw2|...|kwn",
                        p.get("relevant tag" OR {} (si get() = none))))

"""
_FEATURE_FILTERS: dict[str, callable] = {

    "trail":         lambda p: bool(re.search(r"path|footway|track|bridleway",
                         p.get("highway", "") or "")),
    "road":          lambda p: bool(re.search(
                         r"motorway|trunk|primary|secondary|tertiary|unclassified|residential|service",
                         p.get("highway", "") or "")),
    "water":         lambda p: (
                         bool(re.search(r"river|canal", p.get("waterway", "") or ""))
                         or p.get("natural") == "water"),
    "water_small":   lambda p: (
                         bool(re.search(r"stream|drain|ditch", p.get("waterway", "") or ""))),
    "water_crossing": lambda p: (
                         (p.get("bridge") == "yes" and bool(
                             p.get("highway") or p.get("railway") or p.get("footway") or p.get("path")))
                         or p.get("ford") == "yes"
                         or p.get("highway") == "stepping_stones"
                         or (p.get("tunnel") == "culvert" and bool(p.get("waterway")))),
    "bridge":        lambda p: (
                         p.get("bridge") == "yes" and bool(
                             p.get("highway") or p.get("railway") or p.get("footway") or p.get("path"))),
    "ford":          lambda p: (
                         p.get("ford") == "yes"
                         or p.get("natural") == "ford"
                         or p.get("waterway") == "ford"),
    "vegetation":    lambda p: (
                         bool(re.search(r"wood|grassland|heath|scrub", p.get("natural", "") or ""))
                         or bool(re.search(r"forest|farmland|meadow|orchard", p.get("landuse", "") or ""))),
    "wetland":       lambda p: (
                         p.get("natural") == "wetland"
                         or bool(re.search(r"marsh|bog|swamp|fen|reedbed", p.get("wetland", "") or ""))),
    "peak":      lambda p: p.get("natural") == "peak",
    "cliff":     lambda p: p.get("natural") == "cliff",
    "ridge":     lambda p: p.get("natural") == "ridge",
    "valley":    lambda p: p.get("natural") == "valley",
    "arete":     lambda p: p.get("natural") == "arete",
    "scree":     lambda p: p.get("natural") == "scree",
    "bare_rock": lambda p: p.get("natural") == "bare_rock",
    "glacier":   lambda p: p.get("natural") == "glacier",
    "border":    lambda p: (
                         p.get("boundary") == "administrative"
                         and p.get("admin_level") in ("2", "4")),
    "building":  lambda p: bool(p.get("building")),
}

"""
fichier de queries pour l'api overpass

rajoute des query lorsque besoin d'une nouvelle
autheur(s) : marc-emile scholer
date de creation : 07-05-26
"""
from ..structures_communes import BBox

def query_trail() -> str:
    return (
        "(way[\"highway\"~\"path|footway|track|bridleway\"];"
        "relation[\"highway\"~\"path|footway|track|bridleway\"];);"
    )

def query_road() -> str:
    return (
        "(way[\"highway\"~\"motorway|trunk|primary|secondary|tertiary|unclassified|residential|service\"];"
        "relation[\"highway\"~\"motorway|trunk|primary|secondary|tertiary|unclassified|residential|service\"];);"
    )

def query_hydro() -> str:
    return (
        "(way[\"waterway\"~\"river|stream|canal|drain|ditch\"];"
        "relation[\"waterway\"~\"river|stream|canal\"];"
        "way[\"natural\"=\"water\"];"
        "relation[\"natural\"=\"water\"];);"
    )

def query_vegetation() -> str:
    return (
        "(way[\"natural\"~\"wood|grassland|heath|scrub\"];"
        "relation[\"natural\"~\"wood|grassland|heath|scrub\"];"
        "way[\"landuse\"~\"forest|farmland|meadow|orchard\"];"
        "relation[\"landuse\"~\"forest|farmland|meadow|orchard\"];);"
    )

def query_wetland() -> str:
    return (
        "(way[\"natural\"=\"wetland\"];"
        "relation[\"natural\"=\"wetland\"];"
        "way[\"wetland\"~\"marsh|bog|swamp|fen|reedbed\"];"
        "relation[\"wetland\"~\"marsh|bog|swamp|fen|reedbed\"];);"
    )

def query_relief() -> str:
    return (
        "(node[\"natural\"=\"peak\"];"
        "way[\"natural\"~\"cliff|ridge|valley|arete\"];"
        "relation[\"natural\"~\"cliff|ridge|valley|arete\"];);"
    )

def query_natural_water_crossing() -> str:
    return (
        # gues naturels (point où un chemin traverse un cours d'eau a pied/vehicule)
        "(node[\"ford\"=\"yes\"];"
        "way[\"ford\"=\"yes\"];"
        # node explicitement tagués comme traversee naturelle
        "node[\"natural\"=\"ford\"];"
        # cours d'eau peu profond traversable (shallow)
        "node[\"waterway\"=\"ford\"];"
        "way[\"waterway\"=\"ford\"];);"
    )

def query_water_crossing() -> str:
    return (
        # ponts routiers/pietons au-dessus de l'eau
        "(way[\"bridge\"=\"yes\"][\"highway\"];"
        "way[\"bridge\"=\"yes\"][\"railway\"];"
        # gues (traversee a pied ou en vehicule dans l'eau)
        "node[\"ford\"=\"yes\"];"
        "way[\"ford\"=\"yes\"];"
        # passages a niveau sur cours d'eau (stepping_stones, culvert)
        "node[\"highway\"=\"stepping_stones\"];"
        "way[\"tunnel\"=\"culvert\"][\"waterway\"];"
        # passerelles pietonnes
        "way[\"bridge\"=\"yes\"][\"footway\"];"
        "way[\"bridge\"=\"yes\"][\"path\"];);"
    )

def query_peaks() -> str:
    return (
        "(node[\"natural\"=\"peak\"];);"
    )

def query_scree() -> str:
    return (
        "(way[\"natural\"=\"scree\"];"
        "relation[\"natural\"=\"scree\"];);"
    )

def query_bare_rock() -> str:
    return (
        "(way[\"natural\"=\"bare_rock\"];"
        "relation[\"natural\"=\"bare_rock\"];);"
    )

def query_border() -> str:
    return (
        "(relation[\"boundary\"=\"administrative\"][\"admin_level\"~\"2|4\"];);"
    )

def query_bridge() -> str:
    return (
        "(way[\"bridge\"=\"yes\"][\"highway\"];"
        "way[\"bridge\"=\"yes\"][\"railway\"];"
        "way[\"bridge\"=\"yes\"][\"footway\"];"
        "way[\"bridge\"=\"yes\"][\"path\"];);"
    )

def query_cliff() -> str:
    return (
        "(way[\"natural\"=\"cliff\"];"
        "relation[\"natural\"=\"cliff\"];);"
    )

def query_ridge() -> str:
    return (
        "(way[\"natural\"=\"ridge\"];"
        "relation[\"natural\"=\"ridge\"];);"
    )

def query_valley() -> str:
    return (
        "(way[\"natural\"=\"valley\"];"
        "relation[\"natural\"=\"valley\"];);"
    )

def query_arete() -> str:
    return (
        "(way[\"natural\"=\"arete\"];"
        "relation[\"natural\"=\"arete\"];);"
    )

def query_glacier() -> str:
    return (
        "(way[\"natural\"=\"glacier\"];"
        "relation[\"natural\"=\"glacier\"];);"
    )

def query_building() -> str:
    return (
        "(way[\"building\"];"
        "relation[\"building\"];);"
    )


def query_node_by_id(id : int) -> str:
    return (
        f"node({id});"
    )

def query_way_by_id(id : int) -> str:
    return (
        f"way({id});"
    )

def query_relation_by_id(id : int) -> str:
    return (
        f"relation({id});"
    )

def query_area_by_id(id : int) -> str:
    return (
        f"area({id});"
    )

    
#query une bounding box donnee 
def query_box(bbox : BBox) -> str:
    return (
        f"(node({bbox.sud},{bbox.ouest},{bbox.nord},{bbox.est});"
        f"way({bbox.sud},{bbox.ouest},{bbox.nord},{bbox.est});"
        f"relation({bbox.sud},{bbox.ouest},{bbox.nord},{bbox.est}););"
    )

# query les nodes dans une box
def query_nodes_in_box(bbox : BBox) -> str:
    return (
        f"(node({bbox.sud},{bbox.ouest},{bbox.nord},{bbox.est});"
    )


# query toute les features necessaires au raster dans le but de faire 1 seul call API
def query_all_features() -> str:
    return (
        "("
        + query_trail()
        + query_road()
        + query_hydro()
        + query_water_crossing()
        + query_bridge()
        + query_natural_water_crossing()
        + query_vegetation()
        + query_wetland()
        + query_peaks()
        + query_cliff()
        + query_ridge()
        + query_valley()
        + query_arete()
        + query_scree()
        + query_bare_rock()
        + query_glacier()
        + query_building()
        + ");"
    )


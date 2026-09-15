"""
fichier definissant la structure "weights"

celle ci est cree dynamiquement selon les contraintes donnees par le user 

sa structure est standardise comme suit :
"""
import numpy as np
# ici on préfère les trails que les routes
HIKING_WEIGHTS: dict[str, float] = {
    "trail": 0.8,
    "road": 1.6,
    "bridge": 1.00,

    # Obstacles et Milieux Naturels
    "vegetation":    1.85,
    "bare_rock":     2.00,
    "scree":         2.22,
    "wetland":       2.28,
    "glacier":       2.28,
    "arete":         2.42,

    # Milieux aquatiques
    "water_small":   2.42,
    "ford":          2.42,
    "water_crossing":2.57,

    "cliff": 30.0,  # Rupture de pente verticale
    # Barrières infranchissables
    "water": np.inf,  # Barrière physique (sauf si crossing/bridge)
    "building": np.inf,  # Obstacle urbain fermé
}
# weights par defaut arbitraires
DEFAULT_WEIGHTS: dict[str, float] = {
    "trail": 1.00,
    "road": 0.85,
    "bridge": 1.05,

    # Obstacles et Milieux Naturels
    "vegetation": 1.85,
    "bare_rock": 2.00,
    "scree": 2.22,
    "wetland": 2.28,
    "glacier": 2.28,
    "arete": 2.42,

    # Milieux Aquatiques
    "water_small": 2.42,
    "ford": 2.42,
    "water_crossing": 2.57,

    # Barrières infranchissables
    "water": np.inf,  # Barrière physique (sauf si crossing/bridge)
    "cliff": np.inf,  # Rupture de pente verticale
    "building": np.inf,  # Obstacle urbain fermé
}


# weights considerant un environnement tactique
TACTICAL_WEIGHTS: dict[str, float] = {
    "trail":          3.0,    # prefere sentiers
    "road":           250.0,   # evite routes voitures
    "water":          np.inf, # infranchissable
    "water_small":    30.0,   # ruisseau/fossé — difficile mais franchissable
    "water_crossing": 1.0,
    "bridge":         200.0,
    "ford":           15.2,
    "vegetation":     10.0,
    "wetland":        100.5,
    "cliff":          400.0,
    "scree":          20.8,
    "bare_rock":      20.8,
    "glacier":        35.0,
    "arete":          20.8,
    "building":       np.inf, # infranchissable
    # peak, ridge, valley, border → absent = 1.0 (neutre)
}

# gere des conflicts -> exemple : water = infini, mais 1.0 si il y a un crossing. dans une multiplication le infini va toujour gagner
# si tag X est present et que un tag y,z...etc est present, ignore X
_SUPPRESSED_BY: dict[str, list[str]] = {
    "water": ["water_crossing", "trail", "road"],  # eau infranchissable sauf si crossing présent
    "building": ["trail", "road"],   # un sentier qui traverse une empreinte = artefact 30 m
    "cliff":    ["trail", "road", "bridge"],
}


"""
FUTURE FONCTION POUR CUSTOM WEIGHTS, IGNORE FOR NOW
"""
def build_weights(contraintes : list[str]) -> dict[str, float]:
    weights = DEFAULT_WEIGHTS

    for contrainte in contraintes: 
        match contrainte:
            case "max_couvert":
                weights["vegetation"] = 0.6
            case "eviter_routes":
                weights["road"] = 9.0
            case "eviter_traverse_eau":
                weights["water_crossing"] = 1.8
            case _:
                raise ValueError(f"contrainte inconnue : {contrainte}")
    
    return weights

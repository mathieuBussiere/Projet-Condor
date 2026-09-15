"""
file pour parser des donnees binaire de format GeoTIFF 
acquerit via opentopography.

un GeoTIFF contient a la fois les valeurs d'elevation (grille de pixel/valeur(m)) 
et les metadonnees geographique (coin superieur gauche), taille des pixels et et le systeme de coordonnes)

autheur(s) : marc-emile scholer
date de creation : 11-05-26

TRANSFORM :

Affine(a,  b,  c,
       d,  e,  f)

Attribut Signification Valeur typique DEM
.a	largeur d'un pixel en longitude (deg/pixel)	+0.000277... (est)
.b	rotation col → ligne (row rotation)	0.0
.c	longitude du coin top-left	ex. -72.4
.d	rotation ligne → colonne (col rotation)	0.0
.e	hauteur d'un pixel en latitude (deg/pixel)	−0.000277... (négatif = vers le bas)
.f	latitude du coin top-left	ex. 45.5

"""
import rasterio
import rasterio.transform
import io
import numpy as np
from .structures_elevation import DEMdata
from ..structures_communes import latlon_to_rowcol_affine

_METRES_PAR_DEGREE_LAT = 111320.0

def _compute_slope(array: np.ndarray, transform: rasterio.transform.Affine) -> np.ndarray:
    """
    args : 
        array des elevations
        transform de cet array

    return :
        un array des slopes
    """
    # step 1 : la distance d'un degree de longitude est variable selon le cos de la latitude
    #          la distance d'un degre de latitude est presque constante
    m_per_deg_lat = _METRES_PAR_DEGREE_LAT                      # SCALAIRE, ne varie pas 
    lats = transform.f + transform.e * np.arange(array.shape[0])# VECTEUR des latitudes a chaque row
    m_per_deg_lon = m_per_deg_lat * np.cos(np.radians(lats))    # VECTEUR, varie beaucoup selon la latitude
    # step 2 : taile des pixels en metres
    pixel_h_m = abs(transform.e) * m_per_deg_lat # SCALAIRE * SCALAIRE 
    pixel_l_m = abs(transform.a) * m_per_deg_lon[:, np.newaxis] # SCALAIRE * VECTEUR + realigne range comme colonne
    # step 3 : gradient de l'elevation (m/pixel)
    dz_drow, dz_dcol = np.gradient(array) # retourne une liste de N arrays ou N = dimensions du input (2 ici)
    # dz_drow = variation de l'elevation par rapport aux rows N -> S
    # dz_dcol variation de l'elevation par rapport aux cols E -> W
    # step 4 : calculer le rise/run 
    dz_dy = dz_drow/pixel_h_m
    dz_dx = dz_dcol/pixel_l_m
    # dz_dy, dz_dx represente des array 2d pour la slope verticale et horizontale de chaque cells
    # step 5 : calculer pythagore pour chaque couple de cellule dans dz_dy, dz_dx + convertir en degrees
    magnitudes = np.sqrt(dz_dx**2 + dz_dy**2)

    # retourne array des slopes et aspects
    return np.arctan(magnitudes), _compute_aspect(dz_dy, dz_dx)



def _compute_aspect(dz_dy: np.ndarray, dz_dx : np.ndarray) -> np.ndarray:
    """
    args : 
        array des rises
        array des runs
    return :
        un array des aspects (direction de la pente)
    """
    aspect = (90 - np.degrees(np.arctan2(-dz_dy, dz_dx))) % 360
    return aspect


def parse_dem_data(data : bytes) -> DEMdata:
    """
    args : 
        data brut venant de opentopography

    return : 
        Objet DEMdata
    
    peut lever : 
        rasterio.errors.RasterioIOError : invalid data ou corrupted 
    """
    
    with rasterio.open(io.BytesIO(data)) as src : 
        # ici le 1 signifie quelle "band" du data on veut, c'est comme un layer.
        # dans un DEM, il n'y en a qu'une, a l'index 1 (convention geospatiale je pense)
        array = src.read(1).astype(float)
        transform = src.transform

        print(f"[PARSE DEBUG] raw: min={array.min():.1f}  max={array.max():.1f}  nodata={src.nodata}")

        # remplacer les valeurs invalides par nan (not a number)
        nodata = src.nodata
        if nodata is not None:
            nd_count = int((array == nodata).sum())
            print(f"[PARSE DEBUG] nodata pixels: {nd_count}/{array.size} ({nd_count/array.size:.0%})")
            array[array == nodata] = np.nan # ou array == no data, met nan

        # enleve les donnees absurde (rien de plus haut que everest (8848m) et pour le seuil du plus bas j'ai mis -500 parce qu'on marche pas sous leau anyway
        array[array > 9000.0] = np.nan
        array[array < -500.0] = np.nan

        data = _compute_slope(array, transform)
        slope = data[0]
        aspect = data[1]
    
    return DEMdata(array=array, transform=transform, slope=slope, aspect=aspect)

def elevation_at(dem : DEMdata, lat: float, lon: float) -> float:
    """
    retrieve l'elevation en metres au point (lat, lon)

    args :
        dem : resultat de parse_dem
        lat : latitude en degres decimaux
        lon : longitude en degres decimaux

    return :
        elevation en metres
    """
    # va chercher le row/col du point donne grace au transform
    row, col = latlon_to_rowcol_affine(dem.transform, lat, lon)
    # retour float(elevation at row/col)
    return float(dem.array[row, col])

# trouver l'elevation max dans une zone 
# linear scan bien simple
# pourrait recevoir juste la partie array...
def max_elevation(array : np.ndarray) -> float:
    # le array est 2d alors on doit l'applatir ici avec le max de numpy 
    return array.max()

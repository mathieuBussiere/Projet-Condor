import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dataclasses import dataclass
from data.structures_communes import BBox, latlon_to_rowcol_affine
from data.data_fetcher import fetch_terrain
from data.Elevation.structures_elevation import DEMType


"""
classe permettant de preconfigure des zones.
"""
@dataclass
class LocationConfig:
    name: str
    bbox: BBox
    demtype: DEMType = DEMType.COP30
    marker: tuple[int, int] | None = None   # (row, col) pixel
    marker_label: str = ""

ORFORD = LocationConfig(
    name="Mont Orford",
    bbox=BBox(45.1, -72.4, 45.5, -71.9),
    marker=(677, 570),
    marker_label="Sommet Mont Orford (853 m)"
)

EVEREST = LocationConfig(
    name="Mont Everest",
    bbox=BBox(27.6294397, 86.0995530, 28.7010582, 87.9116620),
    marker=None,
    marker_label="Sommet Mont Everest"
    )

COTOPAXI = LocationConfig(
    name="Cotopaxi",
    bbox=BBox(-0.7326320885029514, -78.48263740539552, -0.6328157849265642, -78.36908340454103),
    marker=None,
    marker_label="Volcan Cotopaxi"
    )


def main():
    print("chargement data...\n")
    fetch_terrain(ORFORD.bbox)
    lat = 45.28
    lon = -72.17
    row, col = latlon_to_rowcol_affine(ORFORD.bbox.dem_data.transform, lat, lon)

    print(f"ICIIIIIII ->>>>>>>>{row, col}")



if __name__ == "__main__":
    main()

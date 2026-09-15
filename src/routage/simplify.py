import math


def _project_local_xy(lat: float, lon: float, lat0: float) -> tuple[float, float]:
    """
    Projection simple lat/lon -> mètres (x, y),
    valide pour de petites zones (une bbox de rando, pas un pays).
    lat0 sert de référence pour la mise à l'échelle est-ouest.
    """
    R = 6_371_000.0
    x = math.radians(lon) * R * math.cos(math.radians(lat0))
    y = math.radians(lat) * R
    return x, y


def _perpendicular_distance(
    point: tuple[float, float],
    line_start: tuple[float, float],
    line_end: tuple[float, float],
) -> float:
    """Distance perpendiculaire (mètres) d'un point à la droite (pas le segment) start-end."""
    x0, y0 = point
    x1, y1 = line_start
    x2, y2 = line_end
    dx, dy = x2 - x1, y2 - y1

    if dx == 0.0 and dy == 0.0:
        return math.hypot(x0 - x1, y0 - y1)

    num = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1)
    den = math.hypot(dx, dy)
    return num / den


def simplifier_rdp(
    chemin_latlon: list[tuple[float, float]],
    epsilon_m: float = 5.0,
) -> list[tuple[float, float]]:
    """
    Réduit le nombre de points d'un chemin lat/lon tout en préservant sa
    forme, via Ramer-Douglas-Peucker. Un point n'est retiré que si tous les
    points qu'il "représente" restent à moins de epsilon_m mètres de la
    ligne droite reliant les points conservés de part et d'autre.

    args :
        chemin_latlon: liste de (lat, lon), ex: sortie de traduire_colrow_vers_latlon()
        epsilon_m: tolérance en mètres. Plus haut = moins de points, plus
            de simplification. 5-10m est raisonnable pour de la randonnée.

    return :
        Le chemin simplifié.
    """
    n = len(chemin_latlon)
    if n < 3:
        return list(chemin_latlon)

    lat0 = chemin_latlon[0][0]
    pts_xy = [_project_local_xy(lat, lon, lat0) for lat, lon in chemin_latlon]

    keep = [False] * n
    # RDP conserve toujours les deux extrémités : sans ça, le départ et
    # l'arrivée du chemin sont supprimés (segments droits jetés en entier).
    keep[0] = True
    keep[n - 1] = True

    stack = [(0, n - 1)]
    while stack:
        start_idx, end_idx = stack.pop()
        if end_idx <= start_idx + 1:
            continue

        p_start, p_end = pts_xy[start_idx], pts_xy[end_idx]

        max_dist = -1.0
        max_idx = start_idx
        for i in range(start_idx + 1, end_idx):
            d = _perpendicular_distance(pts_xy[i], p_start, p_end)
            if d > max_dist:
                max_dist = d
                max_idx = i

        if max_dist > epsilon_m:
            keep[max_idx] = True
            stack.append((start_idx, max_idx))
            stack.append((max_idx, end_idx))

    return [chemin_latlon[i] for i in range(n) if keep[i]]
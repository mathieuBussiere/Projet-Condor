import type { Coordinate } from "../types/Coordinate";

/**
 * Normalizes a point of unknown shape into { lat, lng }.
 * Handles:
 *  - { lat, lng } objects
 *  - [lat, lng] tuples (this app's `LatLng` type from useWaypoints)
 *  - GeoJSON Feature<Point> objects (coordinates are [lng, lat])
 */
export function toLatLng(point: unknown): Coordinate {
  if (Array.isArray(point) && point.length >= 2) {
    const [lat, lng] = point as [number, number];
    return { lat, lng };
  }

  if (point && typeof point === "object") {
    const p = point as any;
    if (typeof p.lat === "number" && typeof p.lng === "number") {
      return { lat: p.lat, lng: p.lng };
    }
    if (p.geometry?.coordinates) {
      const [lng, lat] = p.geometry.coordinates;
      return { lat, lng };
    }
  }

  throw new Error("Unrecognized point shape for GPX export");
}

export function toLatLngArray(points: unknown[]): Coordinate[] {
  return points.map(toLatLng);
}

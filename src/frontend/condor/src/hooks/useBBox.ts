import { useMemo } from "react";
import type { LatLng } from "./useWaypoints.ts";

export interface BoundingBox {
sud: number; ouest: number; nord: number; est: number
}

export type LeafletBounds = [[number, number], [number, number]];

interface UseBboxResult {
  bbox: BoundingBox | null;
  leafletBounds: LeafletBounds | null;
  showDebugBox: boolean;
}

type AcceptablePoint = LatLng | { lat: number; lng: number };

function normalizePoint(p: AcceptablePoint): [number, number] {
  if (Array.isArray(p)) return p as [number, number];
  if (p && typeof p === "object" && typeof (p as any).lat === "number" && typeof (p as any).lng === "number") {
    return [(p as any).lat, (p as any).lng];
  }
  throw new Error("Invalid coordinate shape passed to useBbox");
}

export function useBbox(start: AcceptablePoint | null, end: AcceptablePoint | null): UseBboxResult {
  const showDebugBox = import.meta.env.VITE_SHOW_DEBUG_BBOX === "true";

  return useMemo(() => {
    if (!start || !end) {
      return { bbox: null, leafletBounds: null, showDebugBox };
    }

    const [latA, lngA] = normalizePoint(start);
    const [latB, lngB] = normalizePoint(end);

    const latDelta = Math.abs(latA - latB);
    const lngDelta = Math.abs(lngA - lngB);
    const padding = Math.max(latDelta, lngDelta, 0.01) * 0.5; //dynamic buffer

    const north = Math.max(latA, latB) + padding;
    const south = Math.min(latA, latB) - padding;
    const east = Math.max(lngA, lngB) + padding;
    const west = Math.min(lngA, lngB) - padding;

    return {
      bbox: { sud: south, ouest: west, nord: north, est: east },
      leafletBounds: [
        [south, west],
        [north, east],
      ],
      showDebugBox,
    };
  }, [start, end, showDebugBox]);
}
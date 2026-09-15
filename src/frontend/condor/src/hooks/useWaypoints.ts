import { useState, useCallback } from "react";

export type LatLng = [number, number];

export function useWaypoints(initial: LatLng[] = []) {
  const [waypoints, setWaypoints] = useState<LatLng[]>(initial);

  const addWaypoint = useCallback((coords: LatLng) => {
    setWaypoints((prev) => [...prev, coords]);
  }, []);

  const removeWaypoint = useCallback((index: number) => {
    setWaypoints((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const updateWaypoint = useCallback((index: number, coords: LatLng) => {
    setWaypoints((prev) => {
      const updated = [...prev];
      updated[index] = coords;
      return updated;
    });
  }, []);

  const clearWaypoints = useCallback(() => {
    setWaypoints([]);
  }, []);

  return {
    waypoints,
    addWaypoint,
    removeWaypoint,
    updateWaypoint,
    clearWaypoints,
  };
}

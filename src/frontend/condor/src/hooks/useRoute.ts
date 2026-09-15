import { useState, useCallback } from "react";
import type { LatLng } from "./useWaypoints";
import type { RouteStatus } from "../types/Routes";

interface UseRouteReturn {
  start: LatLng | null;
  end: LatLng | null;
  routeFeatures: LatLng[];
  allWaypoints: LatLng[];
  status: RouteStatus;
  error: string | null;
  handleMapClick: (coords: LatLng) => void;
  reset: () => void;
  updateStart: (lat: number, lng: number) => void;
  updateEnd: (lat: number, lng: number) => void;
  updateWaypoint: (index: number, lat: number, lng: number) => void;
}

export function useRoute(): UseRouteReturn {
  const [start, setStart] = useState<LatLng | null>(null);
  const [end, setEnd] = useState<LatLng | null>(null);
  const [routeFeatures, setRouteFeatures] = useState<LatLng[]>([]);
  const [status, setStatus] = useState<RouteStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  const handleMapClick = useCallback(
    (coords: LatLng) => {
      if (status === "loading") return;

      if (!start) {
        setStart(coords);
        setEnd(null);
        setRouteFeatures([]);
        setStatus("idle");
        setError(null);
        return;
      }

      if (!end) {
        setEnd(coords);
        setStatus("idle");
        return;
      }

      setStart(coords);
      setEnd(null);
      setRouteFeatures([]);
      setStatus("idle");
      setError(null);
    },
    [start, status],
  );

  const reset = useCallback(() => {
    setStart(null);
    setEnd(null);
    setRouteFeatures([]);
    setStatus("idle");
    setError(null);
  }, []);

  // 👇 Implement the specific manual updaters
  const updateStart = useCallback((lat: number, lng: number) => {
    setStart([lat, lng]);
  }, []);

  const updateEnd = useCallback((lat: number, lng: number) => {
    setEnd([lat, lng]);
  }, []);

  const updateWaypoint = useCallback((index: number, lat: number, lng: number) => {
    setRouteFeatures((prev) =>
      prev.map((wp, i) => (i === index ? [lat, lng] : wp))
    );
  }, []);

  const allWaypoints: LatLng[] = [
    ...(start ? [start] : []),
    ...routeFeatures,
    ...(end ? [end] : []),
  ];

  return {
    start,
    end,
    routeFeatures,
    allWaypoints,
    status,
    error,
    handleMapClick,
    reset,
    // 👇 Export them
    updateStart,
    updateEnd,
    updateWaypoint,
  };
}
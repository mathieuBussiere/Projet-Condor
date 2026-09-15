import { useState, useCallback } from "react";
import type { LatLng } from "./useWaypoints";

interface GeocodingResult {
  name: string;
  coords: LatLng;
}

interface NavigationResult {
  distance: number; // km
  duration: number; // minutes
  path: LatLng[];
}

export function useNavigation() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [navigationResult, setNavigationResult] =
    useState<NavigationResult | null>(null);

  /** Forward geocode a place name → [lat, lng] using Nominatim */
  const geocodeAddress = useCallback(
    async (address: string): Promise<GeocodingResult | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}&limit=1`;
        const res = await fetch(url, { headers: { "Accept-Language": "en" } });
        const data = await res.json();
        if (!data.length) throw new Error(`No results for "${address}"`);
        const { lat, lon, display_name } = data[0];
        return {
          name: display_name,
          coords: [parseFloat(lat), parseFloat(lon)],
        };
      } catch (e: any) {
        setError(e.message);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  /** Reverse geocode [lat, lng] → human-readable name */
  const reverseGeocode = useCallback(
    async (coords: LatLng): Promise<string> => {
      try {
        const [lat, lng] = coords;
        const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`;
        const res = await fetch(url, { headers: { "Accept-Language": "en" } });
        const data = await res.json();
        return data.display_name ?? `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
      } catch {
        return `${coords[0].toFixed(5)}, ${coords[1].toFixed(5)}`;
      }
    },
    [],
  );

  /**
   * Call your FastAPI routing service.
   * Swap the URL / payload shape to match your backend.
   */
  const calculateRoute = useCallback(
    async (waypoints: LatLng[]): Promise<NavigationResult | null> => {
      if (waypoints.length < 2) return null;
      setIsLoading(true);
      setError(null);
      try {
        const res = await fetch("/api/route", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ waypoints }),
        });
        if (!res.ok) throw new Error(`Routing service returned ${res.status}`);
        const result: NavigationResult = await res.json();
        setNavigationResult(result);
        return result;
      } catch (e: any) {
        setError(e.message);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return {
    geocodeAddress,
    reverseGeocode,
    calculateRoute,
    navigationResult,
    isLoading,
    error,
  };
}

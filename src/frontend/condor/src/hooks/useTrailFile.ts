import { useState, useEffect } from "react";
import { parseGPX } from "@we-gold/gpxjs";
import type { LatLng } from "./useWaypoints";

export function useTrailFile(filePath: string | null) {
  const [trail, setTrail] = useState<LatLng[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!filePath) {
      setTrail([]);
      return;
    }

    const controller = new AbortController();
    const signal = controller.signal;

    setLoading(true);
    setError(null);

    fetch(filePath, { signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to fetch local stream target: ${response.statusText}`);
        }
        return response.text();
      })
      .then((rawText) => {
        let points: LatLng[] = [];
        const lowerPath = filePath.toLowerCase();

        if (lowerPath.includes(".gpx") || lowerPath.startsWith("blob:") || rawText.trim().startsWith("<")) {
          points = parseGPXFile(rawText);

          if (points.length === 0) {
            points = parseCSV(rawText);
          }
        } else {
          points = parseCSV(rawText);
        }

        setTrail(points);
      })
      .catch((e: any) => {
        if (e?.name === "AbortError") {
          // fetch aborted — ignore
          return;
        }
        console.error("[-] Hook fetch/parse failure:", e);
        setError(e.message ?? String(e));
      })
      .finally(() => {
        setLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [filePath]);

  return { trail, loading, error };
}

/**
 * Parses GPX using the type-safe @we-gold/gpxjs package
 */
function parseGPXFile(text: string): LatLng[] {
  const points: LatLng[] = [];

  try {
    const [gpx, parseError] = parseGPX(text);

    if (parseError) {
      console.warn("[-] @we-gold/gpxjs parsing notice:", parseError);
    }

    if (!gpx) return points;

    if (gpx.tracks && gpx.tracks.length > 0) {
      for (const track of gpx.tracks) {
        if (track.points && track.points.length > 0) {
          for (const pt of track.points) {
            if (pt.latitude !== undefined && pt.longitude !== undefined) {
              points.push([pt.latitude, pt.longitude]);
            }
          }
        }
      }
    }
    if (points.length === 0 && gpx.routes && gpx.routes.length > 0) {
      for (const route of gpx.routes) {
        if (route.points && route.points.length > 0) {
          for (const pt of route.points) {
            if (pt.latitude !== undefined && pt.longitude !== undefined) {
              points.push([pt.latitude, pt.longitude]);
            }
          }
        }
      }
    }

    if (points.length === 0 && gpx.waypoints && gpx.waypoints.length > 0) {
      for (const pt of gpx.waypoints) {
        if (pt.latitude !== undefined && pt.longitude !== undefined) {
          points.push([pt.latitude, pt.longitude]);
        }
      }
    }
  } catch (err) {
    console.error("[-] @we-gold/gpxjs parser failed unexpectedly:", err);
  }

  return points;
}

function parseCSV(text: string): LatLng[] {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  if (lines.length <= 1) return [];

  let headerLine = lines[0];

  if (headerLine.charCodeAt(0) === 0xfeff) {
    headerLine = headerLine.slice(1);
  }

  const delimiter = headerLine.includes(";") ? ";" : ",";
  const dataLines = lines.slice(1);

  const headers = headerLine.split(delimiter).map((h) => h.replace(/["']/g, "").trim().toLowerCase());

  const latIdx = headers.findIndex((h) => h === "lat" || h === "latitude" || h === "y");
  const lonIdx = headers.findIndex((h) => h === "lng" || h === "lon" || h === "longitude" || h === "x");

  if (latIdx === -1 || lonIdx === -1) {
    return dataLines
      .map((line) => {
        const columns = line.split(delimiter).map((col) => Number(col.replace(/["']/g, "").trim()));
        return [columns[0], columns[1]] as [number, number];
      })
      .filter(([lat, lon]) => !isNaN(lat) && !isNaN(lon));
  }

  return dataLines
    .map((line) => {
      const columns = line.split(delimiter);

      const rawLat = columns[latIdx] ? columns[latIdx].replace(/["']/g, "").trim() : "";
      const rawLon = columns[lonIdx] ? columns[lonIdx].replace(/["']/g, "").trim() : "";

      return [Number(rawLat), Number(rawLon)] as LatLng;
    })
    .filter(([lat, lon]) => !isNaN(lat) && !isNaN(lon));
}
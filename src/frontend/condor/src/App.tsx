import React, { useCallback, useMemo, useState, useEffect } from "react";

import { useWaypoints, type LatLng } from "./hooks/useWaypoints";
import MapView from "./components/map/MapView";
import Sidebar from "./components/sidebar/Sidebar";
import { useBbox } from "./hooks/useBBox.ts";
import { calculateTrajectory } from "./api/pathService";
import { compareRoute } from "./api/compareRouteService";
import Alert from "./components/ui/Alert";
import type { ExportResquest } from "./types/Export.ts";
import { toLatLng, toLatLngArray } from "./utils/geo.ts";
import { useWeather } from "./hooks/useWeather.ts";
import type { WeatherLayerType } from "./types/Weather.ts";
import type { MapStyleKey } from "./types/MapStyle.ts";
import type { RouteStatus } from "./types/Routes.ts";
import { Spinner } from "./components/ui/Spinner.tsx";

import { useRoute } from "./hooks/useRoute";

const DEFAULT_CENTER: LatLng = [45.401, -71.8922];

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Close sidebar on small screens by default
  useEffect(() => {
    if (window.innerWidth < 768) setSidebarOpen(false);
  }, []);
  // Route state moved into useRoute
  const {
    start,
    end,
    routeFeatures,
    allWaypoints: routeAllWaypoints,
    status: routeStatusFromHook,
    error: routeErrorFromHook,
    handleMapClick,
      updateStart,
    updateEnd,
    updateWaypoint,
    reset: routeReset,
  } = useRoute();

  // Trajectory points returned by the routing API (astar / optimized route)
  const [points, setPoints] = useState<LatLng[]>([]);
  const [distance, setDistance] = useState<string>("0");
  const [time, setTime] = useState<string>("0");
  const [avgElevation, setAvgElevation] = useState<number | null>(null);
  const [maxElevation, setMaxElevation] = useState<number | null>(null);
  const [trajectoryId, setTrajectoryId] = useState<string | null>(null);
  // Comparison metrics
  const [frechet, setFrechet] = useState<string>("0");
  const [dtw, setDtw] = useState<string>("0");
  const [effortRatio, setEffortRatio] = useState<string>("0");
  const [comparisonScore, setComparisonScore] = useState<number | null>(null);
  const [verdict, setVerdict] = useState<string | null>(null);

  // General UI state
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // File tracking
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [trailFilePath, setTrailFilePath] = useState<string | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);



  // Keep a separate list of manual waypoints (UI-only)
  const [waypoints, setWaypoints] = useState<[number, number][]>([]);

  const [mapStyle, setMapStyle] = useState<MapStyleKey>("topographic");

  const { bbox, leafletBounds, showDebugBox } = useBbox(start, end);

  const handleFileChange = useCallback((file: File | null) => {
    if (!file) {
      setUploadedFile(null);
      if (trailFilePath) {
        URL.revokeObjectURL(trailFilePath);
        setTrailFilePath(null);
      }
      return;
    }

    if (!(file instanceof Blob)) {
      setError("Invalid file structure");
      console.error("[-] Selected item is not a valid binary file structure.");
      return;
    }

    if (trailFilePath) {
      URL.revokeObjectURL(trailFilePath);
    }

    setUploadedFile(file);

    const blobUrl = URL.createObjectURL(file);
    setTrailFilePath(blobUrl);
  }, [trailFilePath]);

  const handleResetRoute = useCallback(() => {
    routeReset();
    setPoints([]);
    setDistance("0");
    setTime("0");
    setWaypoints([]);
    setError(null);
    setIsLoading(false);
  }, [routeReset]);

  const handleResetCompare = useCallback(() => {
    if (trailFilePath) {
      URL.revokeObjectURL(trailFilePath);
    }
    setUploadedFile(null);
    setTrailFilePath(null);
    setFrechet("0");
    setDtw("0");
    setEffortRatio("0");
    setComparisonScore(null);
    setVerdict(null);
    setError(null);
    setIsLoading(false);
    setFileInputKey((k) => k + 1);
  }, [trailFilePath]);

  const handleOptimizeRoute = useCallback(async () => {
    if (start && end && bbox) {
      setIsLoading(true);
      try {
        const routingRequest = {
          start: { lat: start[0], lng: start[1] },
          end: { lat: end[0], lng: end[1] },
          bbox: {
            sud: bbox.sud,
            ouest: bbox.ouest,
            nord: bbox.nord,
            est: bbox.est,
          },
        };

        const routeResponse = await calculateTrajectory(routingRequest);
        const trajectoryPoints = routeResponse.points.map(
          (p) => [p.lat, p.lng] as LatLng
        );
        setTrajectoryId(routeResponse.trajectory_id);

        setPoints(trajectoryPoints);
        setDistance(String(routeResponse.distance_km ?? 0));
        setTime(String(routeResponse.time ?? 0));
        setAvgElevation(routeResponse.avg_elevation_m ?? null);
        setMaxElevation(routeResponse.max_elevation_m ?? null);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsLoading(false);
      }
    }
  }, [bbox, start, end]);

  const handleCompareTrack = useCallback(async () => {
    if (!bbox || points.length === 0 || !uploadedFile) return;

    setIsLoading(true);
    try {
      const bboxPayload = {
        sud: bbox.sud,
        ouest: bbox.ouest,
        nord: bbox.nord,
        est: bbox.est,
      };

      const pointsPayload = points.map((p) => ({ lat: p[0], lng: p[1] }));

      const compResponse = await compareRoute(uploadedFile, bboxPayload, pointsPayload);

      const { score, verdict: compVerdict, metrics } = compResponse.comparison;
      setComparisonScore(score);
      setVerdict(compVerdict);
      setFrechet(String(metrics.frechet_distance_meters ?? 0));
      setDtw(String(metrics.dtw_corridor_deviation_meters ?? 0));
      setEffortRatio(String(metrics.tobler_effort_ratio ?? 0));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }, [bbox, points, uploadedFile]);

  const onRemoveWaypoint = useCallback((index: number) => {
    setWaypoints((prev) => prev.filter((_, i) => i !== index));
  }, []);


const exportRequest: ExportResquest | null = useMemo(() => {
  if (!start || !end || !trajectoryId) return null;
  return {
    trajectory_id: trajectoryId,
    name_track: `condor-route-${new Date().toISOString().slice(0, 10)}`,
    start: toLatLng(start),
    end: toLatLng(end),
    points: toLatLngArray(points),
  };
}, [start, end, points, trajectoryId]);
  const handleReset = useCallback(() => {
    if (trailFilePath) {
      URL.revokeObjectURL(trailFilePath);
    }
    routeReset();
    setPoints([]);
    setDistance("0");
    setTime("0");
    setWaypoints([]);
    setFrechet("0");
    setDtw("0");
    setEffortRatio("0");
    setComparisonScore(null);
    setVerdict(null);
    setError(null);
    setIsLoading(false);
    setUploadedFile(null);
    setTrailFilePath(null);
  }, [trailFilePath, routeReset]);

  const {
    weather,
    status: weatherStatus,
    error: weatherError,
    fetchWeather,
  } = useWeather();

  // Surface hook errors as a top-level Alert so users notice them
  useEffect(() => {
    if (routeErrorFromHook) setError(routeErrorFromHook);
  }, [routeErrorFromHook]);

  useEffect(() => {
    if (weatherError) setError(weatherError);
  }, [weatherError]);
  const [showWeatherLayer, setShowWeatherLayer] = useState(false);
  const [weatherLayerType, setWeatherLayerType] = useState<WeatherLayerType>("precipitation_new");
  const [weatherLayerOpacity, setWeatherLayerOpacity] = useState(0.6);

  const handleFetchWeather = useCallback(() => {
    const target = start ?? DEFAULT_CENTER;
    fetchWeather(target);
  }, [fetchWeather, start]);

  // Single memoized array for map/marker rendering
  const allWaypoints = useMemo(() => {
    return [start, ...points, end].filter(Boolean) as LatLng[];
  }, [start, points, end]);

  // routeStatus derived from start/end
  const routeStatus: RouteStatus = useMemo(() => (start && end ? "success" : "idle"), [start, end]);

  // remove leftover /unused useWaypoints call (was used previously)
  // useWaypoints([DEFAULT_START]); // removed on purpose

  return (
    <div className="fixed inset-0 flex overflow-hidden bg-slate-950 text-slate-200 font-sans">
      {/* Toggle for small screens */}
      <button
        aria-label="Toggle sidebar"
        onClick={() => setSidebarOpen((s) => !s)}
        className="md:hidden absolute top-4 left-4 z-[1400] p-2 bg-zinc-800/80 rounded-lg shadow-lg text-zinc-100"
      >
        {/* Simple hamburger */}
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {/* Backdrop when sidebar is open on small screens */}
      {sidebarOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/40 z-[1200]"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}
      {error && <Alert type="error" message={error} />}
      {isLoading && <Spinner />}

      <Sidebar
        start={start}
        end={end}
        waypoints={waypoints}
        onRemoveWaypoint={onRemoveWaypoint}
        avgElevation={avgElevation}
        maxElevation={maxElevation}
        onResetRoute={handleResetRoute}
        onResetCompare={handleResetCompare}
        fileInputKey={fileInputKey}
        distance={distance}
        onOptimizeRoute={handleOptimizeRoute}
        duration={time}
        onCompareTrack={handleCompareTrack}
        canCompare={points.length > 0 && !!uploadedFile}
        uploadedFile={uploadedFile}
        onFileChange={handleFileChange}
        frechet={frechet}
        dtw={dtw}
        effortRatio={effortRatio}
        comparisonScore={comparisonScore}
        verdict={verdict}
        weather={weather}
        weatherStatus={weatherStatus}
        weatherError={weatherError}
        showWeatherLayer={showWeatherLayer}
        weatherLayerType={weatherLayerType}
        weatherLayerOpacity={weatherLayerOpacity}
        onFetchWeather={handleFetchWeather}
        onToggleWeatherLayer={() => setShowWeatherLayer((v) => !v)}
        onWeatherLayerTypeChange={setWeatherLayerType}
        onWeatherOpacityChange={setWeatherLayerOpacity}
        isLoading={isLoading}
        exportRequest={exportRequest}
        onUpdateStart={updateStart}
        onUpdateEnd={updateEnd}
        onUpdateWaypoint={updateWaypoint}
        isOpen={sidebarOpen}
        onRequestClose={() => setSidebarOpen(false)}
      />

      <MapView
        style={mapStyle}
        onStyleChange={setMapStyle}
        allWaypoints={allWaypoints}
        astarWaypoints={allWaypoints}
        trailFilePath={trailFilePath}
        start={start}
        end={end}
        routeStatus={routeStatus}
        onMapClick={handleMapClick}
        showWeatherLayer={showWeatherLayer}
        weatherLayerType={weatherLayerType}
        weatherLayerOpacity={weatherLayerOpacity}
        leafletBounds={leafletBounds}
        showDebugBox={showDebugBox}
      />
    </div>
  );
}
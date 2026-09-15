import React, { useEffect, useState, useMemo, useCallback } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  ZoomControl,
  useMap,
  Rectangle,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { MAP_STYLES } from "./MapConfig";
import { MapStyleSwitcher } from "./controls/MapStyles";
import MapClickHandler from "./MapClickHandler";
import { MarkerIcon } from "./layers/MarkerIcon";
import type { LatLng } from "../../hooks/useWaypoints";
import MapHint from "./MapHint";
import WeatherLayer from "./layers/WeatherLayer";
import type { MapViewProps } from "../../types/MapView.ts";
import { useTrailFile } from "../../hooks/useTrailFile.ts";
import Trajectory, { type RouteStyle } from "./layers/Trajectory";
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-expect-error
import { MgrsGraticule } from "react-leaflet-mgrs-graticule";

function MapController({ style }: { style: string }) {
  const map = useMap();
  useEffect(() => {
    map.invalidateSize();
  }, [map, style]);
  return null;
}

const DEFAULT_CENTER: LatLng = [45.401, -71.8922];

// Quebec bounding box — SW corner to NE corner
const QUEBEC_BOUNDS: [[number, number], [number, number]] = [
  [44.9, -79.8],
  [62.6, -57.1],
];

function MapView({
  style,
  onStyleChange,
  allWaypoints = [],
  start,
  end,
  routeStatus,
  onMapClick,
  showWeatherLayer,
  weatherLayerType,
  weatherLayerOpacity,
  leafletBounds,
  showDebugBox,
  astarWaypoints,
  trailFilePath,
}: MapViewProps) {
  const currentMapStyle = useMemo(
    () => MAP_STYLES[style] ?? MAP_STYLES.topographic,
    [style]
  );

  const safeWaypoints = useMemo(() => allWaypoints ?? [], [allWaypoints]);
  const [showMgrsGrid, setShowMgrsGrid] = useState<boolean>(false);

  const { trail } = useTrailFile(trailFilePath ?? null);

  const routes = useMemo(() => {
    const out: { waypoints: LatLng[]; style: RouteStyle }[] = [];
    if (astarWaypoints && astarWaypoints.length >= 2) {
      out.push({ waypoints: astarWaypoints, style: "astar" as RouteStyle });
    }
    if (trail && trail.length >= 2) {
      out.push({ waypoints: trail, style: "real" as RouteStyle });
    }
    return out;
  }, [astarWaypoints, trail]);

  const onLocationSelect = useCallback(
    (_fmt: any, raw: LatLng) => {
      if (typeof onMapClick === "function") {
        onMapClick(raw);
      } else {
        console.error("MapView: onMapClick prop is missing or not a function", onMapClick);
      }
    },
    [onMapClick]
  );

  return (
    <main className="relative flex-1">
      <div className="absolute top-6 right-6 z-[1200] flex flex-col items-end gap-3">
        <div className="p-1.5 rounded-xl transition-colors">
          <MapStyleSwitcher
            currentStyle={style}
            onStyleChange={onStyleChange}
            showMgrsGrid={showMgrsGrid}
            onMgrsToggle={setShowMgrsGrid}
          />
        </div>
      </div>

      {routeStatus !== "loading" && <MapHint start={start} end={end} />}

      <MapContainer
        center={start ?? DEFAULT_CENTER}
        zoom={13}
        minZoom={6}
        maxZoom={17}
        zoomControl={false}
        className="h-full w-full z-0"
      >
        <MapController style={style} />
        <ZoomControl position="bottomright" />

        <TileLayer url={currentMapStyle.url} attribution="&copy; OSM / OpenTopo" zIndex={1} />

        {showWeatherLayer && <WeatherLayer type={weatherLayerType} opacity={weatherLayerOpacity} />}

        <MgrsGraticule
          name="Tactical MGRS Grid"
          checked={showMgrsGrid}
          options={{
            gridColor: "#020617",
            gridFontColor: "#f8fafc",
            hkColor: "#ef4444",
            gridFont: "bold 12px monospace",
          }}
        />

        {showDebugBox && leafletBounds && (
          <Rectangle
            bounds={leafletBounds}
            pathOptions={{
              color: "#615fff",
              weight: 2,
              opacity: 1,
              dashArray: "8, 8",
              fillColor: "#312c85",
              fillOpacity: 0.4,
            }}
          />
        )}

        {routeStatus !== "loading" && <MapClickHandler onLocationSelect={onLocationSelect} />}

        {routes.length > 0 && <Trajectory routes={routes} />}

        {safeWaypoints.map((pos, idx) => {
          const isOrigin = idx === 0;
          const isTarget = idx === safeWaypoints.length - 1 && !isOrigin;
          const icon = isOrigin ? MarkerIcon.origin : isTarget ? MarkerIcon.target : MarkerIcon.waypoint;

          return <Marker key={`waypoint-${idx}-${pos[0]}-${pos[1]}`} position={pos} icon={icon} />;
        })}
      </MapContainer>
    </main>
  );
}

export default React.memo(MapView);
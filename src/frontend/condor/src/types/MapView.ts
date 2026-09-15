import type { LatLng } from "../hooks/useWaypoints";
import type { MapStyleKey } from "./MapStyle.ts";
import type { WeatherLayerType } from "./Weather.ts";
import type { RouteStatus } from "./Routes.ts";
import type { RouteStyle } from "../components/map/layers/Trajectory.tsx";

export interface MapViewProps {
  style: MapStyleKey;
  onStyleChange: (style: MapStyleKey) => void;
  allWaypoints: LatLng[];
  start: LatLng | null;
  end: LatLng | null;
  routeStatus: RouteStatus;
  onMapClick: (coords: LatLng) => void;
  showWeatherLayer: boolean;
  weatherLayerType: WeatherLayerType;
  weatherLayerOpacity: number;
  leafletBounds: any;
  showDebugBox: boolean;
  astarWaypoints?: LatLng[];
  trailFilePath?: string; // e.g. "/trails/Sentier_du_Mont_SaintJoseph.csv"
  visibleRoutes?: RouteStyle[];
}

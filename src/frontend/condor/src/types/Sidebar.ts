import type { LatLng } from "../hooks/useWaypoints";
import React from "react";
import type { RouteStatus } from "./Routes";
import type { WeatherData, WeatherLayerType, WeatherStatus } from "./Weather";

export interface SidebarSectionProps {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

export interface SidebarProps {
  start: LatLng | null;
  end: LatLng | null;
  waypoints: [number, number][];
  onRemoveWaypoint: (index: number) => void;
  routeFeatures?: LatLng[];
  routeStatus?: RouteStatus;
  routeError?: string | null;
  onOptimizeRoute?: () => void;
  onResetRoute?: () => void;
  onResetCompare?: () => void;
  fileInputKey?: number;
  maxElevation: number | null;
  avgElevation: number | null;

  // route comparaison
  onCompareTrack: () => void;
  canCompare: boolean;
  uploadedFile: File | null;
  onFileChange: (file: File | null) => void;
  frechet?: string;
  dtw?: string;
  effortRatio?: string;
  comparisonScore?: number | null;
  verdict?: string | null;
  onUpdateStart?: (lat: number, lng: number) => void;
  onUpdateEnd?: (lat: number, lng: number) => void;
  onUpdateWaypoint?: (index: number, lat: number, lng: number) => void;

  // Weather
  weather?: WeatherData | null;
  weatherStatus?: WeatherStatus;
  weatherError?: string | null;
  showWeatherLayer?: boolean;
  weatherLayerType?: WeatherLayerType;
  weatherLayerOpacity?: number;
  onFetchWeather?: () => void;
  onToggleWeatherLayer?: () => void;
  onWeatherLayerTypeChange?: (t: WeatherLayerType) => void;
  onWeatherOpacityChange?: (v: number) => void;

  isLoading: boolean;
}

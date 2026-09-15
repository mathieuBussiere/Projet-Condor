import type { LatLng } from "../hooks/useWaypoints.ts";

export interface WeatherPanelProps {
  weather: WeatherData | null;
  status: WeatherStatus;
  error: string | null;
  showLayer: boolean;
  layerType: WeatherLayerType;
  layerOpacity: number;
  onToggleLayer: () => void;
  onLayerTypeChange: (t: WeatherLayerType) => void;
  onOpacityChange: (v: number) => void;
  onFetchWeather: () => void;
    isLoading: boolean;
}

export interface WeatherData {
  temp: number; // °C
  feelsLike: number; // °C
  windSpeed: number; // km/h
  windDirection: number; // degrees
  precipitation: number; // mm
  weatherCode: number; // WMO code
  description: string;
  coords: LatLng;
  fetchedAt: Date;
}

export type WeatherStatus = "idle" | "loading" | "success" | "error";

/**
 * OpenWeatherMap tile layers — free tier, no API key needed for the
 * open tile endpoint. See https://openweathermap.org/api/weathermaps for details.
 *
 * Available layer types:
 *   precipitation_new  — rainfall intensity (blue → purple)
 *   clouds_new         — cloud cover (white → grey)
 *   wind_new           — wind speed
 *   temp_new           — surface temperature
 *   pressure_new       — sea-level pressure
 */

export type WeatherLayerType =
  | "precipitation_new"
  | "clouds_new"
  | "wind_new"
  | "temp_new"
  | "pressure_new";

export const WEATHER_LAYER_LABELS: Record<WeatherLayerType, string> = {
  precipitation_new: "Precipitation",
  clouds_new: "Cloud cover",
  wind_new: "Wind",
  temp_new: "Temperature",
  pressure_new: "Pressure",
};

export interface WeatherLayerProps {
  type: WeatherLayerType;
  opacity?: number;
  apiKey?: string;
}

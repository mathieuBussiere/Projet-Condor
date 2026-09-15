import { TileLayer } from "react-leaflet";
import type { WeatherLayerProps } from "../../../types/Weather";

export default function WeatherLayer({
  type,
  opacity = 0.8,
  apiKey = import.meta.env.VITE_OPENWEATHERMAP_API_KEY,
}: WeatherLayerProps) {
  const url = `${import.meta.env.VITE_OPENWEATHERMAP_URL}/${type}/{z}/{x}/{y}.png?appid=${apiKey}`;
  return (
    <TileLayer
      url={url}
      opacity={opacity}
      zIndex={5000}
      maxZoom={20}
      maxNativeZoom={12}
    />
  );
}

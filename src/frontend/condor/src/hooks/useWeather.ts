import { useState, useCallback, useRef } from "react";
import { type LatLng } from "./useWaypoints";
import type { WeatherData, WeatherStatus } from "../types/Weather";
// WMO Weather interpretation codes → human label
const WMO_LABELS: Record<number, string> = {
  0: "Clear sky",
  1: "Mainly clear",
  2: "Partly cloudy",
  3: "Overcast",
  45: "Fog",
  48: "Icy fog",
  51: "Light drizzle",
  53: "Drizzle",
  55: "Heavy drizzle",
  61: "Light rain",
  63: "Rain",
  65: "Heavy rain",
  71: "Light snow",
  73: "Snow",
  75: "Heavy snow",
  77: "Snow grains",
  80: "Light showers",
  81: "Showers",
  82: "Heavy showers",
  85: "Snow showers",
  86: "Heavy snow showers",
  95: "Thunderstorm",
  96: "Thunderstorm w/ hail",
  99: "Thunderstorm w/ heavy hail",
};

export function weatherLabel(code: number): string {
  return WMO_LABELS[code] ?? "Unknown";
}

// WMO code → emoji for quick glance
export function weatherEmoji(code: number): string {
  if (code === 0 || code === 1) return "☀️";
  if (code === 2 || code === 3) return "⛅";
  if (code <= 48) return "🌫️";
  if (code <= 55) return "🌦️";
  if (code <= 65) return "🌧️";
  if (code <= 77) return "❄️";
  if (code <= 82) return "🌧️";
  if (code <= 86) return "🌨️";
  return "⛈️";
}

export function useWeather() {
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [status, setStatus] = useState<WeatherStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchWeather = useCallback(async (coords: LatLng) => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setStatus("loading");
    setError(null);

    const [lat, lng] = coords;
    const url = [
      "https://api.open-meteo.com/v1/forecast",
      `?latitude=${lat}&longitude=${lng}`,
      "&current=temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
      "&wind_speed_unit=kmh",
      "&forecast_days=1",
    ].join("");

    try {
      const res = await fetch(url, { signal: abortRef.current.signal });
      if (!res.ok) throw new Error(`Open-Meteo error ${res.status}`);
      const data = await res.json();
      const c = data.current;

      setWeather({
        temp: Math.round(c.temperature_2m),
        feelsLike: Math.round(c.apparent_temperature),
        windSpeed: Math.round(c.wind_speed_10m),
        windDirection: c.wind_direction_10m,
        precipitation: c.precipitation,
        weatherCode: c.weather_code,
        description: weatherLabel(c.weather_code),
        coords,
        fetchedAt: new Date(),
      });
      setStatus("success");
    } catch (e: any) {
      if (e.name === "AbortError") return;
      setError(e.message ?? "Failed to fetch weather");
      setStatus("error");
    }
  }, []);

  const clearWeather = useCallback(() => {
    abortRef.current?.abort();
    setWeather(null);
    setStatus("idle");
    setError(null);
  }, []);

  return { weather, status, error, fetchWeather, clearWeather };
}

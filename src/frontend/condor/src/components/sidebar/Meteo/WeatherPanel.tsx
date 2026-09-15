import { weatherEmoji } from "../../../hooks/useWeather";
import Alert from "../../ui/Alert";
import { Switch } from "@headlessui/react";
import { RotateCcw } from "lucide-react";
import SelectList from "../../ui/Select.tsx";
import {
  WEATHER_LAYER_LABELS,
  type WeatherPanelProps,
} from "../../../types/Weather";

function WindArrow({ deg }: { deg: number }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      style={{
        transform: `rotate(${deg}deg)`,
        display: "inline-block",
        verticalAlign: "middle",
      }}
    >
      <line
        x1="7"
        y1="12"
        x2="7"
        y2="2"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <polyline
        points="4,5 7,2 10,5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function WeatherPanel({
  weather,
  status,
  error,
  showLayer,
  layerOpacity,
  onToggleLayer,
  onLayerTypeChange,
  onOpacityChange,
  onFetchWeather,
  isLoading = false, // NEW: Add isLoading prop
}: WeatherPanelProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <button
          onClick={onFetchWeather}
          disabled={status === "loading" || isLoading} // MODIFIED: Add isLoading check
          className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-[12px] active:bg-sky-600  bg-sky-500 border border-zinc-700  hover:bg-sky-400 text-white disabled:opacity-40 transition-colors"
        >
          {status === "loading" ? (
            <span className="animate-pulse">Fetching…</span>
          ) : (
            <>
              <RotateCcw size={12} />
              <span>Fetch weather</span>
            </>
          )}
        </button>
        <span className="text-xs text-zinc-100">Show layer</span>
        <Switch
          checked={showLayer}
          onChange={isLoading ? undefined : onToggleLayer} // MODIFIED: Disable toggle during loading
          disabled={isLoading}
          className={`${showLayer ? "bg-sky-600" : "bg-zinc-700"}
    relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
            isLoading ? "opacity-50" : ""
          }`}
        >
          <span className="sr-only">Toggle layer</span>
          <span
            aria-hidden="true"
            className={`${showLayer ? "translate-x-4" : "translate-x-0"}
      pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out`}
          />
        </Switch>
      </div>

      {/* Weather data card */}
      {status === "success" && weather && (
        <div className="rounded-lg bg-zinc-800/60 border border-zinc-700 p-3 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-2xl">
              {weatherEmoji(weather.weatherCode)}
            </span>
            <div className="text-right">
              <p className="text-lg font-semibold text-zinc-100 leading-none">
                {weather.temp}°C
              </p>
              <p className="text-[10px] text-zinc-300">
                Feels {weather.feelsLike}°C
              </p>
            </div>
          </div>

          <p className="text-[11px] text-zinc-300">{weather.description}</p>

          <div className="grid grid-cols-2 gap-x-4 gap-y-1 pt-1 border-t border-zinc-700">
            <div className="flex items-center gap-1.5 text-[10px] text-zinc-300">
              <WindArrow deg={weather.windDirection} />
              <span>{weather.windSpeed} km/h</span>
            </div>
            <div className="text-[10px] text-zinc-300">
              💧 {weather.precipitation} mm
            </div>
          </div>

          <p className="text-[9px] text-zinc-300 font-mono">
            {weather.coords[0].toFixed(4)}, {weather.coords[1].toFixed(4)}
            {" · "}
            {weather.fetchedAt.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </div>
      )}

      {error && <Alert type="error" message={error} />}

      {showLayer && (
        <div className="flex flex-col gap-2 pt-1">
          <div className="flex flex-col gap-1">
            <SelectList
              labels={WEATHER_LAYER_LABELS}
              onSelect={onLayerTypeChange}
              labelTitle="Layer"
              disabled={isLoading} // NEW: Disable dropdown during loading
            />
          </div>

          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] text-zinc-300  tracking-wider">
                Opacity
              </label>
              <span className="text-[10px] font-mono text-zinc-300">
                {Math.round(layerOpacity * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0.1"
              max="1"
              step="0.05"
              value={layerOpacity}
              onChange={(e) => {
                if (!isLoading) onOpacityChange(parseFloat(e.target.value));
              }}
              disabled={isLoading}
              className={`w-full accent-sky-500 ${
                isLoading ? "opacity-50" : ""
              }`}
            />
          </div>
        </div>
      )}
    </div>
  );
}
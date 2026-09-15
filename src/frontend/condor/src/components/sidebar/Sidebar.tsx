import {
  Crosshair,
  Activity,
  Cloud,
  GitCompare,
} from "lucide-react";
import Branding from "../ui/Branding";
import SidebarSection from "../ui/SidebarSection";
import StatPanel from "./Stats/StatPanel";

import WaypointList from "./Navigation/WaypointsList";
import Alert from "../ui/Alert";
import WeatherPanel from "./Meteo/WeatherPanel";
import { ExportBtn } from "../ui/ExportBtn.tsx";
import type { SidebarProps } from "../../types/Sidebar.ts";
import ComparisonResults from "./Compare/ComparaisonPanel.tsx";
import React from "react";

function Sidebar({
  start,
  end,
  routeFeatures,
  routeStatus,
  routeError,
  onResetRoute,
  onResetCompare,
  fileInputKey,
  maxElevation,
  avgElevation,
  onCompareTrack,
  canCompare = false,
  frechet = "-",
  dtw = "-",
  effortRatio = "-",
  comparisonScore = null,
  verdict = null,
  distance = "—",
  duration = "—",
  uploadedFile,
  onFileChange,
  weather,
  weatherStatus,
  weatherError,
  showWeatherLayer,
  weatherLayerType,
  weatherLayerOpacity,
  onFetchWeather,
  onToggleWeatherLayer,
  onWeatherLayerTypeChange,
  onWeatherOpacityChange,
  onOptimizeRoute,
  isLoading = false,
  exportRequest,
    onUpdateWaypoint,
    onUpdateStart,
    onUpdateEnd,
  isOpen = true,
  onRequestClose,
}: SidebarProps & { isOpen?: boolean; onRequestClose?: () => void }) {
  // responsive: overlay on small screens, static on md+
  return (
    <aside className={`w-85 fixed inset-y-0 left-0 shrink-0 bg-zinc-900/90 backdrop-blur-md border-r border-zinc-800 p-6 flex flex-col gap-6 z-3000 shadow-2xl transform transition-transform duration-300 ease-in-out md:translate-x-0 ${isOpen ? "translate-x-0" : "-translate-x-full"}`}>
      {/* Close for small screens */}
      <div className="md:hidden mb-2 -mr-2 flex justify-end">
        <button
          aria-label="Close sidebar"
          onClick={() => onRequestClose?.()}
          className="p-2 rounded bg-zinc-800/70 hover:bg-zinc-700 text-zinc-100"
        >
          ×
        </button>
      </div>
      <Branding />

      <div className="flex flex-col gap-6 overflow-y-auto pr-2 custom-scrollbar">
        {routeStatus === "loading" && (
          <Alert type="info" message="Calculating route…" dismissible={false} />
        )}
        {routeStatus === "success" && (
          <Alert
            type="success"
            message={`Route found — ${routeFeatures ? routeFeatures.length : 0} waypoints loaded.`}
          />
        )}
        {routeStatus === "error" && routeError && (
          <Alert type="error" message={routeError} />
        )}
        <SidebarSection title="Route Planner" icon={Crosshair}>
          <WaypointList
            start={start}
            end={end}
            features={routeFeatures}
            onOptimizeRoute={onOptimizeRoute ?? (() => {})}
            isLoading={isLoading}
            uploadedFile={uploadedFile}
            onFileChange={(f) => onFileChange?.(f as any)}
            onCompareTrack={onCompareTrack ?? (() => {})}
            canCompare={canCompare}
            onResetRoute={onResetRoute}
            onResetCompare={onResetCompare}
            fileInputKey={fileInputKey}
            // Pass them down here 👇
            onUpdateStart={onUpdateStart}
            onUpdateEnd={onUpdateEnd}
            onUpdateWaypoint={onUpdateWaypoint}
          />
        </SidebarSection>
        {comparisonScore !== null && (
          <SidebarSection title="Track Comparison" icon={GitCompare}>
            <ComparisonResults
              comparisonScore={comparisonScore}
              verdict={verdict}
              dtw={dtw}
              frechet={frechet}
              effortRatio={effortRatio}
            />
          </SidebarSection>
        )}
        <SidebarSection title="Weather" icon={Cloud}>
          <WeatherPanel
            weather={weather ?? null}
            status={(weatherStatus ?? ("idle" as any)) as any}
            error={weatherError ?? null}
            showLayer={!!showWeatherLayer}
            layerType={(weatherLayerType ?? ("radar" as any)) as any}
            layerOpacity={weatherLayerOpacity ?? 1}
            onToggleLayer={onToggleWeatherLayer ?? (() => {})}
            onLayerTypeChange={onWeatherLayerTypeChange ?? (() => {})}
            onOpacityChange={onWeatherOpacityChange ?? (() => {})}
            onFetchWeather={onFetchWeather ?? (() => {})}
            isLoading={isLoading}
          />
        </SidebarSection>


        <SidebarSection title="Telemetry" icon={Activity}>
          <StatPanel
            distance={distance}
            duration={duration}
            maxElevation={maxElevation}
            averageElevation={avgElevation}
          />
        </SidebarSection>
      </div>

      <div className="mt-auto pt-4 flex items-center justify-between text-[10px] text-zinc-500 font-mono">
        <ExportBtn isLoading={isLoading} exportRequest={exportRequest} />
      </div>
    </aside>
  );
}

export default React.memo(Sidebar);

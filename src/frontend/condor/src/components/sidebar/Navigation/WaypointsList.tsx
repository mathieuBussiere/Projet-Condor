import type { LatLng } from "../../../hooks/useWaypoints";
import { GitCompare, RotateCcw } from "lucide-react";
import {CoordInput} from "./CoordInput"
interface WaypointListProps {
  start: LatLng | null;
  end: LatLng | null;
  features?: LatLng[];
  onOptimizeRoute: () => void;
  isLoading?: boolean;
  uploadedFile: File | null;
  onFileChange: (file: File | null) => void;
  onCompareTrack: () => void;
  canCompare: boolean;
  onResetRoute?: () => void;
  onResetCompare?: () => void;
  fileInputKey?: number;
  onUpdateStart?: (lat: number, lng: number) => void;
  onUpdateEnd?: (lat: number, lng: number) => void;
  onUpdateWaypoint?: (index: number, lat: number, lng: number) => void;
}

function CoordBadge({ lat, lng }: { lat?: number | null; lng?: number | null }) {
  const isValid =
    typeof lat === "number" &&
    typeof lng === "number" &&
    !isNaN(lat) &&
    !isNaN(lng);

  if (!isValid) {
    return (
      <span className="font-mono text-[10px] text-red-400/80 bg-red-400/10 px-1 py-0.5 rounded">
        Invalid Coordinates
      </span>
    );
  }

  return (
    <span className="font-mono text-[10px] text-zinc-300">
      {lat.toFixed(4)}, {lng.toFixed(4)}
    </span>
  );
}
function Row({
  dot,
  label,
  sub,
  coords,
  muted,
  onCoordsChange,
}: {
  dot: string;
  label: string;
  sub?: string;
  coords?: [number | null | undefined, number | null | undefined] | null;
  muted?: boolean;
  onCoordsChange?: (lat: number, lng: number) => void;
}) {
  return (
    <li className={`flex items-start gap-2.5 py-2 ${muted ? "opacity-40" : ""}`}>
      <span className={`mt-1 size-2 shrink-0 rounded-full ${dot}`} />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-zinc-200 leading-tight">
          {label}
        </p>
        {sub && <p className="text-[10px] text-zinc-500">{sub}</p>}

        {/* Render our new input component */}
        <CoordInput
          lat={coords?.[0]}
          lng={coords?.[1]}
          onChange={onCoordsChange}
        />
      </div>
    </li>
  );
}
export default function WaypointList({
  start,
  end,
  features = [],
  onOptimizeRoute,
  isLoading = false,
  uploadedFile,
  onFileChange,
  onCompareTrack,
  canCompare,
  onResetRoute,
  onResetCompare,
  fileInputKey,
    onUpdateStart,
  onUpdateEnd,
  onUpdateWaypoint,
}: WaypointListProps) {
  const hasRoute = features?.length > 0;

  const handleFileElementChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileChange(e.target.files[0]);
    }
  };

  return (
    <div className="flex flex-col">
      <ul className="flex flex-col divide-y divide-zinc-800/60">
      {/* Origin */}
        <Row
          dot="bg-sky-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]"
          label="Origin"
          coords={start ?? undefined}
          sub={!start ? "Awaiting deployment point..." : "Mission Start"}
          muted={!start}
          onCoordsChange={onUpdateStart}
        />

        {hasRoute &&
          features.map((coords, idx) => (
            <Row
              key={`wp-${idx}-${coords[0]}-${coords[1]}`}
              dot="bg-amber-500"
              label={`Waypoint ${idx + 1}`}
              sub={undefined}
              coords={coords}
              
              onCoordsChange={(lat, lng) => onUpdateWaypoint?.(idx, lat, lng)}
            />
          ))}

        {/* Destination */}
        <Row
          dot="bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]"
          label="Destination"
          coords={end ?? undefined}
          sub={!start ? "Set origin first" : !end ? "Mark target on map" : "Objective Reachable"}
          muted={!end}
          onCoordsChange={onUpdateEnd}
        />
      </ul>

      <div className="mt-4 flex flex-col gap-2 pt-2 border-t border-zinc-800/60">
        <button
          onClick={onOptimizeRoute}
          disabled={!start || !end || isLoading}
          className="w-full py-2 bg-sky-600 hover:bg-sky-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white rounded text-sm font-semibold transition-colors flex items-center justify-center gap-2"
        >
          Optimize Route
        </button>

        {/* Dynamic File Upload Input Slot */}
        <div className="flex flex-col gap-1.5">
          <label className="text-[11px] text-zinc-300 font-medium">
            Reference Track (.csv, .gpx)
          </label>
          <div className="relative flex items-center justify-between bg-zinc-800 border border-zinc-700 rounded px-2.5 py-1.5 hover:border-zinc-600 transition-colors group">
            <span className="text-xs truncate max-w-[180px] text-zinc-300 font-mono">
              {uploadedFile ? uploadedFile.name : "No file selected"}
            </span>
            <label className="text-[10px]  hover:bg-zinc-700 text-zinc-100 px-2 py-0.5 rounded cursor-pointer font-medium transition-colors select-none">
              Browse
              <input
                key={fileInputKey ?? 0}
                type="file"
                accept=".csv,.gpx"
                onChange={handleFileElementChange}
                className="hidden"
                disabled={isLoading}
              />
            </label>
          </div>
        </div>

        <button
          onClick={onCompareTrack}
          disabled={!canCompare || isLoading}
          className="w-full py-2 bg-teal-700 hover:bg-teal-600 disabled:bg-zinc-800/40 disabled:text-zinc-700 text-white rounded text-sm font-semibold transition-colors flex items-center justify-center gap-2 border border-teal-600/30 disabled:border-transparent"
        >
          <GitCompare className="size-4" />
          Compare with Reference
        </button>

        <div className="flex gap-2 mt-1">
          {(start || end) && (
            <button
              onClick={onResetRoute}
              disabled={isLoading}
              className="flex-1 flex font-bold items-center justify-center gap-1.5 py-1 text-[12px] text-zinc-400 hover:text-sky-400 disabled:text-zinc-600 transition-colors rounded border border-zinc-800/40"
            >
              <RotateCcw className="size-3" />
              Reset route
            </button>
          )}

          {uploadedFile && (
            <button
              onClick={onResetCompare}
              disabled={isLoading}
              className="flex-1 flex font-bold items-center justify-center gap-1.5 py-1 text-[12px] text-zinc-400 hover:text-rose-400 disabled:text-zinc-600 transition-colors rounded border border-zinc-800/40"
            >
              <RotateCcw className="size-3" />
              Reset comparison
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

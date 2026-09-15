import { Grid3X3, Layers, Layers2 } from "lucide-react";
import { MAP_STYLES } from "../MapConfig";
import type {
  MapStyleKey,
  MapStyleSwitcherProps,
} from "../../../types/MapStyle";
import { useState } from "react";

export function MapStyleSwitcher({
  currentStyle,
  onStyleChange,
  showMgrsGrid,
  onMgrsToggle,
}: MapStyleSwitcherProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  return (
    <div className="flex items-center bg-zinc-900/90 backdrop-blur-md p-1 rounded-xl border border-zinc-800/10 shadow-2xl">
      <div className="px-2 border-r border-zinc-800 mr-1 text-zinc-400">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={`hover:text-sky-300  group p-2 rounded-lg transition-colors flex items-center justify-center ${
            isExpanded ? "text-sky-400" : "text-zinc-400 hover:bg-zinc-800"
          }`}
        >
          <div
            className={`transition-all duration-500 transform ${isExpanded ? "rotate-0 scale-110" : "rotate-180 scale-100"}`}
          >
            {isExpanded ? <Layers size={18} /> : <Layers2 size={18} />}
          </div>
        </button>
      </div>
      <div
        className={`flex items-center gap-1 transition-all duration-500 ease-in-out overflow-hidden ${
          isExpanded ? "max-w-md opacity-100 ml-1" : "max-w-0 opacity-0 ml-0"
        }`}
      >
        {(Object.keys(MAP_STYLES) as MapStyleKey[]).map((key) => {
          const config = MAP_STYLES[key];
          return (
            <button
              key={key}
              onClick={() => onStyleChange(key)}
              className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all duration-300 ${
                currentStyle === key
                  ? "bg-sky-600 text-white shadow-lg shadow-blue-500/40"
                  : "text-zinc-400 hover:text-zinc-300 hover:bg-zinc-800/50"
              }`}
            >
              {config.name}
            </button>
          );
        })}
        <div className="w-px h-6 bg-zinc-800 mx-1 rounded-full" />

        {/* 2. MGRS Toggle / Checkbox */}
        <label className="flex items-center gap-2 px-3 py-2 cursor-pointer rounded-xl transition-all hover:bg-zinc-800/50 group">
          <div className="relative flex items-center">
            <input
              type="checkbox"
              className="sr-only"
              checked={showMgrsGrid}
              onChange={(e) => onMgrsToggle(e.target.checked)}
            />
            {/* Custom Toggle Track */}
            <div
              className={`w-8 h-4 rounded-full transition-colors duration-300 ${
                showMgrsGrid ? "bg-sky-500" : "bg-zinc-700"
              }`}
            >
              {/* Custom Toggle Dot */}
              <div
                className={`absolute top-0.5 left-0.5 bg-white w-3 h-3 rounded-full transition-transform duration-300 shadow-sm ${
                  showMgrsGrid ? "translate-x-4" : "translate-x-0"
                }`}
              />
            </div>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-zinc-400 group-hover:text-zinc-300">
            <Grid3X3 size={12} className={showMgrsGrid ? "text-sky-400" : ""} />
            <span className={showMgrsGrid ? "text-sky-400" : ""}>MGRS</span>
          </div>
        </label>
      </div>
    </div>
  );
}

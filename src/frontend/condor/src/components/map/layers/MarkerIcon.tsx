import L from "leaflet";
import type { PinOptions } from "../../../types/PinOptions";

const createPin = ({ color, glow }: PinOptions) => {
  return L.divIcon({
    className: "custom-tactical-pin",
    html: `
      <div class="relative flex items-center justify-center">
        <div class="absolute w-8 h-8 ${glow} rounded-full animate-pulse opacity-40"></div>
        
        <svg width="28" height="36" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="drop-shadow-lg">
          <path d="M12 0C7.58 0 4 3.58 4 8C4 13.54 12 22 12 22C12 22 20 13.54 20 8C20 3.58 16.42 0 12 0Z" 
                class="${color} fill-current stroke-zinc-950 stroke-[1.5px]" />
          <circle cx="12" cy="8" r="2.5" fill="white" />
        </svg>
      </div>`,
    iconSize: [28, 36],
    iconAnchor: [14, 36],
  });
};

export const MarkerIcon = {
  origin: createPin({ color: "text-sky-500", glow: "bg-sky-500/20" }),
  waypoint: createPin({ color: "text-amber-500", glow: "bg-amber-500/20" }),
  target: createPin({ color: "text-red-500", glow: "bg-red-500/20" }),
};

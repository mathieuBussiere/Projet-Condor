import type { MapHintProps } from "../../types/MapHint";

export default function MapHint({ start, end }: MapHintProps) {
  const message = !start
    ? "Click to place origin"
    : !end
      ? "Click to place destination"
      : "Click anywhere to start a new route";

  return (
    <div className="absolute bottom-10 left-1/2 -translate-x-1/2 z-1200 pointer-events-none">
      <div className="bg-zinc-900/80 backdrop-blur-sm text-zinc-300 text-[10px] font-mono px-4 py-2 rounded-full border border-zinc-700 shadow-2xl transition-all duration-500 ease-in-out">
        <div className="flex  items-center gap-2.5">
          <span className="tracking-wider">{message}</span>
        </div>
      </div>
    </div>
  );
}

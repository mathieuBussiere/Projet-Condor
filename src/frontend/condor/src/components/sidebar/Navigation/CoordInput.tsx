import { useState, useEffect } from "react";

interface CoordInputProps {
  lat?: number | null;
  lng?: number | null;
  onChange?: (lat: number, lng: number) => void;
  label?: string;
}

const LAT_MIN = -90;
const LAT_MAX = 90;
const LNG_MIN = -180;
const LNG_MAX = 180;

export function CoordInput({ lat, lng, onChange, label }: CoordInputProps) {
  const [valLat, setValLat] = useState(lat != null ? lat.toFixed(4) : "");
  const [valLng, setValLng] = useState(lng != null ? lng.toFixed(4) : "");
  const [error, setError] = useState<string | null>(null);

  // Sync local state if coords are updated via Map clicks
  useEffect(() => {
    if (lat != null) setValLat(lat.toFixed(4));
    if (lng != null) setValLng(lng.toFixed(4));
  }, [lat, lng]);

  const validate = (rawLat: string, rawLng: string): string | null => {
    if (rawLat.trim() === "" || rawLng.trim() === "") {
      return "Lat and long are required.";
    }

    const parsedLat = parseFloat(rawLat);
    const parsedLng = parseFloat(rawLng);

    if (Number.isNaN(parsedLat) || Number.isNaN(parsedLng)) {
      return "Coordinates must be numbers.";
    }
    if (parsedLat < LAT_MIN || parsedLat > LAT_MAX) {
      return `Lat must be between ${LAT_MIN} and ${LAT_MAX}.`;
    }
    if (parsedLng < LNG_MIN || parsedLng > LNG_MAX) {
      return `Long must be between ${LNG_MIN} and ${LNG_MAX}.`;
    }
    return null;
  };

  const handleBlur = () => {
    const validationError = validate(valLat, valLng);
    setError(validationError);

    if (!validationError && onChange) {
      onChange(parseFloat(valLat), parseFloat(valLng));
    }
  };

  // Clear a stale error as soon as the user starts fixing the value —
  // otherwise it hangs around, out of sync, until the next blur.
  const handleLatChange = (value: string) => {
    setValLat(value);
    if (error) setError(null);
  };

  const handleLngChange = (value: string) => {
    setValLng(value);
    if (error) setError(null);
  };

  return (
    <div className="flex flex-col gap-0.5 mt-0.5">
      <div className="flex items-center gap-1 font-mono text-[10px] text-zinc-300">
        {label && <span className="text-zinc-400 mr-1">{label}</span>}
        <label className="text-[10px] text-zinc-300">Lat</label>
        <input
          type="text"
          value={valLat}
          onChange={(e) => handleLatChange(e.target.value)}
          onBlur={handleBlur}
          placeholder="Lat"
          aria-invalid={!!error}
          className={`w-16 bg-zinc-800/50 border rounded px-1 py-0.5 focus:outline-none transition-colors ${
            error
              ? "border-red-500/70 focus:border-red-500"
              : "border-zinc-700/50 focus:border-sky-500"
          }`}
        />
        <span className="text-zinc-500">,</span>
        <label className="text-[10px] text-zinc-300">Long</label>
        <input
          type="text"
          value={valLng}
          onChange={(e) => handleLngChange(e.target.value)}
          onBlur={handleBlur}
          placeholder="Lng"
          aria-invalid={!!error}
          className={`w-16 bg-zinc-800/50 border rounded px-1 py-0.5 focus:outline-none transition-colors ${
            error
              ? "border-red-500/70 focus:border-red-500"
              : "border-zinc-700/50 focus:border-sky-500"
          }`}
        />
      </div>
      {error && <p className="text-[10px] text-red-400 font-mono">{error}</p>}
    </div>
  );
}

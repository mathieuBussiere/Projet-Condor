import { Navigation } from "lucide-react";

export default function Branding() {
  return (
    <div className="flex items-center gap-4 mb-4">
      <div className="p-2.5 bg-sky-600 rounded-xl shadow-lg shadow-blue-500/20 ring-1 ring-sky-400/30">
        <Navigation size={20} className="text-white fill-white" />
      </div>
      <div>
        <h1 className="text-xl font-black tracking-tighter italic leading-none">
          CONDOR
        </h1>
        <p className="text-[9px] text-sky-500 font-bold tracking-[0.3em] mt-1 uppercase">
          Tactical Nav
        </p>
      </div>
    </div>
  );
}

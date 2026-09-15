import {
  Disclosure,
  DisclosureButton,
  DisclosurePanel,
  Transition,
} from "@headlessui/react";
import {
  Activity,
  Navigation,
  Clock,
  Ruler,
  ChevronDown,
  Icon,
  Mountain,
} from "lucide-react";
import type { StatItemProps } from "../../../types/Stat.ts";

const StatItem = ({
  label,
  value,
  unit,
  icon: Icon,
}: StatItemProps & { icon: LucideIcon }) => (
  <div className="flex flex-col bg-zinc-900/40 p-4 rounded-xl border border-zinc-800/60 hover:border-blue-500/40 hover:bg-zinc-900/60 transition-all duration-300 group">
    <div className="flex items-center gap-2 mb-2">
      <Icon
        size={12}
        className="text-zinc-500 group-hover:text-blue-400 transition-colors"
      />
      <span className="text-[10px] text-slate-500 uppercase font-bold tracking-widest group-hover:text-slate-300">
        {label}
      </span>
    </div>
    <div className="flex items-baseline gap-1">
      <span className="text-lg font-semibold text-zinc-100 tabular-nums tracking-tight">
        {value}
      </span>
      <span className="text-[10px] text-zinc-500 font-medium uppercase">
        {unit}
      </span>
    </div>
  </div>
);

export default function StatsPanel({ distance = "0.0", duration = "0", maxElevation = "0", averageElevation = "0" }) {

  return (
    <section className="mt-auto pt-4 border-t border-zinc-800/40">
      <Disclosure defaultOpen>
        {({ open }) => (
          <>
            <DisclosureButton className="flex w-full items-center justify-between px-1 py-2 group focus:outline-none">
              <div className="flex items-center gap-2">
                <div
                  className={`p-1 rounded-md transition-colors ${open ? "bg-blue-500/20" : "bg-zinc-800/40"}`}
                >
                  <Activity
                    size={14}
                    className={open ? "text-blue-400" : "text-slate-500"}
                  />
                </div>
                <h2 className="text-[11px] font-bold text-zinc-400 uppercase tracking-[0.25em] group-hover:text-zinc-200 transition-colors">
                  Mission Stats
                </h2>
              </div>
              <ChevronDown
                size={14}
                className={`text-zinc-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
              />
            </DisclosureButton>

            <Transition
              enter="transition duration-150 ease-out"
              enterFrom="transform scale-95 opacity-0"
              enterTo="transform scale-100 opacity-100"
              leave="transition duration-100 ease-out"
              leaveFrom="transform scale-100 opacity-100"
              leaveTo="transform scale-95 opacity-0"
            >
              <DisclosurePanel className="mt-4 grid grid-cols-2 gap-3">
                <StatItem
                  label="Travel"
                  value={distance}
                  unit="km"
                  icon={Navigation}
                />
                <StatItem
                  label="Time"
                  value={duration}
                  unit="min"
                  icon={Clock}
                />
                <StatItem
                  label="Max Elevation"
                  value={maxElevation}
                  unit="m"
                  icon={Mountain}
                />
                <StatItem
                  label="Average Elevation"
                  value={averageElevation}
                  unit="m"
                  icon={Mountain}
                />
              </DisclosurePanel>
            </Transition>
          </>
        )}
      </Disclosure>
    </section>
  );
}

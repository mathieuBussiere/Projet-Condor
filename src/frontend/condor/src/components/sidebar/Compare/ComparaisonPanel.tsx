import type {ComparisonResultsProps} from "../../../types/Comparison";

export default function ComparisonResults({
  comparisonScore,
  verdict,
  dtw,
  frechet,
  effortRatio,
}: ComparisonResultsProps) {
  if (comparisonScore === null) return null;

  const scoreColor =
    comparisonScore >= 80
      ? "text-emerald-400"
      : comparisonScore >= 50
        ? "text-amber-400"
        : "text-rose-400";

  return (
    <div className="bg-zinc-900/80 border border-zinc-800/80 rounded-lg p-3 flex flex-col gap-2 shadow-inner">
      <div className="flex items-baseline justify-between">
        <span className="text-xs text-zinc-300 font-bold">Match Accuracy</span>
        <span className={`text-lg font-bold font-mono ${scoreColor}`}>
          {comparisonScore}/100
        </span>
      </div>

      {verdict && (
        <p className="font-medium text-[12px] text-zinc-300 leading-relaxed p-2  ">
          {verdict}
        </p>
      )}

      <div className="grid grid-cols-2 gap-2 mt-1 pt-2 border-t border-zinc-800/40 text-[11px]">
        <div>
          <span className="text-zinc-300 block">DTW Deviation</span>
          <span className="font-mono text-zinc-100 font-medium">{dtw} m</span>
        </div>
        <div>
          <span className="text-zinc-300 block">Frechet</span>
          <span className="font-mono text-zinc-100 font-medium">{frechet} m</span>
        </div>
        <div>
          <span className="text-zinc-300 block">Effort Ratio</span>
          <span className="font-mono text-zinc-100 font-medium">
            {effortRatio}
          </span>
        </div>
      </div>
    </div>
  );
}

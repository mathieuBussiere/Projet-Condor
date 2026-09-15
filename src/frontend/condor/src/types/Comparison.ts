export interface ComparisonResultsProps {
  comparisonScore: number | null;
  verdict: string | null;
  dtw: string | number;
  frechet: string | number;
  effortRatio: string | number;
}
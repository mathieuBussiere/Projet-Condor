import type { Coordinate } from "./Coordinate";

export interface BBoxSchema {
  sud: number;
  ouest: number;
  nord: number;
  est: number;
}

// Request Payload
export interface RouteComparisonRequest {
  trail_file_name: string;
  bbox: BBoxSchema;
  calculated_points: Coordinate[];
}

// Response Structures
export interface ComparisonMetrics {
  frechet_distance_meters: number;
  dtw_corridor_deviation_meters: number;
  tobler_effort_ratio: number;
}

export interface ComparisonAnalysis {
  score: number;
  verdict: string;
  metrics: ComparisonMetrics;
}

export interface RouteComparisonResponse {
  trajectory_id: string;
  comparison: ComparisonAnalysis;
}
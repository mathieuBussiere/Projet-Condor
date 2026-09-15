import type {BoundingBox} from "../hooks/useBBox";
import type { Coordinate } from "./Coordinate";

export interface PathRequest {
  start: Coordinate;
  bbox: BoundingBox;
  end: Coordinate;
  trail_file_name?: string; // Optional CSV file name for trail points
}

export interface PathResponse {
  trajectory_id: string;
  points: Coordinate[];
  distance_km: number;
  time: number; // Time in minutes
  avg_elevation_m?: number | null;
  max_elevation_m?: number | null;
}

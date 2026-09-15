import type { Coordinate } from "./Coordinate";

export interface ExportResquest {
    trajectory_id: string
    name_track: string
    start: Coordinate
    end: Coordinate
    points: Coordinate[]
}
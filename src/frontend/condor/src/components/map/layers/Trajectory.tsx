import { Polyline } from "react-leaflet";
import type { PathOptions } from "leaflet";
import type { TrajectoryProps } from "../../../types/Trajectory";
import type { LatLng } from "../../../hooks/useWaypoints";

export type RouteStyle = "astar" | "real";

export interface RouteLayer {
  waypoints: LatLng[];
  style: RouteStyle;
  label?: string;
}
const ROUTE_STYLES: Record<RouteStyle, PathOptions> = {
  astar: {
    color: "#3b82f6", // blue
    weight: 3,
    dashArray: "10, 10",
    opacity: 0.85,
  },
  real: {
    color: "#ff004a",
    weight: 3,
    dashArray: undefined, // solid line
    opacity: 0.9,
  },
};


interface TrajectoryProps {
  routes: RouteLayer[];
}


export default function Trajectory({ routes }: TrajectoryProps) {

  return (
    <>
      {routes
        .filter((r) => r.waypoints.length >= 2)
        .map((r, idx) => (
          <Polyline
            key={`route-${r.style}-${idx}`}
            positions={r.waypoints}
            pathOptions={{ ...ROUTE_STYLES[r.style], lineJoin: "round" }}
          />
        ))}
    </>
  );
}
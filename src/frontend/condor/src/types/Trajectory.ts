import type { RouteLayer } from "../components/map/layers/Trajectory";

export type TrajectoryProps = {
  // Waypoints are an array of [latitude, longitude] tuples
  waypoints: [number, number][];
  routes: RouteLayer[];
};

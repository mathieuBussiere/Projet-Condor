import type { LatLng } from "../hooks/useWaypoints";

export interface MapHintProps {
  start: LatLng | null;
  end: LatLng | null;
}

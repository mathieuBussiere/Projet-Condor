import { useMapEvents } from "react-leaflet";
import type { MapClickHandlerProps } from "../../types/MapClickHandler";
import type { LeafletMouseEvent } from "leaflet";

export default function MapClickHandler({
  onLocationSelect,
}: MapClickHandlerProps) {
  useMapEvents({
    click: (e: LeafletMouseEvent) => {
      const { lat, lng } = e.latlng;

      const formattedCoords = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;

      onLocationSelect(formattedCoords, [lat, lng]);
    },
  });
  return null;
}

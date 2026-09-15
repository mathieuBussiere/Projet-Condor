import type { ExportResquest } from "./Export";

export const EXPORT_FORMATS = {
  GPX: "GPX (.gpx)",
  KML: "KML (.kml)",
  GeoJSON: "GeoJSON (.geojson)",
};
export type ExportFormat = keyof typeof EXPORT_FORMATS;

export interface ExportDialogProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  exportRequest: ExportResquest;
}

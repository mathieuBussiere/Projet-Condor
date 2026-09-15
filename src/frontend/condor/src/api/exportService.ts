import type { ExportResquest } from "../types/Export";
import type { ExportFormat } from "../types/DialogExport";

const BASE_URL = "/api/v1/export";

const FORMAT_ENDPOINTS: Record<ExportFormat, string> = {
  GPX: "gpx",
  KML: "kml",
  GeoJSON: "geojson",
};

export const FORMAT_EXTENSIONS: Record<ExportFormat, string> = {
  GPX: "gpx",
  KML: "kml",
  GeoJSON: "geojson",
};

/**
 * Calls the backend export endpoint for the given format and returns the
 * file as a Blob. Replaces the previous exportToGPX/exportToGeoJson/
 * exportToKml trio — same fetch logic per format, just the URL differed.
 */
export async function exportRoute(
  request: ExportResquest,
  format: ExportFormat,
): Promise<Blob> {
  const endpoint = FORMAT_ENDPOINTS[format];
  const response = await fetch(`${BASE_URL}/${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => response.statusText);
    throw new Error(
      `Failed to export ${format} (${response.status}): ${errorText}`,
    );
  }

  return response.blob();
}

/**
 * Triggers a browser download for a Blob (e.g. the export file above).
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

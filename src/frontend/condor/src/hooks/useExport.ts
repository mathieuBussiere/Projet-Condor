import { useCallback, useState } from "react";
import type { ExportResquest } from "../types/Export";
import type { ExportFormat } from "../types/DialogExport";
import {
  downloadBlob,
  exportRoute as fetchExport,
  FORMAT_EXTENSIONS,
} from "../api/exportService";

interface UseExportResult {
  exportRoute: (request: ExportResquest, format: ExportFormat) => Promise<void>;
  isExporting: boolean;
  error: string | null;
}

export function useExport(): UseExportResult {
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const exportRoute = useCallback(
    async (request: ExportResquest, format: ExportFormat) => {
      setIsExporting(true);
      setError(null);
      try {
        const blob = await fetchExport(request, format);
        const extension = FORMAT_EXTENSIONS[format];
        const filename = `${request.name_track || "route"}.${extension}`;
        downloadBlob(blob, filename);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : `Failed to export ${format}`,
        );
      } finally {
        setIsExporting(false);
      }
    },
    [],
  );

  return { exportRoute, isExporting, error };
}

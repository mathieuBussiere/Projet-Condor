import { useState } from "react";
import { ArrowDownTrayIcon } from "@heroicons/react/24/outline";
import ExportDialog from "./DialogExport";
import type { ExportResquest } from "../../types/Export";

interface ExportBtnProps {
  isLoading?: boolean;
  /** Null when there's no route yet to export — disables the button. */
  exportRequest: ExportResquest | null;
}

export function ExportBtn({
  isLoading = false,
  exportRequest,
}: ExportBtnProps) {
  const [isExportOpen, setIsExportOpen] = useState(false);

  return (
    <div className="mt-auto mx-auto h-full w-full pt-4  flex items-center justify-between text-[12px] text-zinc-500 ">
      {/* Export Button */}
      <button
        onClick={() => setIsExportOpen(true)}
        disabled={isLoading || !exportRequest}
        className="flex  flex-1 items-center justify-center gap-1.5 py-1.5 rounded-lg text-[12px] font-medium bg-sky-500 border border-zinc-700  hover:bg-sky-400 disabled:hover:bg-sky-500 text-white disabled:opacity-40 transition-colors active:bg-sky-600 group"
      >
        <ArrowDownTrayIcon className="size-4 items-center justify-center text-zinc-50 " />
        <span>Export data</span>
      </button>
      {/* Conditional rendering of the Dialog */}
      {isExportOpen && exportRequest && (
        <ExportDialog
          open={isExportOpen}
          setOpen={setIsExportOpen}
          exportRequest={exportRequest}
        />
      )}
    </div>
  );
}

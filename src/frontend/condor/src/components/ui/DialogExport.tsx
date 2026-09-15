import { useState } from "react";
import {
  Dialog,
  DialogBackdrop,
  DialogPanel,
  DialogTitle,
} from "@headlessui/react";
import { ArrowDownTrayIcon, XMarkIcon } from "@heroicons/react/24/outline";
import SelectList from "./Select";
import {
  EXPORT_FORMATS,
  type ExportDialogProps,
  type ExportFormat,
} from "../../types/DialogExport";
import { useExport } from "../../hooks/useExport";

export default function ExportDialog({
  open,
  setOpen,
  exportRequest,
}: ExportDialogProps) {
  const [format, setFormat] = useState<ExportFormat>("GPX");
  const { exportRoute, isExporting, error } = useExport();

  const handleExport = async () => {
    await exportRoute(exportRequest, format);
    setOpen(false);
  };

  return (
    <Dialog open={open} onClose={setOpen} className="relative z-9999">
      <DialogBackdrop
        transition
        className="fixed inset-0 bg-zinc-950/60 backdrop-blur-sm transition-opacity data-closed:opacity-0 data-enter:duration-300 data-enter:ease-out data-leave:duration-200 data-leave:ease-in"
      />
      <div className="fixed inset-0 z-10 w-screen overflow-y-auto p-4 sm:p-0">
        <div className="flex min-h-full items-center justify-center text-center">
          <DialogPanel
            transition
            className="relative transform overflow-hidden rounded-xl bg-zinc-900 border border-zinc-800 p-6 text-left shadow-2xl transition-all data-closed:scale-95 data-closed:opacity-0 data-enter:duration-300 data-enter:ease-out data-leave:duration-200 data-leave:ease-in sm:my-8 sm:w-full sm:max-w-md"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="flex size-10 items-center justify-center rounded-lg bg-sky-500/10">
                  <ArrowDownTrayIcon className="size-5 text-sky-500" />
                </div>
                <DialogTitle
                  as="h3"
                  className="text-sm font-semibold text-zinc-100"
                >
                  Export Spatial Data
                </DialogTitle>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                <XMarkIcon className="size-5" />
              </button>
            </div>
            <div className="space-y-4">
              <p className="text-xs text-zinc-300 leading-relaxed">
                Select your preferred format to export current trajectory.
              </p>
              <div>
                <SelectList
                  labels={EXPORT_FORMATS}
                  labelTitle={"Export Format"}
                  onSelect={(key) => {
                    setFormat(key as ExportFormat);
                  }}
                />
              </div>
              {error && (
                <p className="text-xs text-red-400 leading-relaxed">{error}</p>
              )}
            </div>
            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={() => setOpen(false)}
                disabled={isExporting}
                className="flex-1 rounded-lg  active:bg-zinc-900 bg-zinc-800 px-3 py-2 text-[11px] font-semibold text-zinc-300 border border-zinc-700 hover:bg-zinc-700 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExport}
                disabled={isExporting || !exportRequest}
                className="flex-1 rounded-lg active:bg-sky-600 bg-sky-500 px-3 py-2 text-[11px] font-semibold text-white shadow-sm hover:bg-sky-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isExporting ? "Exporting..." : "Download Data"}
              </button>
            </div>
          </DialogPanel>
        </div>
      </div>
    </Dialog>
  );
}

import { useEffect, useState } from "react";
import { XMarkIcon } from "@heroicons/react/20/solid";
import type { AlertProps } from "../../types/Alert";
import { VARIANTS } from "../../types/AlertVariants";
import { createPortal } from "react-dom";

export default function Alert({
  type,
  message,
  dismissible = true,
  onDismiss,
}: AlertProps) {
  const [visible, setVisible] = useState(true);
  const v = VARIANTS[type];

  const handleDismiss = () => {
    setVisible(false);
    onDismiss?.();
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      handleDismiss();
    }, 5000); // 5000ms = 5 seconds

    return () => clearTimeout(timer);
  }, [onDismiss]);

  if (!visible) return null;

  return createPortal(
    <div className="fixed top-5 left-1/2 z-50 w-full max-w-md -translate-x-1/2 px-4" role="alert" aria-live="assertive">
      <div className={`rounded-md ${v.wrapper} p-4 shadow-lg`}>
        <div className="flex">
          <div className="shrink-0">
            <v.Icon aria-hidden="true" className={`size-5 ${v.icon}`} />
          </div>
          <div className="ml-3">
            <p className={`text-sm font-medium ${v.text}`}>{message}</p>
          </div>
          {dismissible && (
            <div className="ml-auto pl-3">
              <div className="-mx-1.5 -my-1.5">
                <button
                  type="button"
                  onClick={handleDismiss}
                  className={`inline-flex rounded-md p-1.5 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-hidden ${v.button}`}
                >
                  <span className="sr-only">Dismiss</span>
                  <XMarkIcon aria-hidden="true" className="size-5" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}

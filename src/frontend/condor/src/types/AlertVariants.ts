import {
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from "@heroicons/react/20/solid";
import { CheckCircleIcon, XCircleIcon } from "lucide-react";
import type { AlertType } from "./Alert";

export const VARIANTS: Record<
  AlertType,
  {
    wrapper: string;
    icon: string;
    text: string;
    button: string;
    Icon: React.ElementType;
  }
> = {
  success: {
    wrapper:
      "bg-zinc-950/90 border border-emerald-500/40 backdrop-blur-md shadow-2xl shadow-emerald-500/10",
    icon: "text-emerald-400",
    text: "text-zinc-100",
    button:
      "text-emerald-400 hover:bg-emerald-500/10 focus-visible:ring-emerald-500",
    Icon: CheckCircleIcon,
  },
  warning: {
    wrapper:
      "bg-zinc-950/90 border border-amber-500/40 backdrop-blur-md shadow-2xl shadow-amber-500/10",
    icon: "text-amber-400",
    text: "text-zinc-100",
    button: "text-amber-400 hover:bg-amber-500/10 focus-visible:ring-amber-500",
    Icon: ExclamationTriangleIcon,
  },
  error: {
    wrapper:
      "bg-zinc-950/90 border border-red-500/40 backdrop-blur-md shadow-2xl shadow-red-500/10",
    icon: "text-red-400",
    text: "text-zinc-100",
    button: "text-red-400 hover:bg-red-500/10 focus-visible:ring-red-500",
    Icon: XCircleIcon,
  },
  info: {
    wrapper:
      "bg-zinc-950/90 border border-sky-500/40 backdrop-blur-md shadow-2xl shadow-sky-500/10",
    icon: "text-sky-400",
    text: "text-zinc-100",
    button: "text-sky-400 hover:bg-sky-500/10 focus-visible:ring-sky-500",
    Icon: InformationCircleIcon,
  },
};

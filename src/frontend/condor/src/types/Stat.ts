import type { LucideIcon } from "lucide-react";

export interface StatItemProps {
  label: string;
  value: string;
  unit: string;
  icon: LucideIcon;
  className?: string;
}

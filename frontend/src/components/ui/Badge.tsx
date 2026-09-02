/**
 * Badge — small colored label (risk level, priority, status, confidence...).
 * Color mapping is driven by the `kind` prop; unknown values fall back to a
 * neutral slate style so no classification is ever invented on the client.
 */
import type { ReactNode } from "react";

import {
  CONFIDENCE_STYLES,
  CRITICALITY_STYLES,
  COMPLEXITY_STYLES,
  PRIORITY_STYLES,
  RISK_LEVEL_STYLES,
  SCAN_STATUS_STYLES,
} from "@/lib/utils/format";

export type BadgeKind =
  | "risk"
  | "priority"
  | "criticality"
  | "complexity"
  | "confidence"
  | "status"
  | "neutral"
  | "success"
  | "info"
  | "danger";

const NEUTRAL = "bg-zinc-500/15 text-zinc-300 ring-zinc-500/30";

const FIXED: Partial<Record<BadgeKind, string>> = {
  success: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
  info: "bg-sky-500/15 text-sky-300 ring-sky-500/30",
  danger: "bg-red-500/15 text-red-300 ring-red-500/30",
};

/** Pick a style for a badge whose value comes from the API. */
function styleFor(kind: BadgeKind, value?: string): string {
  if (!value) return NEUTRAL;
  switch (kind) {
    case "risk":
      return RISK_LEVEL_STYLES[value as keyof typeof RISK_LEVEL_STYLES] ?? NEUTRAL;
    case "priority":
      return PRIORITY_STYLES[value as keyof typeof PRIORITY_STYLES] ?? NEUTRAL;
    case "criticality":
      return CRITICALITY_STYLES[value as keyof typeof CRITICALITY_STYLES] ?? NEUTRAL;
    case "complexity":
      return COMPLEXITY_STYLES[value as keyof typeof COMPLEXITY_STYLES] ?? NEUTRAL;
    case "confidence":
      return CONFIDENCE_STYLES[value] ?? NEUTRAL;
    case "status":
      return SCAN_STATUS_STYLES[value as keyof typeof SCAN_STATUS_STYLES] ?? NEUTRAL;
    default:
      return NEUTRAL;
  }
}

interface BadgeProps {
  kind?: BadgeKind;
  children: ReactNode;
  title?: string;
}

export function Badge({ kind = "neutral", children, title }: BadgeProps) {
  const value = typeof children === "string" ? children : undefined;
  const fixed = kind === "neutral" ? NEUTRAL : FIXED[kind];
  const styles = fixed ?? styleFor(kind, value);
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${styles}`}
    >
      {children}
    </span>
  );
}
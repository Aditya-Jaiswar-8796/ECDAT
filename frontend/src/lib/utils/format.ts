/**
 * Presentation helpers shared across dashboard views.
 * Pure formatting -- no data generation, classifications or scoring.
 */
import type {
  CriticalityLevel,
  MigrationComplexity,
  MigrationPriority,
  RiskLevel,
  ScanStatus,
} from "@/lib/types/api";

/** Tailwind classes per risk level for badges / pills. */
export const RISK_LEVEL_STYLES: Record<RiskLevel, string> = {
  CRITICAL: "bg-red-500/15 text-red-400 ring-red-500/30",
  HIGH: "bg-orange-500/15 text-orange-400 ring-orange-500/30",
  MEDIUM: "bg-yellow-500/15 text-yellow-400 ring-yellow-500/30",
  LOW: "bg-emerald-500/15 text-emerald-400 ring-emerald-500/30",
};

/** Tailwind classes per migration priority bucket. */
export const PRIORITY_STYLES: Record<MigrationPriority, string> = {
  URGENT: "bg-red-500/15 text-red-400 ring-red-500/30",
  HIGH: "bg-orange-500/15 text-orange-400 ring-orange-500/30",
  MEDIUM: "bg-yellow-500/15 text-yellow-400 ring-yellow-500/30",
  LOW: "bg-sky-500/15 text-sky-400 ring-sky-500/30",
};

/** Tailwind classes per business criticality level. */
export const CRITICALITY_STYLES: Record<CriticalityLevel, string> = {
  CRITICAL: "bg-red-500/15 text-red-400 ring-red-500/30",
  HIGH: "bg-orange-500/15 text-orange-400 ring-orange-500/30",
  MEDIUM: "bg-yellow-500/15 text-yellow-400 ring-yellow-500/30",
  LOW: "bg-emerald-500/15 text-emerald-400 ring-emerald-500/30",
};

/** Tailwind classes per migration complexity value. */
export const COMPLEXITY_STYLES: Record<MigrationComplexity, string> = {
  HIGH: "bg-red-500/15 text-red-400 ring-red-500/30",
  MEDIUM: "bg-yellow-500/15 text-yellow-400 ring-yellow-500/30",
  LOW: "bg-emerald-500/15 text-emerald-400 ring-emerald-500/30",
};

/** Tailwind classes per scanner confidence value. */
export const CONFIDENCE_STYLES: Record<string, string> = {
  HIGH: "bg-emerald-500/15 text-emerald-400 ring-emerald-500/30",
  MEDIUM: "bg-sky-500/15 text-sky-400 ring-sky-500/30",
  LOW: "bg-zinc-500/15 text-zinc-400 ring-zinc-500/30",
};

/** Tailwind classes per backend scan status. */
export const SCAN_STATUS_STYLES: Record<ScanStatus, string> = {
  RECEIVED: "bg-zinc-500/15 text-zinc-300 ring-zinc-500/30",
  SCANNING: "bg-cyan-500/15 text-cyan-300 ring-cyan-500/30",
  SCAN_COMPLETE: "bg-blue-500/15 text-blue-300 ring-blue-500/30",
  RISK_ASSESSED: "bg-violet-500/15 text-violet-300 ring-violet-500/30",
  FAILED: "bg-red-500/15 text-red-300 ring-red-500/30",
};

/** Render a file:line location (path:line) with a fallback. */
export function locationOf(
  filePath: string | null | undefined,
  line: number | null | undefined,
): string {
  if (!filePath) return "—";
  const base = filePath;
  const linePart = typeof line === "number" ? `:${line}` : "";
  return base + linePart;
}

/** Render a 0..10 risk score with one decimal, or — when absent. */
export function formatScore(score: number | null | undefined): string {
  return typeof score === "number" ? score.toFixed(1) : "—";
}

/** ISO timestamp -> locale date/time string, or — when absent. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

/** Convert "not_valid_after" date-like value to a readable date. */
export function formatDate(raw: string | null | undefined): string {
  if (!raw) return "—";
  const d = new Date(raw);
  return Number.isNaN(d.getTime()) ? raw : d.toLocaleDateString();
}

/** Title-case an enum-ish value, e.g. "risk_assessed" -> "Risk Assessed". */
export function humanize(value: string | null | undefined): string {
  if (!value) return "—";
  return value
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Guard helper: true when a string is non-blank. */
export function isPresent(value: string | null | undefined): boolean {
  return typeof value === "string" && value.trim().length > 0;
}
/**
 * StatCard — KPI tile showing a label, a value from real API data and an
 * optional breakdown hint. No metric is computed on the client beyond simple
 * counts/formatting of values already delivered by the backend.
 */
import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  accent?: "default" | "danger" | "warn" | "ok";
}

const ACCENTS = {
  default: "border-zinc-800",
  danger: "border-red-500/40",
  warn: "border-yellow-500/40",
  ok: "border-emerald-500/40",
};

export function StatCard({ label, value, hint, accent = "default" }: StatCardProps) {
  return (
    <div className={`rounded-xl border bg-zinc-900/60 p-4 ${ACCENTS[accent]}`}>
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-zinc-50">{value}</p>
      {hint && <p className="mt-1 text-xs text-zinc-500">{hint}</p>}
    </div>
  );
}
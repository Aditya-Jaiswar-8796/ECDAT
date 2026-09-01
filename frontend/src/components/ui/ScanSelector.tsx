/**
 * ScanSelector — controlled dropdown to choose the active scan for a view.
 * Selection is owned by the page via useScanSelection (which persists the
 * last choice in localStorage); this component only renders and reports.
 */
"use client";

import type { Scan } from "@/lib/types/api";
import { SCAN_STATUS_STYLES } from "@/lib/utils/format";

interface ScanSelectorProps {
  scans: Scan[] | null;
  loading?: boolean;
  value: string | null;
  onSelect: (scanId: string) => void;
  label?: string;
}

export function ScanSelector({
  scans,
  loading,
  value,
  onSelect,
  label = "Scan",
}: ScanSelectorProps) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-zinc-500">{label}</span>
      <select
        value={value ?? ""}
        onChange={(e) => onSelect(e.target.value)}
        disabled={loading}
        className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-sm text-zinc-200 outline-none focus:border-cyan-500/50 disabled:opacity-50"
      >
        {!loading && (!scans || scans.length === 0) && (
          <option value="">No scans yet</option>
        )}
        {scans?.map((s) => (
          <option key={s.scan_id} value={s.scan_id}>
            {s.name} ({s.scan_id})
          </option>
        ))}
      </select>
      <span
        className={`hidden rounded px-1.5 py-0.5 text-[10px] font-medium ring-1 ring-inset md:inline ${
          SCAN_STATUS_STYLES[scans?.find((s) => s.scan_id === value)?.status ?? "RECEIVED"]
        }`}
      >
        {scans?.find((s) => s.scan_id === value)?.status ?? ""}
      </span>
    </label>
  );
}
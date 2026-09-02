/**
 * DataTable — typed, reusable table of API rows with per-column renderers.
 * Generic over the row type so every view (inventory, risk, priority, CBOM…)
 * shares one consistent table implementation.
 */
import type { ReactNode } from "react";

import { EmptyState } from "@/components/ui/EmptyState";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  emptyTitle?: string;
  emptyDescription?: string;
  compact?: boolean;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  emptyTitle = "No data",
  emptyDescription,
  compact = false,
}: DataTableProps<T>) {
  if (rows.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }
  return (
    <div className="overflow-x-auto rounded-xl border border-zinc-800">
      <table className="w-full min-w-max border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/80">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-zinc-500 ${compact ? "py-2" : ""}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800/70 bg-zinc-950/40">
          {rows.map((row) => (
            <tr key={rowKey(row)} className="transition-colors hover:bg-zinc-900/70">
              {columns.map((col) => (
                <td key={col.key} className={`px-3 py-2.5 align-top ${compact ? "py-2" : ""} ${col.className ?? ""}`}>
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
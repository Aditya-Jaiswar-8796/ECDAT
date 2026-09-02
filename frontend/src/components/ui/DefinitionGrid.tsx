/**
 * DefinitionGrid — label/value list for structured detail screens.
 */
import type { ReactNode } from "react";

export interface DefinitionRow {
  label: string;
  value?: ReactNode;
  mono?: boolean;
}

interface DefinitionGridProps {
  rows: DefinitionRow[];
  columns?: 1 | 2 | 3;
}

export function DefinitionGrid({ rows, columns = 2 }: DefinitionGridProps) {
  const cols =
    columns === 3 ? "sm:grid-cols-3" : columns === 2 ? "sm:grid-cols-2" : "grid-cols-1";
  return (
    <dl className={`grid ${cols} gap-x-6 gap-y-3`}>
      {rows.map((row) => (
        <div key={row.label} className="min-w-0">
          <dt className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            {row.label}
          </dt>
          <dd
            className={`mt-0.5 text-sm text-zinc-200 ${
              row.mono ? "font-mono" : ""
            }`}
          >
            {row.value ?? <span className="text-zinc-600">—</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}
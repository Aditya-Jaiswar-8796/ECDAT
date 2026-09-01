/**
 * DistributionCard — horizontal bar breakdown of a categorical value.
 * Counts are computed client-side from real API rows; colors only, no
 * classifications are invented.
 */
import type { ReactNode } from "react";

import { Card } from "@/components/ui/Card";

export interface DistributionBucket {
  label: string;
  value: number;
  /** Tailwind text color class, e.g. "text-red-400". */
  color?: string;
  hint?: ReactNode;
}

interface DistributionCardProps {
  title: string;
  buckets: DistributionBucket[];
  total: number;
  emptyText?: string;
}

export function DistributionCard({ title, buckets, total, emptyText = "No data" }: DistributionCardProps) {
  if (total === 0) {
    return (
      <Card title={title}>
        <p className="py-6 text-center text-sm text-zinc-500">{emptyText}</p>
      </Card>
    );
  }

  return (
    <Card title={title}>
      <ul className="space-y-2.5">
        {buckets.map((bucket) => {
          const pct = Math.round((bucket.value / total) * 100);
          return (
            <li key={bucket.label}>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="flex items-center gap-1.5 text-zinc-300">
                  <span className={`inline-block h-2 w-2 rounded-full ${bucket.color ?? "bg-zinc-600"}`} />
                  {bucket.label}
                  {bucket.hint}
                </span>
                <span className="font-medium text-zinc-400">
                  {bucket.value} <span className="text-xs text-zinc-600">({pct}%)</span>
                </span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-zinc-800">
                <div
                  className={`h-full rounded-full ${bucket.color ?? "bg-zinc-600"}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
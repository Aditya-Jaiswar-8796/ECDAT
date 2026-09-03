/**
 * Migration priority view.
 *
 * Assets ranked by the migration_priority assigned by the risk engine and
 * grouped into a roadmap (URGENT > HIGH > MEDIUM > LOW). Each row surfaces
 * the matched recommendation (target + effort) so teams can plan the
 * transition work. Priorities come from the API; ordering only sorts what
 * the API already classified.
 */
"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, Suspense } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Column, DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { ScanSelector } from "@/components/ui/ScanSelector";
import { Spinner } from "@/components/ui/Spinner";
import { StatCard } from "@/components/ui/StatCard";
import { useAssets, useRecommendations, useScanSelection, useScans } from "@/lib/hooks/useApi";
import type { CryptoAsset, MigrationPriority, Recommendation } from "@/lib/types/api";
import { formatScore, locationOf } from "@/lib/utils/format";

const PRIORITY_ORDER: (MigrationPriority | "UNASSIGNED")[] = [
  "URGENT",
  "HIGH",
  "MEDIUM",
  "LOW",
  "UNASSIGNED",
];

const PRIORITY_BLURB: Record<MigrationPriority, string> = {
  URGENT: "Action required immediately — harvest-now/decrypt-later exposure",
  HIGH: "High exposure — plan migration into the current sprint",
  MEDIUM: "Moderate exposure — schedule within the next cycle",
  LOW: "Lower urgency — monitor and migrate opportunistically",
};

export default function PriorityPage() {
  return (
    <Suspense fallback={<div className="flex flex-1 items-center justify-center py-24"><Spinner /></div>}>
      <PriorityContent />
    </Suspense>
  );
}

function PriorityContent() {
  const searchParams = useSearchParams();
  const scans = useScans();
  const { selectedScan, onSelect } = useScanSelection(searchParams.get("scan"), scans.data);

  const assets = useAssets(selectedScan);
  const recommendations = useRecommendations(selectedScan);

  // Merge per-asset recommendation from the recommendations list when present.
  const recIndex = useMemo(() => {
    const map = new Map<string, Recommendation>();
    (recommendations.data ?? []).forEach((r) => {
      if (r.asset_id) map.set(r.asset_id, r);
    });
    return map;
  }, [recommendations.data]);

  const grouped = useMemo(() => {
    const list = assets.data ?? [];
    const map = new Map<string, CryptoAsset[]>();
    PRIORITY_ORDER.forEach((p) => map.set(p, []));
    list.forEach((a) => {
      const bucket = a.migration_priority ?? "UNASSIGNED";
      map.get(bucket)?.push(a);
    });
    // Within each bucket sort by risk score descending (nulls last).
    PRIORITY_ORDER.forEach((p) =>
      map
        .get(p)!
        .sort((x, y) => (y.risk_score ?? -1) - (x.risk_score ?? -1)),
    );
    return map;
  }, [assets.data]);

  const counts = useMemo(() => {
    const list = assets.data ?? [];
    return Object.fromEntries(
      PRIORITY_ORDER.map((p) => [
        p,
        list.filter((a) => (a.migration_priority ?? "UNASSIGNED") === p).length,
      ]),
    ) as Record<(typeof PRIORITY_ORDER)[number], number>;
  }, [assets.data]);

  const columns: Column<CryptoAsset>[] = [
    {
      key: "asset",
      header: "Asset",
      render: (a) => (
        <Link
          href={`/assets/${encodeURIComponent(a.id)}?scan=${encodeURIComponent(selectedScan ?? "")}`}
          className="font-mono text-xs text-cyan-400 hover:underline"
        >
          {a.id}
        </Link>
      ),
    },
    {
      key: "algorithm",
      header: "Algorithm",
      render: (a) => <span className="font-mono text-xs text-zinc-100">{a.algorithm}</span>,
    },
    {
      key: "key-size",
      header: "Key size",
      render: (a) =>
        a.key_size != null ? (
          <span className="font-mono text-xs text-zinc-300">{a.key_size}</span>
        ) : (
          <span className="text-zinc-600">—</span>
        ),
    },
    {
      key: "location",
      header: "Path · Line",
      render: (a) => <span className="font-mono text-[11px] text-zinc-400">{locationOf(a.file_path, a.line_number)}</span>,
    },
    {
      key: "risk",
      header: "Risk",
      render: (a) =>
        a.risk_score != null ? (
          <span className="inline-flex items-center gap-1.5">
            <Badge kind={a.risk_level ? "risk" : "neutral"}>{a.risk_level ?? "—"}</Badge>
            <span className="font-mono text-[11px] text-zinc-500">{formatScore(a.risk_score)}</span>
          </span>
        ) : (
          <span className="text-zinc-600">—</span>
        ),
    },
    {
      key: "recommendation",
      header: "Recommendation",
      render: (a) => {
        const rec = recIndex.get(a.id);
        const text = rec?.recommendation ?? a.recommendation;
        const target = rec?.suggested_target;
        const effort = rec?.effort_estimate;
        return (
          <span
            className="block max-w-md"
            title={a.evidence ?? undefined}
          >
            <span className="block truncate text-xs text-zinc-300">{text ?? "—"}</span>
            {(target || effort) && (
              <span className="mt-0.5 block text-[11px] text-zinc-500">
                {target ? `Target: ${target}` : ""}
                {target && effort ? " · " : ""}
                {effort ? `Effort: ${effort}` : ""}
              </span>
            )}
          </span>
        );
      },
    },
  ];

  return (
    <div>
      <PageHeader
        title="Migration priority"
        description="Transition roadmap grouped by the priority the risk engine assigned — with the recommended target and effort for each asset."
        actions={
          <ScanSelector
            scans={scans.data}
            loading={scans.loading}
            value={selectedScan}
            onSelect={onSelect}
            label="Scan"
          />
        }
      />

      <div className="mb-4 grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {PRIORITY_ORDER.map((p) => (
          <StatCard
            key={p}
            label={p === "UNASSIGNED" ? "Unprioritized" : p}
            value={counts[p] ?? 0}
            accent={
              p === "URGENT" && counts[p] > 0
                ? "danger"
                : p === "HIGH" && counts[p] > 0
                  ? "warn"
                  : "default"
            }
            hint={p === "UNASSIGNED" ? undefined : PRIORITY_BLURB[p]}
          />
        ))}
      </div>

      {assets.loading && !assets.data && <Spinner label="Loading priorities…" />}
      {assets.error && <p className="text-sm text-red-400">Failed to load assets: {assets.error}</p>}

      {!assets.loading && !assets.error && (
        <div className="space-y-6">
          {PRIORITY_ORDER.map((p) => {
            const rows = grouped.get(p) ?? [];
            if (rows.length === 0) return null;
            return (
              <Card
                key={p}
                title={
                  <span className="flex items-center gap-2">
                    {p === "UNASSIGNED" ? "Unprioritized" : p}
                    <Badge kind="priority">{p}</Badge>
                  </span>
                }
                subtitle={
                  p === "UNASSIGNED"
                    ? "Assets without a migration priority from the risk engine"
                    : PRIORITY_BLURB[p]
                }
              >
                <DataTable
                  columns={columns}
                  rows={rows}
                  rowKey={(a) => a.id}
                  emptyTitle="No assets"
                />
              </Card>
            );
          })}
          {assets.data && assets.data.length === 0 && (
            <EmptyState
              title="No assets in this scan"
              description="Discover assets first — findings will be ranked here once the risk engine assigns priorities."
            />
          )}
        </div>
      )}
    </div>
  );
}
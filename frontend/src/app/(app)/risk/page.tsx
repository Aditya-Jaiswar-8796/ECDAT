/**
 * Risk assessment view.
 *
 * Shows the risk engine output (GET /risks/{scan_id}) for every assessed
 * asset: risk score, risk level, migration priority and the Mosca assessment.
 * The Mosca text always comes from the API — the dashboard classifies nothing.
 */
"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Column, DataTable } from "@/components/ui/DataTable";
import { DistributionCard } from "@/components/ui/DistributionCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { ScanSelector } from "@/components/ui/ScanSelector";
import { Spinner } from "@/components/ui/Spinner";
import { StatCard } from "@/components/ui/StatCard";
import { useRisks, useScanSelection, useScans } from "@/lib/hooks/useApi";
import type { RiskAssessmentItem, RiskLevel, Scan } from "@/lib/types/api";
import { formatScore } from "@/lib/utils/format";

const LEVEL_ORDER: RiskLevel[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const LEVEL_COLORS: Record<RiskLevel, string> = {
  CRITICAL: "bg-red-400",
  HIGH: "bg-orange-400",
  MEDIUM: "bg-yellow-400",
  LOW: "bg-emerald-400",
};

export default function RiskPage() {
  return (
    <Suspense fallback={<div className="flex flex-1 items-center justify-center py-24"><Spinner /></div>}>
      <RiskContent />
    </Suspense>
  );
}

function RiskContent() {
  const searchParams = useSearchParams();
  const scans = useScans();
  const { selectedScan, onSelect } = useScanSelection(searchParams.get("scan"), scans.data);

  const risks = useRisks(selectedScan);

  const assessments = useMemo(() => risks.data?.assessments ?? [], [risks.data]);
  const distribution = useMemo(() => {
    const counts = new Map<RiskLevel, number>();
    assessments.forEach((a) => {
      if (a.risk_level) counts.set(a.risk_level, (counts.get(a.risk_level) ?? 0) + 1);
    });
    return LEVEL_ORDER.filter((l) => counts.has(l)).map((level) => ({
      label: level,
      value: counts.get(level) ?? 0,
      color: LEVEL_COLORS[level],
    }));
  }, [assessments]);

  const avgScore = useMemo(() => {
    const scored = assessments.filter((a) => typeof a.risk_score === "number");
    if (scored.length === 0) return null;
    return scored.reduce((sum, a) => sum + (a.risk_score ?? 0), 0) / scored.length;
  }, [assessments]);

  const columns: Column<RiskAssessmentItem>[] = [
    {
      key: "asset",
      header: "Asset",
      render: (a) => (
        <Link
          href={`/assets/${encodeURIComponent(a.asset_id)}?scan=${encodeURIComponent(selectedScan ?? "")}`}
          className="font-mono text-xs text-cyan-400 hover:underline"
        >
          {a.asset_id}
        </Link>
      ),
    },
    {
      key: "algorithm",
      header: "Algorithm",
      render: (a) => <span className="font-mono text-xs text-zinc-100">{a.algorithm}</span>,
    },
    {
      key: "path",
      header: "Path",
      render: (a) => <span className="font-mono text-[11px] text-zinc-400">{a.file_path}</span>,
    },
    {
      key: "score",
      header: "Score",
      render: (a) => {
        const s = a.risk_score;
        return (
          <div className="w-24">
            <div className="h-1.5 overflow-hidden rounded-full bg-zinc-800">
              <div
                className={`h-full rounded-full ${a.risk_level ? LEVEL_COLORS[a.risk_level] : "bg-zinc-600"}`}
                style={{ width: `${Math.min(100, Math.max(0, ((s ?? 0) / 10) * 100))}%` }}
              />
            </div>
            <span className="font-mono text-[11px] text-zinc-400">{formatScore(s)} / 10</span>
          </div>
        );
      },
    },
    {
      key: "level",
      header: "Risk level",
      render: (a) =>
        a.risk_level ? <Badge kind="risk">{a.risk_level}</Badge> : <span className="text-zinc-600">—</span>,
    },
    {
      key: "priority",
      header: "Priority",
      render: (a) =>
        a.migration_priority ? (
          <Badge kind="priority">{a.migration_priority}</Badge>
        ) : (
          <span className="text-zinc-600">—</span>
        ),
    },
    {
      key: "mosca",
      header: "Mosca",
      render: (a) => (
        <span
          className="block max-w-xs truncate text-[11px] text-zinc-400"
          title={a.mosca_assessment ?? undefined}
        >
          {a.mosca_assessment ?? "—"}
        </span>
      ),
    },
  ];

  const currentScan = scans.data?.find((s: Scan) => s.scan_id === selectedScan);

  return (
    <div>
      <PageHeader
        title="Risk assessment"
        description="Risk decisions produced by the risk engine (Member 5) — scores, levels, priorities and the qualitative Mosca assessment."
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

      {risks.loading && !risks.data && <Spinner label="Loading risk data…" />}
      {risks.error && <p className="text-sm text-red-400">Failed to load risk data: {risks.error}</p>}

      {risks.data && (
        <>
          <div className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Assets in scan" value={risks.data.asset_count} hint={currentScan?.name ?? selectedScan ?? ""} />
            <StatCard label="Assessed" value={risks.data.assessed_count} hint="Assets with a risk decision" />
            <StatCard label="Average score" value={avgScore != null ? avgScore.toFixed(1) : "—"} hint="Mean of assessed scores (0–10)" />
            <StatCard
              label="Critical"
              value={distribution.find((d) => d.label === "CRITICAL")?.value ?? 0}
              hint="Risk level CRITICAL"
              accent={distribution.find((d) => d.label === "CRITICAL")?.value ? "danger" : "ok"}
            />
          </div>

          <div className="mb-4">
            <DistributionCard
              title="Risk level distribution"
              total={assessments.length}
              buckets={distribution}
              emptyText="No assets have been assessed yet."
            />
          </div>

          <Card
            title="Assessed assets"
            subtitle={`${risks.data.assessed_count} of ${risks.data.asset_count} assets assessed`}
          >
            <DataTable
              columns={columns}
              rows={assessments}
              rowKey={(a) => a.asset_id}
              emptyTitle="Nothing assessed yet"
              emptyDescription="The risk engine has not produced assessments for this scan."
            />
          </Card>
        </>
      )}
    </div>
  );
}
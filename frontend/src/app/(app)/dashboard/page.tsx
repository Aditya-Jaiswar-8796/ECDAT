/**
 * Dashboard overview.
 *
 * Aggregates real API data across all scans: totals, risk distribution,
 * migration priority, algorithm mix, plus the latest scans with their stage
 * progress. No metric is hard-coded — every number flows from GET /scans,
 * /assets, /recommendations.
 */
"use client";

import { useMemo } from "react";
import Link from "next/link";

import { Card } from "@/components/ui/Card";
import { DistributionCard } from "@/components/ui/DistributionCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { ScanStageIndicator } from "@/components/ui/ScanStageIndicator";
import { Spinner } from "@/components/ui/Spinner";
import { StatCard } from "@/components/ui/StatCard";
import { useAssets, useRecommendations, useScans } from "@/lib/hooks/useApi";
import {
  algorithmBreakdown,
  criticalityDistribution,
  priorityDistribution,
  riskDistribution,
} from "@/lib/utils/derivations";
import { formatDateTime, humanize } from "@/lib/utils/format";
import { deriveStages } from "@/lib/utils/stages";

export default function DashboardPage() {
  const scans = useScans();
  const assets = useAssets(undefined);
  const recommendations = useRecommendations(undefined);

  const { total, assessed, critical } = useMemo(() => {
    const list = assets.data ?? [];
    return {
      total: list.length,
      assessed: list.filter((a) => a.risk_level != null).length,
      critical: list.filter((a) => a.risk_level === "CRITICAL").length,
    };
  }, [assets.data]);

  const riskBuckets = useMemo(() => riskDistribution(assets.data ?? []), [assets.data]);
  const priorityBuckets = useMemo(
    () => priorityDistribution(assets.data ?? []),
    [assets.data],
  );
  const algorithmBuckets = useMemo(
    () => algorithmBreakdown(assets.data ?? []).slice(0, 8),
    [assets.data],
  );
  const criticalityBuckets = useMemo(
    () => criticalityDistribution(assets.data ?? []),
    [assets.data],
  );

  const loadingScans = scans.loading && !scans.data;
  const loadingAssets = assets.loading && !assets.data;

  return (
    <div>
      <PageHeader
        title="Overview"
        description="Post-quantum readiness across every scanned codebase: crypto inventory, risk posture and migration progress."
        actions={
          <Link
            href="/scans"
            className="rounded-lg bg-cyan-500 px-3 py-1.5 text-sm font-medium text-zinc-950 transition-colors hover:bg-cyan-400"
          >
            New scan
          </Link>
        }
      />

      {(loadingScans || loadingAssets) && <Spinner label="Loading dashboard data…" />}

      {!loadingScans && !loadingAssets && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Scans" value={scans.data?.length ?? 0} hint="Source bundles analyzed" />
            <StatCard label="Crypto assets" value={total} hint="Findings across all scans" />
            <StatCard
              label="Assessed"
              value={`${assessed}/${total}`}
              hint="Assets with a risk decision"
              accent={critical > 0 ? "danger" : "ok"}
            />
            <StatCard
              label="Critical risk"
              value={critical}
              hint="Risk level CRITICAL"
              accent={critical > 0 ? "danger" : "ok"}
            />
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <DistributionCard
              title="Risk distribution"
              total={total}
              buckets={riskBuckets}
              emptyText="No assets have a risk assessment yet."
            />
            <DistributionCard
              title="Migration priority"
              total={total}
              buckets={priorityBuckets}
              emptyText="No migration priorities assigned yet."
            />
            <DistributionCard
              title="Algorithms in use"
              total={total}
              buckets={algorithmBuckets}
              emptyText="No crypto algorithms discovered yet."
            />
            <DistributionCard
              title="Business criticality"
              total={total}
              buckets={criticalityBuckets}
              emptyText="No criticality assigned yet."
            />
          </div>

          <Card
            title="Latest scans"
            subtitle="Pipeline progress per scan"
            className="mt-6"
            actions={
              <Link href="/scans" className="text-sm text-cyan-400 hover:underline">
                Manage scans →
              </Link>
            }
          >
            {(!scans.data || scans.data.length === 0) && (
              <div>
                <p className="text-sm text-zinc-500">No scans yet.</p>
                <Link href="/scans" className="mt-2 inline-block text-sm text-cyan-400 hover:underline">
                  Create your first scan →
                </Link>
              </div>
            )}
            <div className="space-y-4">
              {scans.data?.slice(0, 3).map((scan) => (
                <div key={scan.scan_id} className="rounded-lg border border-zinc-800 p-3">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <Link
                      href={`/inventory?scan=${encodeURIComponent(scan.scan_id)}`}
                      className="text-sm font-medium text-zinc-200 hover:text-cyan-300"
                    >
                      {scan.name}
                    </Link>
                    <span className="text-xs text-zinc-500">
                      {humanize(scan.status)} · {formatDateTime(scan.created_at)}
                    </span>
                  </div>
                  <ScanStageIndicator
                    stages={deriveStages(scan, null, null)}
                    headline={scan.status === "FAILED" ? `Failed: ${scan.error ?? "unknown"}` : undefined}
                  />
                </div>
              ))}
            </div>
          </Card>

          <Card title="Recommendation inventory" className="mt-6">
            <p className="text-sm text-zinc-400">
              <span className="font-semibold text-zinc-200">
                {recommendations.data?.length ?? 0}
              </span>{" "}
              recommendations have been produced by the risk engine. Review them on the{" "}
              <Link href="/reports" className="text-cyan-400 hover:underline">report view</Link>.
            </p>
            {recommendations.error && (
              <p className="mt-2 text-sm text-red-400">Unable to load recommendations: {recommendations.error}</p>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
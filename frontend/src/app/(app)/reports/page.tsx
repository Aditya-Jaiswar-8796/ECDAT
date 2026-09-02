/**
 * Report view.
 *
 * A consolidated, exportable report for the selected scan built entirely from
 * real API data: scan metadata, summary counters, risk posture, findings,
 * recommendations and the CBOM digest. The JSON export serializes the same
 * live API payloads — nothing is fabricated.
 */
"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, type ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Column, DataTable } from "@/components/ui/DataTable";
import { PageHeader } from "@/components/ui/PageHeader";
import { ScanSelector } from "@/components/ui/ScanSelector";
import { Spinner } from "@/components/ui/Spinner";
import { StatCard } from "@/components/ui/StatCard";
import {
  useAssets,
  useCBOM,
  useRecommendations,
  useRisks,
  useScan,
  useScanSelection,
  useScans,
} from "@/lib/hooks/useApi";
import type {
  CBOM,
  CryptoAsset,
  Recommendation,
  RiskAssessmentSummary,
  Scan,
} from "@/lib/types/api";
import {
  formatDateTime,
  formatScore,
  humanize,
  locationOf,
} from "@/lib/utils/format";

/** Downloadable snapshot assembled from live API responses. */
function buildReportSnapshot(data: {
  scan: Scan;
  assets: CryptoAsset[];
  riskSummary: RiskAssessmentSummary | null;
  recommendations: Recommendation[];
  cbom: CBOM | null;
}) {
  return {
    generated_at: new Date().toISOString(),
    scan: {
      scan_id: data.scan.scan_id,
      name: data.scan.name,
      status: data.scan.status,
      created_at: data.scan.created_at,
    },
    summary: {
      asset_count: data.assets.length,
      risk_assessed: data.riskSummary?.assessed_count ?? 0,
      recommendation_count: data.recommendations.length,
      cbom: data.cbom,
    },
    assets: data.assets,
    risks: data.riskSummary ?? null,
    recommendations: data.recommendations,
  };
}

export default function ReportsPage() {
  return (
    <Suspense fallback={<div className="flex flex-1 items-center justify-center py-24"><Spinner /></div>}>
      <ReportsContent />
    </Suspense>
  );
}

function ReportsContent() {
  const searchParams = useSearchParams();
  const { selectedScan, onSelect } = useScanSelection(searchParams.get("scan"));

  const scans = useScans();
  const assets = useAssets(selectedScan);
  const riskSummary = useRisks(selectedScan);
  const recommendations = useRecommendations(selectedScan);
  const cbom = useCBOM(selectedScan);
  const scanInfo = useScan(selectedScan);

  const loading =
    (scans.loading && !scans.data) ||
    (assets.loading && !assets.data && selectedScan !== null);
  const error = assets.error || riskSummary.error || recommendations.error || cbom.error;

  const handleExport = () => {
    if (!selectedScan || !scanInfo.data) return;
    const snapshot = buildReportSnapshot({
      scan: scanInfo.data.scan,
      assets: assets.data ?? [],
      riskSummary: riskSummary.data,
      recommendations: recommendations.data ?? [],
      cbom: cbom.data,
    });
    const blob = new Blob([JSON.stringify(snapshot, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ecdat-report-${selectedScan}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const columns: Column<CryptoAsset>[] = [
    {
      key: "asset",
      header: "Asset",
      render: (a) => <span className="font-mono text-xs text-cyan-400">{a.id}</span>,
    },
    {
      key: "algorithm",
      header: "Algorithm",
      render: (a) => <span className="font-mono text-xs text-zinc-100">{a.algorithm}</span>,
    },
    {
      key: "key-size",
      header: "Key",
      render: (a) =>
        a.key_size != null ? (
          <span className="font-mono text-xs text-zinc-300">{a.key_size}</span>
        ) : (
          <span className="text-zinc-600">—</span>
        ),
    },
    {
      key: "operation",
      header: "Operation",
      render: (a) => <span className="text-xs text-zinc-400">{humanize(a.operation)}</span>,
    },
    {
      key: "location",
      header: "Path · Line",
      render: (a) => (
        <span className="block max-w-xs truncate font-mono text-[11px] text-zinc-400" title={locationOf(a.file_path, a.line_number)}>
          {locationOf(a.file_path, a.line_number)}
        </span>
      ),
    },
    {
      key: "risk",
      header: "Risk",
      render: (a) =>
        a.risk_level ? (
          <span className="inline-flex items-center gap-1.5">
            <Badge kind="risk">{a.risk_level}</Badge>
            <span className="font-mono text-[11px] text-zinc-500">{formatScore(a.risk_score)}</span>
          </span>
        ) : (
          <span className="text-zinc-600">—</span>
        ),
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
  ];

  const recColumns: Column<Recommendation>[] = [
    {
      key: "asset",
      header: "Asset",
      render: (r) => (
        <span className="font-mono text-xs text-cyan-400">{r.asset_id ?? "Scan-wide"}</span>
      ),
    },
    {
      key: "recommendation",
      header: "Recommendation",
      render: (r) => <span className="block max-w-md text-xs text-zinc-200">{r.recommendation}</span>,
    },
    {
      key: "target",
      header: "Suggested target",
      render: (r) => (
        <span className="font-mono text-xs text-zinc-300">{r.suggested_target ?? "—"}</span>
      ),
    },
    {
      key: "effort",
      header: "Effort",
      render: (r) => <span className="text-xs text-zinc-400">{r.effort_estimate ?? "—"}</span>,
    },
  ];

  return (
    <div>
      <PageHeader
        title="Report"
        description="Consolidated, API-driven report for the selected scan — ready to export as JSON for downstream review."
        actions={
          <>
            <ScanSelector
              scans={scans.data}
              loading={scans.loading}
              value={selectedScan}
              onSelect={onSelect}
              label="Scan"
            />
            <button
              type="button"
              onClick={handleExport}
              disabled={!selectedScan || !scanInfo.data}
              className="rounded-lg bg-cyan-500 px-3 py-1.5 text-sm font-medium text-zinc-950 transition-colors hover:bg-cyan-400 disabled:opacity-40"
            >
              Export JSON
            </button>
          </>
        }
      />

      {loading && <Spinner label="Loading report data…" />}
      {error && <p className="text-sm text-red-400">{error}</p>}

      {!loading && !error && (
        <div className="space-y-6">
          {/* Report metadata */}
          <Card title="Scan metadata" subtitle="As reported by the backend">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {[
                { label: "Scan id", value: scanInfo.data?.scan.scan_id ?? "—" },
                { label: "Name", value: scanInfo.data?.scan.name ?? "—" },
                { label: "Status", value: humanize(scanInfo.data?.scan.status) },
                { label: "Created", value: formatDateTime(scanInfo.data?.scan.created_at) },
              ].map((row) => (
                <div key={row.label}>
                  <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">{row.label}</p>
                  <p className="mt-0.5 text-sm text-zinc-200">{row.value}</p>
                </div>
              ))}
            </div>
          </Card>

          {/* Summary counters */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Assets" value={assets.data?.length ?? 0} hint="Crypto findings" />
            <StatCard label="Assessed" value={riskSummary.data?.assessed_count ?? 0} hint={`of ${riskSummary.data?.asset_count ?? 0} assets`} />
            <StatCard label="Recommendations" value={recommendations.data?.length ?? 0} hint="From the risk engine" />
            <StatCard
              label="CBOM"
              value={`${cbom.data?.dependencies.length ?? 0} deps`}
              hint={`${cbom.data?.certificates.length ?? 0} certificates`}
            />
          </div>

          {/* Findings */}
          <Card title="Crypto findings" subtitle={`${assets.data?.length ?? 0} assets discovered and analyzed`}>
            <DataTable
              columns={columns}
              rows={assets.data ?? []}
              rowKey={(a) => a.id}
              emptyTitle="No findings"
              emptyDescription="No crypto assets were discovered in this scan."
            />
          </Card>

          {/* Recommendations */}
          <Card title="Recommendations" subtitle="Migration guidance produced by the risk engine">
            <DataTable
              columns={recColumns}
              rows={recommendations.data ?? []}
              rowKey={(r) => `${r.asset_id ?? "scan-wide"}-${r.recommendation}`}
              emptyTitle="No recommendations"
              emptyDescription="The risk engine has not produced recommendations for this scan yet."
            />
            <h4 className="mb-2 mt-6 text-sm font-semibold text-zinc-200">Narrative</h4>
            <ul className="list-disc space-y-2 pl-5 text-sm text-zinc-300">
              {(recommendations.data ?? []).length === 0 ? (
                <li className="text-zinc-500">No recommendations available.</li>
              ) : (
                (recommendations.data ?? []).map((r, i) => (
                  <li key={i}>
                    <span className="font-medium text-zinc-200">
                      {r.asset_id ?? "Scan-wide"}:
                    </span>{" "}
                    {r.recommendation}
                    {r.explanation ? (
                      <span className="text-zinc-400"> — {r.explanation}</span>
                    ) : null}
                  </li>
                ))
              )}
            </ul>
          </Card>

          {/* CBOM digest */}
          <Card title="CBOM digest" subtitle="Dependencies and certificates catalogued for the scan">
            <div className="grid gap-4 sm:grid-cols-2">
              <DigestList
                title="Crypto-relevant dependencies"
                empty="None catalogued"
                items={(cbom.data?.dependencies ?? [])
                  .filter((d) => d.crypto_relevant)
                  .map((d) => `${d.name}@${d.version ?? "?"} (${d.ecosystem ?? "?"})`)}
              />
              <DigestList
                title="Certificates"
                empty="None catalogued"
                items={(cbom.data?.certificates ?? []).map(
                  (c) =>
                    `${c.subject ?? "?"} — ${c.signature_algorithm ?? "?"}/${c.key_size ?? "?"}`,
                )}
              />
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

/** Small bulleted list helper for the report digest. */
function DigestList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  let value: ReactNode;
  if (items.length === 0) {
    value = <p className="text-sm text-zinc-500">{empty}</p>;
  } else {
    value = (
      <ul className="max-h-56 list-disc space-y-1 overflow-y-auto pl-5 text-xs text-zinc-300">
        {items.map((item, i) => (
          <li key={i} className="break-all font-mono">
            {item}
          </li>
        ))}
      </ul>
    );
  }
  return (
    <div>
      <h4 className="mb-2 text-sm font-semibold text-zinc-200">{title}</h4>
      {value}
    </div>
  );
}
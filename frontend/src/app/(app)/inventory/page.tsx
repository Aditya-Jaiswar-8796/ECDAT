/**
 * Inventory view.
 *
 * Full crypto asset inventory for the selected scan (or all scans). Every
 * row links to the per-asset detail view which shows algorithm, operation,
 * key size, language, library/API, path, line, evidence, confidence, business
 * context, risk, Mosca, priority and recommendation.
 */
"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Column, DataTable } from "@/components/ui/DataTable";
import { PageHeader } from "@/components/ui/PageHeader";
import { ScanSelector } from "@/components/ui/ScanSelector";
import { Spinner } from "@/components/ui/Spinner";
import { StatCard } from "@/components/ui/StatCard";
import { useAssets, useScanSelection, useScans } from "@/lib/hooks/useApi";
import type { CryptoAsset } from "@/lib/types/api";
import { formatScore, humanize, locationOf } from "@/lib/utils/format";

export default function InventoryPage() {
  return (
    <Suspense fallback={<div className="flex flex-1 items-center justify-center py-24"><Spinner /></div>}>
      <InventoryContent />
    </Suspense>
  );
}

function InventoryContent() {
  const searchParams = useSearchParams();
  const paramScan = searchParams.get("scan");
  const { selectedScan, onSelect } = useScanSelection(paramScan);
  const [query, setQuery] = useState("");

  const scans = useScans();
  const assets = useAssets(selectedScan);

  const filtered = useMemo(() => {
    const list = assets.data ?? [];
    if (!query.trim()) return list;
    const q = query.trim().toLowerCase();
    return list.filter((a) =>
      [
        a.id,
        a.algorithm,
        a.operation,
        a.language,
        a.library,
        a.api,
        a.file_path,
        a.evidence,
        a.mosca_assessment,
        a.recommendation,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q),
    );
  }, [assets.data, query]);

  const assessed = filtered.filter((a) => a.risk_level != null).length;
  const critical = filtered.filter((a) => a.risk_level === "CRITICAL").length;

  const columns: Column<CryptoAsset>[] = [
    {
      key: "algorithm",
      header: "Algorithm",
      render: (a) => <span className="font-mono text-xs font-medium text-zinc-100">{a.algorithm}</span>,
    },
    {
      key: "operation",
      header: "Operation",
      render: (a) => <span className="text-xs text-zinc-400">{humanize(a.operation)}</span>,
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
      key: "language",
      header: "Language",
      render: (a) => <span className="text-xs text-zinc-300">{a.language}</span>,
    },
    {
      key: "library-api",
      header: "Library / API",
      render: (a) => (
        <span className="font-mono text-[11px] text-zinc-400">
          {a.library ?? "—"}
          {a.api ? ` · ${a.api}` : ""}
        </span>
      ),
    },
    {
      key: "location",
      header: "Path · Line",
      render: (a) => (
        <span className="font-mono text-[11px] text-zinc-400">
          {locationOf(a.file_path, a.line_number)}
        </span>
      ),
    },
    {
      key: "confidence",
      header: "Confidence",
      render: (a) => <Badge kind="confidence">{a.confidence}</Badge>,
    },
    {
      key: "criticality",
      header: "Business",
      render: (a) => <Badge kind="criticality">{a.business_criticality}</Badge>,
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
    {
      key: "link",
      header: "",
      render: (a) => (
        <Link
          href={`/assets/${encodeURIComponent(a.id)}?scan=${encodeURIComponent(selectedScan ?? "")}`}
          className="text-xs text-cyan-400 hover:underline"
        >
          Details →
        </Link>
      ),
      className: "text-right",
    },
  ];

  return (
    <div>
      <PageHeader
        title="Inventory"
        description="Every crypto asset discovered by the scanner, with the finding, business context, risk output and mitigation priority."
        actions={
          <ScanSelector
            scans={scans.data}
            loading={scans.loading}
            value={selectedScan}
            onSelect={onSelect}
            label="Scope"
          />
        }
      />

      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <StatCard label="Findings" value={filtered.length} hint="Matching the current filter" />
        <StatCard label="Assessed" value={`${assessed}/${filtered.length}`} hint="With a risk decision" />
        <StatCard label="Critical" value={critical} hint="Risk level CRITICAL" accent={critical > 0 ? "danger" : "ok"} />
      </div>

      <Card
        title="Crypto asset inventory"
        subtitle={selectedScan ? `Scope limited to scan ${selectedScan}` : "Across all scans"}
        actions={
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search algorithm, path, evidence…"
            className="w-64 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-1.5 text-sm text-zinc-200 outline-none focus:border-cyan-500/50"
          />
        }
      >
        {assets.loading && !assets.data && <Spinner label="Loading inventory…" />}
        {assets.error && <p className="text-sm text-red-400">Failed to load assets: {assets.error}</p>}
        {!assets.loading && !assets.error && (
          <DataTable
            columns={columns}
            rows={filtered}
            rowKey={(a) => `${a.scan_id ?? "all"}/${a.id}`}
            emptyTitle="No crypto assets found"
            emptyDescription="Run a scan and let the discovery pipeline ingest findings, then they will appear here."
          />
        )}
      </Card>
    </div>
  );
}
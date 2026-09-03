/**
 * CBOM (Cryptography Bill of Materials) view.
 *
 * Two inventories for the selected scan — dependencies and certificates —
 * served by GET /cbom/{scan_id}/dependencies and /certificates. The
 * crypto_relevant flag and vulnerability strings are exactly what Member 4's
 * CBOM analysis stored; nothing is re-classified here.
 */
"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState, type ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Column, DataTable } from "@/components/ui/DataTable";
import { PageHeader } from "@/components/ui/PageHeader";
import { ScanSelector } from "@/components/ui/ScanSelector";
import { Spinner } from "@/components/ui/Spinner";
import { StatCard } from "@/components/ui/StatCard";
import {
  useCertificates,
  useCBOM,
  useDependencies,
  useScanSelection,
  useScans,
} from "@/lib/hooks/useApi";
import type { Certificate, Dependency } from "@/lib/types/api";
import { formatDate, humanize } from "@/lib/utils/format";

type Tab = "dependencies" | "certificates";

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
        active
          ? "bg-cyan-500/15 text-cyan-300 ring-1 ring-inset ring-cyan-500/30"
          : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
      }`}
    >
      {children}
    </button>
  );
}

export default function CBOMPage() {
  return (
    <Suspense fallback={<div className="flex flex-1 items-center justify-center py-24"><Spinner /></div>}>
      <CBOMContent />
    </Suspense>
  );
}

function CBOMContent() {
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<Tab>("dependencies");

  const scans = useScans();
  const { selectedScan, onSelect } = useScanSelection(searchParams.get("scan"), scans.data);
  const cbom = useCBOM(selectedScan);
  const dependencies = useDependencies(selectedScan);
  const certificates = useCertificates(selectedScan);

  const activeDeps = tab === "dependencies" ? dependencies.data ?? [] : [];
  const activeCerts = tab === "certificates" ? certificates.data ?? [] : [];

  const cryptoRelevantCount = useMemo(
    () => dependencies.data?.filter((d) => d.crypto_relevant).length ?? 0,
    [dependencies.data],
  );
  const vulnerableCount = useMemo(
    () => dependencies.data?.filter((d) => d.known_vulnerabilities).length ?? 0,
    [dependencies.data],
  );

  const depColumns: Column<Dependency>[] = [
    {
      key: "name",
      header: "Name",
      render: (d) => <span className="font-mono text-xs font-medium text-zinc-100">{d.name}</span>,
    },
    {
      key: "version",
      header: "Version",
      render: (d) => <span className="font-mono text-xs text-zinc-300">{d.version ?? "—"}</span>,
    },
    {
      key: "ecosystem",
      header: "Ecosystem",
      render: (d) => <span className="text-xs text-zinc-400">{humanize(d.ecosystem)}</span>,
    },
    {
      key: "crypto-relevant",
      header: "Crypto relevant",
      render: (d) =>
        d.crypto_relevant ? (
          <Badge kind="info">Yes</Badge>
        ) : (
          <Badge kind="neutral">No</Badge>
        ),
    },
    {
      key: "vulnerabilities",
      header: "Known vulnerabilities",
      render: (d) =>
        d.known_vulnerabilities ? (
          <Badge kind="danger">{d.known_vulnerabilities}</Badge>
        ) : (
          <span className="text-zinc-600">—</span>
        ),
    },
    {
      key: "latest",
      header: "Latest version",
      render: (d) => (
        <span className="font-mono text-xs text-zinc-300">{d.latest_version ?? "—"}</span>
      ),
    },
  ];

  const certColumns: Column<Certificate>[] = [
    {
      key: "subject",
      header: "Subject",
      render: (c) => (
        <span className="block max-w-xs truncate font-mono text-[11px] text-zinc-200" title={c.subject ?? undefined}>
          {c.subject ?? "—"}
        </span>
      ),
    },
    {
      key: "issuer",
      header: "Issuer",
      render: (c) => (
        <span className="block max-w-xs truncate font-mono text-[11px] text-zinc-400" title={c.issuer ?? undefined}>
          {c.issuer ?? "—"}
        </span>
      ),
    },
    {
      key: "key-alg",
      header: "Key algorithm",
      render: (c) => <span className="font-mono text-xs text-zinc-300">{c.key_algorithm ?? "—"}</span>,
    },
    {
      key: "key-size",
      header: "Key size",
      render: (c) =>
        c.key_size != null ? (
          <span className="font-mono text-xs text-zinc-300">{c.key_size}</span>
        ) : (
          <span className="text-zinc-600">—</span>
        ),
    },
    {
      key: "sig-alg",
      header: "Signature algorithm",
      render: (c) => <span className="text-xs text-zinc-400">{c.signature_algorithm ?? "—"}</span>,
    },
    {
      key: "validity",
      header: "Validity",
      render: (c) => (
        <span className="whitespace-nowrap text-[11px] text-zinc-400">
          {formatDate(c.not_valid_before)} → {formatDate(c.not_valid_after)}
        </span>
      ),
    },
    {
      key: "source",
      header: "Source file",
      render: (c) => <span className="font-mono text-[11px] text-zinc-500">{c.source_file ?? "—"}</span>,
    },
  ];

  return (
    <div>
      <PageHeader
        title="CBOM"
        description="Cryptography Bill of Materials — the software dependencies and certificates that carry cryptographic material for the selected scan."
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

      <div className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Dependencies" value={dependencies.data?.length ?? 0} hint="Across the source tree" />
        <StatCard
          label="Crypto relevant"
          value={cryptoRelevantCount}
          hint="Libraries that handle cryptography"
          accent={cryptoRelevantCount > 0 ? "warn" : "ok"}
        />
        <StatCard
          label="With known CVEs"
          value={vulnerableCount}
          hint="Dependencies reporting vulnerabilities"
          accent={vulnerableCount > 0 ? "danger" : "ok"}
        />
        <StatCard label="Certificates" value={certificates.data?.length ?? 0} hint="X.509 material found" />
      </div>

      <Card
        title="Bill of materials"
        subtitle={`Scan ${cbom.data?.scan_id ?? selectedScan ?? ""}`}
        actions={
          <div className="flex gap-1">
            <TabButton active={tab === "dependencies"} onClick={() => setTab("dependencies")}>
              Dependencies ({dependencies.data?.length ?? 0})
            </TabButton>
            <TabButton active={tab === "certificates"} onClick={() => setTab("certificates")}>
              Certificates ({certificates.data?.length ?? 0})
            </TabButton>
          </div>
        }
      >
        {(dependencies.loading || certificates.loading) && !cbom.data && (
          <Spinner label="Loading CBOM…" />
        )}
        {(dependencies.error || certificates.error) && (
          <p className="text-sm text-red-400">
            {dependencies.error ?? certificates.error}
          </p>
        )}
        {!dependencies.loading && !certificates.loading && (
          tab === "dependencies" ? (
            <DataTable
              columns={depColumns}
              rows={activeDeps}
              rowKey={(d) => `${d.name}@${d.version ?? "?"}-${d.ecosystem ?? "?"}`}
              emptyTitle="No dependencies catalogued"
              emptyDescription="Dependency inventory for this scan is empty."
            />
          ) : (
            <DataTable
              columns={certColumns}
              rows={activeCerts}
              rowKey={(c) => c.serial_number ?? `${c.subject ?? ""}-${c.key_size ?? ""}`}
              emptyTitle="No certificates catalogued"
              emptyDescription="Certificate inventory for this scan is empty."
            />
          )
        )}
      </Card>
    </div>
  );
}
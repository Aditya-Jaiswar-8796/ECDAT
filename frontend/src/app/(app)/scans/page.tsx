/**
 * Scans view — create a scan, upload a source ZIP bundle and follow the
 * pipeline live:
 *   Upload -> Discover -> Analyze -> Risk Assessment -> Recommendation -> Complete.
 * Status is polled from the real API so the stage indicator advances as the
 * backend pipeline progresses.
 */
"use client";

import { useState } from "react";
import Link from "next/link";

import { ApiError, api } from "@/lib/api/client";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { ScanStageIndicator } from "@/components/ui/ScanStageIndicator";
import { Spinner } from "@/components/ui/Spinner";
import { useScan, useScans } from "@/lib/hooks/useApi";
import type { Scan, ScanCreate } from "@/lib/types/api";
import { formatDateTime, humanize } from "@/lib/utils/format";
import { deriveStages } from "@/lib/utils/stages";

export default function ScansPage() {
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [project, setProject] = useState("");
  const [language, setLanguage] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [uploadingFor, setUploadingFor] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  // Scans list refresh; the detail watcher derives a valid scan id from the
  // explicit selection or falls back to the newest scan (render-time only).
  const scans = useScans(5000);
  const activeScanId = selectedScanId ?? scans.data?.[0]?.scan_id ?? null;
  const detail = useScan(activeScanId);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      const payload: ScanCreate = {
        name: name.trim(),
        project_name: project.trim() || null,
        language: language.trim() || null,
      };
      const created = await api.createScan(payload);
      setName("");
      setProject("");
      setLanguage("");
      setSelectedScanId(created.scan_id);
    } catch (err: unknown) {
      setCreateError(err instanceof ApiError ? err.detail : String(err));
    } finally {
      setCreating(false);
    }
  };

  const handleUpload = async (scanId: string, file: File | null) => {
    if (!file) return;
    setUploadingFor(scanId);
    setUploadStatus(`Uploading ${file.name}…`);
    try {
      await api.uploadBundle(scanId, file);
      setSelectedScanId(scanId);
      setUploadStatus("Upload complete — pipeline started.");
    } catch (err: unknown) {
      setUploadStatus(
        err instanceof ApiError ? `Upload failed: ${err.detail}` : `Upload failed: ${String(err)}`,
      );
    } finally {
      setUploadingFor(null);
    }
  };

  const waitingUpload = selectedScanId !== null && detail.data?.scan.status === "RECEIVED";

  return (
    <div>
      <PageHeader
        title="Scans"
        description="Create a scan, upload the source bundle, then watch the discovery and assessment pipeline advance stage by stage."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* New scan form */}
        <Card title="New scan" subtitle="Register a source bundle for analysis" className="lg:col-span-1 self-start">
          <form onSubmit={handleCreate} className="space-y-3">
            <label className="block text-sm">
              <span className="text-zinc-500">Name *</span>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Payments service"
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-cyan-500/50"
              />
            </label>
            <label className="block text-sm">
              <span className="text-zinc-500">Project</span>
              <input
                value={project}
                onChange={(e) => setProject(e.target.value)}
                placeholder="e.g. core-banking"
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-cyan-500/50"
              />
            </label>
            <label className="block text-sm">
              <span className="text-zinc-500">Language</span>
              <input
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                placeholder="e.g. java"
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-cyan-500/50"
              />
            </label>
            {createError && <p className="text-sm text-red-400">{createError}</p>}
            <button
              type="submit"
              disabled={creating}
              className="w-full rounded-lg bg-cyan-500 px-3 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-cyan-400 disabled:opacity-50"
            >
              {creating ? "Creating…" : "Create scan"}
            </button>
          </form>
        </Card>

        {/* Scan list with upload + stages */}
        <div className="lg:col-span-2 space-y-4">
          {scans.loading && !scans.data && <Spinner label="Loading scans…" />}
          {scans.error && (
            <p className="text-sm text-red-400">Failed to load scans: {scans.error}</p>
          )}

          {!scans.loading && (!scans.data || scans.data.length === 0) && (
            <Card title="No scans yet" subtitle="Create your first scan using the form">
              <p className="text-sm text-zinc-500">
                After creating a scan, a ZIP of the target source tree can be uploaded and the
                pipeline (discover → analyze → risk → recommendation) will start.
              </p>
            </Card>
          )}

          {scans.data?.map((scan: Scan) => {
            const isSelected = scan.scan_id === selectedScanId;
            const stageStages = deriveStages(scan, null, null);
            return (
              <Card
                key={scan.scan_id}
                className={isSelected ? "ring-1 ring-cyan-500/30" : undefined}
                title={scan.name}
                subtitle={`${scan.scan_id} · created ${formatDateTime(scan.created_at)}`}
                actions={
                  <div className="flex items-center gap-2">
                    <Badge kind="status">{scan.status}</Badge>
                    <button
                      type="button"
                      onClick={() => setSelectedScanId(scan.scan_id)}
                      className="rounded-lg border border-zinc-700 px-2 py-1 text-xs text-zinc-300 hover:border-cyan-500/50"
                    >
                      {isSelected ? "Watching" : "Watch"}
                    </button>
                  </div>
                }
              >
                <ScanStageIndicator
                  stages={stageStages}
                  headline={
                    scan.status === "FAILED"
                      ? `Failed: ${scan.error ?? "unknown error"}`
                      : undefined
                  }
                />

                {/* Per-scan quick navigation when findings exist */}
                {scan.asset_count > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <Link
                      href={`/inventory?scan=${scan.scan_id}`}
                      className="rounded-full border border-zinc-700 px-3 py-1 text-zinc-300 hover:border-cyan-500/50"
                    >
                      Inventory · {scan.asset_count} assets
                    </Link>
                    <Link
                      href={`/cbom?scan=${scan.scan_id}`}
                      className="rounded-full border border-zinc-700 px-3 py-1 text-zinc-300 hover:border-cyan-500/50"
                    >
                      CBOM · {scan.dependency_count} deps / {scan.certificate_count} certs
                    </Link>
                    <Link
                      href={`/risk?scan=${scan.scan_id}`}
                      className="rounded-full border border-zinc-700 px-3 py-1 text-zinc-300 hover:border-cyan-500/50"
                    >
                      Risk
                    </Link>
                    <Link
                      href={`/priority?scan=${scan.scan_id}`}
                      className="rounded-full border border-zinc-700 px-3 py-1 text-zinc-300 hover:border-cyan-500/50"
                    >
                      Priority
                    </Link>
                    <Link
                      href={`/reports?scan=${scan.scan_id}`}
                      className="rounded-full border border-zinc-700 px-3 py-1 text-zinc-300 hover:border-cyan-500/50"
                    >
                      Report
                    </Link>
                  </div>
                )}

                {/* Upload control — only allowed before the bundle is accepted */}
                {scan.status === "RECEIVED" && !scan.error && (
                  <div className="mt-3 rounded-lg border border-dashed border-zinc-700 p-3">
                    <label className="cursor-pointer text-sm text-cyan-400 hover:underline">
                      Upload source bundle (ZIP)
                      <input
                        type="file"
                        accept=".zip"
                        className="hidden"
                        disabled={uploadingFor === scan.scan_id}
                        onChange={(e) => {
                          void handleUpload(scan.scan_id, e.target.files?.[0] ?? null);
                          e.currentTarget.value = "";
                        }}
                      />
                    </label>
                    <p className="mt-1 text-xs text-zinc-600">
                      Accepted: single .zip archive. The backend validates the archive and never
                      executes uploaded code.
                    </p>
                  </div>
                )}

                {scan.status === "FAILED" && scan.error && (
                  <p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                    {scan.error}
                  </p>
                )}
              </Card>
            );
          })}
        </div>
      </div>

      {/* Live selected-scan pipeline detail */}
      {selectedScanId && (
        <Card
          title={`Live pipeline — ${detail.data?.scan.name ?? selectedScanId}`}
          subtitle="Refreshes automatically while the scan is running"
          className="mt-6"
          actions={
            detail.isPending ? <Badge kind="info">Running…</Badge> : undefined
          }
        >
          {detail.loading && !detail.data && <Spinner label="Polling scan status…" />}
          {detail.error && (
            <p className="text-sm text-red-400">Unable to poll scan: {detail.error}</p>
          )}
          {detail.data && (
            <div className="space-y-4">
              <ScanStageIndicator
                stages={deriveStages(detail.data.scan, detail.data.summary, detail.data.risks)}
                headline={`Current status: ${humanize(detail.data.scan.status)}`}
              />
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  { label: "Assets", value: detail.data.summary.asset_count },
                  { label: "Dependencies", value: detail.data.summary.dependency_count },
                  { label: "Certificates", value: detail.data.summary.certificate_count },
                  { label: "Recommendations", value: detail.data.summary.recommendation_count },
                ].map((s) => (
                  <div
                    key={s.label}
                    className="rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-center"
                  >
                    <p className="text-xl font-semibold text-zinc-100">{s.value}</p>
                    <p className="text-[11px] uppercase tracking-wide text-zinc-500">{s.label}</p>
                  </div>
                ))}
              </div>
              {uploadStatus && <p className="text-sm text-cyan-300">{uploadStatus}</p>}
              {waitingUpload && (
                <p className="text-sm text-zinc-500">
                  Waiting for a source bundle — upload it from the scan card above.
                </p>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
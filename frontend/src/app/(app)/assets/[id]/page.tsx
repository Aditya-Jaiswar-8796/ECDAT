/**
 * Asset detail view.
 *
 * Shows every field of one crypto asset: algorithm, operation, key size,
 * language, library/API, path, line, evidence, confidence, business context,
 * risk output (score / level / priority / Mosca) and recommendation.
 */
"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { use, useMemo } from "react";

import { AssetDetail } from "@/components/assets/AssetDetail";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { useAssets, useScans } from "@/lib/hooks/useApi";
import { formatDateTime } from "@/lib/utils/format";

interface AssetPageProps {
  params: Promise<{ id: string }>;
}

export default function AssetPage({ params }: AssetPageProps) {
  const { id: assetId } = use(params);
  const searchParams = useSearchParams();
  const scanId = searchParams.get("scan");

  // GET /assets/{pk} requires the DB primary key which the list endpoint does
  // not expose, so resolve the asset by its stable scanner id within the scan.
  const assets = useAssets(scanId);
  const scans = useScans();

  const asset = useMemo(() => {
    const list = assets.data ?? [];
    return (
      list.find((a) => a.id === assetId) ??
      (scanId ? undefined : list.find((a) => a.id === assetId))
    );
  }, [assets.data, assetId, scanId]);

  const scan = scans.data?.find((s) => s.scan_id === scanId);

  const backHref =
    `/inventory${scanId ? `?scan=${encodeURIComponent(scanId)}` : ""}`;

  return (
    <div>
      <PageHeader
        title={`Asset — ${assetId}`}
        description={
          scan ? (
            <>
              Found in scan <span className="font-medium text-zinc-300">{scan.name}</span> (
              {scan.scan_id}), created {formatDateTime(scan.created_at)}
            </>
          ) : (
            "Asset finding details"
          )
        }
        actions={
          <Link href={backHref} className="text-sm text-cyan-400 hover:underline">
            ← Back to inventory
          </Link>
        }
      />

      {assets.loading && !assets.data && <Spinner label="Loading asset…" />}
      {assets.error && <p className="text-sm text-red-400">Failed to load asset: {assets.error}</p>}

      {!assets.loading && !assets.error && asset && (
        <AssetDetail asset={asset} scanName={scan?.name} />
      )}

      {!assets.loading && !assets.error && !asset && (
        <EmptyState
          title="Asset not found"
          description={`No asset with id "${assetId}" was returned by the API${scanId ? ` for scan ${scanId}` : ""}.`}
          action={
            <Link href={backHref} className="text-sm text-cyan-400 hover:underline">
              ← Back to inventory
            </Link>
          }
        />
      )}
    </div>
  );
}
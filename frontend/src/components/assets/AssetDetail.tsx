/**
 * AssetDetail — canonical full detail view of one crypto asset.
 *
 * Renders every required finding field (algorithm, operation, key size,
 * language, library/API, path, line, evidence, confidence), the business
 * context, the risk output (score / level / priority / Mosca) and the
 * recommendation — always from the API-provided asset object.
 */
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { DefinitionGrid } from "@/components/ui/DefinitionGrid";
import type { CryptoAsset } from "@/lib/types/api";
import { formatScore, humanize, locationOf } from "@/lib/utils/format";

interface AssetDetailProps {
  /** A single asset together with its scan_id (when present). */
  asset: CryptoAsset;
  /** Optional "as of scan" line shown in the header. */
  scanName?: string;
}

function NasItem({ label, value, mono }: { label: string; value?: string | null; mono?: boolean }) {
  return (
    <div>
      <dt className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">{label}</dt>
      <dd className={`mt-0.5 text-sm text-zinc-200 ${mono ? "font-mono" : ""}`}>
        {value ?? <span className="text-zinc-600">—</span>}
      </dd>
    </div>
  );
}

export function AssetDetail({ asset, scanName }: AssetDetailProps) {
  return (
    <div className="space-y-4">
      <Card
        title="Finding"
        subtitle={scanName ? `From scan: ${scanName}` : asset.scan_id ?? "Asset finding"}
        actions={<Badge kind="confidence">{asset.confidence}</Badge>}
      >
        <DefinitionGrid
          columns={3}
          rows={[
            { label: "Algorithm", value: asset.algorithm, mono: true },
            { label: "Operation", value: humanize(asset.operation), mono: true },
            {
              label: "Key size",
              value: asset.key_size != null ? `${asset.key_size} bits` : null,
              mono: true,
            },
            { label: "Language", value: asset.language },
            { label: "Library", value: asset.library, mono: true },
            { label: "API", value: asset.api, mono: true },
            { label: "Path", value: locationOf(asset.file_path, asset.line_number), mono: true },
            { label: "Line", value: asset.line_number ?? null, mono: true },
            { label: "Confidence", value: asset.confidence },
          ]}
        />
        {asset.evidence && (
          <div className="mt-4">
            <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">Evidence</p>
            <pre className="mt-1 overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs leading-relaxed text-zinc-300">
              {asset.evidence}
            </pre>
          </div>
        )}
      </Card>

      <Card
        title="Business context"
        actions={<Badge kind="criticality">{asset.business_criticality}</Badge>}
      >
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
          <NasItem label="Business criticality" value={asset.business_criticality} />
          <NasItem
            label="Data lifetime"
            value={asset.data_lifetime_years != null ? `${asset.data_lifetime_years} years` : null}
          />
          <div>
            <dt className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
              Internet exposure
            </dt>
            <dd className="mt-0.5 text-sm text-zinc-200">
              {asset.internet_exposure ? (
                <Badge kind="danger">Exposed</Badge>
              ) : (
                <Badge kind="info">Internal</Badge>
              )}
            </dd>
          </div>
          <NasItem label="Migration complexity" value={asset.migration_complexity} />
        </dl>
      </Card>

      <Card
        title="Risk assessment"
        subtitle="Produced by the risk engine (Member 5)"
        actions={
          asset.risk_level ? (
            <Badge kind="risk">{asset.risk_level}</Badge>
          ) : (
            <Badge kind="neutral">Not assessed</Badge>
          )
        }
      >
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
          <NasItem label="Risk score" value={formatScore(asset.risk_score)} mono />
          <NasItem label="Risk level" value={asset.risk_level} />
          <NasItem label="Migration priority" value={asset.migration_priority} />
          <div>
            <dt className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">Mosca</dt>
            <dd className="mt-0.5 text-sm text-zinc-200">
              {asset.mosca_assessment ? (
                <Badge kind="info">Assessed</Badge>
              ) : (
                <span className="text-zinc-600">—</span>
              )}
            </dd>
          </div>
        </dl>
        {asset.mosca_assessment && (
          <p className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-sm leading-relaxed text-zinc-300">
            {asset.mosca_assessment}
          </p>
        )}
      </Card>

      <Card title="Recommendation" subtitle="Migration guidance from the risk engine">
        <p className="text-sm leading-relaxed text-zinc-200">
          {asset.recommendation ?? "No recommendation available for this asset."}
        </p>
      </Card>
    </div>
  );
}
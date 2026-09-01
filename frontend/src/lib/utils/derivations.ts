/**
 * Derivations — client-side aggregation helpers.
 *
 * These only COUNT / GROUP values that the backend already produced
 * (risk_level, migration_priority, algorithm, ...). They never assign a
 * classification, score or label on the client.
 */
import type { DistributionBucket } from "@/components/ui/DistributionCard";
import type {
  CryptoAsset,
  MigrationPriority,
  RiskLevel,
} from "@/lib/types/api";

const RISK_COLORS: Record<RiskLevel, string> = {
  CRITICAL: "bg-red-400",
  HIGH: "bg-orange-400",
  MEDIUM: "bg-yellow-400",
  LOW: "bg-emerald-400",
};

const PRIORITY_COLORS: Record<MigrationPriority, string> = {
  URGENT: "bg-red-400",
  HIGH: "bg-orange-400",
  MEDIUM: "bg-yellow-400",
  LOW: "bg-sky-400",
};

const GENERIC_COLORS = [
  "bg-cyan-400",
  "bg-violet-400",
  "bg-pink-400",
  "bg-teal-400",
  "bg-amber-400",
  "bg-blue-400",
];

/** Count assets per risk level (values come straight from the API). */
export function riskDistribution(assets: CryptoAsset[]): DistributionBucket[] {
  return countBuckets<RiskLevel>(
    assets,
    (a) => a.risk_level,
    Object.keys(RISK_COLORS) as RiskLevel[],
    RISK_COLORS,
    (key) => `Not assessed (${key})`,
  );
}

/** Count assets per migration priority bucket (API values). */
export function priorityDistribution(assets: CryptoAsset[]): DistributionBucket[] {
  return countBuckets<MigrationPriority>(
    assets,
    (a) => a.migration_priority,
    Object.keys(PRIORITY_COLORS) as MigrationPriority[],
    PRIORITY_COLORS,
    (key) => `No priority (${key})`,
  );
}

/** Count assets per algorithm (API values, descending by count). */
export function algorithmBreakdown(assets: CryptoAsset[]): DistributionBucket[] {
  const counts = new Map<string, number>();
  assets.forEach((a) => counts.set(a.algorithm, (counts.get(a.algorithm) ?? 0) + 1));
  const entries = [...counts.entries()].sort((x, y) => y[1] - x[1]);
  return entries.map(([label, value], i) => ({
    label,
    value,
    color: GENERIC_COLORS[i % GENERIC_COLORS.length],
  }));
}

/** Count assets per business criticality level (API values). */
export function criticalityDistribution(assets: CryptoAsset[]): DistributionBucket[] {
  const order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;
  const counts = new Map<string, number>();
  assets.forEach((a) => {
    const key = a.business_criticality;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  });
  return order
    .filter((k) => counts.has(k))
    .map((k) => ({
      label: k,
      value: counts.get(k) ?? 0,
      color: RISK_COLORS[k as RiskLevel] ?? "bg-zinc-600",
    }));
}

/** Generic bucket counter plus an "unassigned" bucket for null values. */
function countBuckets<T extends string>(
  assets: CryptoAsset[],
  pick: (a: CryptoAsset) => T | null,
  keys: T[],
  colors: Record<T, string>,
  fallbackLabel: (k: string) => string,
): DistributionBucket[] {
  const counts = new Map<string, number>();
  assets.forEach((a) => {
    const key = pick(a) ?? "unassigned";
    counts.set(key, (counts.get(key) ?? 0) + 1);
  });
  const buckets: DistributionBucket[] = keys
    .filter((k) => counts.has(k))
    .map((k) => ({ label: k, value: counts.get(k) ?? 0, color: colors[k] }));
  if (counts.has("unassigned")) {
    buckets.push({
      label: fallbackLabel("unassigned"),
      value: counts.get("unassigned") ?? 0,
      color: "bg-zinc-600",
    });
  }
  return buckets;
}
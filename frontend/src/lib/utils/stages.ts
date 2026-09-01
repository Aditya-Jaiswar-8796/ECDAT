/**
 * Scan stage derivation.
 *
 * Maps backend scan state (status + summary counters + risk counts) onto the
 * frontend stage pipeline:
 *   Upload -> Discover -> Analyze -> Risk Assessment -> Recommendation -> Complete
 * Every stage is computed from real API values; nothing is guessed.
 */
import type {
  RiskAssessmentSummary,
  Scan,
  ScanSummary,
} from "@/lib/types/api";

export type StageKey =
  | "upload"
  | "discover"
  | "analyze"
  | "riskAssessment"
  | "recommendation"
  | "complete";

export interface StageState {
  key: StageKey;
  label: string;
  /** API-backed explanation shown under each stage. */
  detail: string;
  /** done | active | pending | failed */
  state: "done" | "active" | "pending" | "failed";
}

const STAGE_LABELS: Record<StageKey, string> = {
  upload: "Upload",
  discover: "Discover",
  analyze: "Analyze",
  riskAssessment: "Risk Assessment",
  recommendation: "Recommendation",
  complete: "Complete",
};

/**
 * Compute stage states from live API values.
 *
 * @param scan        scan object from GET /scans/{id}
 * @param summary     counters from GET /scans/{id}/summary
 * @param riskSummary assessed assets from GET /risks/{id}
 */
export function deriveStages(
  scan: Scan,
  summary: ScanSummary | null,
  riskSummary: RiskAssessmentSummary | null,
): StageState[] {
  const assetCount = summary?.asset_count ?? scan.asset_count ?? 0;
  const recommendationCount = summary?.recommendation_count ?? 0;
  const assessedCount = riskSummary?.assessed_count ?? 0;

  // Each boolean means "this stage has completed" per the API data.
  const flags: Record<StageKey, boolean> = {
    // Upload done once the backend moved past RECEIVED (bundle uploaded).
    upload: scan.status !== "RECEIVED",
    // Discover done when at least one crypto asset was ingested.
    discover: assetCount > 0,
    // Analyze done when discovery finished and the scan is past SCANNING.
    analyze:
      assetCount > 0 &&
      (scan.status === "SCAN_COMPLETE" || scan.status === "RISK_ASSESSED"),
    // Risk Assessment done when the risk engine assessed at least one asset.
    riskAssessment: assessedCount > 0 || scan.status === "RISK_ASSESSED",
    // Recommendation done when recommendations were ingested.
    recommendation: recommendationCount > 0,
    // Complete only when risk assessed and recommendations exist.
    complete: scan.status === "RISK_ASSESSED" && recommendationCount > 0,
  };

  const order: StageKey[] = [
    "upload",
    "discover",
    "analyze",
    "riskAssessment",
    "recommendation",
    "complete",
  ];

  // First stage that is not yet finished becomes the "active" stage.
  const activeIndex = order.findIndex((k) => !flags[k]);

  return order.map((key, index) => {
    let state: StageState["state"];
    if (flags[key]) {
      state = "done";
    } else if (scan.status === "FAILED" && activeIndex === index) {
      // A failed scan cannot advance; highlight the failure point.
      state = "failed";
    } else if (index === activeIndex) {
      state = "active";
    } else {
      state = "pending";
    }
    return { key, label: STAGE_LABELS[key], detail: stageDetail(key, state, scan), state };
  });
}

/** One-line, API-driven blurb for the stage tooltip/subtext. */
function stageDetail(
  key: StageKey,
  state: StageState["state"],
  scan: Scan,
): string {
  switch (key) {
    case "upload":
      if (scan.status === "FAILED") return "Upload failed: " + (scan.error ?? "unknown error");
      if (scan.status === "RECEIVED") return "Scan created; waiting for bundle";
      return "Bundle received";
    case "discover":
      return state === "done" ? "Crypto assets discovered" : "Waiting for scanner findings";
    case "analyze":
      return state === "done" ? "Findings analyzed" : "Analysis pending";
    case "riskAssessment":
      return state === "done" ? "Risks assessed" : "Risk engine has not assessed yet";
    case "recommendation":
      return state === "done" ? "Recommendations ready" : "No recommendations yet";
    case "complete":
      return state === "done" ? "Scan complete" : "Final status pending";
  }
}
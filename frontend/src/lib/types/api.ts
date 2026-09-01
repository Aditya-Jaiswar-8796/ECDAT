/**
 * ECDAT API TypeScript types.
 *
 * These mirror the canonical Pydantic schemas served by the backend
 * (app/schemas/*.py). They are the single integration contract between
 * the dashboard (Member 6) and the backend (Member 1).
 */

/** Confidence level assigned by the scanner (Member 3). */
export type ConfidenceLevel = "LOW" | "MEDIUM" | "HIGH";

/** Business criticality of an asset (Member 3). */
export type CriticalityLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

/** How costly a migration of this asset is expected to be (Member 3). */
export type MigrationComplexity = "LOW" | "MEDIUM" | "HIGH";

/** Risk level produced by the risk engine (Member 5). */
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

/** Migration priority bucket produced by the risk engine (Member 5). */
export type MigrationPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT";

/** Backend scan lifecycle status values. */
export type ScanStatus =
  | "RECEIVED"
  | "SCANNING"
  | "SCAN_COMPLETE"
  | "RISK_ASSESSED"
  | "FAILED";

/** Canonical crypto asset -- the single source of truth for a finding. */
export interface CryptoAsset {
  id: string;
  algorithm: string;
  operation: string;
  key_size: number | null;
  language: string;
  library: string | null;
  api: string | null;
  file_path: string;
  line_number: number | null;
  evidence: string | null;
  confidence: ConfidenceLevel;
  business_criticality: CriticalityLevel;
  data_lifetime_years: number | null;
  internet_exposure: boolean;
  migration_complexity: MigrationComplexity;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  migration_priority: MigrationPriority | null;
  mosca_assessment: string | null;
  recommendation: string | null;
  /** Present on /assets list & ingest responses (not in the canonical schema). */
  scan_id?: string;
}

/** Scan lifecycle object. */
export interface Scan {
  scan_id: string;
  name: string;
  project_name: string | null;
  language: string | null;
  status: ScanStatus;
  error: string | null;
  created_at: string;
  updated_at: string;
  asset_count: number;
  dependency_count: number;
  certificate_count: number;
}

/** Payload used to create a new scan. */
export interface ScanCreate {
  name: string;
  project_name?: string | null;
  language?: string | null;
}

/** Aggregated counters returned by GET /scans/{id}/summary. */
export interface ScanSummary {
  asset_count: number;
  dependency_count: number;
  certificate_count: number;
  recommendation_count: number;
}

/** Record returned by GET /risks (optionally filtered by scan). */
export interface RiskRecord {
  scan_id: string;
  asset_id: string;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  migration_priority: MigrationPriority | null;
  mosca_assessment: string | null;
}

/** One assessed asset within GET /risks/{scan_id}. */
export interface RiskAssessmentItem {
  asset_id: string;
  algorithm: string;
  file_path: string;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  migration_priority: MigrationPriority | null;
  mosca_assessment: string | null;
}

/** Response of GET /risks/{scan_id}. */
export interface RiskAssessmentSummary {
  scan_id: string;
  asset_count: number;
  assessed_count: number;
  assessments: RiskAssessmentItem[];
}

/** Remediation / migration recommendation (Member 5). */
export interface Recommendation {
  scan_id?: string;
  asset_id: string | null;
  recommendation: string;
  explanation: string | null;
  suggested_target: string | null;
  effort_estimate: string | null;
}

/** Library / package dependency entry for the CBOM (Member 4). */
export interface Dependency {
  name: string;
  version: string | null;
  ecosystem: string | null;
  crypto_relevant: boolean;
  known_vulnerabilities: string | null;
  latest_version: string | null;
}

/** X.509 certificate entry for the CBOM (Member 4). */
export interface Certificate {
  subject: string | null;
  issuer: string | null;
  serial_number: string | null;
  fingerprint_sha256: string | null;
  not_valid_before: string | null;
  not_valid_after: string | null;
  signature_algorithm: string | null;
  key_algorithm: string | null;
  key_size: number | null;
  source_file: string | null;
}

/** Compact CBOM payload returned by GET /cbom/{scan_id}. */
export interface CBOM {
  scan_id: string;
  dependencies: Array<
    Pick<Dependency, "name" | "version" | "ecosystem" | "crypto_relevant">
  >;
  certificates: Array<
    Pick<Certificate, "subject" | "issuer" | "signature_algorithm" | "key_size">
  >;
}

/** Liveness probe result. */
export interface Health {
  status: "ok" | "degraded";
  database: "up" | "down";
}

/**
 * Frontend scan stage model (Upload -> Discover -> Analyze -> Risk Assessment
 * -> Recommendation -> Complete). Derived from backend status + data presence,
 * never hard-coded metrics.
 */
export interface ScanStages {
  upload: boolean;
  discover: boolean;
  analyze: boolean;
  riskAssessment: boolean;
  recommendation: boolean;
  complete: boolean;
}
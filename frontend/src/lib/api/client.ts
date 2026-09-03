/**
 * ECDAT API client.
 *
 * Thin typed wrapper around the backend REST API (FastAPI, port 8000).
 * All data shown by the dashboard flows through these functions -- nothing is
 * hard-coded. Requests go straight to the FastAPI service which already
 * enables CORS for all origins.
 */
import type {
  CBOM,
  Certificate,
  CryptoAsset,
  Dependency,
  Health,
  Recommendation,
  RiskAssessmentSummary,
  RiskRecord,
  Scan,
  ScanCreate,
  ScanSummary,
} from "@/lib/types/api";

/** Backend origin, overridable via NEXT_PUBLIC_API_URL. */
export const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Error raised for any non-2xx API response. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(`API error ${status}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** Core fetch wrapper: JSON encode, JSON decode, surface API detail messages. */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep fallback detail when response is not JSON */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** JSON request helper for POST/PATCH bodies. */
function jsonInit(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export const api = {
  /** Liveness + DB probe. */
  health: () => request<Health>("/health"),

  /* ---- Scans ---- */
  listScans: () => request<Scan[]>("/scans"),
  getScan: (scanId: string) => request<Scan>(`/scans/${scanId}`),
  createScan: (payload: ScanCreate) =>
    request<Scan>("/scans", jsonInit("POST", payload)),
  /** Upload a ZIP bundle for a scan; advances status to SCANNING. */
  uploadBundle: (scanId: string, file: File) => {
    const form = new FormData();
    form.append("upload", file);
    return request<Scan>(`/scans/${scanId}/upload`, { method: "POST", body: form });
  },
  getScanSummary: (scanId: string) =>
    request<ScanSummary>(`/scans/${scanId}/summary`),
  /** Delete every scan and its findings (dashboard 'Clear all' action). */
  clearScans: () => request<{ deleted: number }>("/scans", { method: "DELETE" }),

  /* ---- Crypto assets ---- */
  listAssets: (scanId?: string) => {
    const qs = scanId ? `?scan_id=${encodeURIComponent(scanId)}` : "";
    return request<CryptoAsset[]>(`/assets${qs}`);
  },

  /* ---- Risk ---- */
  listRisks: (scanId?: string) => {
    const qs = scanId ? `?scan_id=${encodeURIComponent(scanId)}` : "";
    return request<RiskRecord[]>(`/risks${qs}`);
  },
  getScanRisks: (scanId: string) =>
    request<RiskAssessmentSummary>(`/risks/${encodeURIComponent(scanId)}`),

  /* ---- Recommendations ---- */
  listRecommendations: (scanId?: string) => {
    const qs = scanId ? `?scan_id=${encodeURIComponent(scanId)}` : "";
    return request<Recommendation[]>(`/recommendations${qs}`);
  },
  getScanRecommendations: (scanId: string) =>
    request<Recommendation[]>(`/recommendations/${encodeURIComponent(scanId)}`),

  /* ---- CBOM ---- */
  getScanCBOM: (scanId: string) =>
    request<CBOM>(`/cbom/${encodeURIComponent(scanId)}`),
  listScanDependencies: (scanId: string) =>
    request<Dependency[]>(`/cbom/${encodeURIComponent(scanId)}/dependencies`),
  listScanCertificates: (scanId: string) =>
    request<Certificate[]>(`/cbom/${encodeURIComponent(scanId)}/certificates`),
};

/** Derive the ordered set of finding fields for asset tables/cards. */
export async function fetchAssetForId(
  scanId: string | undefined,
  assetId: string,
): Promise<CryptoAsset | undefined> {
  const assets = await api.listAssets(scanId);
  return assets.find((a) => a.id === assetId);
}
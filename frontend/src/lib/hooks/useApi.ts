/**
 * Web API hooks.
 *
 * Shared, reusable data-fetching hooks used across inventory / risk /
 * priority / CBOM / report views. Each hook loads the matching backend slice
 * (data id, error message, loading flag) and optionally supports auto-refresh
 * for the live scan status view. All state updates happen asynchronously
 * (inside promise callbacks) so no synchronous setState runs inside effects.
 */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api/client";
import type {
  CBOM,
  Certificate,
  CryptoAsset,
  Dependency,
  Recommendation,
  RiskAssessmentSummary,
  Scan,
  ScanSummary,
} from "@/lib/types/api";

/** Generic result shape returned by every data hook. */
export interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/** Fetches a promise, tracking loading/error/data lifecycle. */
function usePromise<T>(fetcher: () => Promise<T>, deps: unknown[], enabled = true) {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    error: null,
    loading: enabled,
  });
  const cancelled = useRef(false);

  // All state changes happen inside the async fetch callbacks, never
  // synchronously in the effect body (React hooks lint compliance).
  useEffect(() => {
    if (!enabled) return;
    cancelled.current = false;
    fetcher()
      .then((data) => {
        if (!cancelled.current) setState({ data, error: null, loading: false });
      })
      .catch((err: unknown) => {
        if (!cancelled.current) {
          setState({
            data: null,
            error: err instanceof Error ? err.message : String(err),
            loading: false,
          });
        }
      });
    return () => {
      cancelled.current = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}

/** All scans, newest first. */
export function useScans(
  refreshMs = 0,
): AsyncState<Scan[]> & { refresh: () => void } {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (refreshMs <= 0) return;
    const id = setInterval(() => setTick((t) => t + 1), refreshMs);
    return () => clearInterval(id);
  }, [refreshMs]);
  const state = usePromise(() => api.listScans(), [tick]);
  const refresh = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, refresh };
}

/** Single scan + summary + risk-derived stage completion, polled while running. */
export interface ScanDetailState {
  scan: Scan;
  summary: ScanSummary;
  risks: RiskAssessmentSummary;
  recommendations: Recommendation[];
}

export function useScan(
  scanId: string | null,
): AsyncState<ScanDetailState> & { isPending: boolean; refresh: () => void } {
  const [tick, setTick] = useState(0);
  const [state, setState] = useState<AsyncState<ScanDetailState> & { isPending: boolean }>({
    data: null,
    error: null,
    loading: Boolean(scanId),
    isPending: false,
  });

  useEffect(() => {
    if (!scanId) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const scan = await api.getScan(scanId);
        if (cancelled) return;
        const [summary, risks, recommendations] = await Promise.all([
          api.getScanSummary(scanId),
          api.getScanRisks(scanId),
          api.getScanRecommendations(scanId),
        ]);
        if (cancelled) return;
        setState({
          data: { scan, summary, risks, recommendations },
          error: null,
          loading: false,
          isPending: scan.status === "RECEIVED" || scan.status === "SCANNING",
        });
      } catch (err: unknown) {
        if (cancelled) return;
        // A 404 means the scan was deleted (e.g. "Clear all scans" ran while a
        // poll was in flight). Treat it as "nothing to watch" rather than a hard
        // error so the UI doesn't spam the console with 404s for a stale id.
        if (err instanceof Error && err.message.includes("404")) {
          setState({
            data: null,
            error: null,
            loading: false,
            isPending: false,
          });
          return;
        }
        setState({
          data: null,
          error: err instanceof Error ? err.message : String(err),
          loading: false,
          isPending: false,
        });
      }
    };
    void poll();
    // Refresh every 4s so the stage pipeline advances live on screen.
    const id = setInterval(() => void poll(), 4000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [scanId, tick]);

  // Manual refresh (used by views with a refresh button).
  const refresh = useCallback(() => setTick((t) => t + 1), []);

  return { ...state, refresh };
}

/** Crypto assets for a scan (or across all scans when scanId omitted). */
export function useAssets(scanId?: string | null): AsyncState<CryptoAsset[]> {
  return usePromise(
    () => api.listAssets(scanId ?? undefined),
    [scanId ?? null],
    scanId !== undefined,
  );
}

/** Full risk assessment summary for a scan. */
export function useRisks(scanId?: string | null): AsyncState<RiskAssessmentSummary> {
  return usePromise(
    () => api.getScanRisks(scanId!),
    [scanId ?? null],
    Boolean(scanId),
  );
}

/** Recommendations for a scan. */
export function useRecommendations(
  scanId?: string | null,
): AsyncState<Recommendation[]> {
  return usePromise(
    () => api.getScanRecommendations(scanId!),
    [scanId ?? null],
    Boolean(scanId),
  );
}

/** CBOM (dependencies + certificates) for a scan. */
export function useCBOM(scanId?: string | null): AsyncState<CBOM> {
  return usePromise(
    () => api.getScanCBOM(scanId!),
    [scanId ?? null],
    Boolean(scanId),
  );
}

/** Full certificate inventory for a scan. */
export function useCertificates(scanId?: string | null): AsyncState<Certificate[]> {
  return usePromise(
    () => api.listScanCertificates(scanId!),
    [scanId ?? null],
    Boolean(scanId),
  );
}

/** Full dependency inventory for a scan. */
export function useDependencies(scanId?: string | null): AsyncState<Dependency[]> {
  return usePromise(
    () => api.listScanDependencies(scanId!),
    [scanId ?? null],
    Boolean(scanId),
  );
}

/**
 * Last selected scan, persisted across views in localStorage.
 * Lazy-init only; selection changes happen through `select` (event handler),
 * so no synchronous setState runs inside an effect.
 */
export function useStoredScan() {
  const [preferred, setPreferred] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem("ecdat:scan-id");
  });

  const select = useCallback((id: string) => {
    setPreferred(id);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("ecdat:scan-id", id);
    }
  }, []);

  return { preferred, select };
}

/**
 * Page-level scan selection: combines an explicit choice (URL or user click)
 * with the persisted preference, exposing the effective scan + a setter.
 * `selectedScan` is derived at render time (no effect needed).
 *
 * The persisted/chosen id is validated against the current `scanList`: if it no
 * longer exists (e.g. a scan was deleted via "Clear all scans" but its id is
 * still in localStorage), we fall back to the newest existing scan instead of
 * returning a stale id that would produce API 404s on every page.
 */
export function useScanSelection(
  initialId: string | null,
  scanList: Scan[] | null | undefined = null,
) {
  const { preferred, select } = useStoredScan();
  const [chosen, setChosen] = useState<string | null>(initialId);

  const resolved = chosen ?? preferred;
  const valid =
    scanList && scanList.length > 0 && scanList.some((s) => s.scan_id === resolved)
      ? resolved
      : scanList && scanList.length > 0
        ? (scanList[0]?.scan_id ?? null)
        : resolved;

  const selectedScan = valid;
  const onSelect = useCallback(
    (id: string) => {
      setChosen(id);
      select(id);
    },
    [select],
  );
  return { selectedScan, onSelect };
}
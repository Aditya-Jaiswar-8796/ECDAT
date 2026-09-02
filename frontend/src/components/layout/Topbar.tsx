/**
 * Topbar — shows the current page title context plus a live backend health
 * indicator. Health comes from GET /health (real API, polled).
 */
"use client";

import { useEffect, useState } from "react";

import { ApiError, api, API_BASE_URL } from "@/lib/api/client";

interface HealthState {
  ok: boolean;
  detail: string;
}

export function Topbar() {
  const [health, setHealth] = useState<HealthState>({ ok: false, detail: "…" });

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const h = await api.health();
        if (!cancelled) {
          setHealth({ ok: h.status === "ok", detail: `db ${h.database}` });
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setHealth({
            ok: false,
            detail: err instanceof ApiError ? err.detail : "unreachable",
          });
        }
      }
    };
    void poll();
    const id = setInterval(() => void poll(), 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <header className="flex items-center justify-between border-b border-zinc-800 bg-zinc-950/60 px-6 py-3">
      <span className="text-xs uppercase tracking-widest text-zinc-500">
        Crypto Asset Discovery &amp; Transition
      </span>
      <span
        title={`${API_BASE_URL} — ${health.detail}`}
        className="flex items-center gap-2 rounded-full border border-zinc-800 px-3 py-1 text-xs"
      >
        <span
          className={`inline-block h-2 w-2 rounded-full ${
            health.ok ? "bg-emerald-400" : "bg-red-500"
          }`}
        />
        <span className={health.ok ? "text-emerald-300" : "text-red-300"}>
          {health.ok ? "API online" : "API offline"}
        </span>
      </span>
    </header>
  );
}
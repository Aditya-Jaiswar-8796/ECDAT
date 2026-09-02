/**
 * ScanStageIndicator — horizontal stepper for the pipeline
 * Upload -> Discover -> Analyze -> Risk Assessment -> Recommendation -> Complete.
 * Stage states derive from real API data via deriveStages(); the component
 * only renders the resulting states.
 */
import type { StageState } from "@/lib/utils/stages";

interface ScanStageIndicatorProps {
  stages: StageState[];
  /** Small headline used above the stepper, e.g. current status text. */
  headline?: string;
}

/** Dot/content icon per stage state. */
function StateIcon({ state }: { state: StageState["state"] }) {
  const cls = {
    done: "bg-emerald-500 border-emerald-500 text-white",
    active:
      "border-cyan-400 text-cyan-300 animate-pulse",
    pending: "border-zinc-700 text-zinc-600",
    failed: "bg-red-500 border-red-500 text-white",
  }[state];
  return (
    <span
      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold ${cls}`}
    >
      {state === "done" ? "✓" : state === "failed" ? "✕" : ""}
    </span>
  );
}

export function ScanStageIndicator({
  stages,
  headline,
}: ScanStageIndicatorProps) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4">
      {headline && <p className="mb-3 text-sm font-semibold text-zinc-200">{headline}</p>}
      <ol className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-0">
        {stages.map((stage, index) => {
          const connectorCls =
            index === stages.length - 1
              ? "hidden"
              : "hidden sm:flex h-px flex-1 mx-2 " +
                (stage.state === "done" ? "bg-emerald-500/60" : "bg-zinc-800");
          return (
            <li key={stage.key} className="flex flex-col gap-1 sm:min-w-0 sm:flex-1" title={stage.detail}>
              <div className="flex items-center gap-2">
                <StateIcon state={stage.state} />
                <span
                  className={`text-sm font-medium ${
                    stage.state === "active"
                      ? "text-cyan-300"
                      : stage.state === "done"
                        ? "text-zinc-200"
                        : stage.state === "failed"
                          ? "text-red-400"
                          : "text-zinc-600"
                  }`}
                >
                  {stage.label}
                </span>
              </div>
              <span className={`ml-9 text-xs text-zinc-600`}>{stage.detail}</span>
              <span className={connectorCls} />
            </li>
          );
        })}
      </ol>
    </div>
  );
}
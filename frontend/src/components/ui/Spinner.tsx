/**
 * Spinner — lightweight loading indicator with optional label.
 */
export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-8 text-sm text-zinc-500">
      <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-zinc-700 border-t-cyan-400" />
      {label}
    </div>
  );
}
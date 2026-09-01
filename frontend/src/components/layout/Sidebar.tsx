/**
 * Sidebar — main navigation for the ECDAT dashboard.
 * Client-only because active-link highlighting needs the current path.
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "◨" },
  { href: "/scans", label: "Scans", icon: "↻" },
  { href: "/inventory", label: "Inventory", icon: "▦" },
  { href: "/risk", label: "Risk", icon: "▲" },
  { href: "/priority", label: "Migration Priority", icon: "▲▲" },
  { href: "/cbom", label: "CBOM", icon: "☰" },
  { href: "/reports", label: "Reports", icon: "▤" },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950/80">
      <Link href="/dashboard" className="flex items-center gap-2 border-b border-zinc-800 px-4 py-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/20 text-sm font-bold text-cyan-300 ring-1 ring-cyan-500/30">
          E
        </span>
        <span className="leading-tight">
          <span className="block text-sm font-bold text-zinc-100">ECDAT</span>
          <span className="block text-[10px] uppercase tracking-wide text-zinc-500">
            Post-Quantum Readiness
          </span>
        </span>
      </Link>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-cyan-500/10 font-medium text-cyan-300 ring-1 ring-inset ring-cyan-500/20"
                  : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
              }`}
            >
              <span className="w-5 text-center text-xs">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-zinc-800 px-4 py-3 text-[11px] leading-relaxed text-zinc-600">
        SIH 26164 · ECDAT
        <br /> Frontend · Member 6
      </div>
    </aside>
  );
}
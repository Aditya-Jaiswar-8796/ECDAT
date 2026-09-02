/**
 * Card — rounded surface container used across dashboard views.
 */
import type { HTMLAttributes, ReactNode } from "react";

interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}

export function Card({ title, subtitle, actions, children, className = "", ...rest }: CardProps) {
  return (
    <section
      {...rest}
      className={`rounded-xl border border-zinc-800 bg-zinc-900/60 shadow-sm ${className}`}
    >
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-zinc-800 px-4 py-3">
          <div className="min-w-0">
            {title && (
              <h3 className="truncate text-sm font-semibold text-zinc-100">{title}</h3>
            )}
            {subtitle && <p className="mt-0.5 text-xs text-zinc-500">{subtitle}</p>}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
import type { ReactNode } from "react";

/** One Lab section: heading, the "What this shows" line, then the content. */
export function LabFrame({ id, heading, shows, children }: { id: string; heading: string; shows: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className="mt-14 max-w-4xl">
      <h2 id={`${id}-h`} className="text-xl font-semibold">{heading}</h2>
      <p className="mt-2 max-w-2xl text-muted">{shows}</p>
      <div className="mt-6">{children}</div>
    </section>
  );
}

export function Note({ children }: { children: ReactNode }) {
  return <p className="mt-4 max-w-2xl text-sm text-muted">{children}</p>;
}

/** One big number with its label (inside a `<dl>`). */
export function Stat({ value, label, sub }: { value: string; label: string; sub?: string }) {
  return (
    <div>
      <dd className="text-4xl font-semibold tabular-nums tracking-tight">{value}</dd>
      <dt className="mt-2 text-muted">{label}</dt>
      {sub && <p className="mt-1 text-sm text-muted">{sub}</p>}
    </div>
  );
}

/** A plain bordered table with a header row; cells are passed in already formatted. */
export function LabTable({ head, rows }: { head: string[]; rows: { key: string; cells: ReactNode[] }[] }) {
  return (
    <div className="max-w-2xl overflow-x-auto rounded-[10px] border border-rule bg-surface">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-rule text-muted">
            {head.map((h) => (
              <th key={h} scope="col" className="p-3 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key} className="border-b border-rule last:border-0">
              {r.cells.map((c, i) =>
                i === 0 ? (
                  <th key={i} scope="row" className="p-3 font-medium">{c}</th>
                ) : (
                  <td key={i} className="p-3 font-mono tabular-nums">{c}</td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

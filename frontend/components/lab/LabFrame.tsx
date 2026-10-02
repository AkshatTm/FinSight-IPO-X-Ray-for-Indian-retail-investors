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

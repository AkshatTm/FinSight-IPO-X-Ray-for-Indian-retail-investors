import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ADMIN_COSTS, ADMIN_FAILED } from "@/mocks/admin";
import { CostsView } from "./AdminCosts";

describe("CostsView", () => {
  it("shows one row per day, totals, the free-grant share and the provisional note", () => {
    render(<CostsView costs={ADMIN_COSTS} failed={ADMIN_FAILED} />);
    const tables = screen.getAllByRole("table");
    const rows = within(tables[0]).getAllByRole("row");
    expect(rows).toHaveLength(4); // header, two days, totals
    expect(within(rows[1]).getByText("2026-10-02")).toBeInTheDocument();
    expect(within(rows[3]).getByText("5,700")).toBeInTheDocument();
    expect(within(rows[3]).getByText("$0.13")).toBeInTheDocument();
    expect(screen.getByText(/2\.38% of vCPU-seconds, 2\.53% of GiB-seconds/)).toBeInTheDocument();
    expect(screen.getByText(/^Provisional/)).toBeInTheDocument();
    expect(within(tables[1]).getByText("scanned")).toBeInTheDocument();
    expect(within(tables[1]).getByRole("link", { name: "doc_00000000000000aa" })).toHaveAttribute(
      "href",
      "/reports/doc_00000000000000aa",
    );
  });

  it("shows the empty states and warns when the dollar total misses GPU time", () => {
    const costs = { ...ADMIN_COSTS, days: [], usd_incomplete: true, provisional: false };
    render(<CostsView costs={costs} failed={[]} />);
    expect(screen.getByText("No jobs in this window.")).toBeInTheDocument();
    expect(screen.getByText("No failed jobs.")).toBeInTheDocument();
    expect(screen.getByText(/dollar total is too low/)).toBeInTheDocument();
    expect(screen.queryByText(/^Provisional/)).not.toBeInTheDocument();
  });
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Schemas } from "@/lib/api/client";
import { CacheBar } from "./CacheBar";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const DOC = {
  doc_id: "doc_a",
  sha256: "a".repeat(64),
  created_at: "2026-10-01T00:00:00Z",
  status: "ready",
  is_showcase: false,
  analysis_status: "complete",
  degraded_reasons: [],
  skipped_models: [],
} as unknown as Schemas["DocRecord"];

function show(doc = DOC, props: { cache?: Schemas["CacheInfo"]; reanalysing?: boolean } = {}) {
  const onRestarted = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <CacheBar doc={doc} cache={props.cache} reanalysing={props.reanalysing ?? false} onRestarted={onRestarted} />
    </QueryClientProvider>,
  );
  return onRestarted;
}

const calls: { method: string; url: string; body: unknown }[] = [];
function reply(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      calls.push({ method: init?.method ?? "GET", url, body: init?.body ? JSON.parse(String(init.body)) : undefined });
      return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
    }),
  );
}

beforeEach(() => {
  calls.length = 0;
  push.mockClear();
});
afterEach(() => vi.unstubAllGlobals());

describe("CacheBar", () => {
  it("shows no banner for a complete analysis, only the two buttons", () => {
    show();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Re-analyse" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });

  it("shows a degraded banner with the reasons in words", () => {
    show({ ...DOC, status: "partial", analysis_status: "degraded", degraded_reasons: ["skipped_model:ollama", "stage_failed:facts"] });
    const banner = screen.getByTestId("degraded-banner");
    expect(banner).toHaveTextContent("Some parts of this report are incomplete.");
    expect(banner).toHaveTextContent("analysed without the plain-English writer.");
    expect(banner).toHaveTextContent("the facts step did not finish.");
  });

  it("shows the re-analysing banner", () => {
    show({ ...DOC, status: "processing" }, { reanalysing: true });
    expect(screen.getByRole("status")).toHaveTextContent("being analysed again");
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("deletes only after the confirmation, then leaves for the upload page", async () => {
    reply(200, { deleted: "doc_a" });
    show();
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(screen.getByRole("alertdialog")).toHaveTextContent("Delete this report?");
    expect(calls).toEqual([]);
    await userEvent.click(screen.getByRole("button", { name: "Delete report" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/upload"));
    expect(calls[0]).toMatchObject({ method: "DELETE", url: "/api/docs/doc_a" });
  });

  it("cancel closes the confirmation without any request", async () => {
    reply(200, {});
    show();
    await userEvent.click(screen.getByRole("button", { name: "Re-analyse" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(calls).toEqual([]);
  });

  it("re-analyse posts, and a refusal for missing models offers to analyse without them", async () => {
    reply(503, { error: { code: "models_unavailable", message: "Can't analyse right now: Ollama is not running." } });
    const onRestarted = show();
    await userEvent.click(screen.getByRole("button", { name: "Re-analyse" }));
    await userEvent.click(screen.getByRole("button", { name: "Analyse again" }));
    const refused = await screen.findByTestId("refused");
    expect(refused).toHaveTextContent("Ollama is not running");
    expect(onRestarted).not.toHaveBeenCalled();

    reply(200, { doc_id: "doc_a", job_id: "j2", status: "queued" });
    await userEvent.click(screen.getByRole("button", { name: "Analyse without it" }));
    await waitFor(() => expect(onRestarted).toHaveBeenCalled());
    expect(calls.at(-1)?.body).toEqual({ analyse_without: ["ollama", "classifier", "embeddings", "reranker"] });
  });
});

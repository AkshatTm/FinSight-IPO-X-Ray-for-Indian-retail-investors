import { setupWorker } from "msw/browser";
import { handlers } from "./handlers";

const worker = setupWorker(...handlers);
let started: Promise<unknown> | null = null;

/** Idempotent: React StrictMode runs effects twice in dev. */
export function startMocks(): Promise<unknown> {
  started ??= worker.start({ onUnhandledFrame: "bypass", quiet: true });
  return started;
}

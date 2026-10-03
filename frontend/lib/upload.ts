import { ApiError, apiSend, type Schemas } from "@/lib/api/client";

/** Rejection reasons with their own line of copy (B05 §3); everything else uses the generic error. */
export const REJECTIONS = [
  "scanned",
  "password",
  "too_large",
  "hash_mismatch",
  "too_many_pages",
  "not_offer_document",
  "quota",
  "global_quota",
] as const;
export type Rejection = (typeof REJECTIONS)[number];

export type UploadOutcome = { kind: "exists"; docId: string } | { kind: "started"; docId: string; jobId: string };
export type UploadPhase = "hashing" | "sending" | "finishing";

export class UploadError extends Error {
  /** A B05 rejection, `uploads_disabled`, `unauthorized`, `network` or another API code. */
  code: string;
  constructor(code: string, message = code) {
    super(message);
    this.code = code;
  }
}

/** Map an API error code to the B05 rejection key (quota codes are shortened). */
export function rejectionFor(code: string): Rejection | null {
  if (code === "quota_exceeded") return "quota";
  if (code === "global_quota_exceeded") return "global_quota";
  return (REJECTIONS as readonly string[]).includes(code) ? (code as Rejection) : null;
}

/** Hex SHA-256 of a file with WebCrypto (the server recomputes it, B06 §2). */
export async function sha256Hex(file: Blob): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** init → send the bytes (POST to the API) → complete. */
export async function uploadDocument(
  file: File,
  opts: { token: string | null; maxMb: number; onPhase?: (p: UploadPhase) => void },
): Promise<UploadOutcome> {
  const { token, maxMb, onPhase } = opts;
  if (file.size > maxMb * 1024 * 1024) throw new UploadError("too_large");
  try {
    onPhase?.("hashing");
    const sha256 = await sha256Hex(file);
    const init = await apiSend<Schemas["UploadInitResponse"]>(
      "POST",
      "/api/uploads/init",
      { filename: file.name, size_bytes: file.size, sha256 },
      token,
    );
    if (init.status === "exists") return { kind: "exists", docId: init.doc_id };
    if (!init.upload_url) throw new UploadError("internal_error");
    onPhase?.("sending");
    const method = init.upload_method ?? "POST";
    const headers: Record<string, string> = { "Content-Type": "application/pdf" };
    // Only our own API gets the token; a signed storage URL carries its own signature.
    if (method === "POST" && token) headers.Authorization = `Bearer ${token}`;
    let sent: Response;
    try {
      sent = await fetch(init.upload_url, { method, headers, body: file });
    } catch {
      throw new UploadError("network");
    }
    if (!sent.ok) throw new UploadError("hash_mismatch");
    onPhase?.("finishing");
    const done = await apiSend<Schemas["UploadComplete"]>("POST", `/api/uploads/${init.doc_id}/complete`, undefined, token);
    return { kind: "started", docId: done.doc_id, jobId: done.job_id };
  } catch (e) {
    if (e instanceof UploadError) throw e;
    if (e instanceof ApiError) throw new UploadError(rejectionFor(e.code) ?? e.code, e.message);
    throw new UploadError("internal_error");
  }
}

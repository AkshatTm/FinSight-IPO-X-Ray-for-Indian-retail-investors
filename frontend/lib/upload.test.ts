import { afterEach, describe, expect, it, vi } from "vitest";
import { rejectionFor, sha256Hex, uploadDocument, UploadError } from "./upload";

const pdf = (text = "%PDF-1.7 test", name = "acme.pdf") => new File([text], name, { type: "application/pdf" });
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

afterEach(() => vi.unstubAllGlobals());

describe("upload", () => {
  it("hashes with SHA-256", async () => {
    expect(await sha256Hex(new Blob(["abc"]))).toBe("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  });

  it("maps quota codes to the B05 rejection keys", () => {
    expect(rejectionFor("quota_exceeded")).toBe("quota");
    expect(rejectionFor("global_quota_exceeded")).toBe("global_quota");
    expect(rejectionFor("scanned")).toBe("scanned");
    expect(rejectionFor("unauthorized")).toBeNull();
  });

  it("returns exists for a file analysed before, without sending it", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({ status: "exists", doc_id: "doc_x" }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(uploadDocument(pdf(), { token: "t", maxMb: 50 })).resolves.toEqual({ kind: "exists", docId: "doc_x" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect((fetchMock.mock.calls[0][1] as RequestInit).headers).toMatchObject({ Authorization: "Bearer t" });
  });

  it("runs init, PUT to a signed URL without the token, then complete", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json({ status: "upload", doc_id: "doc_y", upload_url: "https://storage.googleapis.com/b/x?sig", upload_method: "PUT" }))
      .mockResolvedValueOnce(new Response(null, { status: 200 }))
      .mockResolvedValueOnce(json({ doc_id: "doc_y", job_id: "j1", status: "queued" }));
    vi.stubGlobal("fetch", fetchMock);
    const phases: string[] = [];
    const out = await uploadDocument(pdf(), { token: "t", maxMb: 50, onPhase: (p) => phases.push(p) });
    expect(out).toEqual({ kind: "started", docId: "doc_y", jobId: "j1" });
    expect(phases).toEqual(["hashing", "sending", "finishing"]);
    const put = fetchMock.mock.calls[1][1] as RequestInit;
    expect(put.method).toBe("PUT");
    expect(put.headers).not.toHaveProperty("Authorization");
  });

  it("rejects too-large files before hashing and turns API codes into rejections", async () => {
    await expect(uploadDocument(pdf("x".repeat(2 * 1024 * 1024)), { token: "t", maxMb: 1 })).rejects.toMatchObject({ code: "too_large" });
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => json({ error: { code: "quota_exceeded", message: "m", limit: 3 } }, 429)));
    await expect(uploadDocument(pdf(), { token: "t", maxMb: 50 })).rejects.toBeInstanceOf(UploadError);
    await expect(uploadDocument(pdf(), { token: "t", maxMb: 50 })).rejects.toMatchObject({ code: "quota" });
  });
});

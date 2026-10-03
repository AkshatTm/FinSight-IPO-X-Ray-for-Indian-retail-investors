import type { components } from "./types";

export type Schemas = components["schemas"];

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

/** Same-origin /api/*: Next rewrites it to FastAPI, or MSW answers it in mock mode. */
export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { ...init, headers: { Accept: "application/json", ...init?.headers } });
  } catch {
    throw new ApiError("network", "network", 0);
  }
  return readJson<T>(res);
}

/** JSON request with an optional bearer token (the Supabase access token for upload routes). */
export async function apiSend<T>(method: "POST" | "PUT", path: string, body?: unknown, token?: string | null): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  let res: Response;
  try {
    res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new ApiError("network", "network", 0);
  }
  return readJson<T>(res);
}

export async function readJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let code = "internal_error";
    let message = res.statusText;
    try {
      const body = (await res.json()) as Partial<Schemas["ErrorResponse"]>;
      if (body.error?.code) code = body.error.code;
      if (body.error?.message) message = body.error.message;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(code, message, res.status);
  }
  return (await res.json()) as T;
}

export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "1";

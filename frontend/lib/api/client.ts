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

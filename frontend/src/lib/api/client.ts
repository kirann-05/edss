// Thin fetch wrapper for the EDSS API. Every request is same-origin (/api/* is proxied
// to FastAPI by next.config.ts), so the httpOnly session cookie travels automatically.

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

function messageFrom(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    // FastAPI's own validation answers with a list of {loc, msg}: say the first one
    if (Array.isArray(detail) && detail[0] && typeof detail[0].msg === "string") {
      const field = Array.isArray(detail[0].loc) ? detail[0].loc.at(-1) : undefined;
      return typeof field === "string" ? `${field.replaceAll("_", " ")}: ${detail[0].msg}` : detail[0].msg;
    }
    if (detail && typeof detail === "object" && "message" in detail) {
      const message = (detail as { message: unknown }).message;
      if (typeof message === "string") return message;
    }
  }
  return `Request failed with status ${status}`;
}

async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const parsed: unknown = text ? safeJson(text) : undefined;

  if (!response.ok) {
    // A 401 is handled once, globally, by the query caches in components/providers.tsx
    throw new ApiError(response.status, messageFrom(response.status, parsed), parsed);
  }
  return parsed as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body ?? {}),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body ?? {}),
  delete: <T>(path: string) => request<T>("DELETE", path),
};

import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "./client";

function answer(status: number, body?: unknown) {
  const text = body === undefined ? "" : typeof body === "string" ? body : JSON.stringify(body);
  return vi.fn().mockResolvedValue(new Response(status === 204 ? null : text, { status }));
}

async function failure(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    return error as ApiError;
  }
  throw new Error("expected the request to fail");
}

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("sends JSON to the same-origin /api path and returns the parsed answer", async () => {
    const fetch = answer(200, { ok: true });
    vi.stubGlobal("fetch", fetch);
    expect(await api.post("/runs", { request: "x" })).toEqual({ ok: true });
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe("/api/runs");
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(init.body).toBe('{"request":"x"}');
  });

  it("sends no body on a GET and takes 204 as nothing", async () => {
    const fetch = answer(204);
    vi.stubGlobal("fetch", fetch);
    expect(await api.get("/x")).toBeUndefined();
    expect(fetch.mock.calls[0][1].body).toBeUndefined();
  });

  it("gives the server's reason when it says one", async () => {
    vi.stubGlobal("fetch", answer(409, { detail: "the brief was already decided" }));
    const error = await failure(api.post("/briefs/1/decision"));
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(409);
    expect(error.message).toBe("the brief was already decided");
  });

  it("reads a reason nested as detail.message", async () => {
    vi.stubGlobal("fetch", answer(422, { detail: { message: "V1 still fails", checks: ["V1"] } }));
    expect((await failure(api.post("/x"))).message).toBe("V1 still fails");
  });

  it("turns FastAPI's validation list into the field and its reason", async () => {
    vi.stubGlobal(
      "fetch",
      answer(422, { detail: [{ loc: ["body", "expires_on"], msg: "Input should be a valid date" }] }),
    );
    expect((await failure(api.post("/admin/grants"))).message).toBe("expires on: Input should be a valid date");
  });

  it("falls back to the status when there is no reason, and keeps a non-JSON body", async () => {
    vi.stubGlobal("fetch", answer(502, "Bad Gateway"));
    const error = await failure(api.get("/x"));
    expect(error.message).toBe("Request failed with status 502");
    expect(error.detail).toBe("Bad Gateway");
  });
});

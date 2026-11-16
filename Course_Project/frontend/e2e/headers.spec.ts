import { expect, test } from "@playwright/test";

// What every answer from the web server says about itself, pages and the proxied API alike.
for (const path of ["/login", "/api/health"]) {
  test(`${path} cannot be framed by another site and does not name the server`, async ({ request }) => {
    const response = await request.get(path);
    const headers = response.headers();
    expect(headers["x-frame-options"]).toBe("DENY");
    expect(headers["content-security-policy"]).toContain("frame-ancestors 'none'");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["referrer-policy"]).toBe("same-origin");
    expect(headers["x-powered-by"]).toBeUndefined();
  });
}

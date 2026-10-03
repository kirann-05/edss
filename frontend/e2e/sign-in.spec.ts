import { expect, test } from "@playwright/test";

import { E2E_PASSWORD } from "../playwright.config";

// Only this test uses the password form with a real account, so its lockout cannot affect another.
test("wrong passwords are refused, and five of them lock that email for a while", async ({ page }) => {
  await page.goto("/login");
  const email = page.getByLabel("Email");
  const password = page.getByLabel("Password");
  const submit = page.getByRole("button", { name: "Sign in", exact: true });
  const message = page.locator("form").getByRole("alert"); // the page also has a route announcer

  await email.fill("admin@edss.test");
  for (let attempt = 1; attempt <= 5; attempt++) {
    await password.fill("not-the-password");
    await submit.click();
    await expect(message).toContainText("do not match an account");
  }

  // the right password is now refused too, with the server's own words about waiting
  await password.fill(E2E_PASSWORD);
  await submit.click();
  await expect(message).toContainText("Too many failed attempts");
  await expect(page).toHaveURL(/\/login/);

  // someone else is not affected
  await email.fill("registrar@edss.test");
  await password.fill(E2E_PASSWORD);
  await submit.click();
  await expect(page).not.toHaveURL(/\/login/);
});

test("signing out ends the session", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("registrar@edss.test");
  await page.getByLabel("Password").fill(E2E_PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).not.toHaveURL(/\/login/);

  await page.getByRole("button", { name: /Registrar/ }).click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);
  expect((await page.request.get("/api/auth/me")).status()).toBe(401);
});

// docs/diagrams/*.svg to PNG beside each, for slide tools that do not take SVG.
// Uses the Chrome that the browser tests already use, so nothing new is installed.
import { readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { chromium } from "@playwright/test";

const folder = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "docs", "diagrams");
const only = process.argv.slice(2);
const browser = await chromium.launch({ channel: process.env.CI ? undefined : "chrome" });
const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 2 });
for (const name of readdirSync(folder).filter((f) => f.endsWith(".svg")).sort()) {
  if (only.length && !only.some((o) => name.startsWith(o))) continue;
  await page.goto(pathToFileURL(join(folder, name)).href);
  await page.screenshot({ path: join(folder, name.replace(/\.svg$/, ".png")) });
  console.log(`docs/diagrams/${name.replace(/\.svg$/, ".png")}`);
}
await browser.close();

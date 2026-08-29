import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { mkdtemp, copyFile, readFile, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");
let runtime;
let server;
let baseURL;
let pairedURL;

async function waitForURL(child) {
  return new Promise((resolve, reject) => {
    let output = "";
    const timer = setTimeout(() => reject(new Error(`Guide server did not start: ${output}`)), 10_000);
    child.stdout.on("data", chunk => {
      output += chunk.toString();
      const match = output.match(/DQ7 guide \(this device\): (http:\/\/127\.0\.0\.1:\d+)/);
      if (match) {
        clearTimeout(timer);
        resolve(match[1]);
      }
    });
    child.stderr.on("data", chunk => { output += chunk.toString(); });
    child.once("exit", code => {
      clearTimeout(timer);
      reject(new Error(`Guide server exited ${code}: ${output}`));
    });
  });
}

test("phone restore and reconnect flow stays explicit and recoverable", async ({ page, context }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto(pairedURL);
  await expect(page.locator("#status")).toHaveText("", { timeout: 10_000 });
  await page.evaluate(() => { location.hash = "progress"; });
  await expect(page.locator("#progress")).toBeVisible();

  const backup = await readFile(path.join(ROOT, "player", "ryan-save-state.json"));
  await page.locator("#restoreFile").setInputFiles({
    name: "phone-smoke-backup.json",
    mimeType: "application/json",
    buffer: backup,
  });
  await expect(page.locator("#restoreConfirm")).toBeVisible();
  await expect(page.locator("#confirmRestoreButton")).toBeFocused();
  await page.locator("#confirmRestoreButton").click();
  await expect(page.locator("#status")).toContainText("Previous state saved as");
  const recoveryFiles = (await readdir(runtime)).filter(name => name.includes("before-restore"));
  expect(recoveryFiles).toHaveLength(1);

  await context.setOffline(true);
  await expect(page.locator("#connectionBanner")).toContainText(
    "changes are disabled and never queued",
  );
  await context.setOffline(false);
  await expect.poll(() => page.evaluate(() => navigator.onLine)).toBe(true);
  await expect.poll(() => page.evaluate(async () => (await fetch("/api/health")).status)).toBe(200);
  await expect(page.locator("#connectionBanner")).toBeHidden();
});

test.beforeAll(async () => {
  runtime = await mkdtemp(path.join(tmpdir(), "dq7-phone-render-"));
  const state = path.join(runtime, "state.json");
  const pairing = path.join(runtime, "pairing-token");
  await copyFile(path.join(ROOT, "player", "ryan-save-state.json"), state);
  server = spawn("python", ["-u", "scripts/guide_server.py", "--port", "0", "--lan",
    "--require-pairing-everywhere", "--state", state, "--pairing-file", pairing], {
    cwd: ROOT,
    stdio: ["ignore", "pipe", "pipe"],
  });
  baseURL = await waitForURL(server);
  const token = (await readFile(pairing, "ascii")).trim();
  pairedURL = `${baseURL}/?pair=${encodeURIComponent(token)}#walkthrough`;
});

test.afterAll(async () => {
  if (server && server.exitCode === null) {
    server.kill("SIGTERM");
    await new Promise(resolve => server.once("exit", resolve));
  }
  if (runtime) await rm(runtime, { recursive: true, force: true });
});

for (const viewport of [
  { name: "portrait", width: 360, height: 800 },
  { name: "landscape", width: 844, height: 390 },
]) {
  test(`${viewport.name} phone workflow renders without obstruction`, async ({ page, request }) => {
    await page.setViewportSize(viewport);
    const denied = await request.get(`${baseURL}/api/health`);
    expect(denied.status()).toBe(401);

    await page.goto(pairedURL);
    await expect(page.locator("#status")).toHaveText("", { timeout: 10_000 });
    await expect(page.locator("#walkthrough")).toBeVisible();
    await expect(page.locator("#nextPowerHeading")).toHaveText("Next power move");
    await expect(page.locator("#playBar")).toBeVisible();

    const health = await page.evaluate(async () => {
      const response = await fetch("/api/health");
      return { status: response.status, body: await response.json() };
    });
    expect(health.status).toBe(200);

    const metrics = await page.evaluate(() => {
      const playBar = document.querySelector("#playBar");
      const nextPower = document.querySelector("#nextPowerHeading");
      const stop = document.querySelector("#checkpointStop:not([hidden])");
      const barRect = playBar.getBoundingClientRect();
      return {
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        barBottomGap: Math.abs(innerHeight - barRect.bottom),
        barWithinViewport: barRect.top >= 0 && barRect.bottom <= innerHeight + 1,
        uniqueControlCount: new Set([...playBar.querySelectorAll("button")].map(node => node.id)).size,
        controlCount: playBar.querySelectorAll("button").length,
        controlSizes: [...playBar.querySelectorAll("button")].map(node => {
          const rect = node.getBoundingClientRect();
          return [rect.width, rect.height];
        }),
        stopBeforePower: !stop || stop.compareDocumentPosition(nextPower) & Node.DOCUMENT_POSITION_FOLLOWING,
      };
    });
    expect(metrics.overflow).toBeLessThanOrEqual(1);
    expect(metrics.barBottomGap).toBeLessThanOrEqual(1);
    expect(metrics.barWithinViewport).toBe(true);
    expect(metrics.uniqueControlCount).toBe(metrics.controlCount);
    expect(metrics.stopBeforePower).toBeTruthy();
    for (const [width, height] of metrics.controlSizes) {
      expect(width).toBeGreaterThanOrEqual(44);
      expect(height).toBeGreaterThanOrEqual(44);
    }

    await page.evaluate(() => { location.hash = "sources"; });
    await expect(page.locator("#sources")).toBeVisible();
    const gapCards = page.locator(".evidence-gap-card");
    await expect(gapCards).toHaveCount(6);
    await expect(page.locator(".evidence-gap-card[open]")).toHaveCount(0);
    await expect(page.locator("#evidenceGaps")).toContainText("5 corroborated but unresolved");
    await expect(page.locator("#evidenceGaps")).toContainText("Separate conflict ledger: 1 unresolved");
    await expect(page.locator("#evidenceGaps")).toContainText("Comparable benchmark still missing");
    await expect(page.locator("#evidenceGaps")).toContainText("1 single-source");
    await expect(page.locator("#evidenceGaps")).toContainText("0 unsupported");
    await expect(page.locator("#evidenceGaps")).not.toContainText("Ruby of Protection individual Faraday drawer");
    await expect(page.locator("#evidenceGaps")).toContainText("Lucky Panel probability algorithm");
    const firstGap = gapCards.first();
    await firstGap.locator("summary").click();
    await expect(firstGap).toHaveAttribute("open", "");
    await expect(firstGap).toContainText("Needed:");
    const sourceMetrics = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      stopVisible: Boolean(document.querySelector("#sourcesStop:not([hidden])")),
      linkSizes: [...document.querySelectorAll(".evidence-gap-card[open] .evidence-claim a")]
        .map(node => { const rect = node.getBoundingClientRect(); return [rect.width, rect.height]; }),
    }));
    expect(sourceMetrics.overflow).toBeLessThanOrEqual(1);
    expect(sourceMetrics.stopVisible).toBe(true);
    expect(sourceMetrics.linkSizes.length).toBeGreaterThan(0);
    for (const [width, height] of sourceMetrics.linkSizes) {
      expect(width).toBeGreaterThanOrEqual(44);
      expect(height).toBeGreaterThanOrEqual(44);
    }

    if (viewport.name === "portrait") {
      const cacheState = await page.evaluate(async () => {
        await navigator.serviceWorker.ready;
        const keys = await caches.keys();
        const requests = (await Promise.all(keys.map(async key => {
          const cache = await caches.open(key);
          return cache.keys();
        }))).flat().map(request => new URL(request.url).pathname);
        return { keys, apiRequests: requests.filter(pathname => pathname.startsWith("/api/")) };
      });
      expect(cacheState.keys).toContain("dq7-guide-shell-v20");
      expect(cacheState.apiRequests).toEqual([]);
    }
  });
}

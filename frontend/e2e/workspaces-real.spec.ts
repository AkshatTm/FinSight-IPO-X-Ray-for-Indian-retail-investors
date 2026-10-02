import { expect, test } from "@playwright/test";

// Real-API regression (2 Oct): clicking an IPO in the Library showed an error and no details,
// because the X-Ray route stalled the whole API for several seconds and the dev proxy reset the
// connections (socket hang up, 500). Opens every IPO workspace from the Library, as a user does,
// and fails on any failed /api request, any error block, or a slow X-Ray.
// Needs a running `pnpm dev` (:3000) and API (:8000): E2E_REAL=1 pnpm test:e2e workspaces-real
test.skip(process.env.E2E_REAL !== "1", "needs the real API: set E2E_REAL=1");

const SLOW_XRAY_MS = 3_000; // it was 5 to 9 s while it opened the parsed documents; now about 20 ms

test("every IPO opens from the Library with facts, no failed request and no error block", async ({ page }) => {
  await page.goto("/ipos");
  await page.locator('a[href^="/ipos/"]').first().waitFor();
  const hrefs = await page.locator('a[href^="/ipos/"]').evaluateAll((a) =>
    [...new Set(a.map((x) => x.getAttribute("href") ?? ""))].filter((h) => /^\/ipos\/[^/]+$/.test(h)),
  );
  expect(hrefs.length).toBeGreaterThanOrEqual(10);

  for (const href of hrefs) {
    const failed: string[] = [];
    const errors: string[] = [];
    let xrayMs = 0;
    const started = new Map<string, number>();
    const onRequest = (r: import("@playwright/test").Request) => started.set(r.url(), Date.now());
    const onResponse = (r: import("@playwright/test").Response) => {
      if (!r.url().includes("/api/")) return;
      if (r.status() >= 400 && !r.url().endsWith("/api/lab/frontier")) failed.push(`${r.status()} ${r.url()}`);
      if (r.url().endsWith("/xray")) xrayMs = Date.now() - (started.get(r.url()) ?? Date.now());
    };
    const onPageError = (e: Error) => errors.push(e.message);
    page.on("request", onRequest);
    page.on("response", onResponse);
    page.on("pageerror", onPageError);

    await page.goto("/ipos");
    await page.locator(`a[href="${href}"]`).first().waitFor();
    await page.locator(`a[href="${href}"]`).first().click();
    await expect(page).toHaveURL(new RegExp(`${href}$`));
    await expect(page.getByRole("heading", { level: 1 })).not.toHaveText("");
    // Facts are listed (the X-Ray arrived): at least five fact rows with a source chip.
    await expect(page.locator('[data-pane="facts"] button').nth(4)).toBeVisible({ timeout: 15_000 });
    // No ErrorBlock anywhere on the page.
    await expect(page.locator('#main [role="alert"]')).toHaveCount(0); // not Next's route announcer

    page.off("request", onRequest);
    page.off("response", onResponse);
    page.off("pageerror", onPageError);
    expect(failed, `${href}: failed API requests`).toEqual([]);
    expect(errors, `${href}: page errors`).toEqual([]);
    expect(xrayMs, `${href}: X-Ray took ${xrayMs} ms`).toBeLessThan(SLOW_XRAY_MS);
  }
});

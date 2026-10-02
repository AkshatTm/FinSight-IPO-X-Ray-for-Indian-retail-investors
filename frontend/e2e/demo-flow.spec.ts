import { expect, test, type Page } from "@playwright/test";

// Spec 16: hotkeys 1 to 7 walk the scripted tour. Runs on the mocks by default and on the real API
// with E2E_REAL=1 (the answers then replay from the recorded demo cache).
const press = async (page: Page, key: string) => {
  await page.locator("body").click({ position: { x: 2, y: 2 } }).catch(() => {});
  await page.keyboard.press(key);
};

test("demo mode: hotkeys 1 to 7", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));

  await page.goto("/ipos?demo=1");
  const step = page.getByRole("status").filter({ hasText: "Demo step" });
  await expect(step).toHaveText("Demo step 0 of 7 · press the next number");
  // No first-visit hint or tour in demo mode.
  await expect(page.getByRole("dialog")).toHaveCount(0);

  await press(page, "1");
  await expect(page).toHaveURL(/\/ipos\/ather-energy-2025/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Ather");
  await expect(step).toContainText("step 1 of 7");
  await expect(page.getByRole("dialog")).toHaveCount(0);

  await press(page, "2");
  await expect(page.getByTestId("highlight")).toBeVisible({ timeout: 20_000 });

  await press(page, "3");
  const ask = page.locator('[data-pane="ask"]');
  await expect(ask.getByText("What will the money be used for?")).toBeVisible();
  // The header's Inspect button unlocks once an answer has finished.
  await expect(page.getByRole("button", { name: /^Inspect/ })).toBeEnabled({ timeout: 90_000 });

  await press(page, "4");
  const drawer = page.getByRole("dialog", { name: "This number doesn't match" });
  await expect(drawer).toBeVisible({ timeout: 60_000 });
  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);

  await press(page, "5");
  await expect(page.locator("textarea")).not.toHaveValue("", { timeout: 60_000 });

  await press(page, "6");
  await expect(ask.getByText("I can't tell you whether to invest.")).toBeVisible({ timeout: 60_000 });

  await press(page, "7");
  await expect(page).toHaveURL(/\/lab/);
  await expect(page.getByRole("heading", { level: 1, name: "Model Lab" })).toBeVisible();

  await press(page, "0");
  await expect(page).toHaveURL(/\/ipos\?demo=1/);
  expect(errors).toEqual([]);
});

test("hotkeys do nothing outside demo mode", async ({ page }) => {
  await page.goto("/ipos");
  await page.keyboard.press("1");
  await expect(page).toHaveURL(/\/ipos$/);
  await expect(page.getByText("Demo step")).toHaveCount(0);
});

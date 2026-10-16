import { expect, test } from "@playwright/test";

// C3.8: the whole product on the real local app, as a reader uses it: upload a PDF in the browser,
// watch the stages, open every tab of the report, then the workspace and the chat.
// Needs the app running (`uv run poe app`) and a text PDF:
//   E2E_REAL=1 E2E_PDF=C:/path/to/rhp.pdf pnpm test:e2e local-app-real
test.skip(process.env.E2E_REAL !== "1" || !process.env.E2E_PDF, "needs the real app and E2E_PDF");
test.setTimeout(1_200_000);

test("upload → stages → report tabs → workspace → chat, with no failed request", async ({ page }) => {
  const failed: string[] = [];
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("response", (r) => {
    if (r.url().includes("/api/") && r.status() >= 500) failed.push(`${r.status()} ${r.url()}`);
  });

  await page.goto("/upload");
  await page.getByTestId("upload-input").setInputFiles(process.env.E2E_PDF as string);
  await expect(page).toHaveURL(/\/reports\/doc_[0-9a-f]{16}$/, { timeout: 60_000 });
  const docId = page.url().split("/").pop() as string;
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Analysing");

  // The stage list fills in while the job runs; the report opens once the facts are ready.
  const seeReady = page.getByRole("button", { name: "See what's ready" });
  await seeReady.waitFor({ timeout: 300_000 });
  await seeReady.click();
  await expect(page.getByRole("tab", { name: "Overview" })).toBeVisible();

  await expect(page.getByTestId("risk-disclaimer")).toBeVisible({ timeout: 900_000 });
  await expect(page.getByRole("heading", { name: /^Risk level:/ })).toBeVisible({ timeout: 900_000 });

  await page.getByRole("tab", { name: "Red flags" }).click();
  await expect(page.locator("li[data-status]")).toHaveCount(13);

  await page.getByRole("tab", { name: "Risks" }).click();
  await expect(page.getByText(/The company lists \d+ risks/)).toBeVisible();

  await page.getByRole("tab", { name: "Compare" }).click();
  await expect(page.getByRole("heading", { name: "How it compares" })).toBeVisible();

  await page.getByRole("link", { name: "Facts, pages and Ask" }).click();
  await expect(page).toHaveURL(new RegExp(`/ipos/${docId}$`));
  await expect(page.getByText("Key facts")).toBeVisible({ timeout: 120_000 });
  const skip = page.getByRole("button", { name: "Skip tour" });
  if (await skip.isVisible()) await skip.click();

  const box = page.getByRole("textbox", { name: "Ask a question" });
  await box.fill("Should I apply for this IPO?");
  await box.press("Enter");
  await expect(page.getByText(/can't tell you whether to apply|not a SEBI-registered/i).first()).toBeVisible({
    timeout: 60_000,
  });

  await box.fill("What is the face value of each share?");
  await box.press("Enter");
  await expect(page.getByText(/Copy/).first()).toBeVisible({ timeout: 240_000 });

  expect(failed).toEqual([]);
  expect(errors).toEqual([]);
});

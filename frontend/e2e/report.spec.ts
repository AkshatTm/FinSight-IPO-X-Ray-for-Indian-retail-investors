import { expect, test } from "@playwright/test";

// B3.1 report page on the MSW mocks (mocks/report.ts, synthetic data).
const SAMPLE = "/reports/doc_5a3f1e2b9c7d4a60";

test("overview → reason opens the red flag → risks: filter, explain, search", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(SAMPLE);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Acme Speciality Chemicals Limited");
  await expect(page.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("heading", { name: "Risk level: Medium" })).toBeVisible();
  await expect(page.getByTestId("risk-disclaimer")).toContainText("It is not a recommendation to apply, buy or avoid");
  await expect(page.getByText("Acme Speciality Chemicals Limited is raising ₹150 crore for itself")).toBeVisible();

  await page.getByText("Who gets the IPO money · +2").click();
  await expect(page.getByRole("tab", { name: "Red flags" })).toHaveAttribute("aria-selected", "true");
  await expect(page.locator("#redflag-RF04")).toContainText("85.0% of the money goes to existing shareholders");
  await expect(page).toHaveURL(/#redflag-RF04$/);
  await page.getByRole("button", { name: /^Concern/ }).click();
  await expect(page.locator("li[data-status]")).toHaveCount(1);

  await page.getByRole("tab", { name: "Risks" }).click();
  await expect(page.getByText("The company lists 18 risks.", { exact: false })).toBeVisible();
  const card = page.locator("#risk-r17");
  await card.getByRole("button", { name: "Explain in plain English" }).click();
  await expect(card).toContainText("Explaining…");
  await expect(card).toContainText("Plain English (synthetic)", { timeout: 15_000 });
  await page.getByLabel("Show only unusual risks").check();
  await expect(page.locator("li[id^=risk-]")).toHaveCount(4);
  await page.getByLabel("Show only unusual risks").uncheck();
  await page.getByRole("searchbox", { name: "Search risks" }).fill("Synthetic risk 12:");
  await expect(page.locator("li[id^=risk-]")).toHaveCount(1);

  await page.getByRole("tab", { name: "Compare" }).click();
  await expect(page.getByRole("heading", { name: "How it compares" })).toBeVisible();
  expect(errors).toEqual([]);
});

test("a risk anchor in the link opens the Risks tab", async ({ page }) => {
  await page.goto(`${SAMPLE}#risk-r4`);
  await expect(page.getByRole("tab", { name: "Risks" })).toHaveAttribute("aria-selected", "true");
  await expect(page.locator("#risk-r4")).toBeInViewport();
});

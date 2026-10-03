import { expect, test, type Page } from "@playwright/test";

// B1.5 upload flow on the MSW mocks (mocks/uploads.ts picks the scenario from the file name).
const pdf = (name: string, body = `%PDF-1.7 ${name} ${Math.random()}`) => ({
  name,
  mimeType: "application/pdf",
  buffer: Buffer.from(body),
});

async function signIn(page: Page) {
  await page.goto("/upload");
  await page.getByRole("button", { name: "Sign in with Google to upload" }).click();
  await expect(page.getByText("You can analyse 3 documents a day.")).toBeVisible();
}

test("signed out → sign in → upload → processing → see what's ready", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/upload");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Analyse an IPO document");
  await expect(page.getByText("Up to 50 MB. Text PDFs only (not scans).")).toBeVisible();
  await expect(page.getByRole("button", { name: "choose a file" })).toBeDisabled();
  await signIn(page);

  await page.getByTestId("upload-input").setInputFiles(pdf("acme-drhp.pdf"));
  await expect(page).toHaveURL(/\/reports\/doc_[0-9a-f]{16}$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Analysing");
  await expect(page.getByText("This is a draft (DRHP).")).toBeVisible({ timeout: 20_000 });
  await expect(page.locator("li", { hasText: "Checking the document" })).toContainText("DRHP412 pages");
  await page.getByRole("button", { name: "See what's ready" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Acme Speciality Chemicals Limited");
  expect(errors).toEqual([]);
});

test("a failing stage shows its row as not finished, the rest continues", async ({ page }) => {
  await signIn(page);
  await page.getByTestId("upload-input").setInputFiles(pdf("acme-partial.pdf"));
  const row = page.locator("li[data-state=failed]").first();
  await expect(row).toContainText("Couldn't finish this step", { timeout: 30_000 });
  await row.getByRole("button", { name: "Details" }).click();
  await expect(row).toContainText("Something went wrong in this step.");
  await expect(page.locator("li[data-state=done]").last()).toContainText("Ready for questions", { timeout: 30_000 });
});

for (const [file, copy] of [
  ["scan-copy.pdf", "This PDF looks like a scan, so there's no text to read."],
  ["locked.pdf", "This PDF is password-protected. Please upload an unlocked copy."],
  ["notipo-annual-report.pdf", "This doesn't look like an IPO offer document."],
  ["huge.pdf", "This document has more than 1,500 pages"],
] as const) {
  test(`rejection copy: ${file}`, async ({ page }) => {
    await signIn(page);
    await page.getByTestId("upload-input").setInputFiles(pdf(file));
    await expect(page.getByTestId("rejection")).toContainText(copy, { timeout: 20_000 });
    await expect(page.getByRole("link", { name: "Analyse a document" }).last()).toBeVisible();
  });
}

test("same file twice opens the existing report with a toast; the fourth upload hits the quota", async ({ page }) => {
  await signIn(page);
  const same = pdf("acme.pdf", "%PDF-1.7 the same bytes");
  await page.getByTestId("upload-input").setInputFiles(same);
  await expect(page).toHaveURL(/\/reports\//);
  await expect(page.getByText("Ready for questions")).toBeVisible({ timeout: 30_000 });
  const back = async () => {
    await page.getByRole("link", { name: "Analyse a document" }).first().click();
    await expect(page).toHaveURL(/\/upload$/);
  };
  await back();
  await page.getByTestId("upload-input").setInputFiles(same);
  await expect(page.getByText("This document was already analysed. Here's its report.")).toBeVisible();
  for (let i = 0; i < 2; i++) {
    await back();
    await page.getByTestId("upload-input").setInputFiles(pdf(`other-${i}.pdf`));
    await expect(page).toHaveURL(/\/reports\//);
  }
  await back();
  await page.getByTestId("upload-input").setInputFiles(pdf("one-more.pdf"));
  await expect(page.getByTestId("rejection")).toHaveText("You've reached today's limit of 3 documents. Try again tomorrow.");
});

test("my uploads lists finished documents", async ({ page }) => {
  await signIn(page);
  await page.getByTestId("upload-input").setInputFiles(pdf("acme.pdf"));
  await expect(page.getByText("Ready for questions")).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Account" }).click();
  await page.getByRole("menuitem", { name: "My uploads" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("My uploads");
  await expect(page.getByRole("cell", { name: "Acme Speciality Chemicals Limited" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Ready" })).toBeVisible();
});

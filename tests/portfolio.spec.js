const { test, expect } = require("@playwright/test");

async function addHolding(page, { ticker, shares, avgPrice }) {
  await page.getByLabel("Ticker").fill(ticker);
  await page.getByLabel("Shares").fill(String(shares));
  await page.getByLabel("Avg buy price").fill(String(avgPrice));
  await page.getByRole("button", { name: "Save holding" }).click();
}

test.describe("Personal Stock Portfolio Tracker", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test("adds holdings, refreshes prices, and computes the total value", async ({ page }) => {
    await addHolding(page, { ticker: "AAPL", shares: 10, avgPrice: 180 });
    await addHolding(page, { ticker: "MSFT", shares: 5, avgPrice: 300 });

    await page.getByRole("button", { name: "Refresh prices" }).click();

    await expect(page.locator("#dataMode")).toContainText("mock");
    await expect(page.locator("#totalValue")).toHaveText("$4,190.50");
    await expect(page.locator("#totalCost")).toHaveText("$3,300.00");
    await expect(page.locator("#totalProfitLoss")).toHaveText("$890.50");

    await expect(page.locator("tbody")).toContainText("AAPL");
    await expect(page.locator("tbody")).toContainText("MSFT");
  });

  test("edits and deletes holdings while recalculating totals", async ({ page }) => {
    await addHolding(page, { ticker: "AAPL", shares: 10, avgPrice: 180 });
    await addHolding(page, { ticker: "MSFT", shares: 5, avgPrice: 300 });

    await page.getByRole("button", { name: "Refresh prices" }).click();
    await page.locator('button[data-action="edit"]').first().click();
    await page.getByLabel("Shares").fill("12");
    await page.getByRole("button", { name: "Update holding" }).click();

    await expect(page.locator("#totalValue")).toHaveText("$4,610.50");
    await expect(page.locator("#totalProfitLoss")).toHaveText("$950.50");

    await page.locator('button[data-action="delete"]').nth(1).click();

    await expect(page.locator("#totalValue")).toHaveText("$2,520.00");
    await expect(page.locator("#totalCost")).toHaveText("$2,160.00");
    await expect(page.locator("#totalProfitLoss")).toHaveText("$360.00");
    await expect(page.locator("tbody")).not.toContainText("MSFT");
  });

  test("persists holdings and theme across reloads", async ({ page }) => {
    await addHolding(page, { ticker: "AAPL", shares: 10, avgPrice: 180 });
    await page.getByRole("button", { name: "Refresh prices" }).click();
    await page.getByRole("button", { name: "Toggle theme" }).click();

    await page.reload();

    await expect(page.locator("body")).toHaveAttribute("data-theme", "dark");
    await expect(page.locator("tbody")).toContainText("AAPL");
    await expect(page.locator("#dataMode")).toContainText("mock");
    await expect(page.locator("#totalValue")).toHaveText("$2,100.00");
  });

  test("supports the main workflow on a mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    await addHolding(page, { ticker: "NVDA", shares: 2, avgPrice: 800 });
    await page.getByRole("button", { name: "Refresh prices" }).click();

    await expect(page.locator("tbody")).toContainText("NVDA");
    await expect(page.locator("#totalValue")).toHaveText("$1,824.80");
    await expect(page.getByRole("button", { name: "Refresh prices" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Toggle theme" })).toBeVisible();
  });
});

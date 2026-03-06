const { test, expect } = require("@playwright/test");

test.describe("Personal Stock Portfolio Tracker", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test("adds holdings, refreshes prices, and computes the total value", async ({ page }) => {
    await page.getByLabel("Ticker").fill("AAPL");
    await page.getByLabel("Shares").fill("10");
    await page.getByLabel("Avg buy price").fill("180");
    await page.getByRole("button", { name: "Save holding" }).click();

    await page.getByLabel("Ticker").fill("MSFT");
    await page.getByLabel("Shares").fill("5");
    await page.getByLabel("Avg buy price").fill("300");
    await page.getByRole("button", { name: "Save holding" }).click();

    await page.getByRole("button", { name: "Refresh prices" }).click();

    await expect(page.locator("#dataMode")).toContainText("mock");
    await expect(page.locator("#totalValue")).toHaveText("$4,190.50");
    await expect(page.locator("#totalCost")).toHaveText("$3,300.00");
    await expect(page.locator("#totalProfitLoss")).toHaveText("$890.50");

    await expect(page.locator("tbody")).toContainText("AAPL");
    await expect(page.locator("tbody")).toContainText("MSFT");
  });
});

const { test, expect } = require("@playwright/test");

async function runScenario(page, mode) {
  await page.locator(`input[name="runMode"][value="${mode}"]`).check();
  await page.getByRole("button", { name: "Run scenario" }).click();
}

test.describe("Tool Search Lab", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/tool-search-lab");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test("renders server inventory and scenario options", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Scenario and mode" })).toBeVisible();
    await expect(page.locator("#serverInventoryLabel")).toContainText("4 servers / 32 tools");
    await expect(page.locator("#scenarioSelect option")).toHaveCount(3);
    await expect(page.locator("#serverList .server-card")).toHaveCount(4);
  });

  test("shows search mode loading fewer definitions than eager mode for the same scenario", async ({
    page,
  }) => {
    await runScenario(page, "search");

    await expect(page.locator("#searchMetrics")).toContainText("Definitions loaded");
    await expect(page.locator("#eagerMetrics")).toContainText("Definitions loaded");
    await expect(page.locator("#equivalenceLabel")).toHaveText("Yes");
    await expect(page.locator("#scenarioOutput")).toContainText("Daily Portfolio Brief");

    const searchDefinitions = await page
      .locator("#searchMetrics .metric-row")
      .filter({ hasText: "Definitions loaded" })
      .locator(".metric-row-value")
      .textContent();
    const eagerDefinitions = await page
      .locator("#eagerMetrics .metric-row")
      .filter({ hasText: "Definitions loaded" })
      .locator(".metric-row-value")
      .textContent();
    const searchBytes = await page
      .locator("#searchMetrics .metric-row")
      .filter({ hasText: "Definition bytes" })
      .locator(".metric-row-value")
      .textContent();
    const eagerBytes = await page
      .locator("#eagerMetrics .metric-row")
      .filter({ hasText: "Definition bytes" })
      .locator(".metric-row-value")
      .textContent();

    expect(Number(searchDefinitions.replace(/,/g, ""))).toBeLessThan(
      Number(eagerDefinitions.replace(/,/g, "")),
    );
    expect(Number(searchBytes.replace(/,/g, ""))).toBeLessThan(Number(eagerBytes.replace(/,/g, "")));

    await expect(page.locator("#searchTrace")).toContainText("load server");
    await expect(page.locator("#eagerTrace")).toContainText("Loaded all 32 tool definitions");
  });

  test("supports alternative scenarios and mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.selectOption("#scenarioSelect", "risk-rebalance-check");
    await runScenario(page, "eager");

    await expect(page.locator("#selectedScenarioLabel")).toHaveText("Risk & Rebalance Check");
    await expect(page.locator("#scenarioOutput")).toContainText("Risk & Rebalance Check");
    await expect(page.locator("#resultSummary")).toContainText("same final output");
    await expect(page.getByRole("button", { name: "Run scenario" })).toBeVisible();
  });
});

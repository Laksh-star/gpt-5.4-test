#!/usr/bin/env node
import { chromium } from "@playwright/test";

const symbols = process.argv.slice(2);
const browser = await chromium.launch({
  headless: true,
  channel: process.env.PLAYWRIGHT_BROWSER_CHANNEL || "chrome",
});
const page = await browser.newPage();
const results = {};

for (const symbol of symbols) {
  try {
    await page.goto(`https://finance.yahoo.com/quote/${symbol}`, {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });

    const quote = await page.evaluate(() => {
      const priceNode = document.querySelector('[data-testid="qsp-price"]');
      const changeNode = document.querySelector('[data-testid="qsp-price-change-percent"]');
      const nameNode = document.querySelector("h1");
      const price = Number(priceNode?.textContent?.replace(/,/g, ""));
      const percentMatch = changeNode?.textContent?.match(/([-+]?\d+(\.\d+)?)%/);
      const changePercent = percentMatch ? Number(percentMatch[1]) : 0;
      const previousClose = changePercent !== -100 ? price / (1 + changePercent / 100) : price;
      return {
        name: nameNode?.textContent || null,
        price,
        previousClose,
      };
    });

    if (Number.isFinite(quote.price)) {
      results[symbol] = {
        ...quote,
        currency: "USD",
      };
    }
  } catch (error) {
    results[symbol] = { error: String(error) };
  }
}

await browser.close();
process.stdout.write(JSON.stringify(results));

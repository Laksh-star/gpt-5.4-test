const DEFAULT_SYMBOLS = ["AAPL", "GOOGL", "TSLA", "MSFT", "NVDA"];
const HOLDINGS_KEY = "portfolio-holdings-v1";
const THEME_KEY = "portfolio-theme-v1";
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

const state = {
  quotes: {},
  holdings: [],
  editingId: null,
  refreshTimer: null,
};

const elements = {
  dataMode: document.getElementById("dataMode"),
  lastUpdated: document.getElementById("lastUpdated"),
  totalValue: document.getElementById("totalValue"),
  totalCost: document.getElementById("totalCost"),
  totalProfitLoss: document.getElementById("totalProfitLoss"),
  profitLossPercent: document.getElementById("profitLossPercent"),
  dailyChange: document.getElementById("dailyChange"),
  quoteGrid: document.getElementById("quoteGrid"),
  holdingForm: document.getElementById("holdingForm"),
  holdingId: document.getElementById("holdingId"),
  tickerInput: document.getElementById("tickerInput"),
  sharesInput: document.getElementById("sharesInput"),
  avgPriceInput: document.getElementById("avgPriceInput"),
  saveHoldingButton: document.getElementById("saveHoldingButton"),
  cancelEditButton: document.getElementById("cancelEditButton"),
  holdingsTableBody: document.getElementById("holdingsTableBody"),
  emptyState: document.getElementById("emptyState"),
  refreshButton: document.getElementById("refreshButton"),
  themeToggle: document.getElementById("themeToggle"),
  quoteCardTemplate: document.getElementById("quoteCardTemplate"),
};

function loadState() {
  try {
    state.holdings = JSON.parse(localStorage.getItem(HOLDINGS_KEY) || "[]");
  } catch {
    state.holdings = [];
  }

  const savedTheme = localStorage.getItem(THEME_KEY);
  if (savedTheme === "dark") {
    document.body.dataset.theme = "dark";
  }
}

function persistHoldings() {
  localStorage.setItem(HOLDINGS_KEY, JSON.stringify(state.holdings));
}

function currency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value || 0);
}

function percent(value) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function number(value) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 4,
  }).format(value);
}

function quoteSymbols() {
  const holdingsSymbols = state.holdings.map((holding) => holding.ticker);
  return [...new Set([...DEFAULT_SYMBOLS, ...holdingsSymbols])];
}

async function refreshQuotes() {
  const symbols = quoteSymbols();
  elements.refreshButton.disabled = true;
  elements.refreshButton.textContent = "Refreshing...";

  try {
    const response = await fetch(`/api/quotes?symbols=${encodeURIComponent(symbols.join(","))}`);
    const payload = await response.json();
    state.quotes = payload.quotes || {};

    const sources = new Set(Object.values(state.quotes).map((quote) => quote.source));
    elements.dataMode.textContent = [...sources].join(", ") || "Unavailable";
    elements.lastUpdated.textContent = payload.updatedAt
      ? new Date(payload.updatedAt).toLocaleString()
      : "Unknown";

    renderQuotes();
    renderHoldings();
    renderSummary();
  } catch (error) {
    elements.dataMode.textContent = "Unavailable";
    elements.lastUpdated.textContent = "Refresh failed";
    console.error(error);
  } finally {
    elements.refreshButton.disabled = false;
    elements.refreshButton.textContent = "Refresh prices";
  }
}

function scheduleAutoRefresh() {
  clearInterval(state.refreshTimer);
  state.refreshTimer = setInterval(refreshQuotes, REFRESH_INTERVAL_MS);
}

function renderQuotes() {
  elements.quoteGrid.innerHTML = "";

  quoteSymbols().forEach((symbol) => {
    const quote = state.quotes[symbol];
    const fragment = elements.quoteCardTemplate.content.cloneNode(true);
    fragment.querySelector(".quote-symbol").textContent = symbol;
    fragment.querySelector(".quote-name").textContent = quote?.name || "No quote available";
    fragment.querySelector(".quote-source").textContent = quote?.source || "n/a";
    fragment.querySelector(".quote-price").textContent = currency(quote?.price || 0);

    const changeNode = fragment.querySelector(".quote-change");
    const changePercent = quote
      ? ((quote.price - quote.previousClose) / quote.previousClose) * 100
      : 0;
    changeNode.textContent = quote ? `${percent(changePercent)} vs. previous close` : "Awaiting data";
    changeNode.classList.add(changePercent >= 0 ? "positive" : "negative");
    elements.quoteGrid.appendChild(fragment);
  });
}

function renderHoldings() {
  elements.holdingsTableBody.innerHTML = "";

  if (!state.holdings.length) {
    elements.emptyState.hidden = false;
    return;
  }

  elements.emptyState.hidden = true;

  state.holdings.forEach((holding) => {
    const quote = state.quotes[holding.ticker];
    const currentPrice = quote?.price || 0;
    const marketValue = currentPrice * holding.shares;
    const costBasis = holding.avgPrice * holding.shares;
    const profitLoss = marketValue - costBasis;

    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${holding.ticker}</td>
      <td>${number(holding.shares)}</td>
      <td>${currency(holding.avgPrice)}</td>
      <td>${currency(currentPrice)}</td>
      <td>${currency(marketValue)}</td>
      <td>${currency(costBasis)}</td>
      <td class="${profitLoss >= 0 ? "positive" : "negative"}">${currency(profitLoss)}</td>
      <td>
        <div class="row-actions">
          <button class="action-button" type="button" data-action="edit" data-id="${holding.id}">Edit</button>
          <button class="action-button" type="button" data-action="delete" data-id="${holding.id}">Delete</button>
        </div>
      </td>
    `;
    elements.holdingsTableBody.appendChild(row);
  });
}

function renderSummary() {
  const totals = state.holdings.reduce(
    (accumulator, holding) => {
      const quote = state.quotes[holding.ticker];
      const currentPrice = quote?.price || 0;
      accumulator.totalValue += currentPrice * holding.shares;
      accumulator.totalCost += holding.avgPrice * holding.shares;
      accumulator.dailyChange += ((currentPrice || 0) - (quote?.previousClose || currentPrice || 0)) * holding.shares;
      return accumulator;
    },
    { totalValue: 0, totalCost: 0, dailyChange: 0 },
  );

  const profitLoss = totals.totalValue - totals.totalCost;
  const profitLossPct = totals.totalCost ? (profitLoss / totals.totalCost) * 100 : 0;

  elements.totalValue.textContent = currency(totals.totalValue);
  elements.totalCost.textContent = currency(totals.totalCost);
  elements.totalProfitLoss.textContent = currency(profitLoss);
  elements.totalProfitLoss.className = profitLoss >= 0 ? "positive" : "negative";
  elements.profitLossPercent.textContent = percent(profitLossPct);
  elements.profitLossPercent.className = profitLossPct >= 0 ? "positive" : "negative";
  elements.dailyChange.textContent = currency(totals.dailyChange);
  elements.dailyChange.className = totals.dailyChange >= 0 ? "positive" : "negative";
}

function resetForm() {
  state.editingId = null;
  elements.holdingId.value = "";
  elements.holdingForm.reset();
  elements.saveHoldingButton.textContent = "Save holding";
  elements.cancelEditButton.hidden = true;
}

function upsertHolding(event) {
  event.preventDefault();

  const holding = {
    id: state.editingId || crypto.randomUUID(),
    ticker: elements.tickerInput.value.trim().toUpperCase(),
    shares: Number(elements.sharesInput.value),
    avgPrice: Number(elements.avgPriceInput.value),
  };

  if (!holding.ticker || !holding.shares || !holding.avgPrice) {
    return;
  }

  const existingIndex = state.holdings.findIndex((entry) => entry.id === holding.id);
  if (existingIndex >= 0) {
    state.holdings[existingIndex] = holding;
  } else {
    state.holdings.push(holding);
  }

  persistHoldings();
  resetForm();
  renderHoldings();
  renderSummary();
  refreshQuotes();
}

function handleTableActions(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }

  const holding = state.holdings.find((entry) => entry.id === button.dataset.id);
  if (!holding) {
    return;
  }

  if (button.dataset.action === "edit") {
    state.editingId = holding.id;
    elements.holdingId.value = holding.id;
    elements.tickerInput.value = holding.ticker;
    elements.sharesInput.value = holding.shares;
    elements.avgPriceInput.value = holding.avgPrice;
    elements.saveHoldingButton.textContent = "Update holding";
    elements.cancelEditButton.hidden = false;
    elements.tickerInput.focus();
    return;
  }

  if (button.dataset.action === "delete") {
    state.holdings = state.holdings.filter((entry) => entry.id !== holding.id);
    persistHoldings();
    renderHoldings();
    renderSummary();
  }
}

function toggleTheme() {
  const nextTheme = document.body.dataset.theme === "dark" ? "light" : "dark";
  if (nextTheme === "light") {
    delete document.body.dataset.theme;
    localStorage.setItem(THEME_KEY, "light");
    return;
  }

  document.body.dataset.theme = "dark";
  localStorage.setItem(THEME_KEY, "dark");
}

function init() {
  loadState();
  renderQuotes();
  renderHoldings();
  renderSummary();

  elements.holdingForm.addEventListener("submit", upsertHolding);
  elements.holdingsTableBody.addEventListener("click", handleTableActions);
  elements.cancelEditButton.addEventListener("click", resetForm);
  elements.refreshButton.addEventListener("click", refreshQuotes);
  elements.themeToggle.addEventListener("click", toggleTheme);

  scheduleAutoRefresh();
  refreshQuotes();
}

init();

const TOOL_SEARCH_THEME_KEY = "portfolio-theme-v1";

const state = {
  servers: [],
  scenarios: [],
  currentScenarioId: null,
  selectedMode: "search",
  results: {
    search: null,
    eager: null,
  },
};

const elements = {
  labThemeToggle: document.getElementById("labThemeToggle"),
  runScenarioButton: document.getElementById("runScenarioButton"),
  selectedModeLabel: document.getElementById("selectedModeLabel"),
  serverInventoryLabel: document.getElementById("serverInventoryLabel"),
  selectedScenarioLabel: document.getElementById("selectedScenarioLabel"),
  definitionsDelta: document.getElementById("definitionsDelta"),
  bytesDelta: document.getElementById("bytesDelta"),
  equivalenceLabel: document.getElementById("equivalenceLabel"),
  searchStepsLabel: document.getElementById("searchStepsLabel"),
  scenarioSelect: document.getElementById("scenarioSelect"),
  serverList: document.getElementById("serverList"),
  searchMetrics: document.getElementById("searchMetrics"),
  eagerMetrics: document.getElementById("eagerMetrics"),
  searchTrace: document.getElementById("searchTrace"),
  eagerTrace: document.getElementById("eagerTrace"),
  scenarioOutput: document.getElementById("scenarioOutput"),
  resultSummary: document.getElementById("resultSummary"),
  serverCardTemplate: document.getElementById("serverCardTemplate"),
  metricItemTemplate: document.getElementById("metricItemTemplate"),
  traceItemTemplate: document.getElementById("traceItemTemplate"),
  modeInputs: Array.from(document.querySelectorAll('input[name="runMode"]')),
};

function applySavedTheme() {
  if (localStorage.getItem(TOOL_SEARCH_THEME_KEY) === "dark") {
    document.body.dataset.theme = "dark";
  }
}

function toggleTheme() {
  const nextTheme = document.body.dataset.theme === "dark" ? "light" : "dark";
  if (nextTheme === "light") {
    delete document.body.dataset.theme;
    localStorage.setItem(TOOL_SEARCH_THEME_KEY, "light");
    return;
  }

  document.body.dataset.theme = "dark";
  localStorage.setItem(TOOL_SEARCH_THEME_KEY, "dark");
}

function formatInteger(value) {
  return new Intl.NumberFormat("en-US").format(value || 0);
}

function scenarioById(id) {
  return state.scenarios.find((scenario) => scenario.id === id);
}

function renderServers() {
  elements.serverList.innerHTML = "";
  state.servers.forEach((server) => {
    const fragment = elements.serverCardTemplate.content.cloneNode(true);
    fragment.querySelector(".server-name").textContent = server.name;
    fragment.querySelector(".server-count").textContent = `${server.toolCount} tools`;
    fragment.querySelector(".server-description").textContent = server.description;
    elements.serverList.appendChild(fragment);
  });
  const totalTools = state.servers.reduce((sum, server) => sum + server.toolCount, 0);
  elements.serverInventoryLabel.textContent = `${state.servers.length} servers / ${totalTools} tools`;
}

function renderScenarioOptions() {
  elements.scenarioSelect.innerHTML = "";
  state.scenarios.forEach((scenario) => {
    const option = document.createElement("option");
    option.value = scenario.id;
    option.textContent = scenario.name;
    elements.scenarioSelect.appendChild(option);
  });
  elements.scenarioSelect.value = state.currentScenarioId;
  updateScenarioLabels();
}

function updateScenarioLabels() {
  const scenario = scenarioById(state.currentScenarioId);
  elements.selectedScenarioLabel.textContent = scenario ? scenario.name : "No scenario selected";
  elements.selectedModeLabel.textContent = state.selectedMode;
}

function renderMetricBlock(container, result) {
  container.innerHTML = "";
  if (!result) {
    container.textContent = "Run this mode to see metrics.";
    return;
  }

  [
    ["Definitions loaded", result.metrics.toolDefinitionsLoaded],
    ["Definition bytes", result.metrics.definitionBytesLoaded],
    ["Tool calls", result.metrics.toolCalls],
    ["Search steps", result.metrics.searchSteps],
    ["Elapsed ms", result.metrics.elapsedMs],
  ].forEach(([label, value]) => {
    const fragment = elements.metricItemTemplate.content.cloneNode(true);
    fragment.querySelector(".metric-row-label").textContent = label;
    fragment.querySelector(".metric-row-value").textContent = formatInteger(value);
    container.appendChild(fragment);
  });
}

function renderTrace(container, result) {
  container.innerHTML = "";
  if (!result) {
    container.textContent = "No trace yet.";
    return;
  }
  result.trace.forEach((step) => {
    const fragment = elements.traceItemTemplate.content.cloneNode(true);
    fragment.querySelector(".trace-badge").textContent = step.type.replace("_", " ");
    fragment.querySelector(".trace-target").textContent = step.target;
    fragment.querySelector(".trace-detail").textContent = step.detail;
    container.appendChild(fragment);
  });
}

function renderComparison() {
  const searchResult = state.results.search;
  const eagerResult = state.results.eager;

  renderMetricBlock(elements.searchMetrics, searchResult);
  renderMetricBlock(elements.eagerMetrics, eagerResult);
  renderTrace(elements.searchTrace, searchResult);
  renderTrace(elements.eagerTrace, eagerResult);

  if (searchResult && eagerResult) {
    const definitionDelta =
      eagerResult.metrics.toolDefinitionsLoaded - searchResult.metrics.toolDefinitionsLoaded;
    const byteDelta = eagerResult.metrics.definitionBytesLoaded - searchResult.metrics.definitionBytesLoaded;
    const outputsMatch = searchResult.output === eagerResult.output;

    elements.definitionsDelta.textContent = `${formatInteger(definitionDelta)} fewer`;
    elements.bytesDelta.textContent = `${formatInteger(byteDelta)} saved`;
    elements.equivalenceLabel.textContent = outputsMatch ? "Yes" : "Check trace";
    elements.equivalenceLabel.className = outputsMatch ? "positive" : "negative";
    elements.searchStepsLabel.textContent = formatInteger(searchResult.metrics.searchSteps);
    elements.scenarioOutput.textContent = searchResult.output;
    elements.resultSummary.textContent =
      `Both modes completed ${scenarioById(state.currentScenarioId)?.name}. ` +
      `Search mode loaded ${searchResult.metrics.toolDefinitionsLoaded} definitions versus ` +
      `${eagerResult.metrics.toolDefinitionsLoaded} in eager mode while producing the same final output.`;
    return;
  }

  const activeResult = state.results[state.selectedMode];
  elements.definitionsDelta.textContent = "-";
  elements.bytesDelta.textContent = "-";
  elements.equivalenceLabel.textContent = "Pending";
  elements.equivalenceLabel.className = "";
  elements.searchStepsLabel.textContent = activeResult
    ? formatInteger(activeResult.metrics.searchSteps)
    : "-";
  elements.scenarioOutput.textContent = activeResult
    ? activeResult.output
    : "Run a scenario to compare eager and search modes.";
}

async function runScenario(mode) {
  const response = await fetch("/api/tool-search/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      mode,
      scenarioId: state.currentScenarioId,
    }),
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  state.results[mode] = await response.json();
  renderComparison();
}

async function handleRun() {
  elements.runScenarioButton.disabled = true;
  elements.runScenarioButton.textContent = "Running...";

  try {
    await runScenario(state.selectedMode);
    if (!state.results.search || !state.results.eager) {
      const alternateMode = state.selectedMode === "search" ? "eager" : "search";
      await runScenario(alternateMode);
    }
  } catch (error) {
    console.error(error);
    elements.resultSummary.textContent = "Scenario execution failed. Check console output.";
  } finally {
    elements.runScenarioButton.disabled = false;
    elements.runScenarioButton.textContent = "Run scenario";
  }
}

async function loadInitialData() {
  const [serversResponse, scenariosResponse] = await Promise.all([
    fetch("/api/tool-search/servers"),
    fetch("/api/tool-search/scenarios"),
  ]);

  const serversPayload = await serversResponse.json();
  const scenariosPayload = await scenariosResponse.json();
  state.servers = serversPayload.servers || [];
  state.scenarios = scenariosPayload.scenarios || [];
  state.currentScenarioId = state.scenarios[0]?.id || null;

  renderServers();
  renderScenarioOptions();
  renderComparison();
}

function bindEvents() {
  elements.labThemeToggle.addEventListener("click", toggleTheme);
  elements.runScenarioButton.addEventListener("click", handleRun);
  elements.scenarioSelect.addEventListener("change", (event) => {
    state.currentScenarioId = event.target.value;
    state.results.search = null;
    state.results.eager = null;
    updateScenarioLabels();
    renderComparison();
  });
  elements.modeInputs.forEach((input) => {
    input.addEventListener("change", (event) => {
      state.selectedMode = event.target.value;
      updateScenarioLabels();
      renderComparison();
    });
  });
}

async function init() {
  applySavedTheme();
  bindEvents();
  await loadInitialData();
}

init().catch((error) => {
  console.error(error);
  elements.resultSummary.textContent = "Unable to load Tool Search Lab data.";
});

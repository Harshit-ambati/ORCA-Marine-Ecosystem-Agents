const $ = (id) => document.getElementById(id);
let datasetId = "sample";
let currentReport = null;
let chartMetric = "dhw_c_weeks";
const SVG_NS = "http://www.w3.org/2000/svg";

function svgNode(tag, attributes = {}) {
  const element = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
  return element;
}

function renderTimeline(rows) {
  const chart = $("timeline-chart");
  chart.replaceChildren();
  const label = chartMetric === "dhw_c_weeks" ? "DHW (°C-weeks)" : "Temperature anomaly (°C)";
  const ordered = [...rows].sort((a, b) => a.date.localeCompare(b.date));
  const stride = Math.max(1, Math.ceil(ordered.length / 450));
  const plotted = ordered.filter((_, index) => index % stride === 0 || index === ordered.length - 1);
  const valid = plotted.filter((row) => Number.isFinite(row[chartMetric]));
  const totalValid = ordered.filter((row) => Number.isFinite(row[chartMetric])).length;
  $("timeline-caption").textContent = `${label} · ${totalValid} of ${ordered.length} records measured` +
    (stride > 1 ? ` · showing ${plotted.length} sampled records` : "");
  chart.setAttribute("aria-label", `${label} over time. ${totalValid} of ${ordered.length} records have a value. Source records are available below.`);
  if (!valid.length) {
    const message = svgNode("text", {x: 400, y: 110, "text-anchor": "middle", class: "chart-empty"});
    message.textContent = "NO MEASUREMENTS AVAILABLE FOR THIS PERIOD";
    chart.append(message);
    return;
  }
  const left = 55, right = 775, top = 22, bottom = 177;
  const earliest = Date.parse(ordered[0].date + "T00:00:00Z");
  const latest = Date.parse(ordered.at(-1).date + "T00:00:00Z");
  const x = (row) => latest === earliest ? (left + right) / 2 :
    left + (Date.parse(row.date + "T00:00:00Z") - earliest) / (latest - earliest) * (right - left);
  const low = Math.min(0, ...valid.map((row) => row[chartMetric]));
  const high = Math.max(0, ...valid.map((row) => row[chartMetric]));
  const upper = high === low ? high + 1 : high;
  const y = (value) => bottom - (value - low) / (upper - low) * (bottom - top);
  for (let tick = 0; tick <= 3; tick++) {
    const value = low + (upper - low) * tick / 3;
    const position = y(value);
    chart.append(svgNode("line", {x1: left, x2: right, y1: position, y2: position, class: "chart-grid"}));
    const text = svgNode("text", {x: left - 10, y: position + 3, "text-anchor": "end", class: "chart-label"});
    text.textContent = value.toFixed(1);
    chart.append(text);
  }
  for (const [position, value, anchor] of [[left, ordered[0].date, "start"], [right, ordered.at(-1).date, "end"]]) {
    const text = svgNode("text", {x: position, y: 208, "text-anchor": anchor, class: "chart-label"});
    text.textContent = value;
    chart.append(text);
  }
  let previous = null;
  for (const row of plotted) {
    if (!Number.isFinite(row[chartMetric])) { previous = null; continue; }
    if (previous) chart.append(svgNode("line", {x1: x(previous), y1: y(previous[chartMetric]),
      x2: x(row), y2: y(row[chartMetric]), class: "chart-line"}));
    const link = svgNode("a", {href: recordHref(row.id),
      "aria-label": `${row.date}: ${row[chartMetric]} ${label}. View source record ${row.id}`});
    const point = svgNode("circle", {cx: x(row), cy: y(row[chartMetric]), r: 4, class: "chart-point"});
    const title = svgNode("title");
    title.textContent = `${row.date} · ${row[chartMetric]} ${label} · ${row.id}`;
    link.append(point, title);
    chart.append(link);
    previous = row;
  }
}

for (const [id, metric] of [["chart-dhw", "dhw_c_weeks"], ["chart-anomaly", "temp_anomaly_c"]]) {
  $(id).addEventListener("click", () => {
    chartMetric = metric;
    for (const buttonId of ["chart-dhw", "chart-anomaly"]) {
      $(buttonId).setAttribute("aria-pressed", String(buttonId === id));
    }
    if (currentReport) renderTimeline(currentReport.result.evidence);
  });
}

function node(tag, value, className = "") {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  return element;
}
function setStatus(message, error = false) {
  $("status").textContent = message;
  $("status").classList.toggle("error", error);
}
function fillList(target, values, empty) {
  target.replaceChildren(...(values.length ? values : [empty]).map((value) => node("li", value)));
}
function setDataset(info, source = "sample") {
  datasetId = info.id;
  currentReport = null;
  $("site").replaceChildren(...info.sites.map((name) => {
    const option = node("option", name);
    option.value = name;
    return option;
  }));
  $("start").value = info.start;
  $("end").value = info.end;
  const labels = {sample: "Synthetic sample", offline: "Offline NOAA excerpt", live: "NOAA station export", upload: "Uploaded CSV"};
  for (const id of ["sample", "offline", "live"]) {
    $("" + id).classList.toggle("active", source === id);
    $("" + id).setAttribute("aria-pressed", String(source === id));
  }
  $("dataset-note").textContent = `${labels[source]} · ${info.rows} records · ${info.sites.length} site(s)`;
  $("report").hidden = true;
  $("empty").hidden = false;
  $("output-state").textContent = "AWAITING INPUT";
}
async function parseResponse(response) {
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Request failed.");
  return body;
}
function recordHref(id) {
  return `#record-${encodeURIComponent(id)}`;
}
function renderClaims(result) {
  const available = new Set(result.evidence.map((row) => row.id));
  const items = result.claims.length ? result.claims : ["No supported claims for this period."];
  $("claims").replaceChildren(...items.map((claim) => {
    const li = node("li", claim);
    for (const id of result.claim_evidence?.[claim] || []) {
      if (!available.has(id)) continue;
      const link = node("a", `[${id}]`, "evidence-link");
      link.href = recordHref(id);
      link.title = `Jump to evidence record ${id}`;
      li.append(" ", link);
    }
    return li;
  }));
}
function sourceLink(source) {
  try {
    const url = new URL(source);
    if (url.protocol !== "https:") throw new Error("Unsupported source URL");
    const link = node("a", url.hostname.includes("noaa.gov") ? "NOAA archive ↗" : "Source ↗", "source-link");
    link.href = url.href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.title = url.href;
    return link;
  } catch {
    return node("span", source);
  }
}
function showReport(result) {
  $("empty").hidden = true;
  $("report").hidden = false;
  $("output-state").textContent = "REPORT READY";
  $("risk").textContent = `${result.risk.toUpperCase()} RISK`;
  $("risk").className = `risk ${result.risk}`;
  $("mode").textContent = result.mode === "llm" ? "LLM agents" : "Rule-based demo";
  $("summary").textContent = result.summary;
  $("site-title").textContent = result.site;
  $("metrics").textContent = `${result.metrics?.latency_ms ?? 0} ms · ${result.metrics?.calls ?? 0} LLM calls · ${result.metrics?.input_tokens ?? 0} input tokens · ${result.metrics?.output_tokens ?? 0} output tokens`;
  renderClaims(result);
  renderTimeline(result.evidence);
  fillList($("limitations"), result.limitations, "No additional data limitations recorded.");
  $("review-tag").textContent = result.mode === "llm"
    ? (result.revised ? "Critic challenged and revised" : "Critic approved")
    : "Rule-based checks passed";
  $("trace").replaceChildren(...result.trace.map((item) => {
    const li = document.createElement("li");
    li.append(node("span", item.agent, "agent"), node("span", item.action, "action"), node("p", item.detail));
    if (item.evidence.length) li.append(node("small", `Evidence: ${item.evidence.join(", ")}`));
    return li;
  }));
  $("evidence").replaceChildren(...result.evidence.map((row) => {
    const tr = document.createElement("tr");
    tr.id = `record-${row.id}`;
    const values = [row.date, row.sea_surface_temp_c, row.temp_anomaly_c,
      row.dhw_c_weeks, row.bleaching_observed === null ? "Not recorded" : row.bleaching_observed ? "Yes" : "No"];
    values.forEach((value) => tr.append(node("td", value ?? "—")));
    const sourceCell = document.createElement("td");
    sourceCell.append(sourceLink(row.source), " · ", node("code", row.id));
    tr.append(sourceCell);
    return tr;
  }));
}
function markdownCell(value) {
  return String(value ?? "—").replace(/\|/g, "\\|").replace(/\r?\n/g, " ");
}
function downloadReport() {
  if (!currentReport) return;
  const {result, selection} = currentReport;
  const lines = [
    "# ORCA investigation report", "",
    `Site: ${result.site}`,
    `Period: ${selection.start} to ${selection.end}`,
    `Question: ${selection.question}`,
    `Mode: ${result.mode === "llm" ? "LLM reasoning and critique" : "Rule-based demo (no LLM calls)"}`,
    `Heat-stress category: ${result.risk}`, "",
    "## Reviewed finding", "", result.summary, "",
    "## Supported findings", "",
    ...(result.claims.length ? result.claims.map((claim) =>
      `- ${claim} (Evidence: ${(result.claim_evidence?.[claim] || []).join(", ") || "none"})`) : ["- No supported findings for this period."]),
    "", "## Limitations", "",
    ...result.limitations.map((item) => `- ${item}`),
    "", "## Agent trace", "",
    ...result.trace.map((item) =>
      `- **${item.agent} / ${item.action}:** ${item.detail} (Evidence: ${item.evidence.join(", ") || "none"})`),
    "", "## Source records", "",
    "| ID | Date | SST °C | Anomaly °C | DHW °C-weeks | Bleaching observed | Source |",
    "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ...result.evidence.map((row) => [
      row.id, row.date, row.sea_surface_temp_c, row.temp_anomaly_c, row.dhw_c_weeks,
      row.bleaching_observed === null ? "Not recorded" : row.bleaching_observed ? "Yes" : "No", row.source
    ].map(markdownCell).join(" | ")).map((row) => `| ${row} |`),
    "", "## Run metrics", "",
    `- Model: ${result.metrics?.model || "none"}`,
    `- Calls: ${result.metrics?.calls ?? 0}`,
    `- Input tokens: ${result.metrics?.input_tokens ?? 0}`,
    `- Output tokens: ${result.metrics?.output_tokens ?? 0}`,
    `- Latency: ${result.metrics?.latency_ms ?? 0} ms`,
    "", "Educational research prototype. Heat stress is not confirmation of bleaching.", ""
  ];
  const blob = new Blob([lines.join("\n")], {type: "text/markdown;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `ORCA_${result.site.replace(/[^a-z0-9]+/gi, "_")}_${selection.start}.md`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$("export-report").addEventListener("click", downloadReport);
async function loadSource(source, request) {
  setStatus(source === "live" ? "Downloading NOAA station export…" : "Loading dataset…");
  try {
    setDataset(await parseResponse(await request()), source);
    setStatus(source === "live" ? "NOAA export loaded." : "Dataset ready.");
  } catch (error) {
    setStatus(error.message, true);
  }
}
$("file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  await loadSource("upload", () => fetch("/api/datasets", {method: "POST", body: form}));
});
$("run").addEventListener("click", async () => {
  if (!$("site").value || !$("start").value || !$("end").value || !$("question").value.trim()) {
    setStatus("Choose a site and dates, and enter a research question.", true);
    return;
  }
  if ($("start").value > $("end").value) {
    setStatus("The start date must be before the end date.", true);
    return;
  }
  $("run").disabled = true;
  $("output-state").textContent = "INVESTIGATING";
  setStatus("Agents are investigating…");
  try {
    const result = await parseResponse(await fetch("/api/investigate", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({dataset_id: datasetId, site: $("site").value,
        start: $("start").value, end: $("end").value,
        question: $("question").value.trim(), use_llm: $("llm").checked})
    }));
    currentReport = {result, selection: {dataset: datasetId, site: $("site").value,
      start: $("start").value, end: $("end").value, question: $("question").value.trim()}};
    showReport(result);
    setStatus(`Complete · ${result.trace.length} agent steps`);
  } catch (error) {
    $("output-state").textContent = "NEEDS ATTENTION";
    setStatus(error.message, true);
  } finally {
    $("run").disabled = false;
  }
});
$("sample").addEventListener("click", () => loadSource("sample", () => fetch("/api/datasets/sample")));
$("offline").addEventListener("click", () => loadSource("offline", () => fetch("/api/datasets/noaa-offline")));
$("live").addEventListener("click", () => loadSource("live", () => fetch("/api/noaa/import", {
  method: "POST", headers: {"Content-Type": "application/json"},
  body: JSON.stringify({station: "florida_keys", start: $("start").value, end: $("end").value})
})));
loadSource("sample", () => fetch("/api/datasets/sample"));

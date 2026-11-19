const $ = (id) => document.getElementById(id);
let datasetId = "sample";

function node(tag, value, className = "") {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  return element;
}
function fillList(target, values, empty) {
  target.replaceChildren(...(values.length ? values : [empty]).map((v) => node("li", v)));
}
function setDataset(info, source = "sample") {
  datasetId = info.id;
  $("site").replaceChildren(...info.sites.map((name) => {
    const option = node("option", name); option.value = name; return option;
  }));
  $("start").value = info.start;
  $("end").value = info.end;
  const labels = {sample: "Synthetic sample", offline: "Offline NOAA excerpt", live: "NOAA station export", upload: "Uploaded CSV"};
  for (const id of ["sample", "offline", "live"]) {
    $(id).classList.toggle("active", source === id);
    $(id).setAttribute("aria-pressed", String(source === id));
  }
  $("report").hidden = true;
  $("dataset-note").textContent = `${labels[source]} · ${info.rows} records · ${info.sites.length} site(s)`;
  $("empty").hidden = false;
}
async function parseResponse(response) {
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Request failed.");
  return body;
}
function showReport(result) {
  $("empty").hidden = true;
  $("report").hidden = false;
  $("risk").textContent = `${result.risk.toUpperCase()} RISK`;
  $("risk").className = `risk ${result.risk}`;
  $("mode").textContent = result.mode === "llm" ? "LLM agents" : "Rule-based demo";
  $("summary").textContent = result.summary;
  $("site-title").textContent = result.site;
  $("metrics").textContent = `${result.metrics?.latency_ms ?? 0} ms · ${result.metrics?.calls ?? 0} LLM calls · ${result.metrics?.input_tokens ?? 0} input tokens · ${result.metrics?.output_tokens ?? 0} output tokens`;
  fillList($("claims"), result.claims.map((claim) => `${claim} [${(result.claim_evidence?.[claim] || []).join(", ")}]`), "No supported claims for this period.");
  fillList($("limitations"), result.limitations, "No additional data limitations recorded.");
  $("review-tag").textContent = result.revised ? "Proposal challenged and revised" : "Proposal approved";
  $("trace").replaceChildren(...result.trace.map((item) => {
    const li = document.createElement("li");
    li.append(node("span", item.agent, "agent"), node("span", item.action, "action"), node("p", item.detail));
    if (item.evidence.length) li.append(node("small", `Evidence: ${item.evidence.join(", ")}`));
    return li;
  }));
  $("evidence").replaceChildren(...result.evidence.map((row) => {
    const tr = document.createElement("tr");
    const values = [row.date, row.sea_surface_temp_c, row.temp_anomaly_c,
      row.dhw_c_weeks, row.bleaching_observed === null ? "Not recorded" : row.bleaching_observed ? "Yes" : "No",
      `${row.source} · ${row.id}`];
    values.forEach((value) => tr.append(node("td", value ?? "—")));
    return tr;
  }));
}
$("file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  $("status").textContent = "Validating CSV…";
  const form = new FormData(); form.append("file", file);
  try {
    setDataset(await parseResponse(await fetch("/api/datasets", { method: "POST", body: form })), "upload");
    $("status").textContent = "Dataset ready.";
  } catch (error) { $("status").textContent = error.message; }
});
$("run").addEventListener("click", async () => {
  $("run").disabled = true;
  $("status").textContent = "Agents are investigating…";
  try {
    const result = await parseResponse(await fetch("/api/investigate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset_id: datasetId, site: $("site").value,
        start: $("start").value, end: $("end").value,
        question: $("question").value, use_llm: $("llm").checked })
    }));
    showReport(result);
    $("status").textContent = `Complete · ${result.trace.length} agent steps`;
  } catch (error) { $("status").textContent = error.message; }
  finally { $("run").disabled = false; }
});
$("offline").addEventListener("click", async () => {
  try { setDataset(await parseResponse(await fetch("/api/datasets/noaa-offline")), "offline"); $("status").textContent = "Offline NOAA excerpt loaded."; }
  catch (error) { $("status").textContent = error.message; }
});
$("live").addEventListener("click", async () => {
  $("status").textContent = "Downloading NOAA station export.";
  try {
    setDataset(await parseResponse(await fetch("/api/noaa/import", {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({station: "florida_keys", start: $("start").value, end: $("end").value})})), "live");
    $("status").textContent = "NOAA export loaded.";
  } catch (error) { $("status").textContent = error.message; }
});
$("sample").addEventListener("click", async () => {
  try { setDataset(await parseResponse(await fetch("/api/datasets/sample")), "sample"); $("status").textContent = "Sample dataset loaded."; }
  catch (error) { $("status").textContent = error.message; }
});
fetch("/api/datasets/sample").then(parseResponse).then((info) => setDataset(info, "sample"))
  .catch((error) => { $("dataset-note").textContent = "Could not load sample data."; $("status").textContent = error.message; });

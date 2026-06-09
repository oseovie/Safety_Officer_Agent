// Consolidated DOM element selectors
const elements = {
  assessmentForm: document.querySelector("#assessmentForm"),
  toolboxForm: document.querySelector("#toolboxForm"),
  whatsappForm: document.querySelector("#whatsappForm"),
  resultEmpty: document.querySelector("#resultEmpty"),
  resultCard: document.querySelector("#resultCard"),
  checklist: document.querySelector("#checklist"),
  checklistSummary: document.querySelector("#checklistSummary"),
  toolboxOutput: document.querySelector("#toolboxOutput"),
  whatsappOutput: document.querySelector("#whatsappOutput"),
  reportList: document.querySelector("#reportList"),
  analyticsList: document.querySelector("#analyticsList"),
  predictiveList: document.querySelector("#predictiveList"),
  siteStatus: document.querySelector("#siteStatus"),
  clearReportButton: document.querySelector("#clearReportButton"),
  resetChecklistButton: document.querySelector("#resetChecklistButton"),
  totalCount: document.querySelector("#totalCount"),
  highCount: document.querySelector("#highCount"),
  mediumCount: document.querySelector("#mediumCount"),
  lowCount: document.querySelector("#lowCount"),
  openCount: document.querySelector("#openCount"),
  criticalCount: document.querySelector("#criticalCount"),
  categoryCount: document.querySelector("#categoryCount"),
  hotspotCount: document.querySelector("#hotspotCount"),
};

// Destructure frequently used elements for convenience
const {
  assessmentForm,
  toolboxForm,
  whatsappForm,
  resultEmpty,
  resultCard,
  checklist,
  checklistSummary,
  toolboxOutput,
  whatsappOutput,
  reportList,
  analyticsList,
  predictiveList,
  siteStatus,
  clearReportButton,
  resetChecklistButton,
  totalCount,
  highCount,
  mediumCount,
  lowCount,
  openCount,
  criticalCount,
  categoryCount,
  hotspotCount,
} = elements;

let risks = [];

function levelClass(level) {
  return String(level).toLowerCase();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function fetchJson(url, options = {}) {
  const { method = "GET", payload } = options;
  const fetchOptions = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  
  if (payload) {
    fetchOptions.body = JSON.stringify(payload);
  }

  const response = await fetch(url, fetchOptions);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }
  return data;
}

// Convenience wrappers for common use cases
const getJson = (url) => fetchJson(url);
const postJson = (url, payload) => fetchJson(url, { method: "POST", payload });

function controlGroup(title, items) {
  return `
    <div class="control-group">
      <h4>${escapeHtml(title)}</h4>
      <ul class="control-list">
        ${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    </div>
  `;
}

function renderCurrentRisk(risk) {
  resultEmpty.classList.add("hidden");
  resultCard.classList.remove("hidden");

  const controls = risk.hierarchy_of_controls || {};
  resultCard.innerHTML = `
    <div class="risk-banner ${levelClass(risk.initial_level)}">
      <div class="risk-score">
        <strong>${risk.initial_score}</strong>
        <span>${escapeHtml(risk.initial_level)} initial risk</span>
      </div>
      <p>Residual risk after controls: ${risk.residual_score} (${escapeHtml(risk.residual_level)})</p>
    </div>
    <div>
      <h3>${escapeHtml(risk.task)}</h3>
      <p>${escapeHtml(risk.hazard)}</p>
      <p><strong>Category:</strong> ${escapeHtml(risk.category)}</p>
      <p><strong>Location:</strong> ${escapeHtml(risk.location)}</p>
      <p><strong>CAPA:</strong> ${escapeHtml(risk.owner)} owns this until ${escapeHtml(risk.due_at)}</p>
      <p><strong>Verification:</strong> ${escapeHtml(risk.verification_required)}</p>
    </div>
    ${controlGroup("Elimination", controls.elimination || [])}
    ${controlGroup("Substitution", controls.substitution || [])}
    ${controlGroup("Engineering", controls.engineering || [])}
    ${controlGroup("Administrative", controls.administrative || [])}
    ${controlGroup("PPE", controls.ppe || [])}
  `;
}

function renderReport() {
  const counts = risks.reduce(
    (summary, risk) => {
      const level = levelClass(risk.initial_level);
      if (level === "critical" || level === "high") summary.high += 1;
      if (level === "medium") summary.medium += 1;
      if (level === "low") summary.low += 1;
      return summary;
    },
    { high: 0, medium: 0, low: 0 },
  );

  totalCount.textContent = risks.length;
  highCount.textContent = counts.high;
  mediumCount.textContent = counts.medium;
  lowCount.textContent = counts.low;
  siteStatus.textContent = risks.length ? `${risks.length} risks logged` : "No risks logged";

  if (!risks.length) {
    reportList.innerHTML = `<div class="empty-state">No risk records yet.</div>`;
    return;
  }

  reportList.innerHTML = risks
    .map(
      (risk) => `
        <article class="report-item">
          <div class="report-line">
            <strong>${escapeHtml(risk.id)} - ${escapeHtml(risk.task)}</strong>
            <span class="level-tag ${levelClass(risk.initial_level)}">${risk.initial_score} ${escapeHtml(risk.initial_level)}</span>
          </div>
          <p>${escapeHtml(risk.hazard)}</p>
          <p>${escapeHtml(risk.location)} | ${escapeHtml(risk.category)} | ${escapeHtml(risk.status)}</p>
          <p>Owner: ${escapeHtml(risk.owner)} | Due: ${escapeHtml(risk.due_at)}</p>
          <button class="ghost-button close-risk-button" data-risk-id="${escapeHtml(risk.id)}" type="button">Close</button>
        </article>
      `,
    )
    .join("");
}

function renderAnalytics(data) {
  openCount.textContent = data.open;
  criticalCount.textContent = data.open_critical;
  categoryCount.textContent = Object.keys(data.by_category).length;
  hotspotCount.textContent = data.hot_locations.length;

  const categoryRows = Object.entries(data.by_category)
    .map(([category, count]) => `<li>${escapeHtml(category)}: ${count}</li>`)
    .join("");
  const locationRows = Object.entries(data.by_location)
    .map(([location, count]) => `<li>${escapeHtml(location)}: ${count}</li>`)
    .join("");

  analyticsList.innerHTML = `
    <article class="report-item">
      <strong>By category</strong>
      <ul class="compact-list">${categoryRows || "<li>No categories yet.</li>"}</ul>
    </article>
    <article class="report-item">
      <strong>By location</strong>
      <ul class="compact-list">${locationRows || "<li>No locations yet.</li>"}</ul>
    </article>
  `;
}

function renderPredictive(items) {
  if (!items.length) {
    predictiveList.innerHTML = `<div class="empty-state">No predictive schedule conflicts found.</div>`;
    return;
  }

  predictiveList.innerHTML = items
    .map(
      (item) => `
        <article class="report-item">
          <strong>${escapeHtml(item.location)} - ${escapeHtml(item.category)}</strong>
          <p>${escapeHtml(item.task)} | ${escapeHtml(item.crew)}</p>
          <p>Initial: ${item.initial_score} (${escapeHtml(item.initial_level)}) | Residual: ${item.residual_score}</p>
          <p>${escapeHtml((item.controls.engineering || [])[0] || "Review controls before shift.")}</p>
        </article>
      `,
    )
    .join("");
}

function renderChecklist(items) {
  checklist.innerHTML = items
    .map(
      (item, index) => `
        <label class="check-item">
          <input type="checkbox" data-check-index="${index}">
          <span>${escapeHtml(item)}</span>
        </label>
      `,
    )
    .join("");
  updateChecklistSummary();
}

function updateChecklistSummary() {
  const boxes = [...checklist.querySelectorAll("input")];
  const checked = boxes.filter((box) => box.checked).length;
  const open = boxes.length - checked;

  if (!boxes.length) {
    checklistSummary.textContent = "Checklist unavailable.";
    return;
  }

  checklistSummary.textContent = open
    ? `${open} item${open === 1 ? "" : "s"} still need confirmation.`
    : "Checklist complete. Continue active monitoring.";
}

async function refreshDashboard() {
  const [riskData, analyticsData, predictiveData] = await Promise.all([
    getJson("/api/risks"),
    getJson("/api/analytics"),
    getJson("/api/predictive-jha"),
  ]);
  risks = riskData.risks;
  renderReport();
  renderAnalytics(analyticsData);
  renderPredictive(predictiveData.items);
}

assessmentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(assessmentForm);

  const payload = {
    task: form.get("task"),
    hazard: form.get("hazard"),
    people_at_risk: form.get("people_at_risk"),
    location: form.get("location"),
    owner: form.get("owner"),
    deadline_hours: Number(form.get("deadline_hours")),
  };

  const likelihood = form.get("likelihood");
  const severity = form.get("severity");
  if (likelihood) payload.likelihood = Number(likelihood);
  if (severity) payload.severity = Number(severity);

  try {
    const risk = await postJson("/api/risks", payload);
    renderCurrentRisk(risk);
    assessmentForm.reset();
    await refreshDashboard();
  } catch (error) {
    alert(error.message);
  }
});

toolboxForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(toolboxForm);

  try {
    const talk = await postJson("/api/toolbox", { topic: form.get("topic") });
    toolboxOutput.innerHTML = talk.points.map((point) => `<li>${escapeHtml(point)}</li>`).join("");
  } catch (error) {
    alert(error.message);
  }
});

whatsappForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(whatsappForm);

  try {
    const data = await postJson("/api/whatsapp/test", { message: form.get("message") });
    whatsappOutput.classList.remove("empty-state");
    whatsappOutput.textContent = data.reply;
    await refreshDashboard();
  } catch (error) {
    alert(error.message);
  }
});

reportList.addEventListener("click", async (event) => {
  const button = event.target.closest(".close-risk-button");
  if (!button) return;

  const note = prompt("Verification note or photo reference:");
  if (!note) return;

  try {
    const data = await postJson("/api/risks/status", {
      id: button.dataset.riskId,
      status: "Closed",
      verification_note: note,
    });
    renderCurrentRisk(data.risk);
    await refreshDashboard();
  } catch (error) {
    alert(error.message);
  }
});

checklist.addEventListener("change", updateChecklistSummary);

resetChecklistButton.addEventListener("click", () => {
  checklist.querySelectorAll("input").forEach((box) => {
    box.checked = false;
  });
  updateChecklistSummary();
});

clearReportButton.addEventListener("click", async () => {
  resultCard.classList.add("hidden");
  resultEmpty.classList.remove("hidden");
});

async function loadChecklist() {
  try {
    const response = await fetch("/api/checklist");
    const data = await response.json();
    renderChecklist(data.items);
  } catch {
    checklistSummary.textContent = "Could not load checklist.";
  }
}

loadChecklist();
refreshDashboard().catch((error) => {
  reportList.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
});

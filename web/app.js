"use strict";

const state = { dashboard: null, checkpoints: [], checkpoint: null, progress: null, conflicts: [] };
const $ = (selector) => document.querySelector(selector);
const empty = () => document.importNode($("#emptyTemplate").content, true);
const escapeHtml = (value = "") => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.status === 204 ? null : response.json();
}

function setStatus(message = "") { $("#status").textContent = message; }
function showView(name) {
  document.querySelectorAll(".view").forEach(view => { view.hidden = view.id !== name; });
  document.querySelectorAll("[data-view]").forEach(link => link.setAttribute("aria-current", link.dataset.view === name ? "page" : "false"));
  $("#primaryNav").classList.remove("open"); $("#menuButton").setAttribute("aria-expanded", "false");
  if (location.hash !== `#${name}`) history.replaceState(null, "", `#${name}`);
}

function renderCards(target, cards) {
  target.innerHTML = cards.map(card => `<div class="summary-card"><strong>${escapeHtml(card.value ?? "—")}</strong><span>${escapeHtml(card.label)}</span></div>`).join("");
}
function renderStop(target, warnings = []) {
  target.hidden = !warnings.length; target.textContent = warnings.join(" ");
}
function renderChecks(target, actions = []) {
  target.replaceChildren();
  if (!actions.length) return target.append(empty());
  actions.forEach(action => {
    const label = document.createElement("label"); label.className = "check-row";
    label.innerHTML = `<input type="checkbox" ${action.completed ? "checked" : ""} data-action-id="${escapeHtml(action.id)}"><span class="check-text"><strong>${escapeHtml(action.title || action.subject)}</strong><br>${escapeHtml(action.action || "")}</span>`;
    target.append(label);
  });
}

function renderDashboard() {
  const d = state.dashboard || {};
  renderStop($("#stopBanner"), d.stop_warnings || []);
  renderCards($("#summaryCards"), [
    { label: "Checkpoint", value: d.checkpoint?.sequence_label || "Unknown" },
    { label: "Mini Medals", value: d.progress?.medals ?? "Unknown" },
    { label: "Hoarder items", value: d.progress?.items ?? "Unknown" },
    { label: "Monsters", value: d.progress?.monsters ?? "Unknown" }
  ]);
  renderChecks($("#nextActions"), d.next_actions || []);
}

function renderCheckpoint() {
  const c = state.checkpoint || {};
  $("#checkpointMeta").textContent = [c.name, c.time_period, c.region].filter(Boolean).join(" · ");
  renderStop($("#checkpointStop"), c.stop_warnings || []);
  renderChecks($("#actions"), c.actions || []);
  $("#actionCount").textContent = `${(c.actions || []).filter(a => !a.completed).length} open`;
  const advice = $("#advice"); advice.innerHTML = (c.advice || []).map(a => `<div class="advice-item"><span class="tag goal-${escapeHtml(a.goal)}">${escapeHtml(a.type)}</span><strong>${escapeHtml(a.subject)}</strong><p>${escapeHtml(a.text)}</p></div>`).join(""); if (!advice.children.length) advice.append(empty());
  const medals = $("#medals"); medals.innerHTML = (c.medals || []).map(m => `<label class="check-row"><input type="checkbox" data-medal="${m.number}" ${m.found ? "checked" : ""}><span class="check-text"><strong>#${m.number} ${escapeHtml(m.location)}</strong><br>${escapeHtml(m.detail)}</span></label>`).join(""); if (!medals.children.length) medals.append(empty());
  const monsters = $("#monsters"); monsters.innerHTML = (c.monsters || []).map(m => `<label class="check-row"><input type="checkbox" data-monster-id="${escapeHtml(m.id)}" ${m.defeated ? "checked" : ""}><span class="check-text"><strong>${escapeHtml(m.name || `Monster #${m.ordinal}`)}</strong><br>${escapeHtml(m.location || "")}${m.drop ? ` · ${escapeHtml(m.drop)}` : ""}</span></label>`).join(""); if (!monsters.children.length) monsters.append(empty());
  $("#safeCondition").textContent = c.safe_condition || "Not yet verified.";
  renderSources(c.sources || []);
}

function renderProgress() {
  const p = state.progress || {};
  renderCards($("#progressCards"), ["actions", "medals", "items", "monsters", "vocations", "achievements"].map(key => ({ label: key[0].toUpperCase() + key.slice(1), value: p[key]?.display ?? p[key] ?? "Unknown" })));
  const open = $("#openWork"); open.innerHTML = (p.open_work || []).map(x => `<div class="advice-item"><strong>${escapeHtml(x.title)}</strong><p>${escapeHtml(x.detail)}</p></div>`).join(""); if (!open.children.length) open.append(empty());
}
function renderSources(sources = state.checkpoint?.sources || []) {
  const target = $("#sourceList"); target.innerHTML = sources.map(s => `<div class="source-item"><a href="${escapeHtml(s.url)}" target="_blank" rel="noreferrer">${escapeHtml(s.title)}</a><br><span class="muted">${escapeHtml(s.locator || "")}</span></div>`).join(""); if (!target.children.length) target.append(empty());
  const conflicts = $("#conflicts"); conflicts.innerHTML = state.conflicts.map(c => `<div class="conflict-item"><strong>${escapeHtml(c.subject)}</strong><p>${escapeHtml(c.summary)}</p><span class="tag">${escapeHtml(c.status || "unresolved")}</span></div>`).join(""); if (!conflicts.children.length) conflicts.append(empty());
}

async function loadCheckpoint(id) {
  setStatus("Loading checkpoint…");
  state.checkpoint = await api(`/checkpoints/${encodeURIComponent(id)}`); renderCheckpoint(); setStatus("");
}
async function loadAll() {
  setStatus("Loading guide…");
  [state.dashboard, state.checkpoints, state.progress, state.conflicts] = await Promise.all([api("/dashboard"), api("/checkpoints"), api("/progress"), api("/conflicts")]);
  renderDashboard(); renderProgress();
  const select = $("#checkpointSelect"); select.innerHTML = state.checkpoints.map(c => `<option value="${escapeHtml(c.id)}">${String(c.sequence).padStart(2,"0")} · ${escapeHtml(c.name)}</option>`).join("");
  const current = state.dashboard?.checkpoint?.id || state.checkpoints[0]?.id; if (current) { select.value = current; await loadCheckpoint(current); }
  setStatus("");
}
async function updateProgress(payload) {
  setStatus("Saving…"); await api("/progress", { method: "PATCH", body: JSON.stringify(payload) }); await loadAll(); setStatus("Saved");
}

document.addEventListener("click", event => {
  const nav = event.target.closest("[data-view]"); if (nav) { event.preventDefault(); showView(nav.dataset.view); }
});
$("#menuButton").addEventListener("click", () => { const open = $("#primaryNav").classList.toggle("open"); $("#menuButton").setAttribute("aria-expanded", String(open)); });
$("#refreshButton").addEventListener("click", () => loadAll().catch(handleError));
$("#checkpointSelect").addEventListener("change", event => loadCheckpoint(event.target.value).catch(handleError));
document.addEventListener("change", event => {
  if (event.target.dataset.actionId) updateProgress({ kind: "action", id: event.target.dataset.actionId, completed: event.target.checked }).catch(handleError);
  if (event.target.dataset.medal) updateProgress({ kind: "medal", id: Number(event.target.dataset.medal), completed: event.target.checked }).catch(handleError);
  if (event.target.dataset.monsterId) updateProgress({ kind: "monster", id: event.target.dataset.monsterId, completed: event.target.checked }).catch(handleError);
});
function handleError(error) { console.error(error); setStatus(`Could not load guide: ${error.message}`); }
showView(location.hash.slice(1) || "dashboard"); loadAll().catch(handleError);

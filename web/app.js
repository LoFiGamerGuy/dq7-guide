"use strict";

const state = { dashboard: null, checkpoints: [], checkpoint: null, progress: null, equipment: null, conflicts: [], vocations: [], catalogs: {}, domain: null, selectedEntry: null, filter: "all", sourcePublisher: "all", sourceFreshness: "all", requests: 0 };
const domains = {
  items: { title: "Items", singular: "item", progressKind: "item", filters: ["all","weapons","armour","accessories","shields","head","usable items"] },
  vocations: { title: "Vocations", singular: "vocation", progressKind: null, filters: ["all","beginner","intermediate","advanced","character-exclusive"] },
  monsters: { title: "Monsters", singular: "monster", progressKind: "monster", filters: ["all","defeated","open"] },
  hearts: { title: "Monster Hearts", singular: "heart", progressKind: "heart", filters: ["all","available","owned","open","unknown"] },
  missables: { title: "Missables", singular: "missable", progressKind: "missable", filters: ["all","verified","unresolved","collector","major_choice"] },
  farms: { title: "Farms", singular: "farm", progressKind: null, filters: ["all","gold","proficiency","exp","seeds","other"] },
  seeds: { title: "Seed Mechanics", singular: "seed mechanic", progressKind: null, filters: ["all","standard","super","reward"] },
  source_registry: { title: "Sources", singular: "source", progressKind: null, filters: ["all","item","monster","vocation","boss","completion","farming","other"] },
  medals: { title: "Mini Medals", singular: "medal", progressKind: "medal", filters: ["all","found","open"] },
  tablets: { title: "Tablets", singular: "tablet", progressKind: "tablet", filters: ["all","tablet","fragment","found","open"] },
  achievements: { title: "Achievements", singular: "achievement", progressKind: "achievement", filters: ["all","story","completion","combat","unlocked","open"] }
};
const viewTitles = { dashboard: "Dashboard", walkthrough: "Walkthrough", progress: "Progress", sources: "Sources & conflicts" };
const $ = (selector) => document.querySelector(selector);
const empty = () => document.importNode($("#emptyTemplate").content, true);
const escapeHtml = (value = "") => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

async function api(path, options = {}) {
  state.requests += 1; $("#main").setAttribute("aria-busy", "true");
  try {
    const response = await fetch(`/api${path}`, { headers: { "Content-Type": "application/json" }, ...options });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.status === 204 ? null : response.json();
  } finally {
    state.requests -= 1; if (!state.requests) $("#main").removeAttribute("aria-busy");
  }
}

function setStatus(message = "") { const target = $("#status"); target.classList.remove("error"); target.textContent = message; }
function setCurrentRoute(predicate) {
  document.querySelectorAll("[data-view],[data-domain]").forEach(link => { if (predicate(link)) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current"); });
}
function showView(name) {
  state.domain = null;
  document.querySelectorAll(".view").forEach(view => { view.hidden = view.id !== name; });
  setCurrentRoute(link => link.dataset.view === name);
  $("#primaryNav").classList.remove("open"); $("#menuButton").setAttribute("aria-expanded", "false");
  document.title = `${viewTitles[name] || "Guide"} · DQ7 Run Guide`;
  if (location.hash !== `#${name}`) history.replaceState(null, "", `#${name}`);
}
function showDomain(name) {
  state.domain = name; state.filter = "all"; state.sourcePublisher = "all"; state.sourceFreshness = "all"; state.selectedEntry = null;
  document.querySelectorAll(".view").forEach(view => { view.hidden = view.id !== "catalog"; });
  setCurrentRoute(link => link.dataset.domain === name);
  $("#primaryNav").classList.remove("open"); $("#menuButton").setAttribute("aria-expanded", "false");
  history.replaceState(null, "", `#${name}`); $("#catalogSearch").value = "";
  loadDomain(name).catch(handleError);
}

function renderCards(target, cards) {
  target.innerHTML = cards.map(card => `<div class="summary-card"><strong>${escapeHtml(card.value ?? "—")}</strong><span>${escapeHtml(card.label)}</span></div>`).join("");
}
function renderStop(target, warnings = []) {
  target.hidden = !warnings.length; target.textContent = warnings.join(" ");
}
function renderChecks(target, actions = [], hideCompleted = false) {
  target.replaceChildren();
  const visible = hideCompleted ? actions.filter(action => !action.completed) : actions;
  if (!visible.length) return target.append(empty());
  visible.forEach(action => {
    const label = document.createElement("label"); label.className = `check-row${action.completed ? " completed" : ""}${action.is_next ? " next-action" : ""}`;
    label.innerHTML = `<input type="checkbox" ${action.completed ? "checked" : ""} data-action-id="${escapeHtml(action.id)}"><span class="check-text"><strong>${action.is_next ? '<span class="tag">Next</span> ' : ""}${escapeHtml(action.title || action.subject)}</strong><br>${escapeHtml(action.action || "")}</span>`;
    target.append(label);
  });
}

function renderStopActions(target, actions = []) {
  target.hidden = !actions.length;
  target.replaceChildren();
  if (!actions.length) return;
  const heading = document.createElement("strong"); heading.textContent = "STOP — clear before advancing"; target.append(heading);
  actions.forEach(action => {
    const label = document.createElement("label"); label.className = "check-row stop-check";
    label.innerHTML = `<input type="checkbox" data-action-id="${escapeHtml(action.id)}"><span class="check-text"><strong>${escapeHtml(action.title)}</strong><br>${escapeHtml(action.action)}</span>`;
    target.append(label);
  });
}

function compactApplicability(value) {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value !== "object") return String(value);
  return Object.entries(value).filter(([key]) => key !== "tradeoff").map(([key, item]) => `${key.replaceAll("_", " ")}: ${typeof item === "object" ? JSON.stringify(item) : item}`).join(" · ");
}

function renderDashboard() {
  const d = state.dashboard || {};
  renderStop($("#stopBanner"), d.stop_warnings || []);
  renderCards($("#summaryCards"), [
    { label: d.checkpoint?.is_saved ? "Saved checkpoint" : "Guide preview", value: d.checkpoint?.name || "Unknown" },
    { label: "Mini Medals", value: d.progress?.medals ?? "Unknown" },
    { label: "Hoarder items", value: d.progress?.items ?? "Unknown" },
    { label: "Monsters", value: d.progress?.monsters ?? "Unknown" }
  ]);
  renderChecks($("#nextActions"), d.next_actions || []);
}

function renderCheckpoint() {
  const c = state.checkpoint || {};
  const index = state.checkpoints.findIndex(row => row.id === c.id);
  $("#previousCheckpoint").disabled = index <= 0;
  $("#nextCheckpoint").disabled = index < 0 || index >= state.checkpoints.length - 1;
  $("#checkpointMeta").textContent = [c.name, c.time_period, c.region].filter(Boolean).join(" · ");
  renderStopActions($("#checkpointStop"), c.stop_actions || []);
  renderChecks($("#actions"), c.actions || [], $("#hideCompleted").checked);
  $("#actionCount").textContent = `${(c.actions || []).filter(a => !a.completed).length} open`;
  const advice = $("#advice"), adviceGroups = [
    ["completion_safe", "Completion-safe"],
    ["strongest_now", "Strongest now"],
    ["optional_grind", "Optional grind"]
  ];
  advice.innerHTML = adviceGroups.map(([group, label]) => {
    const rows = (c.advice || []).filter(a => a.decision_group === group);
    if (!rows.length) return "";
    return `<section class="advice-group" aria-labelledby="advice-${group}"><h4 id="advice-${group}">${label}</h4>${rows.map(a => { const applies = compactApplicability(a.applicability), saved = a.saved_state_applicability || { status: "unknown", reason: "Saved-state check unavailable" }, checked = saved.reason !== "No supported saved-state gate"; return `<div class="advice-item"><span class="tag goal-${escapeHtml(a.goal)}">${escapeHtml(a.type)} · ${escapeHtml(a.goal.replaceAll("_", " "))}</span>${checked ? `<span class="tag applicability-${escapeHtml(saved.status)}">${escapeHtml(saved.status === "satisfied" ? "State: met" : saved.status === "unmet" ? "State: unmet" : "State: unknown")}</span>` : ""}<strong>${escapeHtml(a.subject)}</strong><p>${escapeHtml(a.text)}</p><details class="advice-evidence"><summary>When, tradeoff & source</summary>${checked ? `<p><strong>Saved state:</strong> ${escapeHtml(saved.reason)}</p>` : ""}${applies ? `<p><strong>Applies:</strong> ${escapeHtml(applies)}</p>` : ""}${a.tradeoff ? `<p><strong>Tradeoff:</strong> ${escapeHtml(a.tradeoff)}</p>` : ""}<p><a href="${escapeHtml(a.source?.url || "#")}" target="_blank" rel="noreferrer">${escapeHtml(a.source?.title || "Source")}</a><br><span class="muted">${escapeHtml(a.source?.locator || "Locator unavailable")}</span></p><p class="muted">${escapeHtml(a.confidence || "unknown")} confidence · ${escapeHtml(a.verification_status || "status unknown")}</p></details></div>`; }).join("")}</section>`;
  }).join(""); if (!advice.children.length) advice.append(empty());
  const fragments = c.tablet_fragments || [], checkpointTablets = $("#checkpointTablets");
  $("#tabletFragmentCount").textContent = `${fragments.filter(row => row.found).length}/${fragments.length}`;
  checkpointTablets.innerHTML = fragments.map(row => `<label class="check-row${row.found ? " completed" : ""}"><input type="checkbox" data-tablet-id="${escapeHtml(row.id)}" ${row.found ? "checked" : ""}><span class="check-text"><strong>#${row.ordinal} ${escapeHtml(row.color)} · ${escapeHtml(row.tablet_name)}</strong><br>${escapeHtml(row.location)} · ${escapeHtml(row.detail)}</span></label>`).join(""); if (!checkpointTablets.children.length) checkpointTablets.append(empty());
  const checkpointItems = c.checkpoint_items || [], itemTarget = $("#checkpointItems");
  $("#checkpointItemCount").textContent = `${checkpointItems.filter(row => row.obtained).length}/${checkpointItems.length}`;
  itemTarget.innerHTML = checkpointItems.map(row => `<label class="check-row${row.obtained ? " completed" : ""}"><input type="checkbox" data-item-id="${escapeHtml(row.id)}" ${row.obtained ? "checked" : ""}><span class="check-text"><strong>${escapeHtml(row.name)} · ${escapeHtml(row.category)}</strong><br>${escapeHtml((row.routes || []).map(route => `${route.route_label}${route.is_free === 1 ? " · free" : ""}`).join(" / "))}</span></label>`).join(""); if (!itemTarget.children.length) itemTarget.append(empty());
  const checkpointAchievements = c.checkpoint_achievements || [], dueAchievements = checkpointAchievements.filter(row => row.timing === "due_here"), trackingAchievements = checkpointAchievements.filter(row => row.timing === "tracking_starts"), achievementTarget = $("#checkpointAchievements");
  $("#checkpointAchievementCount").textContent = `${dueAchievements.filter(row => row.unlocked).length}/${dueAchievements.length} due`;
  achievementTarget.innerHTML = dueAchievements.map(row => `<label class="check-row${row.unlocked ? " completed" : ""}"><input type="checkbox" data-achievement-id="${escapeHtml(row.id)}" ${row.unlocked ? "checked" : ""}><span class="check-text"><strong>${escapeHtml(row.name)}</strong><br>${escapeHtml(row.description)}</span></label>`).join("");
  if (trackingAchievements.length) achievementTarget.insertAdjacentHTML("beforeend", `<details class="later-medals"><summary>Track from here (${trackingAchievements.length})</summary>${trackingAchievements.map(row => `<div><strong>${escapeHtml(row.name)}</strong><span>${escapeHtml(row.description)} · ${escapeHtml(row.dependency_progress?.known_count ?? "progress unknown")}/${escapeHtml(row.dependency_progress?.required_count ?? "?")}</span></div>`).join("")}</details>`);
  if (!achievementTarget.children.length) achievementTarget.append(empty());
  const checkpointMissables = c.checkpoint_missables || [], missableTarget = $("#checkpointMissables");
  $("#checkpointMissableCount").textContent = `${checkpointMissables.filter(row => row.progress_status === "completed").length}/${checkpointMissables.length}`;
  missableTarget.innerHTML = checkpointMissables.map(row => `<div class="${row.window_status === "unresolved" ? "uncertain-banner" : ""}">${row.window_status === "unresolved" ? '<strong>Cutoff unknown · not a STOP</strong>' : ""}<label class="check-row${row.progress_status === "completed" ? " completed" : ""}"><input type="checkbox" data-missable-id="${escapeHtml(row.missable_id)}" ${row.progress_status === "completed" ? "checked" : ""}><span class="check-text"><strong>${escapeHtml(row.name)}</strong><br>${escapeHtml(row.available_from)}${row.unavailable_after ? ` · before ${escapeHtml(row.unavailable_after)}` : ""}</span></label></div>`).join(""); if (!missableTarget.children.length) missableTarget.append(empty());
  const medals = $("#medals"), availableMedals = (c.medals || []).filter(m => m.timing !== "later"), laterMedals = (c.medals || []).filter(m => m.timing === "later");
  medals.innerHTML = availableMedals.map(m => `<label class="check-row${m.found ? " completed" : ""}"><input type="checkbox" data-medal="${m.number}" ${m.found ? "checked" : ""}><span class="check-text"><strong>${m.timing === "backtrack" ? '<span class="tag">Backtrack</span> ' : ""}#${m.number} ${escapeHtml(m.location)}</strong><br>${escapeHtml(m.detail)}</span></label>`).join("");
  if (laterMedals.length) medals.insertAdjacentHTML("beforeend", `<details class="later-medals"><summary>Later (${laterMedals.length})</summary>${laterMedals.map(m => `<div><strong>#${m.number} ${escapeHtml(m.location)}</strong><span>${escapeHtml(m.available_checkpoint || m.available_from || "Gate unknown")}</span></div>`).join("")}</details>`);
  if (!medals.children.length) medals.append(empty());
  const monsters = $("#monsters"); monsters.innerHTML = (c.monsters || []).map(m => `<label class="check-row"><input type="checkbox" data-monster-id="${escapeHtml(m.id)}" ${m.defeated ? "checked" : ""}><span class="check-text"><strong>${escapeHtml(m.name || `Monster #${m.ordinal}`)}</strong><br>${escapeHtml(m.location || "")}${m.drop ? ` · ${escapeHtml(m.drop)}` : ""}</span></label>`).join(""); if (!monsters.children.length) monsters.append(empty());
  $("#safeCondition").textContent = c.safe_condition || "Not yet verified.";
  const readiness = c.advancement_readiness || {}, labels = { blocked_by_stop: "STOP open", required_actions_open: "Actions open", manual_confirmation: "Confirm manually" };
  $("#advanceStatus").textContent = labels[readiness.status] || "Unknown";
  $("#advanceReason").textContent = readiness.reason || "Readiness is not machine-verifiable.";
  const advanceButton = $("#advanceCheckpointButton"); advanceButton.disabled = !readiness.can_confirm_and_save_next;
  advanceButton.dataset.nextCheckpoint = readiness.next_checkpoint?.id || "";
  advanceButton.textContent = readiness.next_checkpoint ? `Confirm and set ${readiness.next_checkpoint.name}` : "Final checkpoint";
  renderSources(c.sources || []);
}

function renderProgress() {
  const p = state.progress || {};
  renderCards($("#progressCards"), ["actions", "medals", "items", "monsters", "vocations", "achievements"].map(key => ({ label: key[0].toUpperCase() + key.slice(1), value: p[key]?.display ?? p[key] ?? "Unknown" })));
  const open = $("#openWork"); open.innerHTML = (p.open_work || []).map(x => `<div class="advice-item"><strong>${escapeHtml(x.title)}</strong><p>${escapeHtml(x.detail)}</p></div>`).join(""); if (!open.children.length) open.append(empty());
  const saved = state.checkpoints.find(row => row.id === p.saved_checkpoint);
  $("#savedCheckpoint").textContent = saved ? `Saved: ${saved.sequence} · ${saved.name}` : "Checkpoint not recorded";
  const members = p.party || [];
  $("#partyMemberSelect").innerHTML = members.map(member => `<option value="${escapeHtml(member.name)}">${escapeHtml(member.name)}</option>`).join("");
  $("#partyDetailsMember").innerHTML = members.map(member => `<option value="${escapeHtml(member.name)}">${escapeHtml(member.name)}</option>`).join("");
  $("#masteryVocationSelect").innerHTML = state.vocations.map(vocation => `<option value="${escapeHtml(vocation.vocation_id)}" data-exclusive="${escapeHtml(vocation.exclusive_character || "")}">${escapeHtml(vocation.name)}</option>`).join("");
  $("#medalCountInput").value = p.mini_medal_count ?? "";
  syncVocationChoices();
  syncPartyDetails();
  $("#partyState").innerHTML = members.map(member => `<div><strong>${escapeHtml(member.name)}</strong><span>${escapeHtml([member.level ? `Lv ${member.level}` : "level unknown", member.primary_vocation || "vocation unknown", member.secondary_vocation ? `+ ${member.secondary_vocation}` : null, `${member.mastered_vocations.length} mastered`].filter(Boolean).join(" · "))}</span></div>`).join("");
  const equipment = state.equipment || {}, recommendations = equipment.recommendations || [];
  const mechanics = equipment.mechanics || [];
  const coverage = equipment.compatibility_coverage || {};
  $("#equipmentReadiness").innerHTML = `<div class="uncertain-banner"><strong>Equipment editing unavailable</strong><span>${escapeHtml((equipment.gaps || ["Character/item compatibility is not normalized."])[0])}</span></div>${coverage.audited_item_rows ? `<h4>Compatibility evidence</h4><p class="muted">${escapeHtml(`${coverage.verified_item_rows}/${coverage.audited_item_rows} item rows verified by two independent sources · ${coverage.conflicted_item_rows} disputed · ${coverage.single_source_item_rows} single-source`)}</p>` : ""}${mechanics.length ? `<h4>Verified mechanics</h4><div class="detail-list">${mechanics.map(row => `<div><strong>${escapeHtml(row.rule_type === "slot_count" ? `${row.numeric_value} accessory slots` : `Monster Heart uses ${row.numeric_value} accessory slot`)}</strong><span>${escapeHtml(row.applies_to)} · independently corroborated</span>${sourceLink({source_url: row.source_url, source_title: row.source_title, locator: row.locator})}${sourceLink({source_url: row.corroborating_source_url, source_title: row.corroborating_source_title, locator: row.corroborating_locator})}</div>`).join("")}</div>` : ""}${recommendations.length ? `<h4>Strongest-now comparison</h4><div class="detail-list">${recommendations.map(row => `<div><strong>${escapeHtml([row.character, row.slot, row.item_name].filter(Boolean).join(" · "))}</strong><span>${escapeHtml(row.comparison_status.replaceAll("_", " "))} · ownership ${escapeHtml(row.ownership_status)} · ${escapeHtml(row.availability_status.replaceAll("_", " "))} · compatibility ${escapeHtml((row.compatibility_status || "unknown").replaceAll("_", " "))}</span><span>${escapeHtml(row.recommendation)}</span>${sourceLink({source_url: row.source?.url, source_title: row.source?.title, locator: row.source?.locator})}</div>`).join("")}</div><p class="muted">These are attributed checkpoint recommendations; disputed rows remain unvalidated.</p>` : '<p class="muted">No sourced gear recommendation is normalized for the saved checkpoint.</p>'}`;
}
function syncVocationChoices() {
  const character = $("#partyMemberSelect")?.value, select = $("#masteryVocationSelect");
  if (!select) return;
  [...select.options].forEach(option => { option.disabled = Boolean(option.dataset.exclusive && option.dataset.exclusive !== character); });
  if (select.selectedOptions[0]?.disabled) select.value = [...select.options].find(option => !option.disabled)?.value || "";
}
function syncPartyDetails() {
  const character = $("#partyDetailsMember")?.value;
  if (!character) return;
  const member = (state.progress?.party || []).find(row => row.name === character) || {};
  const options = `<option value="unknown">Unknown</option>${state.vocations.filter(vocation => !vocation.exclusive_character || vocation.exclusive_character === character).map(vocation => `<option value="${escapeHtml(vocation.vocation_id)}">${escapeHtml(vocation.name)}</option>`).join("")}`;
  $("#primaryVocationSelect").innerHTML = options; $("#secondaryVocationSelect").innerHTML = options;
  $("#primaryVocationSelect").value = member.primary_vocation || "unknown";
  $("#secondaryVocationSelect").value = member.secondary_vocation || "unknown";
  $("#partyLevelInput").value = member.level ?? "";
}
function renderSources(sources = state.checkpoint?.sources || []) {
  const target = $("#sourceList"); target.innerHTML = sources.map(s => `<div class="source-item"><a href="${escapeHtml(s.url)}" target="_blank" rel="noreferrer">${escapeHtml(s.title)}</a><br><span class="muted">${escapeHtml(s.locator || "")}</span></div>`).join(""); if (!target.children.length) target.append(empty());
  const conflicts = $("#conflicts"); conflicts.innerHTML = state.conflicts.map(c => `<article class="conflict-item"><div class="conflict-heading"><strong>${escapeHtml(c.subject)}</strong><span class="tag">${escapeHtml(c.status || "unresolved")}</span></div><p class="muted">${escapeHtml(c.predicate)} · ${c.status === "resolved" ? "Resolution is identified below." : "No resolution is implied."}</p><div class="claim-grid">${(c.claims || []).map((claim, index) => `<section class="claim-card" aria-label="Claim ${index + 1}"><h4>Claim ${index + 1}${claim.is_resolution ? " · Resolution" : ""}</h4><p>${escapeHtml(typeof claim.value === "string" ? claim.value : JSON.stringify(claim.value))}</p><dl><dt>Scope</dt><dd>${escapeHtml(JSON.stringify(claim.scope || {}))}</dd><dt>Evidence</dt><dd>${escapeHtml(claim.confidence)} · ${escapeHtml(claim.verification_status)}</dd><dt>Freshness</dt><dd>Updated ${escapeHtml(claim.source?.updated_at || "unknown")} · Retrieved ${escapeHtml(claim.source?.retrieved_at || "unknown")}</dd></dl><a href="${escapeHtml(claim.source?.url || "#")}" target="_blank" rel="noreferrer">${escapeHtml(claim.source?.title || "Source")}</a><br><span class="muted">${escapeHtml(claim.locator || "Precise locator not stored")}</span></section>`).join("")}</div>${c.rationale ? `<p class="muted">Recorded rationale: ${escapeHtml(c.rationale)}</p>` : ""}${c.required_evidence ? `<p><strong>Needed to resolve:</strong> ${escapeHtml(c.required_evidence)}</p>` : ""}</article>`).join(""); if (!conflicts.children.length) conflicts.append(empty());
}

function entryName(entry) { return entry.name || entry.title || (entry.number ? `Mini Medal #${entry.number}` : entry.id); }
function entryCategory(entry) { return String(entry.category || entry.type || entry.rank_group || "uncategorized").toLowerCase(); }
function entrySubtitle(entry) { return entry.summary || entry.location || entry.description || entry.requirement || entry.checkpoint || ""; }
function matchesFilter(entry) {
  if (state.domain === "source_registry" && state.sourcePublisher !== "all" && entry.publisher !== state.sourcePublisher) return false;
  if (state.domain === "source_registry" && state.sourceFreshness !== "all" && entry.retrieval_band !== state.sourceFreshness) return false;
  if (state.filter === "all") return true;
  if (["verified", "unresolved"].includes(state.filter)) return entry.window_status === state.filter;
  if (["found", "unlocked", "defeated"].includes(state.filter)) return entry.completed === true;
  if (state.filter === "open") return entry.completed !== true;
  return entryCategory(entry) === state.filter;
}
function renderCatalog() {
  const config = domains[state.domain], rows = state.catalogs[state.domain] || [];
  $("#catalogTitle").textContent = config.title; document.title = `${config.title} · DQ7 Run Guide`;
  $("#catalogFilters").innerHTML = config.filters.map(value => `<button class="filter-button" type="button" data-filter="${escapeHtml(value)}" aria-pressed="${state.filter === value}">${escapeHtml(value)}</button>`).join("");
  if (state.domain === "source_registry") {
    const publishers = [...new Set(rows.map(row => row.publisher))].sort();
    $("#catalogFilters").insertAdjacentHTML("beforeend", `<label class="compact-filter">Publisher <select id="sourcePublisher"><option value="all">All</option>${publishers.map(value => `<option value="${escapeHtml(value)}" ${state.sourcePublisher === value ? "selected" : ""}>${escapeHtml(value)}</option>`).join("")}</select></label><label class="compact-filter">Retrieved <select id="sourceFreshness"><option value="all">Any date</option><option value="within_180_days" ${state.sourceFreshness === "within_180_days" ? "selected" : ""}>Within 180 days</option><option value="over_180_days" ${state.sourceFreshness === "over_180_days" ? "selected" : ""}>Over 180 days</option><option value="unknown" ${state.sourceFreshness === "unknown" ? "selected" : ""}>Unknown</option></select></label>`);
  }
  const term = $("#catalogSearch").value.trim().toLowerCase();
  const visible = rows.filter(row => matchesFilter(row) && (!term || JSON.stringify(row).toLowerCase().includes(term)));
  $("#catalogCount").textContent = `${visible.length} of ${rows.length}`;
  const list = $("#catalogList"); list.innerHTML = visible.map(row => `<button class="catalog-card" type="button" data-entry-id="${escapeHtml(row.id)}" aria-current="${state.selectedEntry?.id === row.id}"><strong>${escapeHtml(entryName(row))}</strong><span class="tag">${escapeHtml(entryCategory(row))}</span><span class="muted">${escapeHtml(entrySubtitle(row))}</span></button>`).join(""); if (!visible.length) list.append(empty());
  renderDetail();
}
function renderDetail() {
  const target = $("#catalogDetail"), entry = state.selectedEntry, config = domains[state.domain];
  if (!entry) { target.innerHTML = '<p class="empty">Choose an entry for details.</p>'; return; }
  const omitted = new Set(["id","name","title","completed","source","sources","url"]);
  const fields = Object.entries(entry).filter(([key,value]) => !omitted.has(key) && value !== null && value !== "" && typeof value !== "object").slice(0, 10);
  const source = entry.source || entry.sources?.[0];
  const progressKind = entry.progress_kind === null || (state.domain === "tablets" && entryCategory(entry) === "tablet") ? null : (entry.progress_kind || config.progressKind);
  target.innerHTML = `<p class="eyebrow">${escapeHtml(config.singular)}</p><h3>${escapeHtml(entryName(entry))}</h3><dl>${fields.map(([k,v]) => `<dt>${escapeHtml(k.replaceAll("_"," "))}</dt><dd>${escapeHtml(v)}</dd>`).join("")}</dl>${source ? `<p><a href="${escapeHtml(source.url || entry.url || "#")}" target="_blank" rel="noreferrer">${escapeHtml(source.title || "Source")}</a><br><span class="muted">${escapeHtml(source.locator || "")}</span></p>` : ""}${progressKind ? `<label class="progress-toggle"><input type="checkbox" data-catalog-progress="${progressKind}" data-progress-id="${escapeHtml(entry.id)}" ${entry.completed ? "checked" : ""}> Explicitly mark ${config.singular} complete</label>` : `<p class="muted">This entry needs its dedicated player workflow; generic updates are disabled.</p>`}`;
}
function sourceLink(row) {
  if (!row?.source_url) return row?.locator ? `<span class="muted">${escapeHtml(row.locator)}</span>` : "";
  return `<a href="${escapeHtml(row.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(row.source_title || "Source")}</a><br><span class="muted">${escapeHtml(row.locator || "")}</span>`;
}
function renderRichDetail(detail, summary) {
  const target = $("#catalogDetail");
  if (state.domain === "items") {
    const item = detail.item, routes = detail.routes || [];
    target.innerHTML = `<p class="eyebrow">Item · ${escapeHtml(item.category_name || summary.category)}</p><h3>${escapeHtml(item.name)}</h3><p><span class="tag">${item.heroic_hoarder_required ? "Hoarder" : "Optional"}</span> ${escapeHtml(item.confidence || "")}</p><h4>Get it</h4><div class="detail-list">${routes.map(route => `<div><strong>${escapeHtml(route.route_label)}</strong><span>${escapeHtml([route.location_text, route.time_period, route.available_checkpoint].filter(Boolean).join(" · "))}</span><span>${route.is_free === 1 || (route.method === "lucky_panel" && route.panel_system_entry_cost === 0) ? "Free entry" : route.price ? `${route.price} ${escapeHtml(route.currency || "gold")}` : escapeHtml(route.supply_type || "")}</span>${sourceLink(route)}${route.method === "lucky_panel" && route.panel_system_entry_cost === 0 ? `<a href="${escapeHtml(route.panel_cost_source_url)}" target="_blank" rel="noreferrer">Free-entry evidence</a><br><span class="muted">${escapeHtml(route.panel_cost_locator)} · independently corroborated</span>` : ""}</div>`).join("") || '<p class="empty">No verified route yet.</p>'}</div><label class="progress-toggle"><input type="checkbox" data-catalog-progress="item" data-progress-id="${escapeHtml(item.item_id)}" ${item.obtained ? "checked" : ""}> Explicitly mark obtained</label>`;
  } else if (state.domain === "vocations") {
    const vocation = detail.vocation, skills = detail.skills || [], perks = detail.perks || [], requirements = detail.requirements || [];
    const moon = detail.moonlighting || {}, unlock = moon.unlock?.value || {}, mechanics = moon.mechanics?.value || {};
    const plan = detail.unlock_progress || {}, groups = plan.groups || [], partyProgress = plan.party_progress || [], recursivePlans = plan.recursive_plans || [];
    const unlockPlan = groups.length ? `<h4>Unlock path</h4>${groups.map(group => `<div class="callout"><strong>${group.rule === "all_of" ? "Master all" : `Master any ${group.required_count}`}</strong><span>${escapeHtml(group.candidates.map(row => row.name).join(" · "))}</span>${sourceLink(group)}</div>`).join("")}<div class="detail-list">${partyProgress.map(member => { const needed = Math.max(...member.groups.map(group => group.needed_if_unknowns_are_unmastered), 0); return `<div><strong>${escapeHtml(member.party_member)} · ${member.status}</strong><span>${member.status === "satisfied" ? "Direct prerequisites explicitly mastered" : `${needed} still needed if unrecorded masteries are not complete`}</span></div>`; }).join("")}</div><p class="muted">Mastery cost: unknown. Missing records stay unknown.</p>` : '<p class="muted">No prerequisite vocations.</p>';
    const recursive = recursivePlans.length ? `<h4>Next mastery options</h4><div class="detail-list">${recursivePlans.map(member => `<div><strong>${escapeHtml(member.character)} · ${escapeHtml(member.status.replaceAll("_", " "))}</strong><span>${escapeHtml((member.next_options || []).map(row => row.name).join(" · ") || "No next option derived from explicit mastery")}</span></div>`).join("")}</div><p class="muted">Full prerequisite tree is evaluated. Alternative branches are all shown and unranked; costs remain unknown.</p>` : "";
    target.innerHTML = `<p class="eyebrow">${escapeHtml(vocation.tier)} vocation</p><h3>${escapeHtml(vocation.name)}</h3>${vocation.exclusive_character ? `<p class="tag">${escapeHtml(vocation.exclusive_character)} only</p>` : ""}${perks.map(perk => `<div class="callout"><strong>${escapeHtml(perk.perk_name)}</strong><span>${escapeHtml(perk.perk_description)}</span>${sourceLink(perk)}</div>`).join("")}${unlockPlan}${recursive}<h4>Moonlighting</h4><div class="callout"><strong>Unlock: cp012 after Aishe</strong><span>${escapeHtml(unlock.activation || "Exact activation not normalized")}. ${escapeHtml((mechanics.published_behavior || []).join("; "))}.</span>${sourceLink(moon.unlock || {})}</div>${moon.venue_status === "conflicting_sources" ? '<div class="uncertain-banner"><strong>Activation venue conflict</strong><span>Game8 says Alltrades Abbey; RPG Site says Shrine of Mysteries. Follow the cp012 story prompts; resolution remains open.</span></div>' : ""}<p class="muted">Unknown: ${escapeHtml((mechanics.unknown_restrictions || []).join("; ") || "restrictions not normalized")}. Pairing advice is not a legal-pairing rule.</p><h4>Skills</h4><ol class="skill-list">${skills.map(skill => `<li><strong>${skill.proficiency_rank}★ ${escapeHtml(skill.skill_name)}</strong><span>${escapeHtml(skill.skill_description)}</span>${sourceLink(skill)}</li>`).join("") || '<li class="empty">No skill rows.</li>'}</ol><p class="muted">Mastered by: ${escapeHtml((detail.mastered_by || []).join(", ") || "nobody recorded")}</p>`;
  } else if (state.domain === "monsters") {
    const monster = detail.monster, encounters = detail.encounters || [], drops = detail.drops || [];
    const stats = [["HP",monster.hp],["Attack",monster.strength],["Defence",monster.defence],["EXP",monster.experience],["Vocation EXP",monster.vocation_experience],["Gold",monster.gold]].filter(([,v]) => v !== null && v !== undefined);
    target.innerHTML = `<p class="eyebrow">Monster #${escapeHtml(monster.source_ordinal)}</p><h3>${escapeHtml(monster.english_name || summary.name)}</h3><dl>${stats.map(([k,v]) => `<dt>${k}</dt><dd>${escapeHtml(v)}</dd>`).join("")}</dl><h4>Where</h4><div class="detail-list">${encounters.map(row => `<div><strong>${escapeHtml(row.location || row.location_text)}</strong><span>${escapeHtml([row.time_period, row.checkpoint_name].filter(Boolean).join(" · "))}</span>${sourceLink(row)}</div>`).join("") || '<p class="empty">No verified encounter route.</p>'}</div><h4>Drops</h4><div class="detail-list">${drops.map(row => `<div><strong>${escapeHtml(row.item_name || row.drop_name || row.item_id)}</strong><span>${escapeHtml(row.drop_type || "Verified drop")}</span>${sourceLink(row)}</div>`).join("") || '<p class="empty">No verified drops.</p>'}</div>${sourceLink(monster)}<label class="progress-toggle"><input type="checkbox" data-catalog-progress="monster" data-progress-id="${escapeHtml(monster.monster_id)}" ${detail.defeated ? "checked" : ""}> Explicitly mark defeated</label>`;
  } else if (state.domain === "hearts") {
    const routes = detail.routes || [];
    const ownershipNote = detail.ownership_status === "unknown" ? "Ownership unreported. Checking this starts the explicit Heart ledger; it does not infer other Hearts." : "Only explicit saved ownership is shown.";
    target.innerHTML = `<p class="eyebrow">Monster Heart</p><h3>${escapeHtml(detail.name)}</h3><div class="callout"><strong>Effect</strong><span>${escapeHtml(detail.effect_text)}</span></div><h4>Earliest verified gate</h4><p>${escapeHtml(detail.available_checkpoint || "Unknown")}${detail.availability_notes ? `<br><span class="muted">${escapeHtml(detail.availability_notes)}</span>` : ""}</p><h4>Get it</h4><div class="detail-list">${routes.map(route => `<div><strong>${escapeHtml(route.route_label)}</strong><span>${escapeHtml([route.location_text, route.time_period, route.available_checkpoint].filter(Boolean).join(" · "))}</span><span>${route.method === "drop" ? "Drop rate unknown" : escapeHtml(route.method)}</span>${sourceLink(route)}${route.dlc_scope_status === "unknown" ? '<span>DLC scope unknown</span>' : ""}</div>`).join("") || '<p class="empty">No acquisition route normalized yet.</p>'}</div><h4>Effect source</h4><p>${sourceLink(detail)}</p><label class="progress-toggle"><input type="checkbox" data-catalog-progress="heart" data-progress-id="${escapeHtml(detail.heart_id)}" ${detail.owned === true ? "checked" : ""}> Explicitly mark owned</label><p class="muted">${escapeHtml(ownershipNote)} Unknown rates and DLC scope are not inferred.</p>`;
  } else if (state.domain === "missables") {
    const unresolved = detail.window_status !== "verified";
    target.innerHTML = `<p class="eyebrow">${escapeHtml(detail.severity)} missable</p><h3>${escapeHtml(detail.name)}</h3>${unresolved ? `<div class="uncertain-banner"><strong>Exact cutoff unknown</strong><span>${escapeHtml(detail.window_gap_reason || "Do not use this row as a STOP warning yet.")}</span></div>` : '<span class="tag">Verified window</span>'}<h4>Window</h4><dl><dt>From</dt><dd>${escapeHtml(detail.available_from || "Unknown")}</dd><dt>Until</dt><dd>${escapeHtml(detail.unavailable_after || "Unknown — complete promptly")}</dd></dl><h4>Consequence</h4><p>${escapeHtml(detail.consequence)}</p><p><a href="${escapeHtml(detail.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(detail.source_title)}</a><br><span class="muted">${detail.locator ? escapeHtml(detail.locator) : "Precise locator not yet stored"}</span></p><p class="muted">Confidence: ${escapeHtml(detail.confidence)} · ${escapeHtml(detail.verification_status)}</p><label class="progress-toggle"><input type="checkbox" data-catalog-progress="missable" data-progress-id="${escapeHtml(detail.missable_id)}" ${detail.progress_status === "completed" ? "checked" : ""}> Explicitly mark completed</label>`;
  } else if (state.domain === "farms") {
    const strategySource = detail.strategy_source_url ? `<br><a href="${escapeHtml(detail.strategy_source_url)}" target="_blank" rel="noreferrer">Strategy source</a><br><span class="muted">${escapeHtml(detail.strategy_locator)}</span>` : "";
    target.innerHTML = `<p class="eyebrow">${escapeHtml(detail.farm_type)} farm</p><h3>${escapeHtml(detail.target)}</h3><h4>Sourced facts</h4><dl><dt>Location</dt><dd>${escapeHtml(detail.location)}</dd><dt>Period</dt><dd>${escapeHtml(detail.time_period || "Not restricted")}</dd><dt>Available</dt><dd>${escapeHtml(detail.available_checkpoint || detail.available_from)}</dd><dt>Frequency</dt><dd>${escapeHtml(detail.encounter_rate_text || "Numeric rate unpublished")}</dd></dl>${detail.strategy ? `<div class="callout"><strong>Attributed strategy</strong><span>${escapeHtml(detail.strategy)}</span>${strategySource}</div>` : ""}<p><a href="${escapeHtml(detail.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(detail.source_title)}</a><br><span class="muted">${escapeHtml(detail.locator)}</span></p><p class="muted">Confidence: ${escapeHtml(detail.confidence)} · Numeric rate unpublished. Strategy is a recommendation, not a canonical fact.</p><p class="muted">Read-only: farms do not alter player progress.</p>`;
  } else if (state.domain === "source_registry") {
    target.innerHTML = `<p class="eyebrow">${escapeHtml(detail.source_class)}</p><h3>${escapeHtml(detail.title)}</h3><p><a href="${escapeHtml(detail.url)}" target="_blank" rel="noreferrer">Open source</a></p><dl><dt>Publisher</dt><dd>${escapeHtml(detail.publisher)}</dd><dt>Role</dt><dd>${escapeHtml(detail.role)}</dd><dt>Published</dt><dd>${escapeHtml(detail.published_at || "Unknown")}</dd><dt>Updated</dt><dd>${escapeHtml(detail.updated_at || "Unknown")}</dd><dt>Retrieved</dt><dd>${escapeHtml(detail.retrieved_at || "Unknown")}</dd><dt>Status</dt><dd>${escapeHtml(detail.status)}</dd></dl><div class="callout"><strong>Freshness means retrieval only</strong><span>${detail.retrieval_age_days === null ? "Retrieval age is unknown." : `${escapeHtml(detail.retrieval_age_days)} days since retrieval.`} An update date does not prove that every claim is current.</span></div>${detail.notes ? `<p class="muted">${escapeHtml(detail.notes)}</p>` : ""}<p class="muted">Read-only registry.</p>`;
  } else if (state.domain === "achievements") {
    const dependency = detail.dependency_progress || {};
    const count = dependency.known_count === null || dependency.known_count === undefined
      ? `? / ${escapeHtml(dependency.required_count ?? detail.required_count ?? "?")}`
      : `${escapeHtml(dependency.known_count)} / ${escapeHtml(dependency.required_count ?? detail.required_count)}`;
    const label = dependency.status === "complete" ? "Unlocked"
      : dependency.status === "target_met" ? "Requirement met · unlock unrecorded"
      : dependency.status === "partial" ? "Explicit partial progress" : "Progress unknown";
    target.innerHTML = `<p class="eyebrow">${escapeHtml(detail.category)} achievement</p><h3>${escapeHtml(detail.name)}</h3><div class="${dependency.status === "unknown" ? "uncertain-banner" : "callout"}"><strong>${escapeHtml(label)} · ${count}</strong><span>${escapeHtml(dependency.reason || "No dependency status available.")}</span></div><h4>Completion dependency</h4><dl><dt>Requirement</dt><dd>${escapeHtml(detail.description)}</dd><dt>Counter</dt><dd>${escapeHtml(dependency.basis || detail.target_type || "Unknown")}</dd><dt>Earliest</dt><dd>${escapeHtml(detail.earliest_checkpoint_id || "Unknown")}</dd><dt>Completion gate</dt><dd>${escapeHtml(detail.completion_checkpoint_id || "Unknown")}</dd></dl><p>${sourceLink(detail)}</p><p class="muted">Only explicit saved state is counted. Unknown is not zero.</p><label class="progress-toggle"><input type="checkbox" data-catalog-progress="achievement" data-progress-id="${escapeHtml(detail.achievement_id)}" ${detail.unlocked ? "checked" : ""}> Explicitly mark achievement unlocked</label>`;
  } else if (state.domain === "seeds") {
    if (detail.record_type === "effect") {
      target.innerHTML = `<p class="eyebrow">${escapeHtml(detail.variant)} seed</p><h3>${escapeHtml(detail.name)}</h3><div class="callout"><strong>Fixed effect</strong><span>+${escapeHtml(detail.increase_amount)} ${escapeHtml(detail.stat_key.replaceAll("_", " "))}</span></div><dl><dt>Version</dt><dd>${escapeHtml(detail.game_version)}</dd><dt>DLC scope</dt><dd>${escapeHtml(detail.dlc_scope || "Not recorded")}</dd><dt>Confidence</dt><dd>${escapeHtml(detail.confidence)}</dd></dl><p><a href="${escapeHtml(detail.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(detail.source_title)}</a><br><span class="muted">${escapeHtml(detail.locator)}</span></p><p class="muted">Read-only mechanic; inventory is unchanged.</p>`;
    } else {
      target.innerHTML = `<p class="eyebrow">Reward rule</p><h3>${escapeHtml(detail.name)}</h3><div class="uncertain-banner"><strong>Eligible pool unknown</strong><span>The source confirms a random family reward, but not which Super Seeds are eligible.</span></div><dl><dt>Available</dt><dd>${escapeHtml(detail.available_checkpoint || detail.available_from_checkpoint_id || "Unknown")}</dd><dt>Location</dt><dd>${escapeHtml(detail.location_text)}</dd><dt>Trigger</dt><dd>${escapeHtml(detail.trigger_text)}</dd><dt>Quantity</dt><dd>${escapeHtml(detail.reward_quantity ?? "Unknown")}</dd><dt>Selection</dt><dd>${escapeHtml(detail.selection_method)}</dd><dt>Repeatable</dt><dd>${detail.repeatable ? "Yes" : "No"}</dd><dt>DLC scope</dt><dd>${escapeHtml(detail.dlc_scope || "Not recorded")}</dd></dl><p><a href="${escapeHtml(detail.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(detail.source_title)}</a><br><span class="muted">${escapeHtml(detail.locator)}</span></p><p class="muted">Read-only reward rule.</p>`;
    }
  }
}
async function selectCatalogEntry(id) {
  const domain = state.domain, summary = (state.catalogs[domain] || []).find(row => String(row.id) === String(id));
  state.selectedEntry = summary; renderCatalog();
  if (!["items", "vocations", "monsters", "hearts", "missables", "farms", "source_registry", "seeds", "achievements"].includes(domain)) return;
  const target = $("#catalogDetail"); target.setAttribute("aria-busy", "true"); target.innerHTML = '<p class="empty">Loading details…</p>';
  try { const endpoint = domain === "hearts" ? "monster-hearts" : domain === "source_registry" ? "sources" : domain; const detail = await api(`/${endpoint}/${encodeURIComponent(id)}`); if (state.domain === domain && String(state.selectedEntry?.id) === String(id)) renderRichDetail(detail, summary); }
  catch (error) { target.innerHTML = '<p class="empty">Details unavailable. List data is still available.</p>'; console.error(error); }
  finally { if (state.domain === domain && String(state.selectedEntry?.id) === String(id)) target.removeAttribute("aria-busy"); }
}
async function loadDomain(name) {
  setStatus(`Loading ${domains[name].title.toLowerCase()}…`);
  if (!state.catalogs[name]) state.catalogs[name] = await loadCatalog(name);
  renderCatalog(); setStatus("");
}

function normalizeEntry(name, row) {
  const entry = { ...row };
  if (name === "items") Object.assign(entry, { id: row.item_id, completed: row.obtained });
  if (name === "vocations") Object.assign(entry, { id: row.vocation_id, category: row.exclusive_character ? "character-exclusive" : row.tier, completed: null });
  if (name === "monsters") Object.assign(entry, { id: row.monster_id, name: row.english_name || `Monster #${row.source_ordinal}`, ordinal: row.source_ordinal, completed: row.defeated });
  if (name === "hearts") Object.assign(entry, { id: row.heart_id, category: row.owned === true ? "owned" : row.available_from_checkpoint_id ? "available" : "unknown", summary: row.effect_text, location: row.available_checkpoint, completed: row.owned, progress_kind: "heart", source: { title: row.source_title, url: row.source_url, locator: row.locator } });
  if (name === "missables") Object.assign(entry, { id: row.missable_id, category: row.severity, summary: row.window_status === "verified" ? `${row.available_from} → ${row.unavailable_after}` : "Window unresolved", completed: row.progress_status === "completed", progress_kind: "missable", source: { title: row.source_title, url: row.source_url, locator: row.locator } });
  if (name === "farms") Object.assign(entry, { id: row.farming_id, name: row.target, category: row.farm_type, summary: row.location, location: row.available_from, completed: null, progress_kind: null, source: { title: row.source_title, url: row.source_url, locator: row.locator } });
  if (name === "source_registry") { const role = row.role.toLowerCase(); const family = ["item","monster","vocation","boss","completion","farm"].find(value => role.includes(value)); Object.assign(entry, { id: row.source_id, name: row.title, category: family === "farm" ? "farming" : (family || "other"), summary: `${row.publisher} · ${row.role}`, completed: null, progress_kind: null }); }
  if (name === "seeds") Object.assign(entry, { id: row.seed_id, name: row.name, category: row.variant, summary: row.record_type === "effect" ? `+${row.increase_amount} ${row.stat_key.replaceAll("_", " ")}` : `${row.selection_method} reward · eligible pool unknown`, completed: null, progress_kind: null });
  if (name === "medals") Object.assign(entry, { id: row.medal_number, number: row.medal_number, name: `Mini Medal #${row.medal_number}`, category: row.found ? "found" : "open", checkpoint: row.available_checkpoint_id || row.checkpoint_id, completed: row.found });
  if (name === "tablets") Object.assign(entry, { id: row.fragment_id, name: `${row.tablet_name}: ${row.fragment_id}`, category: row.found ? "found" : "fragment", checkpoint: row.checkpoint_id, completed: row.found, progress_kind: "tablet" });
  if (name === "achievements") Object.assign(entry, { id: row.achievement_id, title: row.name, completed: row.unlocked });
  return entry;
}
async function loadCatalog(name) {
  const keys = { items: "items", vocations: "vocations", monsters: "monsters", hearts: "hearts", missables: "missables", farms: "farms", source_registry: "sources", seeds: "seeds", medals: "medals", tablets: "fragments", achievements: "achievements" };
  const paged = ["items", "vocations", "monsters", "hearts", "missables", "farms", "source_registry", "seeds", "achievements"].includes(name);
  let rows = [], offset = 0;
  do {
    const endpoint = name === "hearts" ? "monster-hearts" : name === "source_registry" ? "sources" : name;
    const payload = await api(`/${endpoint}${paged ? `?limit=200&offset=${offset}` : ""}`);
    const batch = payload[keys[name]] || [];
    rows.push(...batch);
    if (!paged || batch.length < 200) break;
    offset += batch.length;
  } while (true);
  return rows.map(row => normalizeEntry(name, row));
}

async function loadCheckpoint(id) {
  setStatus("Loading checkpoint…");
  state.checkpoint = await api(`/checkpoints/${encodeURIComponent(id)}`); renderCheckpoint(); setStatus("");
}
async function stepCheckpoint(delta) {
  const select = $("#checkpointSelect"), next = select.selectedIndex + delta;
  if (next < 0 || next >= select.options.length) return;
  select.selectedIndex = next;
  await loadCheckpoint(select.value);
}
async function loadAll() {
  setStatus("Loading guide…");
  const vocationRequest = state.vocations.length ? Promise.resolve(null) : api("/vocations?limit=200");
  const loaded = await Promise.all([api("/dashboard"), api("/checkpoints"), api("/progress"), api("/equipment"), api("/conflicts?include_resolved=1"), vocationRequest]);
  [state.dashboard, state.checkpoints, state.progress, state.equipment, state.conflicts] = loaded;
  if (loaded[5]) state.vocations = loaded[5].vocations || [];
  renderDashboard(); renderProgress();
  const savedCheckpoint = state.dashboard?.checkpoint?.is_saved ? state.dashboard.checkpoint.id : null;
  const select = $("#checkpointSelect"); select.innerHTML = state.checkpoints.map(c => `<option value="${escapeHtml(c.id)}">${String(c.sequence).padStart(2,"0")} · ${escapeHtml(c.name)}${c.id === savedCheckpoint ? " (saved)" : ""}</option>`).join("");
  const current = state.dashboard?.checkpoint?.id || state.checkpoints[0]?.id; if (current) { select.value = current; await loadCheckpoint(current); }
  setStatus("");
}
async function updateProgress(payload) {
  setStatus("Saving…");
  const resources = { item: "items", tablet: "tablets", achievement: "achievements", missable: "missables", heart: "monster-hearts" };
  const endpoint = resources[payload.kind] ? `/${resources[payload.kind]}/${encodeURIComponent(payload.id)}` : "/progress";
  const body = endpoint === "/progress" ? payload : { completed: payload.completed };
  await api(endpoint, { method: "PATCH", body: JSON.stringify(body) });
  const activeDomain = state.domain; if (activeDomain) delete state.catalogs[activeDomain];
  await loadAll(); if (activeDomain) await loadDomain(activeDomain); setStatus("Saved");
}
async function saveToggle(control, payload) {
  const requested = control.checked;
  control.disabled = true;
  try { await updateProgress(payload); }
  catch (error) {
    console.error(error);
    if (control.isConnected) control.checked = !requested;
    const target = $("#status");
    target.classList.add("error");
    target.textContent = "Save failed. Change was not recorded.";
  } finally { if (control.isConnected) control.disabled = false; }
}
async function recordCommand(command, values) {
  setStatus("Saving explicit state…");
  await api("/progress", { method: "POST", body: JSON.stringify({ command, values }) });
  await loadAll(); setStatus("Saved");
}

document.addEventListener("click", event => {
  const nav = event.target.closest("[data-view]"); if (nav) { event.preventDefault(); showView(nav.dataset.view); $("#main").focus(); }
  const domain = event.target.closest("[data-domain]"); if (domain) { event.preventDefault(); showDomain(domain.dataset.domain); $("#main").focus(); }
  const filter = event.target.closest("[data-filter]"); if (filter) { state.filter = filter.dataset.filter; renderCatalog(); }
  const card = event.target.closest("[data-entry-id]"); if (card) selectCatalogEntry(card.dataset.entryId);
  if (event.target.closest("[data-retry]")) { if (state.domain) loadDomain(state.domain).catch(handleError); else loadAll().catch(handleError); }
});
$("#menuButton").addEventListener("click", () => { const open = $("#primaryNav").classList.toggle("open"); $("#menuButton").setAttribute("aria-expanded", String(open)); });
$("#refreshButton").addEventListener("click", () => loadAll().catch(handleError));
$("#checkpointSelect").addEventListener("change", event => loadCheckpoint(event.target.value).catch(handleError));
$("#previousCheckpoint").addEventListener("click", () => stepCheckpoint(-1).catch(handleError));
$("#nextCheckpoint").addEventListener("click", () => stepCheckpoint(1).catch(handleError));
$("#setCheckpointButton").addEventListener("click", async () => {
  const id = $("#checkpointSelect").value;
  try { setStatus("Saving checkpoint…"); await api(`/checkpoints/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ selected: true }) }); await loadAll(); setStatus("Checkpoint saved"); }
  catch (error) { handleError(error); }
});
$("#advanceCheckpointButton").addEventListener("click", async event => {
  const id = event.currentTarget.dataset.nextCheckpoint;
  if (!id || !state.checkpoint?.advancement_readiness?.can_confirm_and_save_next) return;
  try { setStatus("Saving explicit advancement…"); await api(`/checkpoints/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ selected: true }) }); await loadAll(); setStatus("Checkpoint advanced"); }
  catch (error) { handleError(error); }
});
$("#hideCompleted").addEventListener("change", renderCheckpoint);
$("#partyMemberSelect").addEventListener("change", syncVocationChoices);
$("#partyDetailsMember").addEventListener("change", syncPartyDetails);
$("#medalCountForm").addEventListener("submit", event => { event.preventDefault(); recordCommand("medal-count", [$("#medalCountInput").value]).catch(handleError); });
$("#vocationMasteryForm").addEventListener("submit", event => { event.preventDefault(); recordCommand($("#masteryAction").value, [$("#partyMemberSelect").value, $("#masteryVocationSelect").value]).catch(handleError); });
$("#partyDetailsForm").addEventListener("submit", async event => { event.preventDefault(); const values = { character: $("#partyDetailsMember").value, level: $("#partyLevelInput").value || "unknown", primary: $("#primaryVocationSelect").value, secondary: $("#secondaryVocationSelect").value }; try { await recordCommand("party-level", [values.character, values.level]); await recordCommand("party-vocations", [values.character, values.primary, values.secondary]); } catch (error) { handleError(error); } });
document.addEventListener("change", event => {
  if (event.target.id === "sourcePublisher") { state.sourcePublisher = event.target.value; renderCatalog(); return; }
  if (event.target.id === "sourceFreshness") { state.sourceFreshness = event.target.value; renderCatalog(); return; }
  if (event.target.dataset.actionId) saveToggle(event.target, { kind: "action", id: event.target.dataset.actionId, completed: event.target.checked });
  if (event.target.dataset.medal) saveToggle(event.target, { kind: "medal", id: Number(event.target.dataset.medal), completed: event.target.checked });
  if (event.target.dataset.tabletId) saveToggle(event.target, { kind: "tablet", id: event.target.dataset.tabletId, completed: event.target.checked });
  if (event.target.dataset.itemId) saveToggle(event.target, { kind: "item", id: event.target.dataset.itemId, completed: event.target.checked });
  if (event.target.dataset.achievementId) saveToggle(event.target, { kind: "achievement", id: event.target.dataset.achievementId, completed: event.target.checked });
  if (event.target.dataset.missableId) saveToggle(event.target, { kind: "missable", id: event.target.dataset.missableId, completed: event.target.checked });
  if (event.target.dataset.monsterId) saveToggle(event.target, { kind: "monster", id: event.target.dataset.monsterId, completed: event.target.checked });
  if (event.target.dataset.catalogProgress) { const kind = event.target.dataset.catalogProgress; const raw = event.target.dataset.progressId; saveToggle(event.target, { kind, id: kind === "medal" ? Number(raw) : raw, completed: event.target.checked }); }
});
$("#catalogSearch").addEventListener("input", renderCatalog);
function handleError(error) { console.error(error); const target = $("#status"); target.classList.add("error"); target.innerHTML = `Could not load guide. <button class="secondary" type="button" data-retry>Retry</button>`; }
document.addEventListener("keydown", event => { if (event.key === "Escape" && $("#primaryNav").classList.contains("open")) { $("#primaryNav").classList.remove("open"); $("#menuButton").setAttribute("aria-expanded", "false"); $("#menuButton").focus(); } });
window.addEventListener("hashchange", () => { const route = location.hash.slice(1) || "dashboard"; if (domains[route]) showDomain(route); else if (document.getElementById(route)) showView(route); });
const initialRoute = location.hash.slice(1) || "dashboard";
if (domains[initialRoute]) showDomain(initialRoute); else showView(initialRoute);
loadAll().catch(handleError);

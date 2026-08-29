"use strict";

const state = { dashboard: null, checkpoints: [], checkpoint: null, progress: null, equipment: null, conflicts: [], evidenceGaps: null, vocations: [], catalogs: {}, domain: null, selectedEntry: null, filter: "all", sourcePublisher: "all", sourceFreshness: "all", requests: 0, pendingRestore: null, usingCachedData: false, hostReachable: null, mutations: new Set(), undoAction: null, undoTimer: null };
const domains = {
  items: { title: "Items", singular: "item", progressKind: "item", filters: ["all","weapons","armour","accessories","shields","head","usable items"] },
  vocations: { title: "Vocations", singular: "vocation", progressKind: null, filters: ["all","beginner","intermediate","advanced","character-exclusive"] },
  monsters: { title: "Monsters", singular: "monster", progressKind: "monster", filters: ["all","defeated","open"] },
  hearts: { title: "Monster Hearts", singular: "heart", progressKind: "heart", filters: ["all","available","later","owned","open","unknown"] },
  missables: { title: "Missables", singular: "missable", progressKind: "missable", filters: ["all","verified","unresolved","collector","major_choice"] },
  farms: { title: "Farms", singular: "farm", progressKind: null, filters: ["all","gold","proficiency","exp","seeds","other"] },
  seeds: { title: "Seed Mechanics", singular: "seed mechanic", progressKind: null, filters: ["all","standard","super","reward"] },
  source_registry: { title: "Sources", singular: "source", progressKind: null, filters: ["all","item","monster","vocation","boss","completion","farming","other"] },
  medals: { title: "Mini Medals", singular: "medal", progressKind: "medal", filters: ["all","found","open"] },
  tablets: { title: "Tablets", singular: "tablet", progressKind: "tablet", filters: ["all","tablet","fragment","found","open"] },
  achievements: { title: "Achievements", singular: "achievement", progressKind: "achievement", filters: ["all","story","completion","combat","unlocked","open"] }
};
const viewTitles = { dashboard: "Dashboard", walkthrough: "Walkthrough", progress: "Progress", "phone-setup": "Phone Setup", sources: "Sources & conflicts" };
const $ = (selector) => document.querySelector(selector);
const empty = () => document.importNode($("#emptyTemplate").content, true);
const escapeHtml = (value = "") => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const scrollToTop = () => window.scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
const mobileLayout = () => matchMedia("(max-width: 900px) and (pointer: coarse), (max-width: 520px)").matches;
const urlPairingToken = new URLSearchParams(window.location.search).get("pair") || "";
if (urlPairingToken) sessionStorage.setItem("dq7_pair", urlPairingToken);
const pairingToken = urlPairingToken || sessionStorage.getItem("dq7_pair") || "";
function focusMainAtTop() { scrollToTop(); $("#main").focus({ preventScroll: true }); }
function syncSecondaryLedgers() {
  document.querySelectorAll(".secondary-ledger:not([data-density-ready])").forEach(ledger => {
    ledger.open = !mobileLayout();
    ledger.dataset.densityReady = "true";
  });
}
function showUndo(message, action) {
  window.clearTimeout(state.undoTimer);
  state.undoAction = action;
  $("#undoMessage").textContent = message;
  $("#undoSnackbar").hidden = false;
  state.undoTimer = window.setTimeout(() => { $("#undoSnackbar").hidden = true; state.undoAction = null; }, 7000);
}
function hideUndo() { window.clearTimeout(state.undoTimer); $("#undoSnackbar").hidden = true; state.undoAction = null; }
async function oneMutation(key, operation) {
  if (state.mutations.has(key)) return false;
  state.mutations.add(key);
  try { await operation(); return true; }
  finally { state.mutations.delete(key); }
}
function controlSelector(control) {
  const key = ["actionId","medal","tabletId","itemId","achievementId","missableId","monsterId","catalogProgress"].find(name => control.dataset[name] !== undefined);
  if (!key) return null;
  const attribute = key.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`);
  const value = CSS.escape(control.dataset[key]);
  return `[data-${attribute}="${value}"]`;
}

async function api(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  if (method !== "GET" && (!navigator.onLine || state.usingCachedData || state.hostReachable === false)) throw new Error("Guide host unavailable: reconnect before saving; progress changes are not queued");
  state.requests += 1; $("#main").setAttribute("aria-busy", "true");
  try {
    const response = await fetch(`/api${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(pairingToken ? { "X-DQ7-Pair": pairingToken } : {}),
        ...(options.headers || {})
      }
    });
    const wasUnreachable = state.hostReachable === false;
    const wasCached = state.usingCachedData;
    if (response.status >= 500) {
      state.hostReachable = false;
      state.usingCachedData = false;
      renderConnectionState(false);
      throw new Error(`${response.status} ${response.statusText}`);
    }
    state.hostReachable = true;
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    const isCached = response.headers.get("X-DQ7-Offline-Cache") === "true";
    state.usingCachedData = isCached;
    if (isCached) renderConnectionState(false);
    else if (wasUnreachable || wasCached) renderConnectionState(true);
    return response.status === 204 ? null : response.json();
  } catch (error) {
    if (error instanceof TypeError) { state.hostReachable = false; renderConnectionState(false); }
    throw error;
  } finally {
    state.requests -= 1; if (!state.requests) $("#main").removeAttribute("aria-busy");
  }
}

function renderConnectionState(reconnected = false) {
  const banner = $("#connectionBanner");
  if (!navigator.onLine || state.usingCachedData || state.hostReachable === false) {
    banner.hidden = false;
    banner.className = "connection-banner";
    banner.innerHTML = 'Guide host unavailable · changes are disabled and never queued. <button class="secondary" type="button" data-reconnect>Reconnect</button>';
  } else if (reconnected) {
    banner.hidden = false;
    banner.className = "connection-banner online";
    banner.textContent = "Reconnected · refreshed from the guide host.";
    window.setTimeout(() => { if (navigator.onLine) banner.hidden = true; }, 3500);
  } else {
    banner.hidden = true;
  }
  if (!$("#phone-setup").hidden) renderPhoneSetup();
}

function renderPhoneSetup() {
  const secure = window.isSecureContext;
  const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  const localOnly = ["localhost", "127.0.0.1", "::1"].includes(location.hostname);
  const workerCapable = secure && "serviceWorker" in navigator;
  const online = navigator.onLine && state.hostReachable !== false && !state.usingCachedData && state.dashboard !== null;
  const mode = secure ? (localOnly ? "Host-local secure context" : "Secure network origin") : "Local-network HTTP · online only";
  const rows = [
    ["Connection", online ? "Fresh host data loaded" : "Offline / cached / not loaded", online ? "ok" : "warning"],
    ["Mode", mode, secure ? "ok" : "warning"],
    ["Address", `${location.protocol}//${location.host}`, secure ? "ok" : "warning"],
    ["Offline cache", workerCapable ? (pairingToken ? "Shell only · paired data requires host" : "Unpaired host-local data available") : "Unavailable on this LAN HTTP address", workerCapable && !pairingToken ? "ok" : "warning"],
    ["Display", standalone ? "Opened as installed app" : "Browser tab / bookmark", standalone ? "ok" : "neutral"],
    ["Progress writes", online ? "Direct to host" : "Disabled — never queued", online ? "ok" : "warning"]
  ];
  $("#phoneSetupStatus").innerHTML = rows.map(([label, value, tone]) => `<div class="phone-status ${tone}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("") + (localOnly ? '<p class="muted span-all">This loopback address only works on the host itself. Use the phone address printed by the phone launcher.</p>' : "");
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
  if (name === "phone-setup") renderPhoneSetup();
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

function renderCheckpointActions(target, actions = [], hideCompleted = false) {
  target.replaceChildren();
  const visible = hideCompleted ? actions.filter(action => !action.completed) : actions;
  if (!visible.length) return target.append(empty());
  const immediate = document.createElement("div");
  immediate.className = "immediate-actions";
  renderChecks(immediate, visible.slice(0, 3));
  target.append(immediate);
  const later = visible.slice(3);
  if (!later.length) return;
  const details = document.createElement("details");
  details.className = "later-actions";
  details.innerHTML = `<summary>Later in this checkpoint (${later.length})</summary><div></div>`;
  renderChecks(details.lastElementChild, later);
  target.append(details);
}

function renderStopActions(target, actions = []) {
  target.hidden = !actions.length;
  target.replaceChildren();
  if (!actions.length) return;
  const heading = document.createElement("strong"); heading.textContent = "Clear before advancing"; target.append(heading);
  actions.forEach(action => {
    const label = document.createElement("label"); label.className = "check-row stop-check";
    label.innerHTML = `<input type="checkbox" data-action-id="${escapeHtml(action.id)}"><span class="check-text"><strong>${escapeHtml(action.title)}</strong><br>${escapeHtml(action.action)}</span>`;
    target.append(label);
  });
}

function scrollToPlayPriority() {
  const target = (!$("#checkpointStop").hidden && $("#checkpointStop")) || $("#actions .next-action") || $("#actions") || $("#walkthrough");
  target.scrollIntoView({ block: "start", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
}
function focusPlayPriority() { $("#main").focus({ preventScroll: true }); scrollToPlayPriority(); }

function scrollToPlaySection(section) {
  const targets = {
    next: (!$("#checkpointStop").hidden && $("#checkpointStop")) || $("#actions .next-action") || $("#actions"),
    power: $("#powerPlan .next-power") || $("#powerAdvice"),
    advance: $("#advancePanel")
  };
  targets[section]?.scrollIntoView({ block: "start", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
}

function compactApplicability(value) {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value !== "object") return String(value);
  return Object.entries(value).filter(([key]) => key !== "tradeoff").map(([key, item]) => `${key.replaceAll("_", " ")}: ${typeof item === "object" ? JSON.stringify(item) : item}`).join(" · ");
}

function recommendationEvidence(row) {
  const tier = row.evidence?.tier || "audit_pending";
  if (tier === "two_source_core_single_source_extras") return "Core 2-source · extras 1-source";
  if (tier === "two_source") return "2-source";
  if (tier === "single_source") return "1-source";
  if (tier === "declared_two_source_audit_pending") return "Declared corroboration · links missing";
  return "Evidence audit pending";
}

function adviceEvidenceLinks(row) {
  const claims = row.evidence?.claims || [];
  if (claims.length) return claims.map(claim => `<p><a href="${escapeHtml(claim.url)}" target="_blank" rel="noreferrer">${escapeHtml(claim.publisher || claim.title)}</a><br><span class="muted">${escapeHtml(claim.locator)}</span></p>`).join("");
  return sourceLink({source_url: row.source?.url, source_title: row.source?.title, locator: row.source?.locator});
}

function renderPowerPlan(plan = {}) {
  const target = $("#powerPlan"), party = plan.party || [], strongest = plan.strongest_now || [], safePower = plan.safe_power || [], grind = plan.grind_ceiling || [], gear = plan.gear_checks || [], farms = plan.available_farms || [], vocationPaths = plan.vocation_paths || [], bossTactics = plan.boss_tactics || [], bossPrep = plan.boss_skill_prep || [];
  const brief = plan.play_brief || {};
  const briefRow = (label, row, fallback) => `<li><b>${escapeHtml(label)}</b><span>${escapeHtml(row ? row.subject : fallback)}</span>${row ? `<small class="evidence-strength">${escapeHtml(recommendationEvidence(row))}</small>` : ""}</li>`;
  const advance = brief.advancement || {};
  const playBrief = `<section class="play-brief" aria-labelledby="playBriefHeading"><h4 id="playBriefHeading">At a glance</h4><ul>${briefRow("POWER", brief.power_now, "No separate power move sourced")}${briefRow("SAFE", brief.completion_safe, "No separate completion-safe tradeoff")}${briefRow("GRIND", brief.optional_grind, "Skip — none recommended")}${briefRow("LEAVE", null, advance.safe_condition || "Confirm the checkpoint exit condition")}</ul></section>`;
  const bossNames = [...new Set(bossPrep.map(row => row.boss))];
  const bossRows = bossPrep.map(row => {
    const stateText = row.state_status === "skill_available" ? "Recorded mastered + equipped · skill available" : row.state_status === "mastered_not_equipped" ? "Mastered · equip this vocation" : row.state_status === "rank_progress_unknown" ? "Current vocation · rank unknown" : "Mastery/rank unknown";
    const evidenceText = row.recommendation_evidence?.tier === "two_source" ? "Two-source boss recommendation" : "Single-source boss recommendation";
    const recommendationSources = (row.recommendation_evidence?.claims || []).map(claim => `<p><a href="${escapeHtml(claim.url)}" target="_blank" rel="noreferrer">${escapeHtml(claim.publisher || claim.title)}</a><br><span class="muted">${escapeHtml(claim.locator)}</span></p>`).join("");
    const rankEvidence = row.rank_evidence?.tier === "two_source" ? "two-source" : "single-source";
    return `<li><strong>${escapeHtml(row.boss)} · ${escapeHtml(row.skill)}</strong><span>${escapeHtml(row.characters.join(" or "))} · ${escapeHtml(row.vocation)} ${escapeHtml(row.rank)}★ · ${escapeHtml(row.recommendation_strength)}, not required</span><small class="applicability-${row.state_status === "skill_available" ? "satisfied" : "unknown"}">${escapeHtml(stateText)}</small><details class="advice-evidence"><summary>Evidence · ${escapeHtml(evidenceText)}</summary>${recommendationSources}<p><strong>Skill rank · ${escapeHtml(rankEvidence)}:</strong> <a href="${escapeHtml(row.skill_source.url)}" target="_blank" rel="noreferrer">${escapeHtml(row.skill_source.title)}</a><br><span class="muted">${escapeHtml(row.skill_source.locator)}</span></p></details></li>`;
  }).join("");
  const bossSection = bossRows ? `<details class="boss-prep"><summary>Prepare for ${escapeHtml(bossNames.length === 1 ? bossNames[0] : `${bossNames.length} upcoming bosses`)}</summary><ul class="power-list">${bossRows}</ul><p class="muted">Recommended is not required. State uses explicit mastery/current vocation only; missing rank stays unknown.</p></details>` : "";
  const recordedRoles = party.filter(row => row.active || row.primary_vocation || row.secondary_vocation).map(row => {
    const roles = [row.primary_vocation, row.secondary_vocation].filter(Boolean);
    return `<li><strong>${escapeHtml(row.name)}</strong><span>${escapeHtml(roles.length ? roles.join(" + ") : "Role unknown")}${row.active ? " · active" : " · activity unknown"}</span></li>`;
  }).join("");
  const battleBossRows = bossPrep.map(row => {
    const stateText = row.state_status === "skill_available" ? "READY" : row.state_status === "mastered_not_equipped" ? "EQUIP VOCATION" : row.state_status === "rank_progress_unknown" ? "CHECK RANK" : "STATE UNKNOWN";
    const evidenceText = row.recommendation_evidence?.tier === "two_source" ? "2-source tactic" : "1-source tactic";
    return `<li><strong>${escapeHtml(row.boss)}: ${escapeHtml(row.skill)}</strong><span>${escapeHtml(row.characters.join(" / "))} · ${escapeHtml(row.vocation)} ${escapeHtml(row.rank)}★</span><small class="applicability-${row.state_status === "skill_available" ? "satisfied" : "unknown"}">${escapeHtml(stateText)} · ${escapeHtml(evidenceText)} · rank 1-source</small></li>`;
  }).join("");
  const battleTacticRow = row => `<li><strong>${escapeHtml(row.subject)}</strong><span>${escapeHtml(row.text)}</span><small class="evidence-strength">${escapeHtml(recommendationEvidence(row))}</small></li>`;
  const visibleBattleTactics = bossTactics.slice(0, 2).map(battleTacticRow).join("");
  const laterBattleTactics = bossTactics.slice(2).map(battleTacticRow).join("");
  const battlePlan = (recordedRoles || visibleBattleTactics || battleBossRows) ? `<section class="battle-plan" aria-labelledby="battlePlanHeading"><div class="battle-plan-heading"><h4 id="battlePlanHeading">Battle plan</h4><span>Saved roles · sourced tactics · no ranking</span></div>${recordedRoles ? `<p class="battle-plan-label">Party roles</p><ul class="battle-plan-list">${recordedRoles}</ul>` : `<p class="muted">Party roles are not recorded.</p>`}${visibleBattleTactics ? `<p class="battle-plan-label">Fight plan</p><ol class="battle-plan-list">${visibleBattleTactics}</ol>${laterBattleTactics ? `<details class="battle-plan-more"><summary>${bossTactics.length - 2} later fights</summary><ol class="battle-plan-list">${laterBattleTactics}</ol></details>` : ""}` : ""}${battleBossRows ? `<p class="battle-plan-label">Skill prep</p><ul class="battle-plan-list">${battleBossRows}</ul>` : ""}</section>` : "";
  const partyText = party.length ? party.map(row => `${row.name}: ${row.active ? "Active · " : ""}${row.level ? `Lv ${row.level}` : "level ?"} · ${row.primary_vocation || "vocation ?"}${row.secondary_vocation ? ` + ${row.secondary_vocation}` : ""}`).join(" / ") : "Party levels and vocations not recorded — recommendations remain source-only.";
  const powerRow = row => `<li><strong>${escapeHtml(row.subject)}</strong><span>${escapeHtml(row.text)}</span><small class="evidence-strength">${escapeHtml(recommendationEvidence(row))}</small>${row.saved_state_applicability?.reason !== "No supported saved-state gate" ? `<small class="applicability-${escapeHtml(row.saved_state_applicability?.status || "unknown")}">${escapeHtml(row.saved_state_applicability?.reason || "Saved-state fit unknown")}</small>` : ""}</li>`;
  const primaryPowerRow = strongest[0] ? powerRow(strongest[0]) : "";
  const morePowerRows = strongest.slice(1).map(powerRow).join("");
  const nextPowerSection = primaryPowerRow ? `<section class="next-power" aria-labelledby="nextPowerHeading"><h4 id="nextPowerHeading">Next power move</h4><ol class="power-list primary-power">${primaryPowerRow}</ol>${morePowerRows ? `<details class="power-more"><summary>More strongest-now advice (${strongest.length - 1})</summary><ol class="power-list">${morePowerRows}</ol></details>` : ""}${plan.additional_strongest_count ? `<p class="muted">${plan.additional_strongest_count} more sourced power notes in Full sourced advice.</p>` : ""}</section>` : '<p class="muted">No separate immediate-power recommendation is sourced here.</p>';
  const safeRows = safePower.map(row => `<li><strong>${escapeHtml(row.subject)}</strong><span>${escapeHtml(row.text)}</span></li>`).join("");
  const availableGear = gear.filter(row => row.availability_status === "route_available").slice(0, 4);
  const conditionalGearCount = gear.filter(row => row.availability_status === "route_prerequisite_unconfirmed").length;
  const gearRow = row => {
    const owned = row.ownership_status === "recorded";
    const equipped = row.comparison_status === "matches_recommendation";
    const canRecord = !owned && row.item_id;
    const canEquip = owned && !equipped && row.character && ["weapon","shield","helmet","armour"].includes(row.slot) && row.compatibility_status === "verified_can_equip";
    const route = row.actionable_route, extraRoutes = Math.max((row.actionable_route_count || 0) - 1, 0);
    const statLabels = { attack_bonus: "Atk", defence_bonus: "Def", agility_bonus: "Agi", deftness_bonus: "Deft", magical_might_bonus: "Mag Mt", magical_mending_bonus: "Mag Mend", elemental_damage_reduction_percent: "all-element reduction", fire_damage_reduction_percent: "fire reduction", block_chance_percent: "block", mp_absorption_percent: "MP absorption" };
    const stats = row.verified_stats || {};
    const statText = Object.entries(stats).filter(([key]) => !["battle_use_effect", "drop_rate_effect"].includes(key)).map(([key, stat]) => ["elemental_damage_reduction_percent", "fire_damage_reduction_percent", "block_chance_percent", "mp_absorption_percent"].includes(key) ? `${stat.value}% ${statLabels[key]}` : `${Number(stat.value) > 0 ? "+" : ""}${stat.value} ${statLabels[key]}`).join(" · ");
    const battleEffect = stats.battle_use_effect?.value;
    const dropEffect = stats.drop_rate_effect?.value;
    const routeVerb = route?.method === "shop" ? "Buy now" : "Get now";
    const routeCost = route?.price != null ? ` · ${route.price} ${route.currency || "gold"}` : route?.is_free === 1 ? " · no gold cost" : "";
    return `<li><div class="gear-item-heading"><strong>${escapeHtml(row.item_name)}</strong><span class="gear-slot">${escapeHtml(row.slot || row.category || "gear")}</span></div><span>${escapeHtml(equipped ? "Equipped" : owned ? "Owned" : "Ownership unknown")} · ${escapeHtml((row.compatibility_status || "compatibility unknown").replaceAll("_", " "))}</span>${statText ? `<span><b>Verified:</b> ${escapeHtml(statText)}</span>` : ""}${battleEffect ? `<span><b>Battle use:</b> ${escapeHtml(battleEffect)}</span>` : ""}${dropEffect ? `<span><b>Drop boost:</b> ${escapeHtml(dropEffect)}</span>` : ""}${route ? `<span><b>${routeVerb}:</b> ${escapeHtml(route.route_label || route.location_text || route.method)}${escapeHtml(routeCost)}${extraRoutes ? ` · +${extraRoutes} routes` : ""}</span>` : ""}${canRecord ? `<span class="muted">Ownership tracking only · does not equip</span><button class="secondary compact-button" type="button" aria-label="Mark ${escapeHtml(row.item_name)} owned; does not equip it" data-power-item-owned="${escapeHtml(row.item_id)}">Mark owned</button>` : ""}${canEquip ? `<button class="secondary compact-button" type="button" aria-label="Equip ${escapeHtml(row.item_name)} on ${escapeHtml(row.character)}" data-power-equip-item="${escapeHtml(row.item_id)}" data-power-equip-character="${escapeHtml(row.character)}" data-power-equip-slot="${escapeHtml(row.slot)}">Equip</button>` : ""}</li>`;
  };
  const gearByCharacter = availableGear.reduce((groups, row) => { const character = row.character || "Party"; (groups[character] ||= []).push(row); return groups; }, {});
  const gearGroups = Object.entries(gearByCharacter).map(([character, rows]) => `<section class="gear-character" aria-label="${escapeHtml(character)} sourced gear checks"><h5>${escapeHtml(character)}</h5><ul class="power-list">${rows.map(gearRow).join("")}</ul></section>`).join("");
  const vocationRows = vocationPaths.map(path => {
    const evidenceLabel = recommendationEvidence(path);
    const evidenceLinks = (path.evidence?.claims || []).map(claim => `<p><a href="${escapeHtml(claim.url)}" target="_blank" rel="noreferrer">${escapeHtml(claim.publisher || claim.title)}</a><br><span class="muted">${escapeHtml(claim.locator)}</span></p>`).join("");
    const evidenceDetail = `<small class="evidence-strength">${escapeHtml(evidenceLabel)}</small><details class="advice-evidence"><summary>Recommendation evidence · ${escapeHtml(evidenceLabel)}</summary>${evidenceLinks || sourceLink({source_url: path.source?.url, source_title: path.source?.title, locator: path.source?.locator})}</details>`;
    return `<li><strong>${escapeHtml(path.character)} → ${escapeHtml(path.target_name)}</strong><span>${escapeHtml(path.decision_group === "completion_safe" ? "Completion-safe" : "Strongest now")} · ${escapeHtml(path.status === "target_mastered" ? "Target mastered" : "Next mastery")}</span>${evidenceDetail}${path.status !== "target_mastered" ? `<div class="vocation-options">${path.next_options.map(option => { const skill = option.power_payoff?.earliest_skill, perk = option.power_payoff?.let_loose; return `<div class="vocation-option"><span><b>${escapeHtml(option.name)}</b>${skill ? ` · ${escapeHtml(skill.rank)}★ ${escapeHtml(skill.name)}` : ""}${perk ? `<br>Let Loose: ${escapeHtml(perk.name)} — ${escapeHtml(perk.description)}` : ""}</span><button class="secondary compact-button" type="button" data-power-vocation-mastered="${escapeHtml(option.vocation_id)}" data-power-vocation-character="${escapeHtml(path.character)}">Record mastered</button></div>`; }).join("")}</div>${path.next_options.length > 1 ? '<small>Branch choice preserved · payoffs shown, options not ranked.</small>' : ""}` : `${path.target_payoff?.let_loose ? `<span>Let Loose: ${escapeHtml(path.target_payoff.let_loose.name)} — ${escapeHtml(path.target_payoff.let_loose.description)}</span>` : ""}`}</li>`;
  }).join("");
  target.innerHTML = `${nextPowerSection}<p class="power-party"><strong>Recorded party entries</strong><span>${escapeHtml(partyText)}</span><small>${escapeHtml(plan.party_note || "Unrecorded values remain unknown.")}</small></p>${vocationRows ? `<details class="power-more"><summary>Next vocation payoff (${vocationPaths.length})</summary><ul class="power-list">${vocationRows}</ul></details>` : ""}${safeRows ? `<h4>Completion-safe power</h4><ul class="power-list">${safeRows}</ul>${plan.additional_safe_power_count ? `<p class="muted">${plan.additional_safe_power_count} more safe-power notes below.</p>` : ""}` : ""}${gearGroups ? `<h4>Sourced loadout checks</h4><p class="muted gear-policy">Grouped by character · source order · not a complete or ranked loadout.</p><div class="gear-characters">${gearGroups}</div>` : ""}${conditionalGearCount ? `<p class="muted gear-policy"><strong>${conditionalGearCount} gated gear recommendation${conditionalGearCount === 1 ? "" : "s"} withheld:</strong> checkpoint window open · prerequisite unconfirmed.</p>` : ""}${grind.length ? `<h4>Optional grind ceiling</h4><ul class="power-list">${grind.map(row => `<li><strong>${escapeHtml(row.subject)}</strong><span>${escapeHtml(row.text)}</span></li>`).join("")}</ul>` : '<p class="muted">No checkpoint-specific grind is recommended.</p>'}${farms.length ? `<details class="farm-options"><summary>Other farms available by now (${farms.length})</summary><p class="muted">${escapeHtml(plan.farm_note)}</p>${farms.map(row => `<div><strong>${escapeHtml(row.target)}</strong><span>${escapeHtml(row.location)}${row.time_period ? ` · ${escapeHtml(row.time_period)}` : ""}</span></div>`).join("")}</details>` : ""}`;
  target.insertAdjacentHTML("afterbegin", playBrief);
  if (bossSection) target.querySelector(".power-party").insertAdjacentHTML("afterend", bossSection);
  if (battlePlan) target.querySelector(".power-party").insertAdjacentHTML("afterend", battlePlan);
}

function renderQuickSetup() {
  const members = state.progress?.party || [], vocations = state.vocations || [];
  $("#quickPartyRows").innerHTML = members.map(member => {
    const options = `<option value="unknown">Unknown</option>${vocations.filter(row => !row.exclusive_character || row.exclusive_character === member.name).map(row => `<option value="${escapeHtml(row.vocation_id)}">${escapeHtml(row.name)}</option>`).join("")}`;
    return `<fieldset class="quick-party-row" data-quick-member="${escapeHtml(member.name)}"><legend class="visually-hidden">${escapeHtml(member.name)} party details</legend><label class="quick-active"><input type="checkbox" data-quick-active aria-label="${escapeHtml(member.name)} is active" ${member.active ? "checked" : ""}> <strong>${escapeHtml(member.name)}</strong></label><label>Level<input type="number" min="1" inputmode="numeric" data-quick-level aria-label="${escapeHtml(member.name)} level" value="${escapeHtml(member.level ?? "")}" placeholder="?"></label><label>Vocation<select data-quick-primary aria-label="${escapeHtml(member.name)} current vocation">${options}</select></label><label>Second<select data-quick-secondary aria-label="${escapeHtml(member.name)} second vocation">${options}</select></label></fieldset>`;
  }).join("");
  members.forEach(member => {
    const row = document.querySelector(`[data-quick-member="${CSS.escape(member.name)}"]`);
    row.querySelector("[data-quick-primary]").value = member.primary_vocation || "unknown";
    row.querySelector("[data-quick-secondary]").value = member.secondary_vocation || "unknown";
  });
}

function syncQuickMasteryChoices() {
  const character = $("#quickMasteryMember")?.value, select = $("#quickMasteryVocation");
  if (!select) return;
  const member = (state.progress?.party || []).find(row => row.name === character), mastered = new Set(member?.mastered_vocations || []);
  select.innerHTML = state.vocations.filter(row => (!row.exclusive_character || row.exclusive_character === character) && !mastered.has(row.vocation_id)).map(row => `<option value="${escapeHtml(row.vocation_id)}">${escapeHtml(row.name)}</option>`).join("");
  const submit = $("#quickMasteryForm")?.querySelector('[type="submit"]');
  if (submit) submit.disabled = !select.options.length;
}

function renderQuickMastery(available = false) {
  $("#quickMastery").hidden = !available;
  if (!available) { $("#quickMastery").open = false; return; }
  const members = state.progress?.party || [];
  $("#quickMasteryMember").innerHTML = members.map(row => `<option value="${escapeHtml(row.name)}">${escapeHtml(row.name)}</option>`).join("");
  syncQuickMasteryChoices();
}

function quickSetupPayload() {
  const rows = [...document.querySelectorAll("[data-quick-member]")];
  return { checkpoint_id: state.checkpoint?.id, active: rows.filter(row => row.querySelector("[data-quick-active]").checked).map(row => row.dataset.quickMember), members: rows.map(row => ({ name: row.dataset.quickMember, level: row.querySelector("[data-quick-level]").value || "unknown", primary_vocation: row.querySelector("[data-quick-primary]").value, secondary_vocation: row.querySelector("[data-quick-secondary]").value })) };
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

function renderCheckpointFinder() {
  const finder = $("#checkpointFinder"), saved = state.dashboard?.checkpoint?.is_saved;
  finder.hidden = Boolean(saved);
  if (saved) return;
  finder.open = true;
  const query = $("#checkpointFinderInput").value.trim().toLowerCase();
  const matches = state.checkpoints.filter(row => !query || [row.name, row.region, row.entry_condition, row.time_period].some(value => String(value || "").toLowerCase().includes(query))).slice(0, 5);
  $("#checkpointFinderResults").innerHTML = matches.map(row => `<button class="secondary" type="button" data-preview-checkpoint="${escapeHtml(row.id)}"><strong>${String(row.sequence).padStart(2, "0")} · ${escapeHtml(row.name)}</strong><small>${escapeHtml(row.region)} · ${escapeHtml(row.entry_condition || "Entry step unknown")}</small></button>`).join("") || '<p class="muted">No match. Try a town or region name.</p>';
  const viewed = state.checkpoints.find(row => row.id === state.checkpoint?.id);
  $("#checkpointFinderChoice").innerHTML = viewed ? `<strong>Previewing: ${escapeHtml(viewed.name)}</strong><span>Not saved as current.</span><button type="button" data-save-found-checkpoint="${escapeHtml(viewed.id)}">Save this checkpoint</button>` : "";
}

function renderCheckpoint() {
  const c = state.checkpoint || {};
  renderCheckpointFinder();
  const index = state.checkpoints.findIndex(row => row.id === c.id);
  const savedCheckpoint = state.dashboard?.checkpoint?.is_saved ? state.dashboard.checkpoint.id : null;
  const isSavedCurrent = savedCheckpoint === c.id;
  $("#previousCheckpoint").disabled = index <= 0;
  $("#nextCheckpoint").disabled = index < 0 || index >= state.checkpoints.length - 1;
  $("#mobilePrevious").disabled = index <= 0;
  $("#mobileNext").disabled = index < 0 || index >= state.checkpoints.length - 1;
  $("#checkpointMeta").textContent = [savedCheckpoint ? null : "Preview · not saved", c.name, c.time_period, c.region].filter(Boolean).join(" · ");
  const setCurrent = $("#setCheckpointButton");
  setCurrent.disabled = isSavedCurrent;
  setCurrent.textContent = isSavedCurrent ? "Current" : savedCheckpoint ? "Set current" : "Start here";
  renderStopActions($("#checkpointStop"), c.stop_actions || []);
  renderCheckpointActions($("#actions"), c.actions || [], $("#hideCompleted").checked);
  renderPowerPlan(c.power_plan || {});
  renderQuickSetup();
  renderQuickMastery(Boolean(c.power_plan?.vocation_tracking_available));
  $("#actionCount").textContent = `${(c.actions || []).filter(a => !a.completed).length} open`;
  const advice = $("#advice"), adviceGroups = [
    ["completion_safe", "Completion-safe"],
    ["strongest_now", "Strongest now"],
    ["optional_grind", "Optional grind"]
  ];
  advice.innerHTML = adviceGroups.map(([group, label]) => {
    const rows = (c.advice || []).filter(a => a.decision_group === group);
    if (!rows.length) return "";
    return `<section class="advice-group" aria-labelledby="advice-${group}"><h4 id="advice-${group}">${label}</h4>${rows.map(a => { const applies = compactApplicability(a.applicability), saved = a.saved_state_applicability || { status: "unknown", reason: "Saved-state check unavailable" }, checked = saved.reason !== "No supported saved-state gate", evidenceLabel = recommendationEvidence(a); return `<div class="advice-item"><span class="tag goal-${escapeHtml(a.goal)}">${escapeHtml(a.type)} · ${escapeHtml(a.goal.replaceAll("_", " "))}</span>${checked ? `<span class="tag applicability-${escapeHtml(saved.status)}">${escapeHtml(saved.status === "satisfied" ? "State: met" : saved.status === "unmet" ? "State: unmet" : "State: unknown")}</span>` : ""}<span class="tag evidence-strength">${escapeHtml(evidenceLabel)}</span><strong>${escapeHtml(a.subject)}</strong><p>${escapeHtml(a.text)}</p><details class="advice-evidence"><summary>When, tradeoff & evidence · ${escapeHtml(evidenceLabel)}</summary>${checked ? `<p><strong>Saved state:</strong> ${escapeHtml(saved.reason)}</p>` : ""}${applies ? `<p><strong>Applies:</strong> ${escapeHtml(applies)}</p>` : ""}${a.tradeoff ? `<p><strong>Tradeoff:</strong> ${escapeHtml(a.tradeoff)}</p>` : ""}${adviceEvidenceLinks(a)}<p class="muted">${escapeHtml(a.confidence || "unknown")} confidence · ${escapeHtml(a.verification_status || "status unknown")}</p></details></div>`; }).join("")}</section>`;
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
  missableTarget.innerHTML = checkpointMissables.map(row => `<div class="${row.window_status === "unresolved" ? "uncertain-banner" : ""}">${row.window_status === "unresolved" ? '<strong>Cutoff unknown · not a STOP</strong>' : ""}<div class="check-row${row.progress_status === "completed" ? " completed" : ""}"><span class="check-text"><strong>${escapeHtml(row.name)}</strong><br>${escapeHtml(row.available_from)}${row.unavailable_after ? ` · before ${escapeHtml(row.unavailable_after)}` : ""}</span><label class="select-label">Result<select data-missable-status="${escapeHtml(row.missable_id)}" data-previous-status="${escapeHtml(row.progress_status)}"><option value="unknown" ${row.progress_status === "unknown" ? "selected" : ""}>Not reported</option><option value="completed" ${row.progress_status === "completed" ? "selected" : ""}>Completed</option><option value="missed" ${row.progress_status === "missed" ? "selected" : ""}>Missed · recovery needed</option></select></label></div></div>`).join(""); if (!missableTarget.children.length) missableTarget.append(empty());
  const medals = $("#medals"), availableMedals = (c.medals || []).filter(m => m.timing !== "later"), laterMedals = (c.medals || []).filter(m => m.timing === "later");
  medals.innerHTML = availableMedals.map(m => `<label class="check-row${m.found ? " completed" : ""}"><input type="checkbox" data-medal="${m.number}" ${m.found ? "checked" : ""}><span class="check-text"><strong>${m.timing === "backtrack" ? '<span class="tag">Backtrack</span> ' : ""}#${m.number} ${escapeHtml(m.location)}</strong><br>${escapeHtml(m.detail)}</span></label>`).join("");
  if (laterMedals.length) medals.insertAdjacentHTML("beforeend", `<details class="later-medals"><summary>Later (${laterMedals.length})</summary>${laterMedals.map(m => `<div><strong>#${m.number} ${escapeHtml(m.location)}</strong><span>${escapeHtml(m.available_checkpoint || m.available_from || "Gate unknown")}</span></div>`).join("")}</details>`);
  if (!medals.children.length) medals.append(empty());
  const monsters = $("#monsters"); monsters.innerHTML = (c.monsters || []).map(m => `<label class="check-row"><input type="checkbox" data-monster-id="${escapeHtml(m.id)}" ${m.defeated ? "checked" : ""}><span class="check-text"><strong>${escapeHtml(m.name || `Monster #${m.ordinal}`)}</strong><br>${escapeHtml(m.location || "")}${m.drop ? ` · ${escapeHtml(m.drop)}` : ""}</span></label>`).join(""); if (!monsters.children.length) monsters.append(empty());
  $("#safeCondition").textContent = c.safe_condition || "Not yet verified.";
  const readiness = c.advancement_readiness || {}, labels = { blocked_by_stop: "STOP open", completion_failed: "100% recovery needed", required_actions_open: "Actions open", completion_ledgers_open: "Ledger review", manual_confirmation: "Confirm manually" };
  $("#advanceStatus").textContent = labels[readiness.status] || "Unknown";
  $("#advanceReason").textContent = readiness.reason || "Readiness is not machine-verifiable.";
  const ledgerLabels = [
    ["unrecorded_available_medal_count", "available Mini Medals", "ledgerMedals"],
    ["unrecorded_checkpoint_tablet_fragment_count", "checkpoint Tablet Fragments", "ledgerTablets"],
    ["unrecorded_finite_hoarder_item_count", "finite Heroic Hoarder items", "ledgerItems"],
    ["unrecorded_due_achievement_count", "achievements due here", "ledgerAchievements"],
    ["unrecorded_checkpoint_missable_count", "checkpoint missables needing a result", "ledgerMissables"],
  ];
  $("#advanceLedgerGaps").innerHTML = ledgerLabels.filter(([key]) => Number(readiness[key]) > 0)
    .map(([key, label, target]) => `<li><button type="button" class="secondary ledger-jump" data-ledger-jump="${target}" aria-controls="${target}"><strong>${readiness[key]}</strong><span>${escapeHtml(label)}</span><span aria-hidden="true">Review →</span></button></li>`).join("");
  const advanceButton = $("#advanceCheckpointButton"); advanceButton.disabled = !readiness.can_confirm_and_save_next;
  $("#advancePanel").classList.toggle("advance-ready", Boolean(readiness.can_confirm_and_save_next));
  advanceButton.dataset.nextCheckpoint = readiness.next_checkpoint?.id || "";
  advanceButton.textContent = readiness.next_checkpoint ? `Confirm and set ${readiness.next_checkpoint.name}` : "Final checkpoint";
  renderSources(c.sources || []);
}

function renderProgress() {
  const p = state.progress || {};
  renderCards($("#progressCards"), ["actions", "medals", "items", "monsters", "hearts", "tablets", "vocations", "achievements", "missables"].map(key => ({ label: key[0].toUpperCase() + key.slice(1), value: p[key]?.display ?? p[key] ?? "Unknown" })));
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
  const strength = equipment.strength_analysis || {}, strengthSlots = strength.slots || [];
  const strengthCandidates = strengthSlots.reduce((total, row) => total + (row.candidate_count || 0), 0);
  const strengthProfiled = strengthSlots.reduce((total, row) => total + (row.profiled_candidate_count || 0), 0);
  const strengthNotice = strength.overall_conclusion === "global_strongest_not_proven" ? `<div class="callout uncertain-banner"><strong>Absolute strongest not proven</strong><span>${escapeHtml(`${strengthProfiled}/${strengthCandidates} compatible route-open candidate profiles have the primary verified stat needed for an exhaustive comparison. Recommendations below are attributed and legal, not universal best-in-slot. Effects and tradeoffs are not assigned invented weights.`)}</span></div>` : "";
  const accessoryEditor = equipment.accessory_editor_supported ? `<h4>Owned accessories</h4><p class="muted">Verified compatible items only. A second identical copy requires an exact count of 2+ and item-specific two-publisher legality; currently Rabbit Tail and Meteorite Bracer qualify. Monster Heart duplicates remain unsupported.</p><div class="detail-list">${(equipment.members || []).map(member => `<div><strong>${escapeHtml(member.name)}</strong>${["accessory_1","accessory_2"].map((slot, index) => `<label class="select-label">Slot ${index + 1}<select data-accessory-character="${escapeHtml(member.name)}" data-accessory-slot="${slot}"><option value="">Unknown</option>${(member.accessory_options || []).map(item => `<option value="${escapeHtml(item.item_id)}" ${member.accessory_slots?.[slot] === item.item_id ? "selected" : ""}>${escapeHtml(item.name)} · ${item.quantity_status === "exact" ? `${item.quantity} owned` : "count unknown"}${item.duplicate_legal ? " · 2-copy verified" : ""}</option>`).join("")}</select></label>`).join("")}</div>`).join("")}</div>` : "";
  $("#equipmentReadiness").innerHTML = `<div class="callout"><strong>Validated equipment tracking enabled</strong><span>Owned recommendations can be equipped from Power up now; every write checks slot category, global copy allocation, and verified character compatibility.</span></div>${strengthNotice}${accessoryEditor}${coverage.audited_item_rows ? `<h4>Compatibility evidence</h4><p class="muted">${escapeHtml(`${coverage.verified_item_rows}/${coverage.catalog_item_rows || coverage.audited_item_rows} catalog rows verified by two independent sources · ${coverage.conflicted_item_rows} disputed · ${coverage.single_source_item_rows} single-source · ${coverage.unaudited_item_rows || 0} unaudited`)}</p>` : ""}${mechanics.length ? `<h4>Verified mechanics</h4><div class="detail-list">${mechanics.map(row => `<div><strong>${escapeHtml(row.rule_type === "slot_count" ? `${row.numeric_value} ${row.slot_name} slot${row.numeric_value === 1 ? "" : "s"}` : `Monster Heart uses ${row.numeric_value} accessory slot`)}</strong><span>${escapeHtml(row.applies_to)} · independently corroborated</span>${sourceLink({source_url: row.source_url, source_title: row.source_title, locator: row.locator})}${sourceLink({source_url: row.corroborating_source_url, source_title: row.corroborating_source_title, locator: row.corroborating_locator})}</div>`).join("")}</div>` : ""}${recommendations.length ? `<h4>Attributed strongest-now checks</h4><div class="detail-list">${recommendations.map(row => `<div><strong>${escapeHtml([row.character, row.slot, row.item_name].filter(Boolean).join(" · "))}</strong><span>${escapeHtml(row.comparison_status.replaceAll("_", " "))} · quantity ${escapeHtml(row.quantity_fit || "unknown")} (${escapeHtml(row.quantity_status || "unknown")}${row.quantity !== null && row.quantity !== undefined ? ` ${escapeHtml(row.quantity)}` : ""}) · ${escapeHtml(row.availability_status.replaceAll("_", " "))} · compatibility ${escapeHtml((row.compatibility_status || "unknown").replaceAll("_", " "))}</span><span>${escapeHtml(row.recommendation)}</span><span class="tag">Evidence: ${escapeHtml(row.evidence?.tier?.replaceAll("_", " ") || "audit pending")}</span>${row.equip_block_reason ? `<span>${escapeHtml(row.equip_block_reason)}</span>` : ""}${sourceLink({source_url: row.source?.url, source_title: row.source?.title, locator: row.source?.locator})}</div>`).join("")}</div><p class="muted">These are attributed checkpoint recommendations; every write still requires explicit quantity, verified compatibility, and route availability.</p>` : '<p class="muted">No sourced gear recommendation is normalized for the saved checkpoint.</p>'}`;
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
  const gapStrength = gap => ({ single_source: `${gap.supporting_claim_publisher_count} claim publisher`, unsupported: "No publishable source", corroborated_but_unresolved: `${gap.supporting_claim_publisher_count} claim publishers · still unresolved` }[gap.verification_tier] || "Evidence status unknown");
  const gapStatus = gap => ({ corroborated_inexact: "Exact observation still missing", single_source: "Independent corroboration missing", guide_text_conflict: "Direct UI needed to resolve conflict", no_publishable_source: "Reproducible evidence missing" }[gap.status] || gap.status.replaceAll("_", " "));
  const gapEvidence = gap => {
    const claims = (gap.supporting_claims || []).map(claim => `<div class="evidence-claim"><a href="${escapeHtml(claim.source?.url || "#")}" target="_blank" rel="noreferrer">${escapeHtml(claim.source?.title || claim.source_id)}</a><small>${escapeHtml(claim.locator)}</small></div>`).join("");
    const linkedSources = new Set((gap.supporting_claims || []).map(claim => claim.source_id));
    const additional = gap.sources.filter(source => !linkedSources.has(source.source_id)).map(source => `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(source.title)}</a>`).join(" ");
    if (!claims && !additional) return '<span class="muted">No publishable source found.</span>';
    return `${claims ? `<span><b>Supporting claim locators:</b></span><div class="evidence-claims">${claims}</div>` : ""}${additional ? `<span><b>Additional audited pages:</b> ${additional}</span>` : ""}`;
  };
  const target = $("#sourceList"); target.innerHTML = sources.map(s => `<div class="source-item"><a href="${escapeHtml(s.url)}" target="_blank" rel="noreferrer">${escapeHtml(s.title)}</a><br><span class="muted">${escapeHtml(s.locator || "")}</span></div>`).join(""); if (!target.children.length) target.append(empty());
  const gapTarget = $("#evidenceGaps"), audit = state.evidenceGaps;
  const gapCards = audit?.gaps.map(gap => `<details class="evidence-gap-card"><summary><span class="evidence-gap-heading"><strong>${escapeHtml(gap.subject)}</strong><small class="evidence-strength">${escapeHtml(gapStrength(gap))}</small></span><span class="muted">Open question · ${escapeHtml(gapStatus(gap))}</span></summary><div class="evidence-gap-body"><span>${escapeHtml(gap.summary)}</span><span><b>Needed:</b> ${escapeHtml(gap.acceptance_condition)}</span>${gapEvidence(gap)}<span class="muted">${escapeHtml(gap.freshness_status.replaceAll("_", " "))} · audited ${escapeHtml(gap.last_audited)}</span></div></details>`).join("");
  gapTarget.innerHTML = audit ? `<p class="muted">Priority gaps: ${audit.single_source} single-source · ${audit.unsupported} unsupported · ${audit.corroborated_but_unresolved} corroborated but unresolved. Separate conflict ledger: ${audit.unresolved_conflicts} unresolved. Sources: ${audit.source_freshness.over_180_days} stale · ${audit.source_freshness.unknown} retrieval date unknown.</p><div class="evidence-gap-list">${gapCards}</div>` : '<p class="empty">Evidence audit unavailable.</p>';
  const conflicts = $("#conflicts"); conflicts.innerHTML = state.conflicts.map(c => `<article class="conflict-item"><div class="conflict-heading"><strong>${escapeHtml(c.subject)}</strong><span class="tag">${escapeHtml(c.status || "unresolved")}</span></div><p class="muted">${escapeHtml(c.predicate)} · ${c.status === "resolved" ? "Resolution is identified below." : "No resolution is implied."}</p><div class="claim-grid">${(c.claims || []).map((claim, index) => `<section class="claim-card" aria-label="Claim ${index + 1}"><h4>Claim ${index + 1}${claim.is_resolution ? " · Resolution" : ""}</h4><p>${escapeHtml(typeof claim.value === "string" ? claim.value : JSON.stringify(claim.value))}</p><dl><dt>Scope</dt><dd>${escapeHtml(JSON.stringify(claim.scope || {}))}</dd><dt>Evidence</dt><dd>${escapeHtml(claim.confidence)} · ${escapeHtml(claim.verification_status)}</dd><dt>Freshness</dt><dd>Updated ${escapeHtml(claim.source?.updated_at || "unknown")} · Retrieved ${escapeHtml(claim.source?.retrieved_at || "unknown")}</dd></dl><a href="${escapeHtml(claim.source?.url || "#")}" target="_blank" rel="noreferrer">${escapeHtml(claim.source?.title || "Source")}</a><br><span class="muted">${escapeHtml(claim.locator || "Precise locator not stored")}</span></section>`).join("")}</div>${c.resolution_is_external ? `<section class="claim-card resolution-card" aria-label="Consensus resolution"><h4>Consensus resolution · separate claim</h4><p>${escapeHtml(typeof c.resolution.value === "string" ? c.resolution.value : JSON.stringify(c.resolution.value))}</p><p class="muted">Independent matching publishers:</p>${(c.resolution_evidence || []).map(evidence => `<div class="source-item"><a href="${escapeHtml(evidence.source?.url || "#")}" target="_blank" rel="noreferrer">${escapeHtml(evidence.source?.publisher || evidence.source?.title || "Consensus source")}</a><br><span class="muted">${escapeHtml(evidence.locator || "Precise locator not stored")}</span></div>`).join("")}</section>` : ""}${c.rationale ? `<p class="muted">Recorded rationale: ${escapeHtml(c.rationale)}</p>` : ""}${c.required_evidence ? `<p><strong>Needed to resolve:</strong> ${escapeHtml(c.required_evidence)}</p>` : ""}</article>`).join(""); if (!conflicts.children.length) conflicts.append(empty());
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
function heartRouteSafety(route) {
  if (route.supply_type === "finite") {
    const copies = Number(route.finite_total ?? route.quantity);
    const quantity = Number.isFinite(copies) && copies > 0
      ? ` · ${copies} ${copies === 1 ? "copy" : "copies"}` : "";
    return `Finite pickup${quantity} · No repeatable Heart route established`;
  }
  return route.method === "drop"
    ? "Drop listed · rate and repeatability unknown"
    : "Repeatability not established";
}
function heartRouteEvidence(route) {
  return route.route_evidence?.tier === "two_source"
    ? "Two-source route" : "Sourced route";
}
function heartRouteEvidenceLinks(route) {
  const claims = route.route_evidence?.claims || [];
  return claims.length >= 2 ? claims.map(sourceLink).join("") : sourceLink(route);
}
function itemRouteTiming(route) {
  if (route.availability_status === "available_now") return route.method === "shop" ? "Buy now" : "Get now";
  if (route.availability_status === "conditionally_available") return "Medal threshold unconfirmed";
  if (route.window_status === "later") return "Available later";
  if (route.window_status === "expired") return "Window passed";
  return "Timing unknown";
}
function itemRouteCost(route) {
  if (route.method === "shop" && route.price != null) return `${route.price} ${route.currency || "gold"}`;
  if (route.method === "lucky_panel" && route.panel_system_entry_cost === 0) return "Free entry · reward probability unpublished";
  if (route.method === "drop") return "Drop route · rate/repeatability unknown";
  if (route.is_free === 1) return "No gold cost";
  return route.supply_type || "Cost unknown";
}
function renderRichDetail(detail, summary) {
  const target = $("#catalogDetail");
  if (state.domain === "items") {
    const item = detail.item, routes = detail.routes || [];
    const quantityLabel = item.quantity_status === "exact" ? `Exact copies: ${item.quantity}` : item.quantity_status === "at_least_one" ? "Copies: at least 1 · exact total unknown" : "Copies: unknown · may be zero";
    target.innerHTML = `<p class="eyebrow">Item · ${escapeHtml(item.category_name || summary.category)}</p><h3>${escapeHtml(item.name)}</h3><p><span class="tag">${item.heroic_hoarder_required ? "Hoarder" : "Optional"}</span> ${escapeHtml(item.confidence || "")}</p><h4>Get it</h4><div class="detail-list">${routes.map(route => `<div><strong>${escapeHtml(route.route_label)}</strong><span><b>${escapeHtml(itemRouteTiming(route))}</b> · ${escapeHtml([route.location_text, route.time_period, route.available_checkpoint].filter(Boolean).join(" · "))}</span><span>${escapeHtml(itemRouteCost(route))}</span>${sourceLink(route)}${route.method === "lucky_panel" && route.panel_system_entry_cost === 0 ? `<a href="${escapeHtml(route.panel_cost_source_url)}" target="_blank" rel="noreferrer">Free-entry evidence</a><br><span class="muted">${escapeHtml(route.panel_cost_locator)} · independently corroborated</span>` : ""}</div>`).join("") || '<p class="empty">No verified route yet.</p>'}</div><label class="progress-toggle"><input type="checkbox" data-catalog-progress="item" data-progress-id="${escapeHtml(item.item_id)}" ${item.obtained ? "checked" : ""}> Explicitly mark obtained</label><div class="callout"><strong>${escapeHtml(quantityLabel)}</strong><span>Record a total only when you have counted the copies. Routes never change this value.</span><label class="select-label">Exact total <input type="number" inputmode="numeric" min="0" max="99" value="${item.quantity_status === "exact" ? escapeHtml(item.quantity) : ""}" data-item-quantity-input="${escapeHtml(item.item_id)}" placeholder="Unknown"></label><span><button type="button" data-item-quantity-save="${escapeHtml(item.item_id)}">Save total</button> <button type="button" data-item-quantity-clear="${escapeHtml(item.item_id)}">Clear to unknown</button></span></div>`;
  } else if (state.domain === "vocations") {
    const vocation = detail.vocation, skills = detail.skills || [], perks = detail.perks || [], requirements = detail.requirements || [], rankCosts = detail.rank_costs || [], progression = detail.progression || {}, numericStats = detail.numeric_stat_modifiers || [];
    const moon = detail.moonlighting || {}, unlock = moon.unlock?.value || {}, mechanics = moon.mechanics?.value || {};
    const plan = detail.unlock_progress || {}, groups = plan.groups || [], partyProgress = plan.party_progress || [], recursivePlans = plan.recursive_plans || [];
    const costLabel = progression.progression_mode === "story_granted" ? "Story-granted · no positive point cost" : progression.progression_mode === "story_then_points" ? `${progression.normalized_total_points} points after story-granted early ranks` : progression.normalized_total_points !== undefined ? `${progression.normalized_total_points} total points` : "Unknown";
    const costPanel = progression.progression_mode ? `<h4>Proficiency costs</h4><div class="callout"><strong>${escapeHtml(costLabel)}</strong><span>${escapeHtml(progression.notes || "Two-source verified progression profile")}</span>${sourceLink(progression)}</div>${rankCosts.length ? `<div class="detail-list">${rankCosts.map(row => `<div><strong>${row.proficiency_rank}★ · ${row.proficiency_points} points</strong><span>${row.cumulative_points} cumulative</span>${sourceLink(row)}</div>`).join("")}</div>` : ""}` : '<p class="muted">Numeric proficiency costs remain unknown.</p>';
    const statPanel = numericStats.length ? `<h4>Stat modifiers</h4><div class="detail-list">${numericStats.map(row => `<div><strong>${escapeHtml(row.stat_key.replaceAll("_", " "))}</strong><span>${Number(row.modifier_value) > 0 ? "+" : ""}${escapeHtml(row.modifier_value)}%</span></div>`).join("")}</div><p class="muted">All values independently match dq_st and hyperWiki.</p>` : "";
    const baseUnlockPlan = groups.length ? `<h4>Unlock path</h4>${groups.map(group => `<div class="callout"><strong>${group.rule === "all_of" ? "Master all" : `Master any ${group.required_count}`}</strong><span>${escapeHtml(group.candidates.map(row => row.name).join(" · "))}</span>${sourceLink(group)}</div>`).join("")}<div class="detail-list">${partyProgress.map(member => { const needed = Math.max(...member.groups.map(group => group.needed_if_unknowns_are_unmastered), 0); return `<div><strong>${escapeHtml(member.party_member)} · ${member.status}</strong><span>${member.status === "satisfied" ? "Direct prerequisites explicitly mastered" : `${needed} still needed if unrecorded masteries are not complete`}</span></div>`; }).join("")}</div>` : '<p class="muted">No prerequisite vocations.</p>';
    const unlockPlan = costPanel + statPanel + baseUnlockPlan;
    const recursive = recursivePlans.length ? `<h4>Next mastery options</h4><div class="detail-list">${recursivePlans.map(member => `<div><strong>${escapeHtml(member.character)} · ${escapeHtml(member.status.replaceAll("_", " "))}</strong><span>${escapeHtml((member.next_options || []).map(row => row.name).join(" · ") || "No next option derived from explicit mastery")}</span></div>`).join("")}</div><p class="muted">Full prerequisite tree is evaluated. Alternative branches are all shown and unranked.</p>` : "";
    const pairingSources = (moon.pairing_rules || []).map(sourceLink).join("");
    target.innerHTML = `<p class="eyebrow">${escapeHtml(vocation.tier)} vocation</p><h3>${escapeHtml(vocation.name)}</h3>${vocation.exclusive_character ? `<p class="tag">${escapeHtml(vocation.exclusive_character)} only</p>` : ""}${perks.map(perk => `<div class="callout"><strong>${escapeHtml(perk.perk_name)}</strong><span>${escapeHtml(perk.perk_description)}</span>${sourceLink(perk)}</div>`).join("")}${unlockPlan}${recursive}<h4>Moonlighting</h4><div class="callout"><strong>Unlock: cp012 after Aishe</strong><span>${escapeHtml(unlock.activation || "Exact activation not normalized")}. ${escapeHtml((mechanics.published_behavior || []).join("; "))}.</span>${sourceLink(moon.unlock || {})}</div>${moon.pairing_summary ? `<div class="callout"><strong>Legal pairing</strong><span>${escapeHtml(moon.pairing_summary)}</span>${pairingSources}</div>` : '<p class="muted">Complete legal pairing restrictions remain unknown.</p>'}<h4>Skills</h4><ol class="skill-list">${skills.map(skill => `<li><strong>${skill.proficiency_rank}★ ${escapeHtml(skill.skill_name)}</strong><span>${escapeHtml(skill.skill_description)}</span>${sourceLink(skill)}</li>`).join("") || '<li class="empty">No skill rows.</li>'}</ol><p class="muted">Mastered by: ${escapeHtml((detail.mastered_by || []).join(", ") || "nobody recorded")}</p>`;
  } else if (state.domain === "monsters") {
    const monster = detail.monster, encounters = detail.encounters || [], drops = detail.drops || [];
    const stats = [["HP",monster.hp],["Attack",monster.strength],["Defence",monster.defence],["EXP",monster.experience],["Vocation EXP",monster.vocation_experience],["Gold",monster.gold]].filter(([,v]) => v !== null && v !== undefined);
    target.innerHTML = `<p class="eyebrow">Monster #${escapeHtml(monster.source_ordinal)}</p><h3>${escapeHtml(monster.english_name || summary.name)}</h3><dl>${stats.map(([k,v]) => `<dt>${k}</dt><dd>${escapeHtml(v)}</dd>`).join("")}</dl><h4>Where</h4><div class="detail-list">${encounters.map(row => `<div><strong>${escapeHtml(row.location || row.location_text)}</strong><span>${escapeHtml([row.time_period, row.checkpoint_name].filter(Boolean).join(" · "))}</span>${sourceLink(row)}</div>`).join("") || '<p class="empty">No verified encounter route.</p>'}</div><h4>Drops</h4><div class="detail-list">${drops.map(row => `<div><strong>${escapeHtml(row.item_name || row.drop_name || row.item_id)}</strong><span>${escapeHtml(row.drop_type || "Verified drop")}</span>${sourceLink(row)}</div>`).join("") || '<p class="empty">No verified drops.</p>'}</div>${sourceLink(monster)}<label class="progress-toggle"><input type="checkbox" data-catalog-progress="monster" data-progress-id="${escapeHtml(monster.monster_id)}" ${detail.defeated ? "checked" : ""}> Explicitly mark defeated</label>`;
  } else if (state.domain === "hearts") {
    const routes = detail.routes || [];
    const ownershipNote = detail.ownership_status === "unknown" ? "Ownership unreported. Checking this starts the explicit Heart ledger; it does not infer other Hearts." : "Only explicit saved ownership is shown.";
    let dlcWarning = detail.dlc_ownership_status === "unknown" ? `<div class="uncertain-banner"><strong>DLC ownership unconfirmed</strong><span>${escapeHtml(detail.dlc_scope)} is required. This Heart is not shown as currently obtainable until ownership is explicitly reported.</span></div>` : "";
    const dlcControl = detail.dlc_scope ? `<label class="select-label">DLC access for ${escapeHtml(detail.dlc_scope)}<select data-dlc-entitlement="${escapeHtml(detail.dlc_scope)}"><option value="unknown" ${detail.dlc_ownership_status === "unknown" ? "selected" : ""}>Not reported</option><option value="owned" ${detail.dlc_ownership_status === "owned" ? "selected" : ""}>Owned / installed</option><option value="not-owned" ${detail.dlc_ownership_status === "not_owned" ? "selected" : ""}>Not owned</option></select></label>` : "";
    dlcWarning += dlcControl;
    const gateSource = sourceLink({ source_url: detail.availability_source_url, source_title: detail.availability_source_title, locator: detail.availability_locator });
    target.innerHTML = `<p class="eyebrow">Monster Heart</p><h3>${escapeHtml(detail.name)}</h3>${dlcWarning}<div class="callout"><strong>Effect</strong><span>${escapeHtml(detail.effect_text)}</span></div><h4>Earliest verified gate</h4><p>${escapeHtml(detail.available_checkpoint || "Unknown")}${detail.availability_notes ? `<br><span class="muted">${escapeHtml(detail.availability_notes)}</span>` : ""}${gateSource ? `<br>${gateSource}` : ""}</p><h4>Get it</h4><div class="detail-list">${routes.map(route => `<div><strong>${escapeHtml(route.route_label)}</strong><span>${escapeHtml([route.location_text, route.time_period, route.available_checkpoint].filter(Boolean).join(" · "))}</span><span>${escapeHtml(heartRouteSafety(route))}</span><small class="tag">${escapeHtml(heartRouteEvidence(route))}</small>${heartRouteEvidenceLinks(route)}${route.dlc_scope_status === "unknown" ? '<span>DLC scope unknown</span>' : ""}</div>`).join("") || '<p class="empty">No normalized non-DLC acquisition route.</p>'}</div><h4>Effect source</h4><p>${sourceLink(detail)}</p><label class="progress-toggle"><input type="checkbox" data-catalog-progress="heart" data-progress-id="${escapeHtml(detail.heart_id)}" ${detail.owned === true ? "checked" : ""}> Explicitly mark owned</label><p class="muted">${escapeHtml(ownershipNote)} Unknown rates and DLC ownership are not inferred.</p>`;
  } else if (state.domain === "missables") {
    const unresolved = detail.window_status !== "verified";
    target.innerHTML = `<p class="eyebrow">${escapeHtml(detail.severity)} missable</p><h3>${escapeHtml(detail.name)}</h3>${unresolved ? `<div class="uncertain-banner"><strong>Exact cutoff unknown</strong><span>${escapeHtml(detail.window_gap_reason || "Do not use this row as a STOP warning yet.")}</span></div>` : '<span class="tag">Verified window</span>'}<h4>Window</h4><dl><dt>From</dt><dd>${escapeHtml(detail.available_from || "Unknown")}</dd><dt>Until</dt><dd>${escapeHtml(detail.unavailable_after || "Unknown — complete promptly")}</dd></dl><h4>Consequence</h4><p>${escapeHtml(detail.consequence)}</p><p><a href="${escapeHtml(detail.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(detail.source_title)}</a><br><span class="muted">${detail.locator ? escapeHtml(detail.locator) : "Precise locator not yet stored"}</span></p><p class="muted">Confidence: ${escapeHtml(detail.confidence)} · ${escapeHtml(detail.verification_status)}</p><label class="select-label">Recorded result<select data-missable-status="${escapeHtml(detail.missable_id)}" data-previous-status="${escapeHtml(detail.progress_status)}"><option value="unknown" ${detail.progress_status === "unknown" ? "selected" : ""}>Not reported</option><option value="completed" ${detail.progress_status === "completed" ? "selected" : ""}>Completed</option><option value="missed" ${detail.progress_status === "missed" ? "selected" : ""}>Missed · recovery needed</option></select></label><p class="muted">Recording missed blocks 100% advancement until you recover an earlier save or correct the record.</p>`;
  } else if (state.domain === "farms") {
    const strategySource = detail.strategy_source_url ? `<br><a href="${escapeHtml(detail.strategy_source_url)}" target="_blank" rel="noreferrer">Strategy source</a><br><span class="muted">${escapeHtml(detail.strategy_locator)}</span>` : "";
    target.innerHTML = `<p class="eyebrow">${escapeHtml(detail.farm_type)} farm</p><h3>${escapeHtml(detail.target)}</h3><h4>Sourced facts</h4><dl><dt>Location</dt><dd>${escapeHtml(detail.location)}</dd><dt>Period</dt><dd>${escapeHtml(detail.time_period || "Not restricted")}</dd><dt>Available</dt><dd>${escapeHtml(detail.available_checkpoint || detail.available_from)}</dd><dt>Frequency</dt><dd>${escapeHtml(detail.encounter_rate_text || "Numeric rate unpublished")}</dd></dl>${detail.strategy ? `<div class="callout"><strong>Attributed strategy</strong><span>${escapeHtml(detail.strategy)}</span>${strategySource}</div>` : ""}<p><a href="${escapeHtml(detail.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(detail.source_title)}</a><br><span class="muted">${escapeHtml(detail.locator)}</span></p><p class="muted">Confidence: ${escapeHtml(detail.confidence)} · Numeric rate unpublished. Strategy is a recommendation, not a canonical fact.</p><p class="muted">Read-only: farms do not alter player progress.</p>`;
  } else if (state.domain === "source_registry") {
    target.innerHTML = `<p class="eyebrow">${escapeHtml(detail.source_class)}</p><h3>${escapeHtml(detail.title)}</h3><p><a href="${escapeHtml(detail.url)}" target="_blank" rel="noreferrer">Open source</a></p><dl><dt>Publisher</dt><dd>${escapeHtml(detail.publisher)}</dd><dt>Role</dt><dd>${escapeHtml(detail.role)}</dd><dt>Published</dt><dd>${escapeHtml(detail.published_at || "Unknown")}</dd><dt>Updated</dt><dd>${escapeHtml(detail.updated_at || "Unknown")}</dd><dt>Retrieved</dt><dd>${escapeHtml(detail.retrieved_at || "Unknown")}</dd><dt>Status</dt><dd>${escapeHtml(detail.status)}</dd></dl><div class="callout"><strong>Freshness means retrieval only</strong><span>${detail.retrieval_age_days === null ? "Retrieval age is unknown." : `${escapeHtml(detail.retrieval_age_days)} days since retrieval.`} An update date does not prove that every claim is current.</span></div>${detail.notes ? `<p class="muted">${escapeHtml(detail.notes)}</p>` : ""}<p class="muted">Read-only registry.</p>`;
  } else if (state.domain === "achievements") {
    const dependency = detail.dependency_progress || {};
    const counterSemantics = detail.counter_semantics || [];
    const counterConflicts = detail.counter_conflicts || [];
    const unresolvedCounterConflicts = counterConflicts.filter(row => row.status !== "resolved");
    const resolvedCounterConflicts = counterConflicts.filter(row => row.status === "resolved" && row.resolution);
    const count = dependency.known_count === null || dependency.known_count === undefined
      ? `? / ${escapeHtml(dependency.required_count ?? detail.required_count ?? "?")}`
      : `${escapeHtml(dependency.known_count)} / ${escapeHtml(dependency.required_count ?? detail.required_count)}`;
    const label = dependency.status === "complete" ? "Unlocked"
      : dependency.status === "target_met" ? "Requirement met · unlock unrecorded"
      : dependency.status === "partial" ? "Explicit partial progress" : "Progress unknown";
    const semantics = counterSemantics.length ? `<h4>Counter evidence</h4><div class="detail-list">${counterSemantics.map(row => `<div><strong>${escapeHtml(row.predicate.replaceAll("_", " "))}</strong><small class="evidence-strength">Evidence: ${row.evidence?.tier === "two_source" ? "2-source" : "1-source"}</small><span>${escapeHtml(typeof row.value === "string" ? row.value : JSON.stringify(row.value))}</span>${sourceLink(row)}</div>`).join("")}</div>` : "";
    const counterUnknowns = detail.achievement_id === "ach_straight_to_the_point" ? '<div class="uncertain-banner"><strong>Still unknown</strong><span>Whether quick wins also increment Field Day, Monster Masher, or Metal Mangler, and whether counters persist across save slots, New Game, demo transfer, or reset.</span></div>' : "";
    const conflicts = unresolvedCounterConflicts.length ? `<div class="uncertain-banner"><strong>Counter rule conflict — do not assume</strong><span>${escapeHtml(unresolvedCounterConflicts.flatMap(row => row.claims || []).map(row => typeof row.value === "string" ? row.value : JSON.stringify(row.value)).join(" versus "))}</span></div>` : "";
    const resolvedRules = resolvedCounterConflicts.map(row => `<div class="callout"><strong>Resolved counter rule · independently corroborated</strong><span>${escapeHtml(typeof row.resolution.value === "string" ? row.resolution.value : JSON.stringify(row.resolution.value))}. The losing interpretation remains visible below.</span>${sourceLink(row.resolution)}</div>`).join("");
    const requirementSource = detail.requirement_source_url ? `<a href="${escapeHtml(detail.requirement_source_url)}" target="_blank" rel="noreferrer">Requirement source</a><br><span class="muted">${escapeHtml(detail.requirement_locator || "Locator unavailable")}</span>` : sourceLink(detail);
    target.innerHTML = `<p class="eyebrow">${escapeHtml(detail.category)} achievement</p><h3>${escapeHtml(detail.name)}</h3>${conflicts}${resolvedRules}<div class="${dependency.status === "unknown" ? "uncertain-banner" : "callout"}"><strong>${escapeHtml(label)} · ${count}</strong><span>${escapeHtml(dependency.reason || "No dependency status available.")}</span></div><h4>Completion dependency</h4><dl><dt>Requirement</dt><dd>${escapeHtml(detail.description)}</dd><dt>Counter</dt><dd>${escapeHtml(dependency.basis || detail.target_type || "Unknown")}</dd><dt>Evidence status</dt><dd>${escapeHtml(detail.requirement_verification_status || "Not structured")}</dd><dt>Earliest</dt><dd>${escapeHtml(detail.earliest_checkpoint_id || "Unknown")}</dd><dt>Completion gate</dt><dd>${escapeHtml(detail.completion_checkpoint_id || "Unknown")}</dd></dl><p>${requirementSource}</p>${semantics}${counterUnknowns}<p class="muted">Only explicit saved state is counted. Unknown is not zero.</p><label class="progress-toggle"><input type="checkbox" data-catalog-progress="achievement" data-progress-id="${escapeHtml(detail.achievement_id)}" ${detail.unlocked ? "checked" : ""}> Explicitly mark achievement unlocked</label>`;
  } else if (state.domain === "seeds") {
    if (detail.record_type === "effect") {
      target.innerHTML = `<p class="eyebrow">${escapeHtml(detail.variant)} seed</p><h3>${escapeHtml(detail.name)}</h3><div class="callout"><strong>Fixed effect</strong><span>+${escapeHtml(detail.increase_amount)} ${escapeHtml(detail.stat_key.replaceAll("_", " "))}</span></div><dl><dt>Version</dt><dd>${escapeHtml(detail.game_version)}</dd><dt>DLC scope</dt><dd>${escapeHtml(detail.dlc_scope || "Not recorded")}</dd><dt>Confidence</dt><dd>${escapeHtml(detail.confidence)}</dd></dl><p><a href="${escapeHtml(detail.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(detail.source_title)}</a><br><span class="muted">${escapeHtml(detail.locator)}</span></p><p class="muted">Read-only mechanic; inventory is unchanged.</p>`;
    } else {
      const poolKnown = detail.eligible_pool_status === "known";
      const pool = poolKnown ? `<div class="callout"><strong>Verified eligible pool</strong><span>${escapeHtml((detail.eligible_item_names || detail.eligible_items || []).join(" · "))}</span></div><div class="uncertain-banner"><strong>Selection weights unknown</strong><span>Do not assume equal probability or a published draw algorithm.</span></div>` : `<div class="uncertain-banner"><strong>Eligible pool unknown</strong><span>The source confirms a random family reward, but not which Super Seeds are eligible.</span></div>`;
      target.innerHTML = `<p class="eyebrow">Reward rule</p><h3>${escapeHtml(detail.name)}</h3>${pool}<dl><dt>Available</dt><dd>${escapeHtml(detail.available_checkpoint || detail.available_from_checkpoint_id || "Unknown")}</dd><dt>Location</dt><dd>${escapeHtml(detail.location_text)}</dd><dt>Trigger</dt><dd>${escapeHtml(detail.trigger_text)}</dd><dt>Quantity</dt><dd>${escapeHtml(detail.reward_quantity ?? "Unknown")}</dd><dt>Selection</dt><dd>${escapeHtml(detail.selection_method)}</dd><dt>Repeatable</dt><dd>${detail.repeatable ? "Yes" : "No"}</dd><dt>DLC scope</dt><dd>${escapeHtml(detail.dlc_scope || "Not recorded")}</dd></dl><p><a href="${escapeHtml(detail.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(detail.source_title)}</a><br><span class="muted">${escapeHtml(detail.locator)}</span></p><p class="muted">Read-only reward rule.</p>`;
    }
  }
}
async function selectCatalogEntry(id) {
  const domain = state.domain, summary = (state.catalogs[domain] || []).find(row => String(row.id) === String(id));
  state.selectedEntry = summary; renderCatalog();
  if (!["items", "vocations", "monsters", "hearts", "missables", "farms", "source_registry", "seeds", "achievements"].includes(domain)) return;
  const target = $("#catalogDetail"); target.setAttribute("aria-busy", "true"); target.innerHTML = '<p class="empty">Loading details…</p>';
  try { const endpoint = domain === "hearts" ? "monster-hearts" : domain === "source_registry" ? "sources" : domain; const detail = await api(`/${endpoint}/${encodeURIComponent(id)}`); if (state.domain === domain && String(state.selectedEntry?.id) === String(id)) { renderRichDetail(detail, summary); if (mobileLayout()) target.scrollIntoView({ block: "start", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }); } }
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
  if (name === "hearts") Object.assign(entry, { id: row.heart_id, category: row.owned === true ? "owned" : row.available_now === true ? "available" : row.available_now === false ? "later" : "unknown", summary: row.effect_text, location: row.available_checkpoint, completed: row.owned, progress_kind: "heart", source: { title: row.source_title, url: row.source_url, locator: row.locator } });
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
    const parameters = paged ? [`limit=200`, `offset=${offset}`] : [];
    if (name === "farms" && state.checkpoint?.id) parameters.push(`through_checkpoint=${encodeURIComponent(state.checkpoint.id)}`);
    const payload = await api(`/${endpoint}${parameters.length ? `?${parameters.join("&")}` : ""}`);
    const batch = payload[keys[name]] || [];
    rows.push(...batch);
    if (!paged || batch.length < 200) break;
    offset += batch.length;
  } while (true);
  return rows.map(row => normalizeEntry(name, row));
}

async function loadCheckpoint(id) {
  setStatus("Loading checkpoint…");
  state.checkpoint = await api(`/checkpoints/${encodeURIComponent(id)}`);
  delete state.catalogs.farms;
  renderCheckpoint(); setStatus("");
}
async function stepCheckpoint(delta) {
  const select = $("#checkpointSelect"), next = select.selectedIndex + delta;
  if (next < 0 || next >= select.options.length) return;
  select.selectedIndex = next;
  await loadCheckpoint(select.value);
}
async function loadAll() {
  const viewedCheckpoint = state.checkpoint?.id;
  setStatus("Loading guide…");
  const vocationRequest = state.vocations.length ? Promise.resolve(null) : api("/vocations?limit=200");
  const loaded = await Promise.all([api("/dashboard"), api("/checkpoints"), api("/progress"), api("/equipment"), api("/conflicts?include_resolved=1"), api("/evidence-gaps"), vocationRequest]);
  [state.dashboard, state.checkpoints, state.progress, state.equipment, state.conflicts, state.evidenceGaps] = loaded;
  if (loaded[6]) state.vocations = loaded[6].vocations || [];
  renderDashboard(); renderProgress();
  const savedCheckpoint = state.dashboard?.checkpoint?.is_saved ? state.dashboard.checkpoint.id : null;
  const select = $("#checkpointSelect"); select.innerHTML = state.checkpoints.map(c => `<option value="${escapeHtml(c.id)}">${String(c.sequence).padStart(2,"0")} · ${escapeHtml(c.name)}${c.id === savedCheckpoint ? " (saved)" : ""}</option>`).join("");
  const current = savedCheckpoint || (viewedCheckpoint && state.checkpoints.some(row => row.id === viewedCheckpoint) ? viewedCheckpoint : null) || state.dashboard?.checkpoint?.id || state.checkpoints[0]?.id; if (current) { select.value = current; await loadCheckpoint(current); }
  syncSecondaryLedgers();
  if (!$("#phone-setup").hidden) renderPhoneSetup();
  setStatus("");
}
async function refreshPreservingPlayContext(focusSelector = null) {
  const top = window.scrollY, viewedCheckpoint = state.checkpoint?.id, activeDomain = state.domain;
  if (activeDomain) delete state.catalogs[activeDomain];
  await loadAll();
  if (viewedCheckpoint && state.checkpoint?.id !== viewedCheckpoint && state.checkpoints.some(row => row.id === viewedCheckpoint)) {
    $("#checkpointSelect").value = viewedCheckpoint;
    await loadCheckpoint(viewedCheckpoint);
  }
  if (activeDomain) await loadDomain(activeDomain);
  window.scrollTo({ top, behavior: "auto" });
  const focusTarget = focusSelector ? document.querySelector(focusSelector) : null;
  (focusTarget || $("#main")).focus({ preventScroll: true });
}
async function updateProgress(payload, focusSelector = null) {
  setStatus("Saving…");
  const resources = { item: "items", tablet: "tablets", achievement: "achievements", missable: "missables", heart: "monster-hearts" };
  const endpoint = resources[payload.kind] ? `/${resources[payload.kind]}/${encodeURIComponent(payload.id)}` : "/progress";
  const body = endpoint === "/progress" ? payload : { completed: payload.completed };
  await api(endpoint, { method: "PATCH", body: JSON.stringify(body) });
  await refreshPreservingPlayContext(focusSelector); setStatus("Saved");
}
async function saveToggle(control, payload) {
  const requested = control.checked;
  const wasReady = Boolean(state.checkpoint?.advancement_readiness?.can_confirm_and_save_next);
  if (requested && control.closest("#checkpointStop") && !window.confirm("Mark this STOP cleared?")) { control.checked = false; return; }
  const mutationKey = `${payload.kind}:${payload.id}`, focusSelector = controlSelector(control);
  if (state.mutations.has(mutationKey)) { control.checked = !requested; return; }
  control.disabled = true;
  try {
    const saved = await oneMutation(mutationKey, () => updateProgress(payload, focusSelector));
    if (saved) { const becameReady = !wasReady && Boolean(state.checkpoint?.advancement_readiness?.can_confirm_and_save_next); showUndo(becameReady ? "Required work clear · tap Advance when ready." : "Saved.", async () => { await oneMutation(`undo:${mutationKey}`, () => updateProgress({ ...payload, completed: !requested }, focusSelector)); setStatus("Undone"); }); }
  }
  catch (error) {
    console.error(error);
    if (control.isConnected) control.checked = !requested;
    const target = $("#status");
    target.classList.add("error");
    target.textContent = "Save failed. Change was not recorded.";
  } finally { if (control.isConnected) control.disabled = false; }
}
async function recordCommand(command, values) {
  await oneMutation(`command:${command}:${values.join(":")}`, async () => {
    setStatus("Saving explicit state…");
    await api("/progress", { method: "POST", body: JSON.stringify({ command, values }) });
    await refreshPreservingPlayContext(); setStatus("Saved");
  });
}

document.addEventListener("click", event => {
  const ledgerJump = event.target.closest("[data-ledger-jump]");
  if (ledgerJump) {
    const allowed = new Set(["ledgerMedals", "ledgerTablets", "ledgerItems", "ledgerAchievements", "ledgerMissables"]);
    const targetId = ledgerJump.dataset.ledgerJump;
    const ledger = allowed.has(targetId) ? document.getElementById(targetId) : null;
    if (ledger) {
      ledger.open = true;
      window.requestAnimationFrame(() => {
        ledger.querySelector(":scope > summary")?.focus({ preventScroll: true });
        const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        ledger.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
      });
    }
    return;
  }
  const previewCheckpoint = event.target.closest("[data-preview-checkpoint]");
  if (previewCheckpoint) {
    const id = previewCheckpoint.dataset.previewCheckpoint;
    $("#checkpointSelect").value = id;
    loadCheckpoint(id).then(() => $("#checkpointFinderChoice").scrollIntoView({ block: "nearest" })).catch(handleError);
    return;
  }
  const saveFoundCheckpoint = event.target.closest("[data-save-found-checkpoint]");
  if (saveFoundCheckpoint) {
    const id = saveFoundCheckpoint.dataset.saveFoundCheckpoint;
    const checkpoint = state.checkpoints.find(row => row.id === id);
    if (!checkpoint || !window.confirm(`Save ${checkpoint.name} as your current checkpoint?`)) return;
    saveFoundCheckpoint.disabled = true;
    oneMutation("checkpoint-finder", async () => {
      setStatus("Saving confirmed checkpoint…");
      await api(`/checkpoints/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ selected: true, intent: "set" }) });
      await loadAll();
      setStatus("Checkpoint saved");
    }).catch(handleError).finally(() => { if (saveFoundCheckpoint.isConnected) saveFoundCheckpoint.disabled = false; });
    return;
  }
  const powerVocation = event.target.closest("[data-power-vocation-mastered]");
  if (powerVocation) {
    const vocationId = powerVocation.dataset.powerVocationMastered, character = powerVocation.dataset.powerVocationCharacter;
    const path = `/vocations/${encodeURIComponent(vocationId)}`;
    powerVocation.disabled = true;
    oneMutation(`power-vocation:${character}:${vocationId}`, async () => { await api(path, { method: "PATCH", body: JSON.stringify({ character, completed: true }) }); await refreshPreservingPlayContext(); })
      .then(saved => { if (saved) showUndo("Vocation mastery recorded.", () => oneMutation(`undo:power-vocation:${character}:${vocationId}`, async () => { await api(path, { method: "PATCH", body: JSON.stringify({ character, completed: false }) }); await refreshPreservingPlayContext(); })); })
      .catch(handleError)
      .finally(() => { if (powerVocation.isConnected) powerVocation.disabled = false; });
    return;
  }
  const powerEquip = event.target.closest("[data-power-equip-item]");
  if (powerEquip) {
    const { powerEquipItem: itemId, powerEquipCharacter: character, powerEquipSlot: slot } = powerEquip.dataset;
    const member = (state.equipment?.members || []).find(row => row.name === character);
    const previous = member?.standard_slots?.[slot] || null;
    if (previous && previous !== itemId && !window.confirm(`Replace the currently recorded ${slot}?`)) return;
    const path = `/equipment/slots/${encodeURIComponent(character)}/${encodeURIComponent(slot)}`;
    powerEquip.disabled = true;
    oneMutation(`power-equip:${character}:${slot}`, async () => { await api(path, { method: "PATCH", body: JSON.stringify({ item_id: itemId }) }); await refreshPreservingPlayContext(); })
      .then(saved => { if (saved) showUndo("Equipment saved.", () => oneMutation(`undo:power-equip:${character}:${slot}`, async () => { await api(path, { method: "PATCH", body: JSON.stringify({ item_id: previous }) }); await refreshPreservingPlayContext(); })); })
      .catch(handleError)
      .finally(() => { if (powerEquip.isConnected) powerEquip.disabled = false; });
    return;
  }
  const powerOwned = event.target.closest("[data-power-item-owned]");
  if (powerOwned) {
    const itemId = powerOwned.dataset.powerItemOwned;
    powerOwned.disabled = true;
    oneMutation(`power-item:${itemId}`, () => updateProgress({ kind: "item", id: itemId, completed: true }))
      .then(saved => { if (saved) showUndo("Item marked owned.", () => oneMutation(`undo:power-item:${itemId}`, () => updateProgress({ kind: "item", id: itemId, completed: false }))); })
      .catch(handleError)
      .finally(() => { if (powerOwned.isConnected) powerOwned.disabled = false; });
    return;
  }
  const quantitySave = event.target.closest("[data-item-quantity-save]");
  const quantityClear = event.target.closest("[data-item-quantity-clear]");
  if (quantitySave || quantityClear) {
    const itemId = (quantitySave || quantityClear).dataset.itemQuantitySave || (quantitySave || quantityClear).dataset.itemQuantityClear;
    const input = document.querySelector(`[data-item-quantity-input="${CSS.escape(itemId)}"]`);
    const detailItem = state.selectedEntry;
    const previousQuantity = detailItem?.quantity_status === "exact" ? Number(detailItem.quantity) : null;
    const previousObtained = Boolean(detailItem?.obtained);
    const requested = quantityClear ? null : Number(input?.value);
    if (!quantityClear && (!input?.value || !Number.isInteger(requested) || requested < 0 || requested > 99)) { setStatus("Enter an exact total from 0 to 99."); input?.focus(); return; }
    const button = quantitySave || quantityClear, path = `/items/${encodeURIComponent(itemId)}/quantity`;
    button.disabled = true;
    oneMutation(`item-quantity:${itemId}`, async () => { setStatus("Saving explicit quantity…"); await api(path, { method: "PATCH", body: JSON.stringify({ quantity: requested }) }); await loadDomain("items"); await selectCatalogEntry(itemId); setStatus("Saved"); })
      .then(saved => { if (saved) showUndo("Item quantity saved.", () => oneMutation(`undo:item-quantity:${itemId}`, async () => { await api(path, { method: "PATCH", body: JSON.stringify({ quantity: previousQuantity, obtained: previousObtained }) }); await loadDomain("items"); await selectCatalogEntry(itemId); setStatus("Undone"); })); })
      .catch(handleError)
      .finally(() => { if (button.isConnected) button.disabled = false; });
    return;
  }
  const nav = event.target.closest("[data-view]"); if (nav) { event.preventDefault(); showView(nav.dataset.view); focusMainAtTop(); }
  const domain = event.target.closest("[data-domain]"); if (domain) { event.preventDefault(); showDomain(domain.dataset.domain); focusMainAtTop(); }
  const filter = event.target.closest("[data-filter]"); if (filter) { state.filter = filter.dataset.filter; renderCatalog(); }
  const card = event.target.closest("[data-entry-id]"); if (card) selectCatalogEntry(card.dataset.entryId);
  if (event.target.closest("[data-retry]")) { if (state.domain) loadDomain(state.domain).catch(handleError); else loadAll().catch(handleError); }
  if (event.target.closest("[data-reconnect]")) { state.usingCachedData = false; loadAll().catch(handleError); }
  const playJump = event.target.closest("[data-play-jump]"); if (playJump) scrollToPlaySection(playJump.dataset.playJump);
});
$("#menuButton").addEventListener("click", () => { const open = $("#primaryNav").classList.toggle("open"); $("#menuButton").setAttribute("aria-expanded", String(open)); if (open) $("#primaryNav a").focus(); });
$("#refreshButton").addEventListener("click", () => loadAll().catch(handleError));
$("#checkpointSelect").addEventListener("change", event => loadCheckpoint(event.target.value).catch(handleError));
$("#checkpointFinderInput").addEventListener("input", renderCheckpointFinder);
$("#previousCheckpoint").addEventListener("click", () => stepCheckpoint(-1).catch(handleError));
$("#nextCheckpoint").addEventListener("click", () => stepCheckpoint(1).catch(handleError));
$("#mobilePrevious").addEventListener("click", () => { showView("walkthrough"); stepCheckpoint(-1).then(scrollToTop).catch(handleError); });
$("#mobileNext").addEventListener("click", () => { showView("walkthrough"); stepCheckpoint(1).then(scrollToTop).catch(handleError); });
$("#mobilePower").addEventListener("click", () => {
  showView("walkthrough");
  const id = state.checkpoint?.id || (state.dashboard?.checkpoint?.is_saved ? state.dashboard.checkpoint.id : state.checkpoints[0]?.id);
  if (!id) return scrollToTop();
  $("#checkpointSelect").value = id;
  const ready = state.checkpoint?.id === id ? Promise.resolve() : loadCheckpoint(id);
  ready.then(() => scrollToPlaySection("power")).catch(handleError);
});
document.querySelectorAll("[data-mobile-view]").forEach(button => button.addEventListener("click", () => { showView(button.dataset.mobileView); scrollToTop(); }));
$("#mobileCurrent").addEventListener("click", () => {
  showView("walkthrough");
  const id = state.dashboard?.checkpoint?.is_saved ? state.dashboard.checkpoint.id : state.checkpoints[0]?.id;
  if (!id) return scrollToTop();
  $("#checkpointSelect").value = id;
  loadCheckpoint(id).then(scrollToPlayPriority).catch(handleError);
});
$("#setCheckpointButton").addEventListener("click", async () => {
  const id = $("#checkpointSelect").value, previous = state.dashboard?.checkpoint?.is_saved ? state.dashboard.checkpoint.id : null;
  try { const saved = await oneMutation("checkpoint", async () => { setStatus("Saving checkpoint…"); await api(`/checkpoints/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ selected: true, intent: "set" }) }); await refreshPreservingPlayContext("#setCheckpointButton"); setStatus("Checkpoint saved"); }); if (saved && previous && previous !== id) showUndo("Checkpoint saved.", async () => { await oneMutation("undo:checkpoint", async () => { await api(`/checkpoints/${encodeURIComponent(previous)}`, { method: "PATCH", body: JSON.stringify({ selected: true, intent: "set" }) }); await refreshPreservingPlayContext("#setCheckpointButton"); }); }); }
  catch (error) { handleError(error); }
});
$("#advanceCheckpointButton").addEventListener("click", async event => {
  const id = event.currentTarget.dataset.nextCheckpoint, previous = state.dashboard?.checkpoint?.is_saved ? state.dashboard.checkpoint.id : null;
  if (!id || !state.checkpoint?.advancement_readiness?.can_confirm_and_save_next) return;
  if (!window.confirm("Advance the saved checkpoint?")) return;
  try { const saved = await oneMutation("checkpoint", async () => { setStatus("Saving explicit advancement…"); await api(`/checkpoints/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ selected: true, intent: "advance" }) }); await loadAll(); focusPlayPriority(); setStatus("Checkpoint advanced"); }); if (saved && previous) showUndo("Checkpoint advanced.", async () => { await oneMutation("undo:checkpoint", async () => { await api(`/checkpoints/${encodeURIComponent(previous)}`, { method: "PATCH", body: JSON.stringify({ selected: true, intent: "set" }) }); await loadAll(); focusPlayPriority(); }); }); }
  catch (error) { handleError(error); }
});
$("#hideCompleted").addEventListener("change", renderCheckpoint);
$("#partyMemberSelect").addEventListener("change", syncVocationChoices);
$("#partyDetailsMember").addEventListener("change", syncPartyDetails);
$("#medalCountForm").addEventListener("submit", event => { event.preventDefault(); recordCommand("medal-count", [$("#medalCountInput").value]).catch(handleError); });
$("#vocationMasteryForm").addEventListener("submit", async event => {
  event.preventDefault();
  const command = $("#masteryAction").value, character = $("#partyMemberSelect").value, vocationId = $("#masteryVocationSelect").value;
  if (command === "vocation-undo" && !window.confirm("Remove this recorded mastery?")) return;
  try {
    await recordCommand(command, [character, vocationId]);
    const inverse = command === "vocation-mastered" ? "vocation-undo" : "vocation-mastered";
    showUndo(command === "vocation-mastered" ? "Vocation mastery recorded." : "Vocation mastery removed.", () => recordCommand(inverse, [character, vocationId]));
  } catch (error) { handleError(error); }
});
$("#quickMasteryMember").addEventListener("change", syncQuickMasteryChoices);
$("#quickMasteryForm").addEventListener("submit", async event => {
  event.preventDefault();
  const character = $("#quickMasteryMember").value, vocationId = $("#quickMasteryVocation").value;
  const vocationName = $("#quickMasteryVocation").selectedOptions[0]?.textContent || "this vocation";
  if (!window.confirm(`Record ${vocationName} mastered for ${character}?`)) return;
  const submit = event.currentTarget.querySelector('[type="submit"]'); submit.disabled = true;
  try {
    await recordCommand("vocation-mastered", [character, vocationId]);
    $("#quickMastery").open = false;
    showUndo("Vocation mastery recorded.", () => recordCommand("vocation-undo", [character, vocationId]));
  } catch (error) { handleError(error); }
  finally { if (submit.isConnected) submit.disabled = false; }
});
$("#partyDetailsForm").addEventListener("submit", async event => { event.preventDefault(); const values = { character: $("#partyDetailsMember").value, level: $("#partyLevelInput").value || "unknown", primary: $("#primaryVocationSelect").value, secondary: $("#secondaryVocationSelect").value }; try { await recordCommand("party-level", [values.character, values.level]); await recordCommand("party-vocations", [values.character, values.primary, values.secondary]); } catch (error) { handleError(error); } });
$("#quickSetupForm").addEventListener("submit", async event => {
  event.preventDefault();
  const submit = event.currentTarget.querySelector('[type="submit"]');
  const payload = quickSetupPayload();
  const error = $("#quickSetupError"); error.hidden = true;
  if (!payload.active.length) { error.textContent = "Choose at least one active party member."; error.hidden = false; error.focus(); return; }
  const previous = { checkpoint_id: state.progress?.saved_checkpoint || null, active: (state.progress?.party || []).filter(row => row.active).map(row => row.name), members: (state.progress?.party || []).map(row => ({ name: row.name, level: row.level ?? "unknown", primary_vocation: row.primary_vocation || "unknown", secondary_vocation: row.secondary_vocation || "unknown" })) };
  try {
    submit.disabled = true;
    await recordCommand("party-setup", [JSON.stringify(payload)]);
    $("#quickSetup").open = false;
    showUndo("Party plan personalized.", async () => { await recordCommand("party-setup", [JSON.stringify(previous)]); });
  } catch (saveError) {
    console.error(saveError);
    const currentError = $("#quickSetupError"); currentError.textContent = "Could not save party. Nothing was recorded."; currentError.hidden = false; currentError.focus();
  } finally { if (submit.isConnected) submit.disabled = false; }
});
$("#chooseRestoreButton").addEventListener("click", () => $("#restoreFile").click());
$("#restoreFile").addEventListener("change", async event => {
  state.pendingRestore = null;
  $("#restoreConfirm").hidden = true;
  const file = event.target.files[0];
  if (!file) return;
  try {
    const parsed = JSON.parse(await file.text());
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("Backup must contain a JSON object");
    state.pendingRestore = parsed;
    $("#restoreConfirm").hidden = false;
    $("#confirmRestoreButton").focus();
    setStatus(`Backup selected: ${file.name}`);
  } catch (error) { state.pendingRestore = null; handleError(error); }
});
function cancelRestore() { state.pendingRestore = null; $("#restoreFile").value = ""; $("#restoreConfirm").hidden = true; setStatus("Restore cancelled"); $("#chooseRestoreButton").focus(); }
$("#cancelRestoreButton").addEventListener("click", cancelRestore);
$("#confirmRestoreButton").addEventListener("click", async () => {
  if (!state.pendingRestore) return;
  try {
    await oneMutation("state-restore", async () => {
      setStatus("Restoring progress…");
      const result = await api("/state-restore", { method: "POST", body: JSON.stringify({ confirmation: "RESTORE", state: state.pendingRestore }) });
      state.pendingRestore = null; $("#restoreFile").value = ""; $("#restoreConfirm").hidden = true;
      await loadAll(); setStatus(`${result.message} Previous state saved as ${result.recovery_file}.`);
    });
  } catch (error) { handleError(error); }
});
document.addEventListener("change", event => {
  if (event.target.dataset.missableStatus) {
    const control = event.target, missableId = control.dataset.missableStatus;
    const previous = control.dataset.previousStatus || "unknown", requested = control.value;
    if (requested === "missed" && !window.confirm("Record this missable as missed? 100% completion will require recovery from an earlier save.")) { control.value = previous; return; }
    const save = async status => { await api(`/missables/${encodeURIComponent(missableId)}`, { method: "PATCH", body: JSON.stringify({ status }) }); await refreshPreservingPlayContext(`[data-missable-status="${CSS.escape(missableId)}"]`); };
    oneMutation(`missable:${missableId}`, () => save(requested))
      .then(saved => { if (saved) showUndo("Missable result saved.", () => oneMutation(`undo:missable:${missableId}`, () => save(previous))); })
      .catch(error => { control.value = previous; handleError(error); });
    return;
  }
  if (event.target.dataset.dlcEntitlement) {
    const control = event.target, scope = control.dataset.dlcEntitlement;
    const previous = state.selectedEntry?.dlc_ownership_status === "not_owned" ? "not-owned" : state.selectedEntry?.dlc_ownership_status || "unknown";
    const key = `dlc:${scope}`, selector = `[data-dlc-entitlement="${CSS.escape(scope)}"]`;
    if (state.mutations.has(key)) { control.value = previous; return; }
    oneMutation(key, async () => { setStatus("Saving DLC access…"); await api(`/dlc-entitlements/${encodeURIComponent(scope)}`, { method: "PATCH", body: JSON.stringify({ status: control.value }) }); await refreshPreservingPlayContext(selector); setStatus("Saved"); })
      .then(saved => { if (saved) showUndo("DLC access saved.", async () => { await oneMutation(`undo:${key}`, async () => { await api(`/dlc-entitlements/${encodeURIComponent(scope)}`, { method: "PATCH", body: JSON.stringify({ status: previous }) }); await refreshPreservingPlayContext(selector); setStatus("Undone"); }); }); })
      .catch(error => { control.value = previous; handleError(error); });
    return;
  }
  if (event.target.dataset.accessoryCharacter) {
    const control = event.target, character = control.dataset.accessoryCharacter, slot = control.dataset.accessorySlot;
    const path = `/equipment/accessories/${encodeURIComponent(character)}/${slot}`, requested = control.value || null;
    const member = (state.equipment?.members || []).find(row => row.name === character), previous = member?.accessory_slots?.[slot] || null;
    const key = `accessory:${character}:${slot}`, selector = `[data-accessory-character="${CSS.escape(character)}"][data-accessory-slot="${CSS.escape(slot)}"]`;
    if (state.mutations.has(key)) { control.value = previous || ""; return; }
    oneMutation(key, async () => { setStatus("Saving accessory…"); await api(path, { method: "PATCH", body: JSON.stringify({ item_id: requested }) }); await refreshPreservingPlayContext(selector); setStatus("Saved"); })
      .then(saved => { if (saved) showUndo("Accessory saved.", async () => { await oneMutation(`undo:${key}`, async () => { await api(path, { method: "PATCH", body: JSON.stringify({ item_id: previous }) }); await refreshPreservingPlayContext(selector); setStatus("Undone"); }); }); })
      .catch(error => { control.value = previous || ""; handleError(error); });
    return;
  }
  if (event.target.id === "sourcePublisher") { state.sourcePublisher = event.target.value; renderCatalog(); return; }
  if (event.target.id === "sourceFreshness") { state.sourceFreshness = event.target.value; renderCatalog(); return; }
  if (event.target.dataset.actionId) saveToggle(event.target, { kind: "action", id: event.target.dataset.actionId, completed: event.target.checked });
  if (event.target.dataset.medal) saveToggle(event.target, { kind: "medal", id: Number(event.target.dataset.medal), completed: event.target.checked });
  if (event.target.dataset.tabletId) saveToggle(event.target, { kind: "tablet", id: event.target.dataset.tabletId, completed: event.target.checked });
  if (event.target.dataset.itemId) saveToggle(event.target, { kind: "item", id: event.target.dataset.itemId, completed: event.target.checked });
  if (event.target.dataset.achievementId) saveToggle(event.target, { kind: "achievement", id: event.target.dataset.achievementId, completed: event.target.checked });
  if (event.target.dataset.monsterId) saveToggle(event.target, { kind: "monster", id: event.target.dataset.monsterId, completed: event.target.checked });
  if (event.target.dataset.catalogProgress) { const kind = event.target.dataset.catalogProgress; const raw = event.target.dataset.progressId; saveToggle(event.target, { kind, id: kind === "medal" ? Number(raw) : raw, completed: event.target.checked }); }
});
$("#undoButton").addEventListener("click", async () => {
  const action = state.undoAction;
  if (!action) return;
  hideUndo();
  $("#undoButton").disabled = true;
  try { await action(); }
  catch (error) { handleError(error); }
  finally { $("#undoButton").disabled = false; }
});
$("#catalogSearch").addEventListener("input", renderCatalog);
function handleError(error) { console.error(error); const target = $("#status"); target.classList.add("error"); target.innerHTML = `Could not load guide. <button class="secondary" type="button" data-retry>Retry</button>`; }
document.addEventListener("keydown", event => { if (event.key === "Escape" && !$("#restoreConfirm").hidden) { event.preventDefault(); cancelRestore(); return; } if (event.key === "Escape" && $("#primaryNav").classList.contains("open")) { $("#primaryNav").classList.remove("open"); $("#menuButton").setAttribute("aria-expanded", "false"); $("#menuButton").focus(); } });
window.addEventListener("hashchange", () => { const route = location.hash.slice(1) || "dashboard"; if (domains[route]) showDomain(route); else if (document.getElementById(route)) showView(route); });
window.addEventListener("offline", () => { state.hostReachable = false; renderConnectionState(false); });
window.addEventListener("online", () => loadAll().catch(handleError));
document.addEventListener("visibilitychange", () => { if (!document.hidden && (state.hostReachable === false || state.usingCachedData)) loadAll().catch(handleError); });
const initialRoute = location.hash.slice(1) || "dashboard";
if (domains[initialRoute]) showDomain(initialRoute); else showView(initialRoute);
renderConnectionState(false);
if (window.isSecureContext && "serviceWorker" in navigator) {
  let reloadingForWorkerUpdate = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (reloadingForWorkerUpdate) return;
    reloadingForWorkerUpdate = true;
    window.location.reload();
  });
  navigator.serviceWorker.register("/service-worker.js")
    .then(registration => registration.update())
    .catch(error => console.warn("Offline shell unavailable", error));
}
loadAll().catch(handleError);

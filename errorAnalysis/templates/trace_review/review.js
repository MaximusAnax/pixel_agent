/* Taxonomy discovery in-page labeling (multi-annotator, localStorage + server save). */
(function () {
  const cfg = window.REVIEW_CONFIG || {};
  const registered = cfg.registeredAnnotators || ["abdoul", "raghav"];
  const annotatorKey = "taxonomy_review_annotator";
  const packetId = cfg.packetId || "";
  const apiBase = cfg.apiBase || "";

  function currentAnnotator() {
    // The stored picker choice must outrank cfg.annotator: every page bakes in
    // the same build-time default, so cfg-first would silently reset the
    // annotator each time a new page is opened.
    const stored = localStorage.getItem(annotatorKey);
    if (stored && registered.includes(stored)) return stored;
    const fromCfg = cfg.annotator;
    if (fromCfg && registered.includes(fromCfg)) return fromCfg;
    return registered[0];
  }

  function setCurrentAnnotator(id) {
    if (!registered.includes(id)) return;
    localStorage.setItem(annotatorKey, id);
    cfg.annotator = id;
  }

  function storageKey() {
    const ann = currentAnnotator();
    const base = cfg.storageKeyBase || `taxonomy_discovery_${packetId}`.replace(/-/g, "_");
    return `${base}_${ann}`;
  }

  function partnerAnnotator() {
    const me = currentAnnotator();
    return registered.find((id) => id !== me) || "";
  }

  function loadAll() {
    try {
      const raw = localStorage.getItem(storageKey());
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  }

  function saveAll(data) {
    localStorage.setItem(storageKey(), JSON.stringify(data));
  }

  function getEntry() {
    const all = loadAll();
    return all[cfg.labelKey] || {};
  }

  function setEntry(entry) {
    const all = loadAll();
    entry.updated_at = new Date().toISOString();
    all[cfg.labelKey] = entry;
    saveAll(all);
    return entry;
  }

  function renderModeList(container, modes) {
    container.innerHTML = "";
    modes.forEach((mode, idx) => {
      const li = document.createElement("li");
      li.className = "mode-item";
      li.dataset.mode = mode;
      li.innerHTML =
        '<span class="mode-rank">' +
        (idx + 1) +
        "</span>" +
        '<span class="mode-name">' +
        escapeHtml(mode) +
        "</span>" +
        '<button type="button" class="btn-small btn-up" title="Higher priority">↑</button>' +
        '<button type="button" class="btn-small btn-down" title="Lower priority">↓</button>' +
        '<button type="button" class="btn-small btn-remove" title="Remove">×</button>';
      container.appendChild(li);
    });
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function readModes(container) {
    return [...container.querySelectorAll(".mode-item")].map((li) => li.dataset.mode);
  }

  function readForm() {
    const modesEl = document.getElementById("human-modes-list");
    return {
      root_step: parseInt(document.getElementById("root-step")?.value, 10) || null,
      modes_ordered: modesEl ? readModes(modesEl) : [],
      reasoning: document.getElementById("human-reasoning")?.value?.trim() || "",
      confidence: parseFloat(document.getElementById("human-confidence")?.value) || null,
      is_propagated: document.getElementById("is-propagated")?.checked || false,
      propagated_from_step:
        parseInt(document.getElementById("propagated-from-step")?.value, 10) || null,
      evaluator_mismatch: document.getElementById("evaluator-mismatch")?.checked || false,
      taxonomy_issue: document.getElementById("taxonomy-issue")?.value?.trim() || "",
      candidate_new_leaf: document.getElementById("candidate-new-leaf")?.value?.trim() || "",
      notes: document.getElementById("notes")?.value?.trim() || "",
    };
  }

  function fillForm(entry) {
    if (!entry) return;
    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val ?? "";
    };
    set("root-step", entry.root_step);
    set("human-reasoning", entry.reasoning);
    set("human-confidence", entry.confidence);
    set("propagated-from-step", entry.propagated_from_step);
    set("taxonomy-issue", entry.taxonomy_issue);
    set("candidate-new-leaf", entry.candidate_new_leaf);
    set("notes", entry.notes);
    const ip = document.getElementById("is-propagated");
    if (ip) ip.checked = !!entry.is_propagated;
    const em = document.getElementById("evaluator-mismatch");
    if (em) em.checked = !!entry.evaluator_mismatch;
    const modesEl = document.getElementById("human-modes-list");
    if (modesEl) renderModeList(modesEl, entry.modes_ordered || []);
  }

  function showStatus(msg, ok) {
    const el = document.getElementById("save-status");
    if (!el) return;
    el.textContent = msg;
    el.className = ok ? "save-ok" : "save-err";
  }

  async function fetchServerLabels(annotator) {
    if (!apiBase) return null;
    try {
      const res = await fetch(`${apiBase}/api/labels?annotator=${encodeURIComponent(annotator)}`);
      if (!res.ok) return null;
      const data = await res.json();
      return data.labels || {};
    } catch {
      return null;
    }
  }

  async function fetchSummary() {
    if (!apiBase) return null;
    try {
      const res = await fetch(`${apiBase}/api/annotations/summary`);
      if (!res.ok) return null;
      const data = await res.json();
      return data.summary || {};
    } catch {
      return null;
    }
  }

  async function hydrateFromServer() {
    const labels = await fetchServerLabels(currentAnnotator());
    if (!labels) return;
    saveAll(labels);
    if (cfg.page === "episode" && cfg.labelKey) {
      fillForm(labels[cfg.labelKey] || {});
    }
  }

  async function persistServer(entry) {
    if (!apiBase) return false;
    const annotator = currentAnnotator();
    const all = loadAll();
    all[cfg.labelKey] = entry;
    try {
      const res = await fetch(`${apiBase}/api/labels`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ annotator, labels: all }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  async function saveLabels() {
    const entry = readForm();
    setEntry(entry);
    const ok = await persistServer(entry);
    showStatus(
      ok
        ? `Saved as ${currentAnnotator()} (browser + file)`
        : "Saved in browser (run serve script with --annotator)",
      true
    );
  }

  function exportLabels() {
    const payload = {
      schema_version: 2,
      packet_id: packetId,
      annotator: currentAnnotator(),
      exported_at: new Date().toISOString(),
      labels: loadAll(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `annotations_${currentAnnotator()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function importLabels(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result);
        const labels = data.labels || data;
        saveAll(labels);
        fillForm(labels[cfg.labelKey] || {});
        showStatus("Imported labels", true);
      } catch {
        showStatus("Import failed", false);
      }
    };
    reader.readAsText(file);
  }

  function updateAnnotatorBanner() {
    const el = document.getElementById("annotator-banner");
    if (el) {
      el.textContent = `Labeling as: ${currentAnnotator()}`;
      el.dataset.annotator = currentAnnotator();
    }
    const partner = partnerAnnotator();
    const partnerEl = document.getElementById("partner-label-badge");
    if (partnerEl && partner) {
      partnerEl.textContent = `Partner (${partner}): loading…`;
    }
  }

  async function showPartnerLabelOnEpisode() {
    const partner = partnerAnnotator();
    const badge = document.getElementById("partner-label-badge");
    if (!partner || !badge || !cfg.labelKey) return;
    const summary = await fetchSummary();
    const mode = summary?.[partner]?.[cfg.labelKey];
    badge.textContent = mode
      ? `Partner (${partner}): ${mode}`
      : `Partner (${partner}): —`;
  }

  function applySummaryToIndex(summary) {
    document.querySelectorAll("[data-label-key][data-annotator]").forEach((cell) => {
      const key = cell.dataset.labelKey;
      const annotatorId = cell.dataset.annotator;
      const mode = summary?.[annotatorId]?.[key];
      cell.textContent = mode || "—";
      cell.classList.toggle("has-label", !!mode);
    });
  }

  function initAnnotatorPicker() {
    const select = document.getElementById("annotator-select");
    if (!select) return;
    select.innerHTML = "";
    registered.forEach((id) => {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = id;
      select.appendChild(opt);
    });
    select.value = currentAnnotator();
    updateAnnotatorBanner();
    select.addEventListener("change", async () => {
      setCurrentAnnotator(select.value);
      updateAnnotatorBanner();
      await hydrateFromServer();
      if (cfg.page === "index") {
        const summary = await fetchSummary();
        if (summary) applySummaryToIndex(summary);
      }
    });
  }

  function initEpisodePage() {
    initAnnotatorPicker();
    hydrateFromServer().then(() => fillForm(getEntry()));
    showPartnerLabelOnEpisode();

    const modesEl = document.getElementById("human-modes-list");
    const addSelect = document.getElementById("add-mode-select");
    const addBtn = document.getElementById("add-mode-btn");

    if (addBtn && addSelect && modesEl) {
      addBtn.addEventListener("click", () => {
        const mode = addSelect.value;
        if (!mode) return;
        const modes = readModes(modesEl);
        if (!modes.includes(mode)) modes.push(mode);
        renderModeList(modesEl, modes);
      });
      modesEl.addEventListener("click", (e) => {
        const btn = e.target.closest("button");
        if (!btn) return;
        const li = btn.closest(".mode-item");
        if (!li) return;
        let modes = readModes(modesEl);
        const idx = modes.indexOf(li.dataset.mode);
        if (btn.classList.contains("btn-remove")) {
          modes.splice(idx, 1);
        } else if (btn.classList.contains("btn-up") && idx > 0) {
          [modes[idx - 1], modes[idx]] = [modes[idx], modes[idx - 1]];
        } else if (btn.classList.contains("btn-down") && idx < modes.length - 1) {
          [modes[idx + 1], modes[idx]] = [modes[idx], modes[idx + 1]];
        }
        renderModeList(modesEl, modes);
      });
    }

    document.getElementById("btn-save")?.addEventListener("click", saveLabels);
    document.getElementById("btn-export")?.addEventListener("click", exportLabels);
    document.getElementById("import-file")?.addEventListener("change", (e) => {
      if (e.target.files[0]) importLabels(e.target.files[0]);
    });

    setInterval(() => {
      if (document.getElementById("human-reasoning")) setEntry(readForm());
    }, 30000);
  }

  async function initIndexPage() {
    initAnnotatorPicker();
    document.getElementById("btn-export-all")?.addEventListener("click", exportLabels);
    document.getElementById("import-file")?.addEventListener("change", (e) => {
      if (e.target.files[0]) importLabels(e.target.files[0]);
    });

    await hydrateFromServer();
    const summary = await fetchSummary();
    if (summary) {
      applySummaryToIndex(summary);
    } else {
      const all = loadAll();
      const fallback = { [currentAnnotator()]: all };
      applySummaryToIndex(fallback);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      if (cfg.page === "index") initIndexPage();
      else initEpisodePage();
    });
  } else {
    if (cfg.page === "index") initIndexPage();
    else initEpisodePage();
  }
})();

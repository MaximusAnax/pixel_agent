/* Taxonomy discovery in-page labeling (localStorage + optional server save). */
(function () {
  const cfg = window.REVIEW_CONFIG || {};
  const storageKey = cfg.storageKey || "taxonomy_discovery_labels";
  const labelKey = cfg.labelKey || "";
  const apiBase = cfg.apiBase || "";

  function loadAll() {
    try {
      const raw = localStorage.getItem(storageKey);
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  }

  function saveAll(data) {
    localStorage.setItem(storageKey, JSON.stringify(data));
  }

  function getEntry() {
    const all = loadAll();
    return all[labelKey] || {};
  }

  function setEntry(entry) {
    const all = loadAll();
    entry.updated_at = new Date().toISOString();
    all[labelKey] = entry;
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
      reviewer: document.getElementById("reviewer")?.value?.trim() || "",
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
    set("reviewer", entry.reviewer);
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

  async function persistServer(entry) {
    if (!apiBase) return false;
    const all = loadAll();
    all[labelKey] = entry;
    try {
      const res = await fetch(apiBase + "/api/labels", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ labels: all }),
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
    showStatus(ok ? "Saved (browser + file)" : "Saved in browser (use Export or run serve script)", true);
  }

  function exportLabels() {
    const payload = {
      packet_id: cfg.packetId || "",
      exported_at: new Date().toISOString(),
      labels: loadAll(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "human_labels.json";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function importLabels(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result);
        const labels = data.labels || data;
        localStorage.setItem(storageKey, JSON.stringify(labels));
        fillForm(labels[labelKey] || {});
        showStatus("Imported labels", true);
      } catch {
        showStatus("Import failed", false);
      }
    };
    reader.readAsText(file);
  }

  function initEpisodePage() {
    fillForm(getEntry());
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

    // Auto-save draft every 30s
    setInterval(() => {
      if (document.getElementById("human-reasoning")) setEntry(readForm());
    }, 30000);
  }

  function initIndexPage() {
    document.getElementById("btn-export-all")?.addEventListener("click", exportLabels);
    document.getElementById("import-file")?.addEventListener("change", (e) => {
      if (e.target.files[0]) importLabels(e.target.files[0]);
    });
    const all = loadAll();
    document.querySelectorAll("[data-label-key]").forEach((row) => {
      const key = row.dataset.labelKey;
      const entry = all[key];
      const badge = row.querySelector(".human-status");
      if (badge) {
        if (entry?.modes_ordered?.length) {
          badge.textContent = entry.modes_ordered[0];
          badge.classList.add("has-label");
        } else {
          badge.textContent = "—";
        }
      }
    });
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

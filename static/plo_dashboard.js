/**
 * PLO Dashboard — hierarchical drill-down viewer.
 *
 * Levels:
 *   L1  Programs
 *   L2  PLOs per program
 *   L3  CLOs mapped to a PLO (with assessment data)
 *   L4  Course sections per CLO
 */
(function () {
  "use strict";

  /* ── Configuration ──────────────────────────────────────────── */
  const TREE_API = "/api/plo-dashboard/tree";
  const TERMS_API = "/api/terms";
  const PROGRAMS_API = "/api/programs";
  const BINARY_PASS_THRESHOLD = 0.7;
  const DEBOUNCE_MS = 300;

  /* ── DOM references (resolved on init) ─────────────────────── */
  let termSelect, programSelect, refreshBtn, treeContainer;
  let statPrograms, statPlos, statMappedClos, statWithData, statMissingData;

  /* ── State ──────────────────────────────────────────────────── */
  let debounceTimer = null;

  /* ================================================================
   *  Helpers
   * ============================================================= */

  function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function escapeHtml(text) {
    const el = document.createElement("span");
    el.textContent = text;
    return el.innerHTML;
  }

  /**
   * Format assessment data according to the program's display mode.
   *
   * @param {number|null} took   students who took the assessment
   * @param {number|null} passed students who passed
   * @param {string}      mode   "percentage" | "binary" | "both"
   * @returns {{ text: string, cssClass: string }}
   */
  function formatAssessment(took, passed, mode) {
    if (took == null || took === 0) {
      return { text: "N/A", cssClass: "rate-na" };
    }

    const pct = Math.round((passed / took) * 100);
    const binary = pct >= BINARY_PASS_THRESHOLD * 100 ? "S" : "U";

    let cssClass;
    if (pct >= 80) cssClass = "rate-high";
    else if (pct >= 60) cssClass = "rate-mid";
    else cssClass = "rate-low";

    if (mode === "binary") {
      return { text: binary, cssClass };
    }
    if (mode === "both") {
      return { text: binary + " (" + pct + "%)", cssClass };
    }
    // default: percentage
    return { text: pct + "%", cssClass };
  }

  function statusBadgeHtml(status) {
    const colors = {
      approved: "bg-success",
      awaiting_approval: "bg-warning text-dark",
      assigned: "bg-secondary",
      submitted: "bg-info",
      needs_rework: "bg-danger",
      never_coming_in: "bg-dark",
      in_progress: "bg-primary",
      unassigned: "bg-light text-dark border",
    };
    const label = (status || "unknown").replace(/_/g, " ");
    const cls = colors[status] || "bg-secondary";
    return (
      '<span class="badge plo-status-badge ' +
      cls +
      '">' +
      escapeHtml(label) +
      "</span>"
    );
  }

  /* ================================================================
   *  Data fetching
   * ============================================================= */

  async function fetchJson(url) {
    const resp = await fetch(url, {
      headers: {
        Accept: "application/json",
        "X-CSRFToken": csrfToken(),
      },
    });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    return resp.json();
  }

  async function loadFilters() {
    // Terms
    try {
      const data = await fetchJson(TERMS_API);
      const terms = data.terms || data.data || [];
      termSelect.innerHTML = "";
      if (terms.length === 0) {
        termSelect.innerHTML = '<option value="">No terms available</option>';
        return;
      }

      // Find the active / current term
      let defaultTermId = "";
      for (const t of terms) {
        if (t.status === "active" || t.active) {
          defaultTermId = t.id;
          break;
        }
      }
      if (!defaultTermId && terms.length > 0) {
        defaultTermId = terms[terms.length - 1].id; // fallback to last
      }

      // Sort descending by start_date so most recent is first
      terms.sort(function (a, b) {
        return (b.start_date || "").localeCompare(a.start_date || "");
      });

      for (const t of terms) {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = t.name || t.term_code || t.id;
        if (t.id === defaultTermId) opt.selected = true;
        termSelect.appendChild(opt);
      }
    } catch (err) {
      console.error("[PLO Dashboard] Failed to load terms:", err);
      termSelect.innerHTML = '<option value="">Failed to load terms</option>';
    }

    // Programs
    try {
      const data = await fetchJson(PROGRAMS_API);
      const programs = data.programs || data.data || [];
      programSelect.innerHTML = '<option value="">All Programs</option>';
      for (const p of programs) {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent =
          (p.short_name || p.code || "") + " — " + (p.name || "");
        programSelect.appendChild(opt);
      }
    } catch (err) {
      console.error("[PLO Dashboard] Failed to load programs:", err);
    }
  }

  async function loadTree() {
    showLoading();

    const termId = termSelect.value;
    const programId = programSelect.value;
    let url = TREE_API + "?";
    if (termId) url += "term_id=" + encodeURIComponent(termId) + "&";
    if (programId) url += "program_id=" + encodeURIComponent(programId);

    try {
      const json = await fetchJson(url);
      if (!json.success) throw new Error(json.error || "Unknown error");
      renderTree(json.data);
    } catch (err) {
      console.error("[PLO Dashboard] Failed to load tree:", err);
      treeContainer.innerHTML =
        '<div class="alert alert-danger"><i class="fas fa-exclamation-triangle me-2"></i>Failed to load PLO data. Please try again.</div>';
    }
  }

  /* ================================================================
   *  Rendering
   * ============================================================= */

  function showLoading() {
    treeContainer.innerHTML =
      '<div class="text-center py-5">' +
      '<div class="spinner-border text-primary"><span class="visually-hidden">Loading...</span></div>' +
      '<p class="text-muted mt-2">Loading PLO data...</p></div>';
  }

  function renderSummary(summary) {
    statPrograms.textContent = summary.total_programs;
    statPlos.textContent = summary.total_plos;
    statMappedClos.textContent = summary.total_mapped_clos;
    statWithData.textContent = summary.clos_with_data;
    statMissingData.textContent = summary.clos_missing_data;
  }

  function renderTree(data) {
    renderSummary(data.summary);

    const programs = data.programs || [];
    if (programs.length === 0) {
      treeContainer.innerHTML = renderEmptyState(
        "fa-sitemap",
        "No Programs Found",
        "No programs are available for the current filters.",
      );
      return;
    }

    let html = "";
    for (const prog of programs) {
      html += renderProgramCard(prog);
    }
    treeContainer.innerHTML = html;
    attachTreeListeners();
  }

  /* ── L1: Program card ──────────────────────────────────────── */

  function renderProgramCard(prog) {
    const versionBadge = prog.mapping_version
      ? '<span class="badge bg-info plo-mapping-badge ms-2">v' +
        prog.mapping_version +
        "</span>"
      : '<span class="badge bg-warning text-dark plo-mapping-badge ms-2">No mapping</span>';

    let html =
      '<div class="plo-program-card" data-program-id="' +
      escapeHtml(prog.id) +
      '">';
    html +=
      '<div class="plo-program-header" data-toggle="program">' +
      "<div>" +
      '<i class="fas fa-chevron-right plo-expand-icon me-2"></i>' +
      '<span class="program-name">' +
      escapeHtml(prog.short_name || "") +
      " — " +
      escapeHtml(prog.name || "") +
      "</span>" +
      versionBadge +
      "</div>" +
      "<div>" +
      '<span class="badge bg-primary rounded-pill me-1">' +
      prog.plo_count +
      " PLOs</span>" +
      '<span class="badge bg-secondary rounded-pill">' +
      prog.mapped_clo_count +
      " CLOs</span>" +
      "</div>" +
      "</div>";

    html += '<div class="plo-program-body" style="display:none;">';
    if (prog.plos.length === 0) {
      html += renderEmptyState(
        "fa-bullseye",
        "No PLOs Defined",
        "Add program learning outcomes to get started.",
      );
    } else {
      for (const plo of prog.plos) {
        html += renderPloItem(
          plo,
          prog.assessment_display_mode || "percentage",
        );
      }
    }
    html += "</div></div>";
    return html;
  }

  /* ── L2: PLO row ───────────────────────────────────────────── */

  function renderPloItem(plo, displayMode) {
    let html =
      '<div class="plo-item" data-plo-id="' + escapeHtml(plo.id) + '">';
    html +=
      '<div class="plo-item-header" data-toggle="plo">' +
      '<div class="d-flex align-items-center flex-grow-1">' +
      '<i class="fas fa-chevron-right plo-expand-icon me-2"></i>' +
      '<span class="plo-number">' +
      plo.plo_number +
      "</span>" +
      '<span class="plo-description">' +
      escapeHtml(plo.description) +
      "</span>" +
      "</div>" +
      '<span class="badge bg-secondary rounded-pill">' +
      plo.mapped_clo_count +
      " CLOs</span>" +
      "</div>";

    html += '<div class="plo-item-body" style="display:none;">';
    if (plo.mapped_clos.length === 0) {
      html += renderEmptyState(
        "fa-link",
        "No CLO Mappings",
        "No course learning outcomes are mapped to this PLO.",
      );
    } else {
      html += renderCloTable(plo.mapped_clos, displayMode);
    }
    html += "</div></div>";
    return html;
  }

  /* ── L3: CLO table ─────────────────────────────────────────── */

  function renderCloTable(clos, displayMode) {
    let html =
      '<table class="plo-clo-table"><thead><tr>' +
      "<th>CLO</th><th>Course</th><th>Description</th>" +
      "<th>Assessment</th><th>Took</th><th>Passed</th>" +
      "<th>Success</th><th>Status</th>" +
      "</tr></thead><tbody>";

    for (const clo of clos) {
      const assess = formatAssessment(
        clo.students_took,
        clo.students_passed,
        displayMode,
      );

      html +=
        '<tr data-clo-id="' +
        escapeHtml(clo.id) +
        '" data-toggle="clo">' +
        "<td><strong>" +
        escapeHtml(String(clo.clo_number)) +
        "</strong></td>" +
        "<td>" +
        escapeHtml(clo.course_code || "") +
        "</td>" +
        '<td class="text-truncate" style="max-width:250px;" title="' +
        escapeHtml(clo.description || "") +
        '">' +
        escapeHtml(clo.description || "") +
        "</td>" +
        "<td>" +
        escapeHtml(clo.assessment_method || "—") +
        "</td>" +
        "<td>" +
        (clo.students_took != null ? clo.students_took : "—") +
        "</td>" +
        "<td>" +
        (clo.students_passed != null ? clo.students_passed : "—") +
        "</td>" +
        '<td><span class="plo-success-rate ' +
        assess.cssClass +
        '">' +
        assess.text +
        "</span></td>" +
        "<td>" +
        statusBadgeHtml(clo.status) +
        "</td>" +
        "</tr>";

      // Hidden section rows (L4)
      if (clo.sections && clo.sections.length > 0) {
        for (const sec of clo.sections) {
          const secAssess = formatAssessment(
            sec.students_took,
            sec.students_passed,
            displayMode,
          );
          html +=
            '<tr class="plo-section-row" data-parent-clo="' +
            escapeHtml(clo.id) +
            '" style="display:none;">' +
            '<td></td><td colspan="2"><i class="fas fa-indent me-1 text-muted"></i>' +
            "Section " +
            escapeHtml(sec.section_number || "?") +
            " &mdash; " +
            escapeHtml(sec.instructor_name || "Unassigned") +
            "</td>" +
            "<td>" +
            escapeHtml(sec.assessment_tool || "—") +
            "</td>" +
            "<td>" +
            (sec.students_took != null ? sec.students_took : "—") +
            "</td>" +
            "<td>" +
            (sec.students_passed != null ? sec.students_passed : "—") +
            "</td>" +
            '<td><span class="plo-success-rate ' +
            secAssess.cssClass +
            '">' +
            secAssess.text +
            "</span></td>" +
            "<td>" +
            statusBadgeHtml(sec.status) +
            "</td>" +
            "</tr>";
        }
      } else {
        html +=
          '<tr class="plo-section-row" data-parent-clo="' +
          escapeHtml(clo.id) +
          '" style="display:none;">' +
          '<td></td><td colspan="7" class="text-muted fst-italic">No section data for this CLO in the selected term.</td>' +
          "</tr>";
      }
    }

    html += "</tbody></table>";
    return html;
  }

  /* ── Empty state helper ────────────────────────────────────── */

  function renderEmptyState(icon, title, subtitle) {
    return (
      '<div class="plo-empty-state">' +
      '<i class="fas ' +
      icon +
      '"></i>' +
      '<div class="empty-title">' +
      escapeHtml(title) +
      "</div>" +
      '<div class="empty-subtitle">' +
      escapeHtml(subtitle) +
      "</div>" +
      "</div>"
    );
  }

  /* ================================================================
   *  Event listeners (delegated)
   * ============================================================= */

  function attachTreeListeners() {
    // Program expand/collapse
    treeContainer
      .querySelectorAll('[data-toggle="program"]')
      .forEach(function (el) {
        el.addEventListener("click", function () {
          const body = this.nextElementSibling;
          const icon = this.querySelector(".plo-expand-icon");
          if (body.style.display === "none") {
            body.style.display = "";
            if (icon) icon.classList.add("expanded");
          } else {
            body.style.display = "none";
            if (icon) icon.classList.remove("expanded");
          }
        });
      });

    // PLO expand/collapse
    treeContainer
      .querySelectorAll('[data-toggle="plo"]')
      .forEach(function (el) {
        el.addEventListener("click", function () {
          const body = this.nextElementSibling;
          const icon = this.querySelector(".plo-expand-icon");
          if (body.style.display === "none") {
            body.style.display = "";
            if (icon) icon.classList.add("expanded");
          } else {
            body.style.display = "none";
            if (icon) icon.classList.remove("expanded");
          }
        });
      });

    // CLO row expand/collapse → show/hide section rows
    treeContainer
      .querySelectorAll('[data-toggle="clo"]')
      .forEach(function (el) {
        el.addEventListener("click", function () {
          const cloId = this.getAttribute("data-clo-id");
          const isExpanded = this.classList.toggle("expanded");
          const sectionRows = treeContainer.querySelectorAll(
            '[data-parent-clo="' + cloId + '"]',
          );
          sectionRows.forEach(function (row) {
            row.style.display = isExpanded ? "" : "none";
          });
        });
      });
  }

  /* ================================================================
   *  Initialisation
   * ============================================================= */

  function init() {
    termSelect = document.getElementById("ploTermFilter");
    programSelect = document.getElementById("ploProgramFilter");
    refreshBtn = document.getElementById("ploRefreshBtn");
    treeContainer = document.getElementById("ploTreeContainer");
    statPrograms = document.getElementById("statPrograms");
    statPlos = document.getElementById("statPlos");
    statMappedClos = document.getElementById("statMappedClos");
    statWithData = document.getElementById("statWithData");
    statMissingData = document.getElementById("statMissingData");

    if (!treeContainer) return; // not on PLO dashboard page

    // Filter change handlers
    function debouncedLoad() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(loadTree, DEBOUNCE_MS);
    }

    termSelect.addEventListener("change", debouncedLoad);
    programSelect.addEventListener("change", debouncedLoad);
    refreshBtn.addEventListener("click", function () {
      loadTree();
    });

    // Initial load
    loadFilters().then(function () {
      loadTree();
    });
  }

  /** Set DOM references without starting async operations (for testing). */
  function _setDomRefs() {
    termSelect = document.getElementById("ploTermFilter");
    programSelect = document.getElementById("ploProgramFilter");
    refreshBtn = document.getElementById("ploRefreshBtn");
    treeContainer = document.getElementById("ploTreeContainer");
    statPrograms = document.getElementById("statPrograms");
    statPlos = document.getElementById("statPlos");
    statMappedClos = document.getElementById("statMappedClos");
    statWithData = document.getElementById("statWithData");
    statMissingData = document.getElementById("statMissingData");
  }

  document.addEventListener("DOMContentLoaded", init);

  // Expose functions for testing
  globalThis.PloDashboard = { formatAssessment: formatAssessment };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      formatAssessment: formatAssessment,
      statusBadgeHtml: statusBadgeHtml,
      renderEmptyState: renderEmptyState,
      renderProgramCard: renderProgramCard,
      renderPloItem: renderPloItem,
      renderCloTable: renderCloTable,
      escapeHtml: escapeHtml,
      csrfToken: csrfToken,
      fetchJson: fetchJson,
      showLoading: showLoading,
      renderSummary: renderSummary,
      renderTree: renderTree,
      attachTreeListeners: attachTreeListeners,
      loadFilters: loadFilters,
      loadTree: loadTree,
      init: init,
      _setDomRefs: _setDomRefs,
    };
  }
})();

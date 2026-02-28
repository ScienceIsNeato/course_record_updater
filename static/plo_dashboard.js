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
  const TERMS_API = "/api/terms?all=true";
  const PROGRAMS_API = "/api/programs";
  const BINARY_PASS_THRESHOLD = 0.7;
  const DEBOUNCE_MS = 300;

  /* ── DOM references (resolved on init) ─────────────────────── */
  let termSelect, programSelect, displayModeSelect, treeContainer;
  let statPrograms, statPlos, statMappedClos, statWithData, statMissingData;
  let createPloBtn, mapCloBtn, expandAllBtn, collapseAllBtn;

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
   * Show a diagnostic message in the Map CLO modal alert area.
   * @param {string} message  Text to display
   * @param {string} type     Bootstrap alert type: "info", "warning", "danger"
   */
  function showMapCloAlert(message, type) {
    var alertEl = document.getElementById("mapCloModalAlert");
    if (alertEl) {
      alertEl.textContent = message;
      alertEl.className = "alert alert-" + (type || "info");
    }
  }

  /** Hide the Map CLO modal alert area. */
  function hideMapCloAlert() {
    var alertEl = document.getElementById("mapCloModalAlert");
    if (alertEl) {
      alertEl.className = "alert d-none";
      alertEl.textContent = "";
    }
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

    const safePassed = passed != null ? passed : 0;
    const pct = Math.round((safePassed / took) * 100);
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

  async function postJson(url, body) {
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-CSRFToken": csrfToken(),
      },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    return resp.json();
  }

  /** Return the currently selected display mode from the dropdown. */
  function getDisplayMode() {
    return displayModeSelect ? displayModeSelect.value : "percentage";
  }

  async function loadFilters() {
    // Terms
    try {
      const data = await fetchJson(TERMS_API);
      const terms = data.terms || data.data || [];
      termSelect.innerHTML = "";
      if (terms.length === 0) {
        termSelect.innerHTML = '<option value="">No terms available</option>';
      } else {
        // Normalize: API may return term_id instead of id
        for (const t of terms) {
          if (!t.id && t.term_id) t.id = t.term_id;
          if (!t.name && t.term_name) t.name = t.term_name;
        }

        // Sort descending by start_date so most recent is first
        terms.sort(function (a, b) {
          return (b.start_date || "").localeCompare(a.start_date || "");
        });

        // Find the active / current term (after sort)
        let defaultTermId = "";
        for (const t of terms) {
          if (t.status === "active" || t.active) {
            defaultTermId = t.id;
            break;
          }
        }
        if (!defaultTermId && terms.length > 0) {
          defaultTermId = terms[0].id; // fallback to most recent (first after sort)
        }

        for (const t of terms) {
          const opt = document.createElement("option");
          opt.value = t.id;
          opt.textContent = t.name || t.term_code || t.id;
          if (t.id === defaultTermId) opt.selected = true;
          termSelect.appendChild(opt);
        }
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
        if (!p.id && p.program_id) p.id = p.program_id;
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

    const mode = getDisplayMode();
    let html = "";
    for (const prog of programs) {
      html += renderProgramCard(prog, mode);
    }
    treeContainer.innerHTML = html;
    attachTreeListeners();
  }

  /* ── L1: Program card ──────────────────────────────────────── */

  function renderProgramCard(prog, modeOverride) {
    const displayMode =
      modeOverride || prog.assessment_display_mode || "percentage";
    const versionBadge = prog.mapping_version
      ? '<span class="badge bg-info plo-mapping-badge ms-2">v' +
        escapeHtml(String(prog.mapping_version)) +
        "</span>"
      : '<span class="badge bg-warning text-dark plo-mapping-badge ms-2">No mapping</span>';

    let html =
      '<div class="plo-program-card" data-program-id="' +
      escapeHtml(prog.id) +
      '">';
    var progAssess = formatAssessment(
      prog.students_took,
      prog.students_passed,
      displayMode,
    );
    var progAssessHtml =
      prog.students_took != null
        ? '<span class="plo-success-rate ' +
          progAssess.cssClass +
          ' ms-2">' +
          progAssess.text +
          "</span>"
        : "";

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
      '<div class="d-flex align-items-center gap-2">' +
      progAssessHtml +
      '<span class="badge bg-primary rounded-pill">' +
      escapeHtml(String(prog.plo_count)) +
      " PLOs</span>" +
      '<span class="badge bg-secondary rounded-pill">' +
      escapeHtml(String(prog.mapped_clo_count)) +
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
        html += renderPloItem(plo, displayMode);
      }
    }
    html += "</div></div>";
    return html;
  }

  /* ── L2: PLO row ───────────────────────────────────────────── */

  function renderPloItem(plo, displayMode) {
    var ploAssess = formatAssessment(
      plo.students_took,
      plo.students_passed,
      displayMode,
    );
    var ploAssessHtml =
      plo.students_took != null
        ? '<span class="plo-success-rate ' +
          ploAssess.cssClass +
          '">' +
          ploAssess.text +
          "</span>"
        : "";

    let html =
      '<div class="plo-item" data-plo-id="' + escapeHtml(plo.id) + '">';
    html +=
      '<div class="plo-item-header" data-toggle="plo">' +
      '<div class="d-flex align-items-center">' +
      '<i class="fas fa-chevron-right plo-expand-icon me-2"></i>' +
      '<span class="plo-number">' +
      escapeHtml(String(plo.plo_number)) +
      "</span>" +
      '<span class="plo-description">' +
      escapeHtml(plo.description) +
      "</span>" +
      "</div>" +
      '<div class="d-flex align-items-center gap-2 ms-auto plo-item-right">' +
      '<span class="badge bg-secondary rounded-pill">' +
      escapeHtml(String(plo.mapped_clo_count)) +
      " CLOs</span>" +
      ploAssessHtml +
      "</div>" +
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
      "<th>Assessment</th><th>Status</th>" +
      '<th class="text-end">Took</th><th class="text-end">Passed</th>' +
      '<th class="text-end">Score</th>' +
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
        statusBadgeHtml(clo.status) +
        "</td>" +
        '<td class="text-end">' +
        (clo.students_took != null ? clo.students_took : "—") +
        "</td>" +
        '<td class="text-end">' +
        (clo.students_passed != null ? clo.students_passed : "—") +
        "</td>" +
        '<td class="text-end"><span class="plo-success-rate ' +
        assess.cssClass +
        '">' +
        assess.text +
        "</span></td>" +
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
            statusBadgeHtml(sec.status) +
            "</td>" +
            '<td class="text-end">' +
            (sec.students_took != null ? sec.students_took : "—") +
            "</td>" +
            '<td class="text-end">' +
            (sec.students_passed != null ? sec.students_passed : "—") +
            "</td>" +
            '<td class="text-end"><span class="plo-success-rate ' +
            secAssess.cssClass +
            '">' +
            secAssess.text +
            "</span></td>" +
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
    // Sanitize icon class: only allow letters, digits, hyphens
    const safeIcon = (icon || "").replace(/[^a-zA-Z0-9-]/g, "");
    return (
      '<div class="plo-empty-state">' +
      '<i class="fas ' +
      safeIcon +
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
    treeContainer = document.getElementById("ploTreeContainer");
    statPrograms = document.getElementById("statPrograms");
    statPlos = document.getElementById("statPlos");
    statMappedClos = document.getElementById("statMappedClos");
    statWithData = document.getElementById("statWithData");
    statMissingData = document.getElementById("statMissingData");
    displayModeSelect = document.getElementById("ploDisplayMode");
    createPloBtn = document.getElementById("createPloBtn");
    mapCloBtn = document.getElementById("mapCloBtn");
    expandAllBtn = document.getElementById("expandAllBtn");
    collapseAllBtn = document.getElementById("collapseAllBtn");

    if (!treeContainer) return; // not on PLO dashboard page

    // Filter change handlers
    function debouncedLoad() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(loadTree, DEBOUNCE_MS);
    }

    termSelect.addEventListener("change", debouncedLoad);
    programSelect.addEventListener("change", debouncedLoad);

    // Display mode change → re-render tree without re-fetch
    if (displayModeSelect) {
      displayModeSelect.addEventListener("change", function () {
        loadTree();
      });
    }

    // Expand / Collapse all levels
    if (expandAllBtn) {
      expandAllBtn.addEventListener("click", function () {
        treeContainer
          .querySelectorAll(".plo-program-body")
          .forEach(function (el) {
            el.style.display = "";
          });
        treeContainer.querySelectorAll(".plo-item-body").forEach(function (el) {
          el.style.display = "";
        });
        treeContainer
          .querySelectorAll(".plo-expand-icon")
          .forEach(function (el) {
            el.classList.add("expanded");
          });
      });
    }
    if (collapseAllBtn) {
      collapseAllBtn.addEventListener("click", function () {
        treeContainer
          .querySelectorAll(".plo-program-body")
          .forEach(function (el) {
            el.style.display = "none";
          });
        treeContainer.querySelectorAll(".plo-item-body").forEach(function (el) {
          el.style.display = "none";
        });
        treeContainer
          .querySelectorAll(".plo-expand-icon")
          .forEach(function (el) {
            el.classList.remove("expanded");
          });
        treeContainer
          .querySelectorAll(".plo-section-row")
          .forEach(function (el) {
            el.style.display = "none";
          });
        treeContainer
          .querySelectorAll('[data-toggle="clo"].expanded')
          .forEach(function (el) {
            el.classList.remove("expanded");
          });
      });
    }

    // Create PLO modal
    if (createPloBtn) {
      createPloBtn.addEventListener("click", function () {
        var modal = document.getElementById("ploModal");
        if (modal) {
          var programDropdown = document.getElementById("ploModalProgram");
          if (programDropdown && programSelect) {
            programDropdown.innerHTML = "";
            Array.from(programSelect.options).forEach(function (opt) {
              if (opt.value) {
                var o = document.createElement("option");
                o.value = opt.value;
                o.textContent = opt.textContent;
                programDropdown.appendChild(o);
              }
            });
          }
          // eslint-disable-next-line no-undef
          var bsModal = new bootstrap.Modal(modal);
          bsModal.show();
        }
      });
    }

    // Create PLO form submit
    var ploForm = document.getElementById("ploForm");
    if (ploForm) {
      ploForm.addEventListener("submit", function (e) {
        e.preventDefault();
        var programId = document.getElementById("ploModalProgram").value;
        var ploDescription = document.getElementById(
          "ploModalDescription",
        ).value;
        if (!programId || !ploDescription) return;
        postJson("/api/programs/" + programId + "/plos", {
          description: ploDescription,
        }).then(function () {
          // eslint-disable-next-line no-undef
          var modal = bootstrap.Modal.getInstance(
            document.getElementById("ploModal"),
          );
          if (modal) modal.hide();
          ploForm.reset();
          loadTree();
        });
      });
    }

    // Map CLO to PLO modal — open handler
    if (mapCloBtn) {
      mapCloBtn.addEventListener("click", function () {
        var modal = document.getElementById("mapCloModal");
        if (modal) {
          var programDropdown = document.getElementById("mapCloModalProgram");
          if (programDropdown && programSelect) {
            programDropdown.innerHTML = "";
            Array.from(programSelect.options).forEach(function (opt) {
              if (opt.value) {
                var o = document.createElement("option");
                o.value = opt.value;
                o.textContent = opt.textContent;
                programDropdown.appendChild(o);
              }
            });
            // Reset dependent controls
            var ploDropdown = document.getElementById("mapCloModalPlo");
            if (ploDropdown)
              ploDropdown.innerHTML = '<option value="">Select a PLO…</option>';
            var picker = document.getElementById("mapCloPickerContainer");
            if (picker) picker.style.display = "none";
            hideMapCloAlert();
            // Auto-trigger PLO fetch for first selected program
            if (programDropdown.value) {
              programDropdown.dispatchEvent(new Event("change"));
            }
          }
          // eslint-disable-next-line no-undef
          var bsModal = new bootstrap.Modal(modal);
          bsModal.show();
        }
      });
    }

    // Map CLO modal — program change → load PLOs
    var mapCloModalProgram = document.getElementById("mapCloModalProgram");
    if (mapCloModalProgram) {
      mapCloModalProgram.addEventListener("change", function () {
        var programId = mapCloModalProgram.value;
        var ploDropdown = document.getElementById("mapCloModalPlo");
        var picker = document.getElementById("mapCloPickerContainer");
        if (ploDropdown)
          ploDropdown.innerHTML = '<option value="">Select a PLO…</option>';
        if (picker) picker.style.display = "none";
        hideMapCloAlert();
        if (!programId) return;
        fetchJson("/api/programs/" + programId + "/plos").then(function (data) {
          var plos = data.plos || [];
          ploDropdown.innerHTML = '<option value="">Select a PLO…</option>';
          plos.forEach(function (plo) {
            var o = document.createElement("option");
            o.value = plo.id;
            o.textContent =
              "PLO " + plo.plo_number + ": " + (plo.description || "");
            ploDropdown.appendChild(o);
          });
          if (plos.length === 0) {
            showMapCloAlert(
              "No PLOs defined for this program. Create one using the \u201c+ New PLO\u201d button.",
              "info",
            );
          }
        });
      });
    }

    // Map CLO modal — PLO change → load cherry-picker data
    var mapCloModalPlo = document.getElementById("mapCloModalPlo");
    if (mapCloModalPlo) {
      mapCloModalPlo.addEventListener("change", function () {
        var programId = (mapCloModalProgram || {}).value;
        var picker = document.getElementById("mapCloPickerContainer");
        if (picker) picker.style.display = "none";
        hideMapCloAlert();
        if (!programId || !mapCloModalPlo.value) return;
        fetchJson(
          "/api/programs/" +
            programId +
            "/plos/" +
            mapCloModalPlo.value +
            "/clo-picker",
        ).then(function (data) {
          var mapped = data.mapped || [];
          var available = data.available || [];
          var courseCount = data.course_count || 0;
          var totalCloCount = data.total_clo_count || 0;

          // Diagnostic empty-state messages
          if (courseCount === 0) {
            showMapCloAlert(
              "This program has no courses linked. Go to the Programs admin page to associate courses with this program.",
              "warning",
            );
            return;
          }
          if (totalCloCount === 0) {
            showMapCloAlert(
              "The courses in this program don\u2019t have any learning outcomes yet. Add CLOs to courses before mapping them to PLOs.",
              "info",
            );
            return;
          }

          // Render cherry picker
          renderPickerPanel("mappedCloList", mapped);
          renderPickerPanel("availableCloList", available);
          updatePickerCounts();
          if (picker) picker.style.display = "";
        });
      });
    }

    // Cherry picker — move buttons
    var moveCloLeft = document.getElementById("moveCloLeft");
    var moveCloRight = document.getElementById("moveCloRight");

    if (moveCloLeft) {
      moveCloLeft.addEventListener("click", function () {
        moveCheckedItems("availableCloList", "mappedCloList");
        updatePickerCounts();
      });
    }
    if (moveCloRight) {
      moveCloRight.addEventListener("click", function () {
        moveCheckedItems("mappedCloList", "availableCloList");
        updatePickerCounts();
      });
    }

    // Save Mappings button
    var mapCloSaveBtn = document.getElementById("mapCloSaveBtn");
    if (mapCloSaveBtn) {
      mapCloSaveBtn.addEventListener("click", function () {
        var programId = (document.getElementById("mapCloModalProgram") || {})
          .value;
        var ploId = (document.getElementById("mapCloModalPlo") || {}).value;
        if (!programId || !ploId) return;

        var mappedList = document.getElementById("mappedCloList");
        var cloIds = [];
        if (mappedList) {
          mappedList
            .querySelectorAll('input[type="checkbox"]')
            .forEach(function (cb) {
              cloIds.push(cb.value);
            });
        }

        // PUT to sync endpoint
        fetch(
          "/api/programs/" + programId + "/plos/" + ploId + "/clo-mappings",
          {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
              Accept: "application/json",
              "X-CSRFToken": csrfToken(),
            },
            body: JSON.stringify({ clo_ids: cloIds }),
          },
        )
          .then(function (resp) {
            if (!resp.ok) throw new Error("HTTP " + resp.status);
            return resp.json();
          })
          .then(function () {
            showMapCloAlert("Mappings saved to draft successfully.", "success");
            loadTree();
          })
          .catch(function (err) {
            showMapCloAlert("Error saving mappings: " + err.message, "danger");
          });
      });
    }

    // Publish draft button
    var mapCloPublishBtn = document.getElementById("mapCloPublishBtn");
    if (mapCloPublishBtn) {
      mapCloPublishBtn.addEventListener("click", function () {
        var programId = (document.getElementById("mapCloModalProgram") || {})
          .value;
        if (!programId) return;

        // Get draft, then publish it
        postJson("/api/programs/" + programId + "/plo-mappings/draft", {})
          .then(function (draftData) {
            var mappingId = draftData.mapping.id;
            return postJson(
              "/api/programs/" +
                programId +
                "/plo-mappings/" +
                mappingId +
                "/publish",
              {},
            );
          })
          .then(function () {
            // eslint-disable-next-line no-undef
            var modal = bootstrap.Modal.getInstance(
              document.getElementById("mapCloModal"),
            );
            if (modal) modal.hide();
            loadTree();
          })
          .catch(function (err) {
            showMapCloAlert("Error: " + err.message, "danger");
          });
      });
    }

    // Initial load
    loadFilters().then(function () {
      loadTree();
    });
  }

  /* ================================================================
   *  Cherry-picker helpers
   * ============================================================= */

  /**
   * Render a list of CLOs into a picker panel.
   * @param {string} listId  DOM id of the list-group container
   * @param {Array}  clos    Array of CLO objects
   */
  function renderPickerPanel(listId, clos) {
    var list = document.getElementById(listId);
    if (!list) return;
    list.innerHTML = "";

    if (clos.length === 0) {
      list.innerHTML =
        '<div class="text-center text-muted py-3 small">No CLOs</div>';
      return;
    }

    clos.forEach(function (clo) {
      var label = document.createElement("label");
      label.className =
        "list-group-item list-group-item-action d-flex align-items-start gap-2 py-2";

      var cb = document.createElement("input");
      cb.type = "checkbox";
      cb.className = "form-check-input mt-1";
      cb.value = clo.outcome_id;

      var div = document.createElement("div");
      var courseCode =
        (clo.course && (clo.course.course_number || clo.course.course_code)) ||
        "";
      var title = document.createElement("div");
      title.className = "fw-semibold small";
      title.textContent =
        courseCode + " CLO " + clo.clo_number + ": " + (clo.description || "");

      div.appendChild(title);

      if (clo.mapped_to_plo_id) {
        var badge = document.createElement("span");
        badge.className = "badge bg-warning text-dark mt-1";
        badge.textContent = "Mapped to another PLO";
        div.appendChild(badge);
      }

      label.appendChild(cb);
      label.appendChild(div);
      list.appendChild(label);
    });
  }

  /** Move checked items from one picker panel to another. */
  function moveCheckedItems(fromId, toId) {
    var fromList = document.getElementById(fromId);
    var toList = document.getElementById(toId);
    if (!fromList || !toList) return;

    // Remove "No CLOs" placeholder if present in target
    var placeholder = toList.querySelector(".text-center.text-muted");
    if (placeholder) placeholder.remove();

    var checked = fromList.querySelectorAll('input[type="checkbox"]:checked');
    checked.forEach(function (cb) {
      var item = cb.closest(".list-group-item");
      if (item) {
        cb.checked = false;
        // Remove "Mapped to another PLO" badge when moving to mapped panel
        var badge = item.querySelector(".badge.bg-warning");
        if (badge) badge.remove();
        toList.appendChild(item);
      }
    });

    // Show placeholder if source is now empty
    if (fromList.children.length === 0) {
      fromList.innerHTML =
        '<div class="text-center text-muted py-3 small">No CLOs</div>';
    }
  }

  /** Update the count badges on both cherry-picker panels. */
  function updatePickerCounts() {
    var mappedList = document.getElementById("mappedCloList");
    var availableList = document.getElementById("availableCloList");
    var mappedCount = document.getElementById("mappedCloCount");
    var availableCount = document.getElementById("availableCloCount");

    if (mappedCount && mappedList) {
      mappedCount.textContent = mappedList.querySelectorAll(
        'input[type="checkbox"]',
      ).length;
    }
    if (availableCount && availableList) {
      availableCount.textContent = availableList.querySelectorAll(
        'input[type="checkbox"]',
      ).length;
    }
  }

  /** Set DOM references without starting async operations (for testing). */
  function _setDomRefs() {
    termSelect = document.getElementById("ploTermFilter");
    programSelect = document.getElementById("ploProgramFilter");
    treeContainer = document.getElementById("ploTreeContainer");
    statPrograms = document.getElementById("statPrograms");
    statPlos = document.getElementById("statPlos");
    statMappedClos = document.getElementById("statMappedClos");
    statWithData = document.getElementById("statWithData");
    statMissingData = document.getElementById("statMissingData");
    displayModeSelect = document.getElementById("ploDisplayMode");
    createPloBtn = document.getElementById("createPloBtn");
    mapCloBtn = document.getElementById("mapCloBtn");
    expandAllBtn = document.getElementById("expandAllBtn");
    collapseAllBtn = document.getElementById("collapseAllBtn");
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
      postJson: postJson,
      getDisplayMode: getDisplayMode,
      showLoading: showLoading,
      renderSummary: renderSummary,
      renderTree: renderTree,
      attachTreeListeners: attachTreeListeners,
      loadFilters: loadFilters,
      loadTree: loadTree,
      init: init,
      _setDomRefs: _setDomRefs,
      showMapCloAlert: showMapCloAlert,
      hideMapCloAlert: hideMapCloAlert,
      renderPickerPanel: renderPickerPanel,
      moveCheckedItems: moveCheckedItems,
      updatePickerCounts: updatePickerCounts,
    };
  }
})();

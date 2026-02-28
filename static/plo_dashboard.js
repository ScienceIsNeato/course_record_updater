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
  let termSelect, programSelect, displayModeSelect, refreshBtn, treeContainer;
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
    refreshBtn = document.getElementById("ploRefreshBtn");
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
    refreshBtn.addEventListener("click", function () {
      loadTree();
    });

    // Display mode change → re-render tree without re-fetch
    if (displayModeSelect) {
      displayModeSelect.addEventListener("change", function () {
        loadTree();
      });
    }

    // Expand / Collapse all PLO items
    if (expandAllBtn) {
      expandAllBtn.addEventListener("click", function () {
        var items = treeContainer.querySelectorAll(".plo-item-content");
        items.forEach(function (el) {
          el.style.display = "";
        });
        var chevrons = treeContainer.querySelectorAll(".plo-item-chevron");
        chevrons.forEach(function (el) {
          el.classList.remove("fa-chevron-right");
          el.classList.add("fa-chevron-down");
        });
      });
    }
    if (collapseAllBtn) {
      collapseAllBtn.addEventListener("click", function () {
        var items = treeContainer.querySelectorAll(".plo-item-content");
        items.forEach(function (el) {
          el.style.display = "none";
        });
        var chevrons = treeContainer.querySelectorAll(".plo-item-chevron");
        chevrons.forEach(function (el) {
          el.classList.remove("fa-chevron-down");
          el.classList.add("fa-chevron-right");
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

    // Map CLO to PLO modal
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
            // Reset dependent dropdowns
            var ploDropdown = document.getElementById("mapCloModalPlo");
            if (ploDropdown)
              ploDropdown.innerHTML = '<option value="">Select a PLO…</option>';
            var cloDropdown = document.getElementById("mapCloModalClo");
            if (cloDropdown)
              cloDropdown.innerHTML = '<option value="">Select a CLO…</option>';
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
        var cloDropdown = document.getElementById("mapCloModalClo");
        if (ploDropdown)
          ploDropdown.innerHTML = '<option value="">Select a PLO…</option>';
        if (cloDropdown)
          cloDropdown.innerHTML = '<option value="">Select a CLO…</option>';
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
        });
      });
    }

    // Map CLO modal — PLO change → load unmapped CLOs
    var mapCloModalPlo = document.getElementById("mapCloModalPlo");
    if (mapCloModalPlo) {
      mapCloModalPlo.addEventListener("change", function () {
        var programId = (mapCloModalProgram || {}).value;
        var cloDropdown = document.getElementById("mapCloModalClo");
        if (cloDropdown)
          cloDropdown.innerHTML = '<option value="">Select a CLO…</option>';
        if (!programId || !mapCloModalPlo.value) return;
        fetchJson(
          "/api/programs/" + programId + "/plo-mappings/unmapped-clos",
        ).then(function (data) {
          var clos = data.unmapped_clos || [];
          cloDropdown.innerHTML = '<option value="">Select a CLO…</option>';
          clos.forEach(function (clo) {
            var o = document.createElement("option");
            o.value = clo.outcome_id;
            o.textContent =
              clo.course_code +
              " CLO " +
              clo.clo_number +
              ": " +
              (clo.description || "");
            cloDropdown.appendChild(o);
          });
        });
      });
    }

    // Map CLO form submit — create draft + add entry
    var mapCloForm = document.getElementById("mapCloForm");
    if (mapCloForm) {
      mapCloForm.addEventListener("submit", function (e) {
        e.preventDefault();
        var programId = (document.getElementById("mapCloModalProgram") || {})
          .value;
        var ploId = (document.getElementById("mapCloModalPlo") || {}).value;
        var cloId = (document.getElementById("mapCloModalClo") || {}).value;
        if (!programId || !ploId || !cloId) return;

        // Get or create draft, then add entry
        postJson("/api/programs/" + programId + "/plo-mappings/draft", {})
          .then(function (draftData) {
            var mappingId = draftData.mapping.id;
            return postJson(
              "/api/programs/" +
                programId +
                "/plo-mappings/" +
                mappingId +
                "/entries",
              { program_outcome_id: ploId, course_outcome_id: cloId },
            );
          })
          .then(function () {
            // Show success, hide modal, reload tree
            // eslint-disable-next-line no-undef
            var modal = bootstrap.Modal.getInstance(
              document.getElementById("mapCloModal"),
            );
            if (modal) modal.hide();
            mapCloForm.reset();
            loadTree();
          })
          .catch(function (err) {
            var alertEl = document.getElementById("mapCloModalAlert");
            if (alertEl) {
              alertEl.textContent = "Error: " + err.message;
              alertEl.classList.remove("d-none");
              alertEl.classList.add("alert-danger");
            }
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
            var alertEl = document.getElementById("mapCloModalAlert");
            if (alertEl) {
              alertEl.textContent = "Error: " + err.message;
              alertEl.classList.remove("d-none");
              alertEl.classList.add("alert-danger");
            }
          });
      });
    }

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
    };
  }
})();

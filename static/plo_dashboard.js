/* global setLoadingState, setErrorState, setEmptyState */
/**
 * PLO Dashboard — Program → PLO → CLO → section drilldown.
 *
 * Fetches the hierarchical tree from /api/programs/<id>/plo-dashboard and
 * renders it as a collapsible list.  Assessment badges honour the
 * per-program `assessment_display_mode` setting ("binary" | "percentage" |
 * "both"), which the user can change from the filter bar (persisted via
 * PUT /api/programs/<id>).
 *
 * Exports `PloDashboard` on globalThis for integration tests / other pages
 * and via module.exports for Jest unit tests.
 */

(function () {
  "use strict";

  const STORAGE_KEY_PROGRAM = "ploDashboard.lastProgramId";
  const DEFAULT_PASS_THRESHOLD = 70; // % at/above which a node is "S"

  /**
   * Render an assessment result as a short badge string.
   *
   * Display rule (see DESIGN_APPROACH.md):
   *  - mode "binary"     → "S" or "U"
   *  - mode "percentage" → "78%"
   *  - mode "both"       → "S (78%)" or "U (54%)"
   * When *passRate* is null (no data) returns "—" regardless of mode.
   */
  function formatAssessment(passRate, mode, threshold) {
    const t =
      typeof threshold === "number" ? threshold : DEFAULT_PASS_THRESHOLD;
    if (passRate === null || passRate === undefined) {
      return { text: "—", cssClass: "nodata" };
    }
    const isPass = passRate >= t;
    const binary = isPass ? "S" : "U";
    const pct = `${Math.round(passRate)}%`;

    let text;
    if (mode === "binary") {
      text = binary;
    } else if (mode === "percentage") {
      text = pct;
    } else {
      text = `${binary} (${pct})`;
    }
    return { text, cssClass: isPass ? "pass" : "fail" };
  }

  /** Pick a sensible default term: first active, else most-recent by start_date. */
  function pickDefaultTerm(terms) {
    if (!Array.isArray(terms) || terms.length === 0) return "";
    const active = terms.find(
      (t) =>
        t.term_status === "ACTIVE" ||
        t.status === "ACTIVE" ||
        t.is_active === true ||
        t.active === true,
    );
    if (active) return active.term_id || active.id || "";
    const sorted = [...terms].sort(
      (a, b) => new Date(b.start_date || 0) - new Date(a.start_date || 0),
    );
    return sorted[0].term_id || sorted[0].id || "";
  }

  const PloDashboard = {
    // ---- state ---------------------------------------------------------
    programs: [],
    terms: [],
    tree: null,
    currentProgramId: null,
    currentTermId: null,
    displayMode: "both",
    draftMappingId: null,

    // ---- cached DOM refs ----------------------------------------------
    _el: {},

    // ===================================================================
    // Bootstrap
    // ===================================================================
    init() {
      this._cacheSelectors();
      this._bindEvents();
      this._loadFilters().then(() => this.loadTree());
    },

    _cacheSelectors() {
      this._el = {
        programFilter: document.getElementById("ploProgramFilter"),
        termFilter: document.getElementById("ploTermFilter"),
        displayMode: document.getElementById("ploDisplayMode"),
        treeContainer: document.getElementById("ploTreeContainer"),
        programName: document.getElementById("ploTreeProgramName"),
        versionBadge: document.getElementById("ploTreeVersionBadge"),
        statPloCount: document.getElementById("statPloCount"),
        statMappedCloCount: document.getElementById("statMappedCloCount"),
        statOverallPassRate: document.getElementById("statOverallPassRate"),
        statMappingStatus: document.getElementById("statMappingStatus"),
        expandAllBtn: document.getElementById("expandAllBtn"),
        collapseAllBtn: document.getElementById("collapseAllBtn"),
        createPloBtn: document.getElementById("createPloBtn"),
        mapCloBtn: document.getElementById("mapCloBtn"),
        // modals
        ploModal: document.getElementById("ploModal"),
        ploForm: document.getElementById("ploForm"),
        ploModalId: document.getElementById("ploModalId"),
        ploModalNumber: document.getElementById("ploModalNumber"),
        ploModalDescription: document.getElementById("ploModalDescription"),
        ploModalLabel: document.getElementById("ploModalLabel"),
        ploModalAlert: document.getElementById("ploModalAlert"),
        mapCloModal: document.getElementById("mapCloModal"),
        mapCloForm: document.getElementById("mapCloForm"),
        mapCloModalPlo: document.getElementById("mapCloModalPlo"),
        mapCloModalClo: document.getElementById("mapCloModalClo"),
        mapCloModalAlert: document.getElementById("mapCloModalAlert"),
        mapCloPublishBtn: document.getElementById("mapCloPublishBtn"),
      };
    },

    _bindEvents() {
      const el = this._el;
      if (el.programFilter) {
        el.programFilter.addEventListener("change", () => {
          this.currentProgramId = el.programFilter.value;
          try {
            localStorage.setItem(STORAGE_KEY_PROGRAM, this.currentProgramId);
          } catch (_) {
            /* ignore storage quota / private-mode errors */
          }
          this.loadTree();
        });
      }
      if (el.termFilter) {
        el.termFilter.addEventListener("change", () => {
          this.currentTermId = el.termFilter.value;
          this.loadTree();
        });
      }
      if (el.displayMode) {
        el.displayMode.addEventListener("change", () => {
          this.displayMode = el.displayMode.value;
          this._persistDisplayMode();
          this._renderTree();
        });
      }
      if (el.expandAllBtn) {
        el.expandAllBtn.addEventListener("click", () => this._toggleAll(true));
      }
      if (el.collapseAllBtn) {
        el.collapseAllBtn.addEventListener("click", () =>
          this._toggleAll(false),
        );
      }
      if (el.createPloBtn) {
        el.createPloBtn.addEventListener("click", () => this._openPloModal());
      }
      if (el.mapCloBtn) {
        el.mapCloBtn.addEventListener("click", () => this._openMapCloModal());
      }
      if (el.ploForm) {
        el.ploForm.addEventListener("submit", (e) => this._submitPloForm(e));
      }
      if (el.mapCloForm) {
        el.mapCloForm.addEventListener("submit", (e) =>
          this._submitMapCloForm(e),
        );
      }
      if (el.mapCloPublishBtn) {
        el.mapCloPublishBtn.addEventListener("click", () =>
          this._publishDraft(),
        );
      }
    },

    // ===================================================================
    // Filter population
    // ===================================================================
    async _loadFilters() {
      await Promise.all([this._loadPrograms(), this._loadTerms()]);
    },

    async _loadPrograms() {
      const resp = await fetch("/api/programs", { credentials: "include" });
      if (!resp.ok) return;
      const data = await resp.json();
      this.programs = data.programs || [];

      const sel = this._el.programFilter;
      if (!sel) return;
      sel.innerHTML = "";

      if (this.programs.length === 0) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "No programs found";
        sel.appendChild(opt);
        return;
      }

      this.programs.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.program_id || p.id;
        opt.textContent = p.name;
        sel.appendChild(opt);
      });

      // Default program: last selected (localStorage) → first in list
      let initial = null;
      try {
        initial = localStorage.getItem(STORAGE_KEY_PROGRAM);
      } catch (_) {
        /* ignore */
      }
      const validIds = this.programs.map((p) => p.program_id || p.id);
      if (!initial || !validIds.includes(initial)) {
        initial = validIds[0];
      }
      sel.value = initial;
      this.currentProgramId = initial;
    },

    async _loadTerms() {
      const resp = await fetch("/api/terms?all=true", {
        credentials: "include",
      });
      if (!resp.ok) return;
      const data = await resp.json();
      this.terms = data.terms || [];

      const sel = this._el.termFilter;
      if (!sel) return;
      // keep the "All Terms" option, append the rest
      this.terms
        .slice()
        .sort(
          (a, b) => new Date(b.start_date || 0) - new Date(a.start_date || 0),
        )
        .forEach((t) => {
          const opt = document.createElement("option");
          opt.value = t.term_id || t.id || "";
          opt.textContent = t.term_name || t.name || "Term";
          sel.appendChild(opt);
        });

      const defaultTerm = pickDefaultTerm(this.terms);
      sel.value = defaultTerm;
      this.currentTermId = defaultTerm;
    },

    // ===================================================================
    // Tree fetch + render
    // ===================================================================
    async loadTree() {
      const pid = this.currentProgramId;
      if (!pid) {
        setEmptyState(
          "ploTreeContainer",
          "Select a program to see its outcomes.",
        );
        this._updateStats(null);
        return;
      }
      setLoadingState("ploTreeContainer", "Loading PLO tree…");

      const qs = new URLSearchParams();
      if (this.currentTermId) qs.set("term_id", this.currentTermId);
      const url = `/api/programs/${encodeURIComponent(pid)}/plo-dashboard?${qs}`;

      try {
        const resp = await fetch(url, {
          credentials: "include",
          headers: { Accept: "application/json" },
        });
        if (!resp.ok) {
          setErrorState(
            "ploTreeContainer",
            `Failed to load PLO dashboard (HTTP ${resp.status}).`,
          );
          return;
        }
        const data = await resp.json();
        this.tree = data;
        this.displayMode = data.assessment_display_mode || "both";
        if (this._el.displayMode) this._el.displayMode.value = this.displayMode;
        this.draftMappingId = null; // reset; re-fetched when modal opens
        this._renderTree();
        this._updateStats(data);
      } catch (err) {
        setErrorState("ploTreeContainer", `Error: ${err.message}`);
      }
    },

    _renderTree() {
      const container = this._el.treeContainer;
      if (!container) return;
      const data = this.tree;

      // Header: program name + mapping version badge
      const prog = this.programs.find(
        (p) => (p.program_id || p.id) === this.currentProgramId,
      );
      if (this._el.programName) {
        this._el.programName.textContent = prog ? prog.name : "Program";
      }
      if (this._el.versionBadge) {
        if (data && data.mapping && data.mapping.version) {
          this._el.versionBadge.textContent = `Mapping v${data.mapping.version}`;
          this._el.versionBadge.style.display = "";
        } else {
          this._el.versionBadge.style.display = "none";
        }
      }

      // Empty states
      if (!data || !Array.isArray(data.plos) || data.plos.length === 0) {
        setEmptyState(
          "ploTreeContainer",
          "No Program Learning Outcomes defined yet. Use “New PLO” to create one.",
        );
        return;
      }

      const ul = document.createElement("ul");
      ul.className = "plo-tree";
      data.plos.forEach((plo) => ul.appendChild(this._buildPloNode(plo)));

      container.innerHTML = "";
      container.appendChild(ul);
    },

    _updateStats(data) {
      const set = (el, val) => {
        if (el) el.textContent = val;
      };
      if (!data) {
        set(this._el.statPloCount, "-");
        set(this._el.statMappedCloCount, "-");
        set(this._el.statOverallPassRate, "-");
        set(this._el.statMappingStatus, "-");
        return;
      }
      const plos = data.plos || [];
      const cloCount = plos.reduce((n, p) => n + (p.clo_count || 0), 0);
      set(this._el.statPloCount, plos.length);
      set(this._el.statMappedCloCount, cloCount);

      // overall pass rate aggregated across all PLO aggregates
      let took = 0;
      let passed = 0;
      plos.forEach((p) => {
        const a = p.aggregate || {};
        if (a.students_took) {
          took += a.students_took;
          passed += a.students_passed || 0;
        }
      });
      if (took > 0) {
        set(
          this._el.statOverallPassRate,
          `${Math.round((passed / took) * 100)}%`,
        );
      } else {
        set(this._el.statOverallPassRate, "—");
      }

      const status = data.mapping_status || "none";
      const label = {
        published: "Published",
        draft: "Draft",
        none: "Not mapped",
      }[status];
      set(this._el.statMappingStatus, label || status);
    },

    // ===================================================================
    // Node builders (PLO → CLO → Section)
    // ===================================================================
    _buildPloNode(plo) {
      const li = document.createElement("li");
      li.className = "plo-tree-node";
      li.dataset.ploId = plo.id;

      const header = this._buildHeader(
        `PLO-${plo.plo_number}`,
        plo.description,
        plo.aggregate,
        { level: "plo", plo },
      );
      li.appendChild(header);

      const children = document.createElement("ul");
      children.className = "plo-tree-children";
      if (!plo.clos || plo.clos.length === 0) {
        children.appendChild(
          this._buildLeafMessage("No CLOs mapped to this PLO yet."),
        );
      } else {
        plo.clos.forEach((clo) =>
          children.appendChild(this._buildCloNode(clo)),
        );
      }
      li.appendChild(children);

      this._wireToggle(li, header, plo.clos && plo.clos.length > 0);
      return li;
    },

    _buildCloNode(clo) {
      const li = document.createElement("li");
      li.className = "plo-tree-node";
      li.dataset.cloId = clo.outcome_id;

      const title = `${clo.course_number || ""} — CLO ${clo.clo_number || "?"}`;
      const header = this._buildHeader(title, clo.description, clo.aggregate, {
        level: "clo",
      });
      li.appendChild(header);

      const children = document.createElement("ul");
      children.className = "plo-tree-children";
      if (!clo.sections || clo.sections.length === 0) {
        children.appendChild(
          this._buildLeafMessage(
            "No section assessments in the selected term.",
          ),
        );
      } else {
        clo.sections.forEach((s) =>
          children.appendChild(this._buildSectionNode(s)),
        );
      }
      li.appendChild(children);

      this._wireToggle(li, header, clo.sections && clo.sections.length > 0);
      return li;
    },

    _buildSectionNode(section) {
      const li = document.createElement("li");
      li.className = "plo-tree-node leaf";

      const s = section._section || {};
      const offering = section._offering || {};
      const instructor = section._instructor || {};
      const term = section._term || {};
      const took = section.students_took;
      const passed = section.students_passed;
      let rate = null;
      if (typeof took === "number" && took > 0 && typeof passed === "number") {
        rate = (passed / took) * 100;
      }

      const title =
        `Section ${s.section_number || "?"}` +
        (term.name ? ` — ${term.name}` : "");
      const detailParts = [];
      if (instructor.last_name || instructor.first_name) {
        detailParts.push(
          `${instructor.first_name || ""} ${instructor.last_name || ""}`.trim(),
        );
      }
      if (section.assessment_tool) {
        detailParts.push(section.assessment_tool);
      }
      if (typeof took === "number" && typeof passed === "number") {
        detailParts.push(`${passed}/${took} passed`);
      }

      const header = this._buildHeader(
        title,
        detailParts.join(" · "),
        { pass_rate: rate, section_count: 1 },
        { level: "section" },
      );
      // reference offering for potential future navigation without lint warnings
      li.dataset.offeringId = offering.offering_id || offering.id || "";
      li.appendChild(header);
      return li;
    },

    _buildHeader(number, desc, aggregate, opts) {
      const header = document.createElement("div");
      header.className = "plo-tree-header";

      const toggle = document.createElement("span");
      toggle.className = "plo-tree-toggle";
      toggle.innerHTML = '<i class="fas fa-chevron-right"></i>';
      header.appendChild(toggle);

      const label = document.createElement("div");
      label.className = "plo-tree-label";
      const numEl = document.createElement("div");
      numEl.className = "plo-tree-number";
      numEl.textContent = number;
      if (opts && opts.level === "plo" && opts.plo) {
        const pill = document.createElement("span");
        pill.className = "plo-clo-count-pill ms-2";
        pill.textContent = `${opts.plo.clo_count || 0} CLO${(opts.plo.clo_count || 0) === 1 ? "" : "s"}`;
        numEl.appendChild(pill);
      }
      label.appendChild(numEl);
      if (desc) {
        const descEl = document.createElement("div");
        descEl.className = "plo-tree-desc";
        descEl.textContent = desc;
        label.appendChild(descEl);
      }
      header.appendChild(label);

      const meta = document.createElement("div");
      meta.className = "plo-tree-meta";

      const badge = document.createElement("span");
      badge.className = "plo-assessment-badge";
      const passRate =
        aggregate && aggregate.pass_rate != null ? aggregate.pass_rate : null;
      const { text, cssClass } = formatAssessment(passRate, this.displayMode);
      badge.classList.add(cssClass);
      badge.textContent = text;
      meta.appendChild(badge);

      if (opts && opts.level === "plo" && opts.plo) {
        const actions = document.createElement("span");
        actions.className = "plo-tree-actions ms-2";
        const editBtn = document.createElement("button");
        editBtn.type = "button";
        editBtn.className = "btn btn-outline-secondary";
        editBtn.innerHTML = '<i class="fas fa-pencil"></i>';
        editBtn.title = "Edit PLO";
        editBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          this._openPloModal(opts.plo);
        });
        actions.appendChild(editBtn);
        meta.appendChild(actions);
      }

      header.appendChild(meta);
      return header;
    },

    _buildLeafMessage(text) {
      const li = document.createElement("li");
      li.className = "plo-tree-node leaf";
      const div = document.createElement("div");
      div.className = "plo-tree-header text-muted small fst-italic";
      div.textContent = text;
      li.appendChild(div);
      return li;
    },

    _wireToggle(li, header, hasChildren) {
      if (!hasChildren) {
        li.classList.add("expanded"); // so empty-message is visible
        return;
      }
      header.addEventListener("click", () => li.classList.toggle("expanded"));
    },

    _toggleAll(expand) {
      const nodes = this._el.treeContainer
        ? this._el.treeContainer.querySelectorAll(".plo-tree-node")
        : [];
      nodes.forEach((n) => {
        if (expand) n.classList.add("expanded");
        else n.classList.remove("expanded");
      });
    },

    // ===================================================================
    // Display-mode persistence (PUT to program extras)
    // ===================================================================
    async _persistDisplayMode() {
      if (!this.currentProgramId) return;
      try {
        await fetch(
          `/api/programs/${encodeURIComponent(this.currentProgramId)}`,
          {
            method: "PUT",
            credentials: "include",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": this._csrf(),
            },
            body: JSON.stringify({ assessment_display_mode: this.displayMode }),
          },
        );
      } catch (_) {
        /* non-fatal; badge re-renders locally anyway */
      }
    },

    _csrf() {
      const meta = document.querySelector('meta[name="csrf-token"]');
      return meta ? meta.content : "";
    },

    // ===================================================================
    // PLO create / edit modal
    // ===================================================================
    _openPloModal(plo) {
      const el = this._el;
      if (!el.ploModal) return;
      el.ploModalAlert.className = "alert d-none";
      if (plo) {
        el.ploModalLabel.textContent = "Edit Program Outcome";
        el.ploModalId.value = plo.id;
        el.ploModalNumber.value = plo.plo_number || "";
        el.ploModalDescription.value = plo.description || "";
      } else {
        el.ploModalLabel.textContent = "New Program Outcome";
        el.ploModalId.value = "";
        el.ploModalNumber.value = "";
        el.ploModalDescription.value = "";
      }
      this._showModal(el.ploModal);
    },

    async _submitPloForm(e) {
      e.preventDefault();
      const el = this._el;
      const pid = this.currentProgramId;
      const ploId = el.ploModalId.value;
      // plo_number is stored as an INTEGER — coerce textual input so the
      // unique constraint (program_id, plo_number) behaves consistently and
      // ordering in get_program_outcomes() is numeric.
      const rawNum = el.ploModalNumber.value.trim();
      const parsed = parseInt(rawNum, 10);
      const body = {
        plo_number: Number.isFinite(parsed) ? parsed : rawNum,
        description: el.ploModalDescription.value.trim(),
      };

      const method = ploId ? "PUT" : "POST";
      const url = ploId
        ? `/api/programs/${encodeURIComponent(pid)}/plos/${encodeURIComponent(ploId)}`
        : `/api/programs/${encodeURIComponent(pid)}/plos`;

      try {
        const resp = await fetch(url, {
          method,
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": this._csrf(),
          },
          body: JSON.stringify(body),
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) {
          this._modalAlert(
            el.ploModalAlert,
            data.error || "Save failed",
            "danger",
          );
          return;
        }
        this._hideModal(el.ploModal);
        this.loadTree();
      } catch (err) {
        this._modalAlert(el.ploModalAlert, err.message, "danger");
      }
    },

    // ===================================================================
    // Map CLO modal
    // ===================================================================
    async _openMapCloModal(prefillPloId) {
      const el = this._el;
      if (!el.mapCloModal) return;
      el.mapCloModalAlert.className = "alert d-none";

      // populate PLO select from current tree
      el.mapCloModalPlo.innerHTML = '<option value="">Select a PLO…</option>';
      (this.tree && this.tree.plos ? this.tree.plos : []).forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `PLO-${p.plo_number} — ${p.description}`;
        el.mapCloModalPlo.appendChild(opt);
      });
      if (prefillPloId) el.mapCloModalPlo.value = prefillPloId;

      // ensure a draft exists & populate unmapped CLOs
      const pid = this.currentProgramId;
      el.mapCloModalClo.innerHTML = '<option value="">Loading…</option>';
      try {
        const draftResp = await fetch(
          `/api/programs/${encodeURIComponent(pid)}/plo-mappings/draft`,
          {
            method: "POST",
            credentials: "include",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": this._csrf(),
            },
            body: JSON.stringify({}),
          },
        );
        const draftData = await draftResp.json();
        this.draftMappingId =
          draftData.mapping && draftData.mapping.id
            ? draftData.mapping.id
            : null;

        const cloResp = await fetch(
          `/api/programs/${encodeURIComponent(pid)}/plo-mappings/unmapped-clos`,
          { credentials: "include" },
        );
        const cloData = await cloResp.json();
        const clos = cloData.unmapped_clos || [];

        el.mapCloModalClo.innerHTML = '<option value="">Select a CLO…</option>';
        clos.forEach((c) => {
          const opt = document.createElement("option");
          opt.value = c.outcome_id;
          const course = c.course || {};
          opt.textContent =
            `${course.course_number || ""} CLO ${c.clo_number || "?"} — ` +
            `${c.description || ""}`.slice(0, 80);
          el.mapCloModalClo.appendChild(opt);
        });
        if (clos.length === 0) {
          el.mapCloModalClo.innerHTML =
            '<option value="">All CLOs are already mapped</option>';
        }
      } catch (err) {
        this._modalAlert(el.mapCloModalAlert, err.message, "danger");
      }

      this._showModal(el.mapCloModal);
    },

    async _submitMapCloForm(e) {
      e.preventDefault();
      const el = this._el;
      const pid = this.currentProgramId;
      const ploId = el.mapCloModalPlo.value;
      const cloId = el.mapCloModalClo.value;
      if (!this.draftMappingId || !ploId || !cloId) {
        this._modalAlert(
          el.mapCloModalAlert,
          "Select both a PLO and a CLO.",
          "warning",
        );
        return;
      }
      try {
        const resp = await fetch(
          `/api/programs/${encodeURIComponent(pid)}/plo-mappings/${encodeURIComponent(this.draftMappingId)}/entries`,
          {
            method: "POST",
            credentials: "include",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": this._csrf(),
            },
            body: JSON.stringify({
              program_outcome_id: ploId,
              course_outcome_id: cloId,
            }),
          },
        );
        const data = await resp.json();
        if (!resp.ok || !data.success) {
          this._modalAlert(
            el.mapCloModalAlert,
            data.error || "Failed to add mapping",
            "danger",
          );
          return;
        }
        this._modalAlert(
          el.mapCloModalAlert,
          "Mapping added to draft. Publish when ready.",
          "success",
        );
        // refresh unmapped CLO list so user can add another
        this._openMapCloModal(ploId);
      } catch (err) {
        this._modalAlert(el.mapCloModalAlert, err.message, "danger");
      }
    },

    async _publishDraft() {
      if (!this.draftMappingId || !this.currentProgramId) return;
      const el = this._el;
      try {
        const resp = await fetch(
          `/api/programs/${encodeURIComponent(this.currentProgramId)}/plo-mappings/${encodeURIComponent(this.draftMappingId)}/publish`,
          {
            method: "POST",
            credentials: "include",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": this._csrf(),
            },
            body: JSON.stringify({}),
          },
        );
        const data = await resp.json();
        if (!resp.ok || !data.success) {
          this._modalAlert(
            el.mapCloModalAlert,
            data.error || "Publish failed",
            "danger",
          );
          return;
        }
        this._hideModal(el.mapCloModal);
        this.loadTree();
      } catch (err) {
        this._modalAlert(el.mapCloModalAlert, err.message, "danger");
      }
    },

    // ===================================================================
    // Modal helpers (Bootstrap 5 — fall back to class toggle for tests)
    // ===================================================================
    _showModal(el) {
      if (
        typeof globalThis.bootstrap !== "undefined" &&
        globalThis.bootstrap.Modal
      ) {
        globalThis.bootstrap.Modal.getOrCreateInstance(el).show();
      } else {
        el.classList.add("show");
        el.style.display = "block";
      }
    },
    _hideModal(el) {
      if (
        typeof globalThis.bootstrap !== "undefined" &&
        globalThis.bootstrap.Modal
      ) {
        const inst = globalThis.bootstrap.Modal.getInstance(el);
        if (inst) inst.hide();
      } else {
        el.classList.remove("show");
        el.style.display = "none";
      }
    },
    _modalAlert(el, msg, level) {
      if (!el) return;
      el.className = `alert alert-${level || "info"}`;
      el.textContent = msg;
    },
  };

  // -------------------------------------------------------------------
  // Boot + exports
  // -------------------------------------------------------------------
  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", () => PloDashboard.init());
  }
  if (typeof globalThis !== "undefined") {
    globalThis.PloDashboard = PloDashboard;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      PloDashboard,
      formatAssessment,
      pickDefaultTerm,
      DEFAULT_PASS_THRESHOLD,
    };
  }
})();

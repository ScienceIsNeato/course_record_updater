(function () {
  "use strict";

  /* ---- helpers --------------------------------------------------------- */

  function passRateBadge(passRate) {
    const span = document.createElement("span");
    span.className = "plo-assessment-badge";
    span.textContent = passRate != null ? Math.round(passRate) + "%" : "N/A";
    return span;
  }

  function narrativeBlock(label, text, type) {
    if (!text) return null;
    var wrap = document.createElement("div");
    wrap.className = "plo-detail-narrative";
    if (type) wrap.classList.add("plo-detail-narrative--" + type);
    var lbl = document.createElement("span");
    lbl.className = "plo-detail-narrative-label";
    lbl.textContent = label;
    var body = document.createElement("span");
    body.className = "plo-detail-narrative-text";
    body.textContent = text;
    wrap.appendChild(lbl);
    wrap.appendChild(body);
    return wrap;
  }

  function getCloRows(panel) {
    return Array.from(panel.querySelectorAll(".plo-detail-clo"));
  }

  function syncToggleAllButton(panel) {
    var btn = panel.querySelector(".plo-detail-panel-toggle-all");
    if (!btn) return;
    var cloRows = getCloRows(panel);
    var allExpanded =
      cloRows.length > 0 &&
      cloRows.every(function (row) {
        return row.classList.contains("expanded");
      });
    btn.textContent = allExpanded ? "Collapse all CLOs" : "Expand all CLOs";
    btn.setAttribute("aria-expanded", allExpanded ? "true" : "false");
  }

  function flagButton(storageKey) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "plo-detail-flag-btn";
    btn.title = "Flag for follow-up";
    var isFlagged = false;
    try {
      isFlagged = localStorage.getItem(storageKey) === "1";
    } catch (_) {
      /* ignore */
    }
    if (isFlagged) btn.classList.add("flagged");
    btn.innerHTML = '<i class="fas fa-flag"></i>';
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var now = btn.classList.toggle("flagged");
      try {
        if (now) localStorage.setItem(storageKey, "1");
        else localStorage.removeItem(storageKey);
      } catch (_) {
        /* ignore */
      }
    });
    return btn;
  }

  function sectionRow(sec) {
    const li = document.createElement("li");
    li.className = "plo-detail-section";

    const instructor = sec._instructor
      ? sec._instructor.first_name + " " + sec._instructor.last_name
      : "Unknown";
    const counts = sec.students_passed + "/" + sec.students_took;
    const passRate =
      sec.students_took > 0
        ? (sec.students_passed / sec.students_took) * 100
        : null;

    /* top line: section link + summary info + badge */
    var topLine = document.createElement("div");
    topLine.className = "plo-detail-section-top";

    const link = document.createElement("a");
    const offeringId =
      sec._offering && sec._offering.offering_id
        ? sec._offering.offering_id
        : "";
    link.href = "/sections?offering_id=" + encodeURIComponent(offeringId);
    link.textContent =
      "Section " + (sec._section ? sec._section.section_number : "?");

    const info = document.createElement("span");
    info.className = "plo-detail-section-info";
    var infoParts = [instructor];
    if (sec.assessment_tool) infoParts.push(sec.assessment_tool);
    infoParts.push(counts);
    var secObj = sec._section || {};
    if (secObj.enrollment != null) {
      infoParts.push("enrolled: " + secObj.enrollment);
    }
    info.textContent = infoParts.join(" \u2014 ");

    topLine.appendChild(link);
    topLine.appendChild(info);
    topLine.appendChild(passRateBadge(passRate));

    var flagKey =
      "plo-followup-" +
      (offeringId || "") +
      "-" +
      (sec._section ? sec._section.section_number : "");
    topLine.appendChild(flagButton(flagKey));

    li.appendChild(topLine);

    /* assessment method from CLO template */
    var tpl = sec._template || {};
    if (tpl.assessment_method) {
      var method = document.createElement("div");
      method.className = "plo-detail-section-method";
      method.textContent = "Method: " + tpl.assessment_method;
      li.appendChild(method);
    }

    /* instructor narratives */
    var narr = sec._section || {};
    var blocks = [
      narrativeBlock(
        "Celebrations:",
        narr.narrative_celebrations,
        "celebrations",
      ),
      narrativeBlock("Challenges:", narr.narrative_challenges, "challenges"),
      narrativeBlock("Changes planned:", narr.narrative_changes, "changes"),
      narrativeBlock(
        "Reconciliation:",
        narr.reconciliation_note,
        "reconciliation",
      ),
    ];
    blocks.forEach(function (b) {
      if (b) li.appendChild(b);
    });

    /* reviewer feedback on this section outcome */
    if (sec.feedback_comments) {
      li.appendChild(
        narrativeBlock("Reviewer feedback:", sec.feedback_comments, "feedback"),
      );
    }

    return li;
  }

  /* ---- CLO row -------------------------------------------------------- */

  function cloRow(clo, onToggle) {
    const div = document.createElement("div");
    div.className = "plo-detail-clo";

    const header = document.createElement("div");
    header.className = "plo-detail-clo-header";
    header.setAttribute("role", "button");
    header.setAttribute("tabindex", "0");

    var toggle = document.createElement("span");
    toggle.className = "plo-detail-clo-toggle";
    toggle.textContent = "\u25B6";

    const label = document.createElement("span");
    label.className = "plo-detail-clo-label";
    var labelParts = [];
    if (clo.course_number) labelParts.push(clo.course_number);
    if (clo.course_title) labelParts.push(clo.course_title);
    var courseInfo = labelParts.join(" \u2014 ");
    label.textContent =
      (courseInfo ? courseInfo + " \u2014 " : "") +
      "CLO " +
      clo.clo_number +
      ": " +
      clo.description;

    const badge = passRateBadge(clo.aggregate ? clo.aggregate.pass_rate : null);

    header.appendChild(toggle);
    header.appendChild(label);
    header.appendChild(badge);
    div.appendChild(header);

    /* children (sections) */
    const children = document.createElement("ul");
    children.className = "plo-detail-clo-children";
    if (clo.sections) {
      clo.sections.forEach(function (sec) {
        children.appendChild(sectionRow(sec));
      });
    }
    div.appendChild(children);

    /* expand / collapse */
    header.addEventListener("click", function () {
      div.classList.toggle("expanded");
      if (typeof onToggle === "function") onToggle();
    });

    return div;
  }

  /* ---- public API ----------------------------------------------------- */

  function createDetailPanel(ploData, termLabel) {
    var panel = document.createElement("div");
    panel.className = "plo-detail-panel plo-detail-panel--entering";

    /* close button */
    var closeBtn = document.createElement("button");
    closeBtn.className = "plo-detail-panel-close";
    closeBtn.setAttribute("aria-label", "Close detail panel");
    closeBtn.textContent = "\u00D7";
    closeBtn.addEventListener("click", function () {
      panel.remove();
    });
    panel.appendChild(closeBtn);

    /* header */
    var header = document.createElement("div");
    header.className = "plo-detail-panel-header";
    header.textContent =
      "PLO " +
      ploData.plo_number +
      ": " +
      ploData.description +
      " \u2014 " +
      termLabel;
    panel.appendChild(header);

    if (ploData.clos && ploData.clos.length > 0) {
      var controls = document.createElement("div");
      controls.className = "plo-detail-panel-controls";

      var toggleAllBtn = document.createElement("button");
      toggleAllBtn.type = "button";
      toggleAllBtn.className = "plo-detail-panel-toggle-all";
      toggleAllBtn.addEventListener("click", function () {
        var cloRows = getCloRows(panel);
        var shouldExpand = cloRows.some(function (row) {
          return !row.classList.contains("expanded");
        });
        cloRows.forEach(function (row) {
          row.classList.toggle("expanded", shouldExpand);
        });
        syncToggleAllButton(panel);
      });

      controls.appendChild(toggleAllBtn);
      panel.appendChild(controls);
    }

    /* CLO list or empty message */
    if (!ploData.clos || ploData.clos.length === 0) {
      var empty = document.createElement("div");
      empty.className = "plo-detail-empty";
      empty.textContent = "No CLO data available for this term.";
      panel.appendChild(empty);
    } else {
      ploData.clos.forEach(function (clo) {
        panel.appendChild(
          cloRow(clo, function () {
            syncToggleAllButton(panel);
          }),
        );
      });
      syncToggleAllButton(panel);
    }

    return panel;
  }

  function destroyDetailPanel(container) {
    var existing = container.querySelector(".plo-detail-panel");
    if (existing) {
      existing.remove();
    }
  }

  /* ---- exports -------------------------------------------------------- */

  var exportsObj = {
    createDetailPanel: createDetailPanel,
    destroyDetailPanel: destroyDetailPanel,
  };
  if (typeof globalThis !== "undefined") {
    globalThis.PloDetailPanel = exportsObj;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = exportsObj;
  }
})();

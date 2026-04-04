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

  function setCloExpanded(row, header, expanded) {
    row.classList.toggle("expanded", expanded);
    if (header) {
      header.setAttribute("aria-expanded", expanded ? "true" : "false");
    }
  }

  function schedulePanelEntrance(panel) {
    function enterPanel() {
      if (panel.isConnected) {
        panel.classList.add("plo-detail-panel--entering");
      }
    }

    if (typeof requestAnimationFrame === "function") {
      requestAnimationFrame(function () {
        requestAnimationFrame(enterPanel);
      });
      return;
    }

    setTimeout(enterPanel, 0);
  }

  function pluralize(count, singular, plural) {
    return count + " " + (count === 1 ? singular : plural || singular + "s");
  }

  function sectionHasNarrative(sec) {
    var narr = sec._section || {};
    return Boolean(
      narr.narrative_celebrations ||
        narr.narrative_challenges ||
        narr.narrative_changes ||
        narr.reconciliation_note,
    );
  }

  function buildSummaryMetrics(ploData) {
    var summary = {
      cloCount: Array.isArray(ploData.clos) ? ploData.clos.length : 0,
      sectionCount: 0,
      assessedStudents: 0,
      passRate: ploData.aggregate ? ploData.aggregate.pass_rate : null,
      sectionsWithNarratives: 0,
      sectionsWithFeedback: 0,
    };

    if (ploData.aggregate && ploData.aggregate.students_took != null) {
      summary.assessedStudents = ploData.aggregate.students_took;
    }

    (ploData.clos || []).forEach(function (clo) {
      (clo.sections || []).forEach(function (sec) {
        summary.sectionCount += 1;
        if (sectionHasNarrative(sec)) summary.sectionsWithNarratives += 1;
        if (sec.feedback_comments) summary.sectionsWithFeedback += 1;
      });
    });

    return summary;
  }

  function buildMetricChip(text, accent) {
    var chip = document.createElement("span");
    chip.className = "plo-detail-panel-metric";
    if (accent) chip.classList.add("plo-detail-panel-metric--" + accent);
    chip.textContent = text;
    return chip;
  }

  function buildContextHint(summary) {
    var parts = [];
    if (summary.cloCount > 0) {
      parts.push(pluralize(summary.cloCount, "mapped CLO"));
    }
    if (summary.sectionCount > 0) {
      parts.push(pluralize(summary.sectionCount, "assessed section"));
    }
    if (summary.assessedStudents > 0) {
      parts.push(pluralize(summary.assessedStudents, "student") + " assessed");
    }
    if (summary.passRate != null) {
      parts.push(Math.round(summary.passRate) + "% meeting target");
    }
    if (parts.length === 0) {
      return "No assessed sections are available for this term yet.";
    }
    return parts.join(" - ");
  }

  function buildPanelContext(ploData, termLabel) {
    var summary = buildSummaryMetrics(ploData);
    var context = document.createElement("div");
    context.className = "plo-detail-panel-context";

    var contextCopy = document.createElement("div");
    contextCopy.className = "plo-detail-panel-context-copy";

    var contextLabel = document.createElement("div");
    contextLabel.className = "plo-detail-panel-context-label";
    contextLabel.textContent = "Chart drill-through";

    var contextHint = document.createElement("div");
    contextHint.className = "plo-detail-panel-context-hint";
    contextHint.textContent = buildContextHint(summary);

    var metrics = document.createElement("div");
    metrics.className = "plo-detail-panel-metrics";
    metrics.appendChild(buildMetricChip(pluralize(summary.cloCount, "CLO")));
    metrics.appendChild(
      buildMetricChip(pluralize(summary.sectionCount, "section")),
    );
    if (summary.sectionsWithNarratives > 0) {
      metrics.appendChild(
        buildMetricChip(
          pluralize(
            summary.sectionsWithNarratives,
            "section with notes",
            "sections with notes",
          ),
          "notes",
        ),
      );
    }
    if (summary.sectionsWithFeedback > 0) {
      metrics.appendChild(
        buildMetricChip(
          pluralize(summary.sectionsWithFeedback, "reviewer comment"),
          "feedback",
        ),
      );
    }

    var termWrap = document.createElement("div");
    termWrap.className = "plo-detail-panel-term";

    var termEyebrow = document.createElement("span");
    termEyebrow.className = "plo-detail-panel-term-eyebrow";
    termEyebrow.textContent = "Selected term";

    var termBadge = document.createElement("span");
    termBadge.className = "plo-detail-panel-term-badge";
    termBadge.textContent = termLabel;

    contextCopy.appendChild(contextLabel);
    contextCopy.appendChild(contextHint);
    contextCopy.appendChild(metrics);
    termWrap.appendChild(termEyebrow);
    termWrap.appendChild(termBadge);
    context.appendChild(contextCopy);
    context.appendChild(termWrap);

    return context;
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

  function cloRow(clo, onToggle, expandedByDefault) {
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

    setCloExpanded(div, header, Boolean(expandedByDefault));

    /* expand / collapse */
    header.addEventListener("click", function () {
      setCloExpanded(div, header, !div.classList.contains("expanded"));
      if (typeof onToggle === "function") onToggle();
    });
    header.addEventListener("keydown", function (event) {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      setCloExpanded(div, header, !div.classList.contains("expanded"));
      if (typeof onToggle === "function") onToggle();
    });

    return div;
  }

  /* ---- public API ----------------------------------------------------- */

  function createDetailPanel(ploData, termLabel) {
    var panel = document.createElement("div");
    panel.className = "plo-detail-panel";

    /* close button */
    var closeBtn = document.createElement("button");
    closeBtn.className = "plo-detail-panel-close";
    closeBtn.setAttribute("aria-label", "Close detail panel");
    closeBtn.textContent = "\u00D7";
    closeBtn.addEventListener("click", function () {
      panel.remove();
    });
    panel.appendChild(closeBtn);

    panel.appendChild(buildPanelContext(ploData, termLabel));

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
          setCloExpanded(
            row,
            row.querySelector(".plo-detail-clo-header"),
            shouldExpand,
          );
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
          cloRow(
            clo,
            function () {
              syncToggleAllButton(panel);
            },
            true,
          ),
        );
      });
      syncToggleAllButton(panel);
    }

    schedulePanelEntrance(panel);

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

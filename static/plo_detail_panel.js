(function () {
  "use strict";

  /* ---- helpers --------------------------------------------------------- */

  function passRateBadge(passRate) {
    const span = document.createElement("span");
    span.className = "plo-assessment-badge";
    span.textContent = passRate != null ? Math.round(passRate) + "%" : "N/A";
    return span;
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
    info.textContent =
      instructor +
      " \u2014 " +
      (sec.assessment_tool || "") +
      " \u2014 " +
      counts;

    li.appendChild(link);
    li.appendChild(info);
    li.appendChild(passRateBadge(passRate));
    return li;
  }

  /* ---- CLO row -------------------------------------------------------- */

  function cloRow(clo) {
    const div = document.createElement("div");
    div.className = "plo-detail-clo";

    const header = document.createElement("div");
    header.className = "plo-detail-clo-header";
    header.setAttribute("role", "button");
    header.setAttribute("tabindex", "0");

    const label = document.createElement("span");
    label.className = "plo-detail-clo-label";
    label.textContent =
      (clo.course_number || "") +
      " \u2014 CLO " +
      clo.clo_number +
      ": " +
      clo.description;

    const badge = passRateBadge(clo.aggregate ? clo.aggregate.pass_rate : null);

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

    /* CLO list or empty message */
    if (!ploData.clos || ploData.clos.length === 0) {
      var empty = document.createElement("div");
      empty.className = "plo-detail-empty";
      empty.textContent = "No CLO data available for this term.";
      panel.appendChild(empty);
    } else {
      ploData.clos.forEach(function (clo) {
        panel.appendChild(cloRow(clo));
      });
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

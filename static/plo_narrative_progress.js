/**
 * Narrative progress pill — counts unique sections with instructor narratives
 * for a PLO and returns a ready-to-insert DOM element (or null).
 */
(function () {
  "use strict";

  function narrativeProgressPill(plo) {
    var seen = {};
    var total = 0;
    var reported = 0;
    (plo.clos || []).forEach(function (clo) {
      (clo.sections || []).forEach(function (sec) {
        var s = sec._section || {};
        var o = sec._offering || {};
        var key = (o.offering_id || "") + "|" + (s.section_number || "");
        if (seen[key]) return;
        seen[key] = true;
        total++;
        if (
          s.narrative_celebrations ||
          s.narrative_challenges ||
          s.narrative_changes
        ) {
          reported++;
        }
      });
    });
    if (total === 0) return null;
    var pill = document.createElement("span");
    pill.className = "plo-narrative-progress";
    if (reported === total) pill.classList.add("complete");
    pill.textContent = reported + "/" + total + " reported";
    pill.title =
      reported + " of " + total + " sections have instructor narratives";
    return pill;
  }

  if (typeof globalThis !== "undefined") {
    globalThis.narrativeProgressPill = narrativeProgressPill;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { narrativeProgressPill };
  }
})();

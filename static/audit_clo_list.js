(function () {
  "use strict";

  function renderCLOList(deps) {
    const {
      allCLOs,
      cloListContainer,
      getStatusBadge,
      renderHistoryCellContent,
      sortCLOs,
      approveOutcome,
      assignOutcome,
      remindOutcome,
    } = deps;

    if (cloListContainer.offsetHeight > 0) {
      cloListContainer.style.minHeight = `${cloListContainer.offsetHeight}px`;
    }
    cloListContainer.textContent = "";

    const tableResp = document.createElement("div");
    tableResp.className = "table-responsive";
    const table = document.createElement("table");
    table.className = "table table-hover align-middle";
    table.appendChild(buildHeader());

    const tbody = document.createElement("tbody");
    if (allCLOs.length === 0) {
      tbody.appendChild(buildEmptyRow());
      table.appendChild(tbody);
      tableResp.appendChild(table);
      cloListContainer.appendChild(tableResp);
      return;
    }

    const groupedData = groupCLOs(sortCLOs([...allCLOs]));
    Object.keys(groupedData)
      .sort()
      .forEach((courseKey) => {
        const safeKey = courseKey.replace(/[^a-zA-Z0-9]/g, "");
        tbody.appendChild(buildCourseHeaderRow(courseKey, safeKey));
        const sectionGroups = groupedData[courseKey];
        Object.keys(sectionGroups)
          .sort()
          .forEach((sectionKey) => {
            const sectionSafeKey = `${safeKey}-${sectionKey.replace(/[^a-zA-Z0-9]/g, "")}`;
            tbody.appendChild(
              buildSectionHeaderRow(sectionKey, safeKey, sectionSafeKey),
            );
            sectionGroups[sectionKey].forEach((clo) => {
              tbody.appendChild(
                buildCloRow(clo, safeKey, sectionSafeKey, {
                  getStatusBadge,
                  renderHistoryCellContent,
                  approveOutcome,
                  assignOutcome,
                  remindOutcome,
                }),
              );
            });
          });
      });

    table.appendChild(tbody);
    tableResp.appendChild(table);
    cloListContainer.appendChild(tableResp);
  }

  function buildHeader() {
    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    [
      "Status",
      "Course",
      "Section",
      "Outcome #",
      "Description",
      "Instructor",
      "History",
      "Actions",
    ].forEach((text) => {
      const th = document.createElement("th");
      th.textContent = text;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    return thead;
  }

  function buildEmptyRow() {
    const emptyRow = document.createElement("tr");
    const emptyCell = document.createElement("td");
    emptyCell.colSpan = 8;
    emptyCell.className = "text-center text-muted py-4";
    emptyCell.textContent = "No Outcomes found for the selected filter.";
    emptyRow.appendChild(emptyCell);
    return emptyRow;
  }

  function groupCLOs(sorted) {
    const groupedData = {};
    sorted.forEach((clo) => {
      const courseKey = `${clo.course_number || "Unknown"} - ${clo.course_title || ""}`;
      if (!groupedData[courseKey]) groupedData[courseKey] = {};
      const sectionKey = clo.section_number
        ? `Section ${clo.section_number}`
        : "Unassigned Section";
      if (!groupedData[courseKey][sectionKey]) {
        groupedData[courseKey][sectionKey] = [];
      }
      groupedData[courseKey][sectionKey].push(clo);
    });
    return groupedData;
  }

  function buildCourseHeaderRow(courseKey, safeKey) {
    const courseRow = document.createElement("tr");
    courseRow.className = "table-light";
    const courseCell = document.createElement("td");
    courseCell.colSpan = 8;
    const courseDiv = document.createElement("div");
    courseDiv.className = "d-flex align-items-center";
    courseDiv.style.cursor = "pointer";
    courseDiv.setAttribute("data-bs-toggle", "collapse");
    courseDiv.setAttribute("data-bs-target", `.group-${safeKey}`);
    const chevronIcon = document.createElement("i");
    chevronIcon.className = "fas fa-chevron-down me-2";
    const courseStrong = document.createElement("strong");
    courseStrong.textContent = courseKey;
    courseDiv.appendChild(chevronIcon);
    courseDiv.appendChild(courseStrong);
    courseCell.appendChild(courseDiv);
    courseRow.appendChild(courseCell);
    return courseRow;
  }

  function buildSectionHeaderRow(sectionKey, safeKey, sectionSafeKey) {
    const sectionRow = document.createElement("tr");
    sectionRow.className = `table-secondary group-${safeKey} collapse show`;
    const sectionCell = document.createElement("td");
    sectionCell.colSpan = 8;
    sectionCell.style.paddingLeft = "30px";
    sectionCell.classList.add("fw-semibold");
    const sectionDiv = document.createElement("div");
    sectionDiv.className = "d-flex align-items-center";
    sectionDiv.style.cursor = "pointer";
    sectionDiv.setAttribute("data-bs-toggle", "collapse");
    sectionDiv.setAttribute("data-bs-target", `.section-${sectionSafeKey}`);
    const sectionChevron = document.createElement("i");
    sectionChevron.className = "fas fa-chevron-down me-2";
    const sectionStrong = document.createElement("strong");
    sectionStrong.className = "text-secondary";
    sectionStrong.textContent = sectionKey;
    sectionDiv.appendChild(sectionChevron);
    sectionDiv.appendChild(sectionStrong);
    sectionCell.appendChild(sectionDiv);
    sectionRow.appendChild(sectionCell);
    return sectionRow;
  }

  function buildCloRow(clo, safeKey, sectionSafeKey, deps) {
    const outcomeId = clo.id || clo.outcome_id || "";
    const tr = document.createElement("tr");
    tr.className = `clo-row group-${safeKey} section-${sectionSafeKey} collapse show`;
    tr.style.cursor = "pointer";
    tr.dataset.outcomeId = outcomeId;
    appendBasicCells(tr, clo, deps);
    tr.appendChild(buildActionsCell(clo, outcomeId, deps));
    return tr;
  }

  function appendBasicCells(tr, clo, deps) {
    const { getStatusBadge, renderHistoryCellContent } = deps;
    const tdStatus = document.createElement("td");
    tdStatus.appendChild(getStatusBadge(clo.status));
    tr.appendChild(tdStatus);

    ["course_number", "section_number", "clo_number"].forEach((field) => {
      const td = document.createElement("td");
      td.textContent = clo[field] || "N/A";
      tr.appendChild(td);
    });

    const tdDesc = document.createElement("td");
    tdDesc.style.maxWidth = "250px";
    const descDiv = document.createElement("div");
    descDiv.textContent = clo.description || "";
    descDiv.title = clo.description;
    descDiv.style.display = "-webkit-box";
    descDiv.style.webkitLineClamp = "3";
    descDiv.style.webkitBoxOrient = "vertical";
    descDiv.style.overflow = "hidden";
    tdDesc.appendChild(descDiv);
    tr.appendChild(tdDesc);

    const tdInst = document.createElement("td");
    tdInst.textContent = clo.instructor_name || "N/A";
    tr.appendChild(tdInst);

    const tdHistory = document.createElement("td");
    tdHistory.appendChild(renderHistoryCellContent(clo));
    tr.appendChild(tdHistory);
  }

  function buildActionsCell(clo, outcomeId, deps) {
    const { approveOutcome, assignOutcome, remindOutcome } = deps;
    const tdActions = document.createElement("td");
    tdActions.className = "clo-actions";
    const btnGroup = document.createElement("div");
    btnGroup.className = "btn-group btn-group-sm";

    buildActionButtons(clo, outcomeId, {
      approveOutcome,
      assignOutcome,
      remindOutcome,
    }).forEach((btn) => btnGroup.appendChild(btn));

    const viewBtn = document.createElement("button");
    viewBtn.type = "button";
    viewBtn.className = "btn btn-outline-secondary";
    viewBtn.dataset.outcomeId = outcomeId;
    viewBtn.title = "View Details";
    viewBtn.innerHTML = '<i class="fas fa-eye"></i>';
    viewBtn.onclick = (e) => {
      e.stopPropagation();
      globalThis.showCLODetails(outcomeId);
    };
    btnGroup.appendChild(viewBtn);
    tdActions.appendChild(btnGroup);
    return tdActions;
  }

  function buildActionButtons(clo, outcomeId, deps) {
    const buttons = [];
    if (
      ["awaiting_approval", "in_progress", "approval_pending"].includes(
        clo.status,
      )
    ) {
      buttons.push(
        buildIconButton(
          "btn btn-success text-white",
          "Approve Outcome",
          "fas fa-check",
          (e) => {
            e.stopPropagation();
            deps.approveOutcome(outcomeId);
          },
        ),
      );
    }
    if (clo.status === "awaiting_approval") {
      buttons.push(
        buildIconButton(
          "btn btn-warning text-dark",
          "Request Rework",
          "fas fa-exclamation-triangle",
          (e) => {
            e.stopPropagation();
            globalThis.pendingReworkOutcomeId = outcomeId || null;
            globalThis.showCLODetails(outcomeId);
          },
        ),
      );
    }
    if (clo.status === "unassigned") {
      buttons.push(
        buildIconButton(
          "btn btn-primary text-white",
          "Assign Instructor",
          "fas fa-user-plus",
          (e) => {
            e.stopPropagation();
            deps.assignOutcome(outcomeId);
          },
        ),
      );
    }
    if (["in_progress", "approval_pending", "assigned"].includes(clo.status)) {
      buttons.push(
        buildIconButton(
          "btn btn-info text-white",
          "Send Reminder",
          "fas fa-bell",
          (e) => {
            e.stopPropagation();
            deps.remindOutcome(outcomeId, clo.instructor_id, clo.course_id);
          },
        ),
      );
    }
    return buttons;
  }

  function buildIconButton(className, title, iconClass, onClick) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = className;
    btn.title = title;
    btn.innerHTML = `<i class="${iconClass}"></i>`;
    btn.onclick = onClick;
    return btn;
  }

  const exportsObj = { renderCLOList };
  if (typeof globalThis !== "undefined") {
    globalThis.AuditCloList = exportsObj;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = exportsObj;
  }
})();

global.fetch = global.fetch || jest.fn();
global.bootstrap = global.bootstrap || {
  Modal: Object.assign(jest.fn(), {
    getInstance: jest.fn(),
    getOrCreateInstance: jest.fn(),
  }),
};
global.bootstrap.Modal.getInstance =
  global.bootstrap.Modal.getInstance || jest.fn();
global.bootstrap.Modal.getOrCreateInstance =
  global.bootstrap.Modal.getOrCreateInstance || jest.fn();
global.alert = global.alert || jest.fn();
global.prompt = global.prompt || jest.fn();

function setupAuditCloDom() {
  document.body.innerHTML = `
    <meta name="csrf-token" content="test-csrf-token">
    <select id="statusFilter"></select>
    <select id="sortBy"></select>
    <select id="sortOrder"></select>
    <select id="programFilter"></select>
    <select id="termFilter"></select>
    <button id="exportCsvBtn"></button>
    <div id="cloListContainer"></div>
    <div id="cloDetailModal">
      <div id="cloDetailContentMain"></div>
      <div id="cloReworkSection" style="display: none;">
        <form id="cloReworkForm">
          <div id="reworkCloDescription"></div>
          <textarea id="reworkFeedbackComments"></textarea>
          <input type="checkbox" id="reworkSendEmail" checked>
          <div id="reworkAlert" class="d-none"></div>
        </form>
      </div>
      <div id="cloDetailActionsStandard">
        <button id="requestReworkBtn" style="display: none;"></button>
        <button id="markNCIBtn" style="display: none;"></button>
        <button id="reopenBtn" style="display: none;"></button>
        <button id="approveBtn" style="display: none;"></button>
      </div>
      <div id="cloDetailActionsRework" style="display: none;">
        <button id="cancelReworkBtn"></button>
      </div>
    </div>
    <span id="statAwaitingApproval">0</span>
    <span id="statNeedsRework">0</span>
    <span id="statApproved">0</span>
    <span id="statInProgress">0</span>
    <span id="statNCI">0</span>
    <div id="assignInstructorModal" class="modal fade">
      <div class="modal-dialog">
        <div class="modal-content">
          <form id="assignInstructorForm">
            <select id="assignInstructorSelect" class="form-select">
              <option value="">Select Instructor...</option>
            </select>
            <button type="submit" id="saveInstructorBtn">Save</button>
          </form>
        </div>
      </div>
    </div>
    <div id="sendReminderModal" class="modal fade">
      <div id="reminderCloDescription"></div>
      <div id="reminderCourseDescription"></div>
      <div id="reminderInstructorEmail"></div>
      <textarea id="reminderMessage"></textarea>
    </div>
    <div id="inviteInstructorModal" class="modal fade">
      <form id="inviteInstructorForm">
        <input id="inviteFirstName">
        <input id="inviteLastName">
        <input id="inviteEmail">
        <div id="inviteAlert"></div>
      </form>
    </div>
    <div id="inviteSuccessModal" class="modal fade">
      <div id="inviteSuccessMessage"></div>
    </div>
  `;
}

function createMockModalInstance() {
  return {
    hide: jest.fn(),
    show: jest.fn(),
  };
}

function installDefaultAuditFetch(fetchMock) {
  fetchMock.mockImplementation((url) => {
    if (url === "/api/programs") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ programs: [{ id: "p1", name: "CS" }] }),
      });
    }
    if (url === "/api/terms") {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            terms: [
              {
                term_id: "t1",
                term_name: "Fall 2024",
                start_date: "2024-08-01",
              },
            ],
          }),
      });
    }
    if (url.includes("/api/outcomes/audit?status=")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ count: 5, outcomes: [] }),
      });
    }
    if (url.includes("/api/outcomes/")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({}),
    });
  });
}

function loadAuditCloViaEval() {
  const fs = require("fs");
  const path = require("path");
  const auditCloCode = fs.readFileSync(
    path.join(__dirname, "../../../../static/audit_clo.js"),
    "utf8",
  );
  eval(auditCloCode);
}

module.exports = {
  createMockModalInstance,
  installDefaultAuditFetch,
  loadAuditCloViaEval,
  setupAuditCloDom,
};

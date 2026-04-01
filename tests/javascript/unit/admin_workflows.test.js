const admin = require("../../../static/admin");
const { setBody } = require("../helpers/dom");

describe("admin module workflows", () => {
  beforeEach(() => {
    admin.__resetAdminState();
    setBody(`
      <div class="container-fluid"><div></div><div></div></div>
      <div id="usersLoading"></div>
      <div id="usersEmpty" class="d-none"></div>
      <table><tbody id="usersTableBody"></tbody></table>
      <div id="invitationsLoading"></div>
      <div id="invitationsEmpty" class="d-none"></div>
      <table><tbody id="invitationsTableBody"></tbody></table>
      <ul id="pagination"></ul>
      <span id="showingCount"></span>
      <span id="totalCount"></span>
      <button id="bulkActionsDropdown" class="d-none"></button>
      <span id="usersCount"></span>
      <span id="invitationsCount"></span>
      <select id="invitePrograms" multiple></select>
    `);
    const modalInstance = { show: jest.fn(), hide: jest.fn() };
    global.bootstrap = {
      Modal: jest.fn(() => modalInstance),
    };
    global.bootstrap.Modal.getInstance = jest.fn(() => modalInstance);
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, json: async () => ({ success: true }) }),
    );
  });

  describe("initialization and setup", () => {
    it("initializes event listeners correctly", () => {
      setBody(`
        <input id="searchInput" />
        <select id="roleFilter"></select>
        <select id="statusFilter"></select>
        <button id="clearFilters"></button>
        <input id="selectAllUsers" type="checkbox" />
        <input id="selectAllInvitations" type="checkbox" />
        <button id="inviteUserBtn"></button>
        <button id="bulkInviteBtn"></button>
        <button id="bulkResendBtn"></button>
        <button id="bulkCancelBtn"></button>
        <button id="bulkDeactivateBtn"></button>
      `);

      const addEventListener = jest.spyOn(document, "addEventListener");
      const querySelector = jest
        .spyOn(document, "getElementById")
        .mockImplementation(() => {
          const element = document.createElement("input");
          element.addEventListener = jest.fn();
          return element;
        });

      admin.initializeEventListeners();

      expect(querySelector).toHaveBeenCalledWith("searchInput");
      expect(querySelector).toHaveBeenCalledWith("roleFilter");
      expect(querySelector).toHaveBeenCalledWith("statusFilter");

      querySelector.mockRestore();
      addEventListener.mockRestore();
    });

    it("initializes filters with default values", () => {
      setBody(`
        <input id="searchInput" value="" />
        <select id="roleFilter"><option value="">All</option></select>
        <select id="statusFilter"><option value="">All</option></select>
      `);

      admin.initializeFilters();

      expect(document.getElementById("searchInput").value).toBe("");
      expect(document.getElementById("roleFilter").value).toBe("");
      expect(document.getElementById("statusFilter").value).toBe("");
    });

    it("initializes tabs correctly", () => {
      setBody(`
        <button class="tab-btn" data-tab="users">Users</button>
        <button class="tab-btn" data-tab="invitations">Invitations</button>
        <div id="usersTab" class="tab-content"></div>
        <div id="invitationsTab" class="tab-content"></div>
      `);

      admin.initializeTabs();

      const tabButtons = document.querySelectorAll(".tab-btn");
      expect(tabButtons.length).toBe(2);
    });

    it("handles debounced search correctly", (done) => {
      const mockHandler = jest.fn();

      const debouncedHandler = admin.debounce(mockHandler, 100);

      debouncedHandler();
      debouncedHandler();
      debouncedHandler();

      expect(mockHandler).not.toHaveBeenCalled();

      setTimeout(() => {
        expect(mockHandler).toHaveBeenCalledTimes(1);
        done();
      }, 150);
    });
  });

  describe("success message handling", () => {
    it("shows success messages correctly", () => {
      setBody(`
        <div class="container-fluid">
          <div>Header</div>
          <div>Content</div>
        </div>
      `);

      admin.showSuccess("Test success message");

      const successMessage = document.querySelector(".alert-success");
      expect(successMessage).toBeTruthy();
      expect(successMessage.textContent).toContain("Test success message");
    });

    it("sets up confirmation dialogs correctly", () => {
      setBody(`
        <div id="confirmModal" class="modal">
          <div class="modal-body">
            <div id="confirmModalLabel"></div>
            <div id="confirmModalBody"></div>
          </div>
          <button id="confirmActionBtn"></button>
        </div>
      `);

      global.bootstrap = {
        Modal: Object.assign(
          jest.fn(() => ({
            show: jest.fn(),
            hide: jest.fn(),
          })),
          {
            getInstance: jest.fn(() => ({
              hide: jest.fn(),
            })),
          },
        ),
      };

      expect(document.getElementById("confirmModalLabel")).toBeTruthy();
      expect(document.getElementById("confirmModalBody")).toBeTruthy();
      expect(document.getElementById("confirmActionBtn")).toBeTruthy();
    });
  });

  describe("utility functions", () => {
    it("formats roles correctly", () => {
      expect(admin.formatRole("program_admin")).toBe("Program Admin");
      expect(admin.formatRole("site_admin")).toBe("Site Admin");
      expect(admin.formatRole("faculty")).toBe("Faculty");
      expect(admin.formatRole("student")).toBe("Student");
    });

    it("formats status correctly", () => {
      expect(admin.formatStatus("active")).toBe("Active");
      expect(admin.formatStatus("inactive")).toBe("Inactive");
      expect(admin.formatStatus("pending")).toBe("Pending");
    });

    it("gets initials correctly", () => {
      expect(admin.getInitials("John", "Doe")).toBe("JD");
      expect(admin.getInitials("Jane", null)).toBe("J");
      expect(admin.getInitials(null, "Smith")).toBe("S");
      expect(admin.getInitials(null, null)).toBe("");
    });

    it("escapes HTML correctly", () => {
      expect(admin.escapeHtml('<script>alert("xss")</script>')).toContain(
        "&lt;script&gt;",
      );
      expect(admin.escapeHtml('<script>alert("xss")</script>')).toContain(
        "&gt;",
      );
      expect(admin.escapeHtml("Safe text")).toBe("Safe text");
      expect(admin.escapeHtml("A & B")).toBe("A &amp; B");
    });

    it("handles loading states correctly", () => {
      setBody(`
        <div id="testLoading"></div>
        <div id="testEmpty" class="d-none"></div>
        <button id="testButton">Test</button>
      `);

      const element = document.getElementById("testLoading");
      const button = document.getElementById("testButton");

      admin.setButtonLoadingState(button, true);
      expect(button.disabled).toBe(true);

      admin.setButtonLoadingState(button, false);
      expect(button.disabled).toBe(false);

      admin.showLoading("test");
      expect(element.style.display).toBe("block");

      admin.hideLoading("test");
      expect(element.style.display).toBe("none");
    });

    it("handles empty states correctly", () => {
      setBody(`
        <div id="testEmpty" class="d-none"></div>
      `);

      const element = document.getElementById("testEmpty");

      admin.showEmpty("test");
      expect(element.classList.contains("d-none")).toBe(false);

      admin.hideEmpty("test");
      expect(element.classList.contains("d-none")).toBe(true);
    });
  });

  it("covers all state properties in __setAdminState", () => {
    admin.__setAdminState({
      currentTab: "users",
      currentUsers: [],
      currentInvitations: [],
      selectedUsers: ["1"],
      selectedInvitations: ["2"],
      currentPage: 2,
      totalItems: 100,
      filters: { search: "test" },
    });

    expect(admin.__getAdminState()).toEqual(
      expect.objectContaining({
        currentTab: "users",
        currentUsers: [],
        currentInvitations: [],
        currentPage: 2,
        totalItems: 100,
        filters: { search: "test", role: "", status: "" },
      }),
    );
    expect(Array.from(admin.__getAdminState().selectedUsers)).toEqual(["1"]);
    expect(Array.from(admin.__getAdminState().selectedInvitations)).toEqual([
      "2",
    ]);
  });

  describe("openInviteModal", () => {
    beforeEach(() => {
      admin.__resetInviteModalWorkflows();
      setBody(`
        <div id="inviteUserModal" class="modal">
          <form id="inviteUserForm">
            <div id="sectionAssignmentGroup"></div>
            <input id="inviteSectionId" />
            <select id="inviteRole"></select>
            <input id="inviteFirstName" />
            <input id="inviteLastName" />
            <div id="programSelection"></div>
            <select id="invitePrograms"></select>
          </form>
        </div>
      `);

      const modalInstance = { show: jest.fn(), hide: jest.fn() };
      global.bootstrap = {
        Modal: jest.fn(() => modalInstance),
      };
    });

    it("opens modal with default workflow when no options provided", () => {
      admin.openInviteModal();
      expect(global.bootstrap.Modal).toHaveBeenCalled();
      expect(
        global.bootstrap.Modal.mock.results[0].value.show,
      ).toHaveBeenCalled();
    });

    it("warns when modal element not found", () => {
      const consoleSpy = jest.spyOn(console, "warn").mockImplementation();
      setBody("<div></div>");

      admin.openInviteModal();

      expect(consoleSpy).toHaveBeenCalledWith(
        "Invite modal is not present in the current DOM.",
      );
      consoleSpy.mockRestore();
    });

    it("uses custom workflow when specified", () => {
      const customReset = jest.fn();
      const customSetup = jest.fn();

      admin.registerInviteModalWorkflow("custom", {
        reset: customReset,
        setup: customSetup,
      });

      admin.openInviteModal({ workflow: "custom" });

      expect(customReset).toHaveBeenCalled();
      expect(customSetup).toHaveBeenCalled();
    });

    it("passes correct context to workflow functions", () => {
      let capturedContext;
      admin.registerInviteModalWorkflow("test", {
        reset: jest.fn(),
        setup: (context) => {
          capturedContext = context;
        },
      });

      const options = { sectionId: "sec-123", workflow: "test" };
      admin.openInviteModal(options);

      expect(capturedContext).toHaveProperty("modal");
      expect(capturedContext).toHaveProperty("form");
      expect(capturedContext).toHaveProperty("options", options);
    });

    it("handles workflow without reset function", () => {
      admin.registerInviteModalWorkflow("no-reset", {
        setup: jest.fn(),
      });

      expect(() =>
        admin.openInviteModal({ workflow: "no-reset" }),
      ).not.toThrow();
    });

    it("handles workflow without setup function", () => {
      admin.registerInviteModalWorkflow("no-setup", {
        reset: jest.fn(),
      });

      expect(() =>
        admin.openInviteModal({ workflow: "no-setup" }),
      ).not.toThrow();
    });

    it("falls back to default workflow for unknown workflow name", () => {
      admin.openInviteModal({ workflow: "nonexistent" });
      expect(global.bootstrap.Modal).toHaveBeenCalled();
    });
  });

  describe("registerInviteModalWorkflow", () => {
    beforeEach(() => {
      admin.__resetInviteModalWorkflows();
    });

    it("registers workflow with both reset and setup", () => {
      const reset = jest.fn();
      const setup = jest.fn();

      admin.registerInviteModalWorkflow("test", { reset, setup });

      const workflows = admin.__getInviteModalWorkflows();
      expect(workflows).toContain("test");
    });

    it("registers workflow with only reset function", () => {
      admin.registerInviteModalWorkflow("reset-only", { reset: jest.fn() });

      const workflows = admin.__getInviteModalWorkflows();
      expect(workflows).toContain("reset-only");
    });

    it("registers workflow with only setup function", () => {
      admin.registerInviteModalWorkflow("setup-only", { setup: jest.fn() });

      const workflows = admin.__getInviteModalWorkflows();
      expect(workflows).toContain("setup-only");
    });

    it("allows multiple workflows to be registered", () => {
      admin.registerInviteModalWorkflow("workflow1", {});
      admin.registerInviteModalWorkflow("workflow2", {});
      admin.registerInviteModalWorkflow("workflow3", {});

      const workflows = admin.__getInviteModalWorkflows();
      expect(workflows).toContain("workflow1");
      expect(workflows).toContain("workflow2");
      expect(workflows).toContain("workflow3");
    });
  });

  describe("default workflow", () => {
    beforeEach(() => {
      admin.__resetInviteModalWorkflows();

      admin.registerInviteModalWorkflow(admin.DEFAULT_INVITE_WORKFLOW, {
        reset({ form, sectionGroup, sectionIdField, roleSelect }) {
          if (form) {
            form.reset();
            form.classList.remove("was-validated");
          }
          if (sectionGroup) {
            sectionGroup.style.display = "none";
          }
          if (sectionIdField) {
            sectionIdField.value = "";
          }
          if (roleSelect) {
            roleSelect.value = "instructor";
            admin.setProgramSelectionVisibility("instructor");
          }
        },
        setup({
          options = {},
          sectionGroup,
          sectionIdField,
          roleSelect,
          inviteProgramsSelect,
          firstNameField,
          lastNameField,
        }) {
          const hasSection = Boolean(options.sectionId);
          if (hasSection && sectionGroup) {
            sectionGroup.style.display = "block";
            if (sectionIdField) {
              sectionIdField.value = options.sectionId;
            }
          }

          const roleToApply =
            options.prefillRole ||
            (hasSection ? "instructor" : roleSelect?.value) ||
            "instructor";
          if (roleSelect) {
            roleSelect.value = roleToApply;
          }
          admin.setProgramSelectionVisibility(roleToApply);

          if (firstNameField) {
            firstNameField.value = options.firstName || "";
          }
          if (lastNameField) {
            lastNameField.value = options.lastName || "";
          }

          if (
            options.programId &&
            roleToApply === "program_admin" &&
            inviteProgramsSelect
          ) {
            const applySelection = () => {
              Array.from(inviteProgramsSelect.options).forEach((opt) => {
                opt.selected = opt.value === options.programId;
              });
            };
            if (inviteProgramsSelect.options.length === 0) {
              setTimeout(applySelection, 50);
            } else {
              applySelection();
            }
          }
        },
      });

      setBody(`
        <div id="inviteUserModal" class="modal">
          <form id="inviteUserForm">
            <div id="sectionAssignmentGroup" style="display: none;"></div>
            <input id="inviteSectionId" value="" />
            <select id="inviteRole">
              <option value="instructor" selected></option>
              <option value="program_admin"></option>
            </select>
            <input id="inviteFirstName" value="" />
            <input id="inviteLastName" value="" />
            <div id="programSelection" style="display: none;"></div>
            <select id="invitePrograms"></select>
          </form>
        </div>
      `);

      const modalInstance = { show: jest.fn(), hide: jest.fn() };
      global.bootstrap = {
        Modal: jest.fn(() => modalInstance),
      };
    });

    it("shows section assignment when sectionId provided", () => {
      admin.openInviteModal({ sectionId: "sec-456" });

      const sectionGroup = document.getElementById("sectionAssignmentGroup");
      const sectionIdField = document.getElementById("inviteSectionId");

      expect(sectionGroup.style.display).toBe("block");
      expect(sectionIdField.value).toBe("sec-456");
    });

    it("prefills role when provided", () => {
      admin.openInviteModal({ prefillRole: "program_admin" });

      const roleSelect = document.getElementById("inviteRole");
      expect(roleSelect.value).toBe("program_admin");
    });

    it("prefills first and last names when provided", () => {
      admin.openInviteModal({
        firstName: "John",
        lastName: "Doe",
      });

      const firstNameField = document.getElementById("inviteFirstName");
      const lastNameField = document.getElementById("inviteLastName");

      expect(firstNameField.value).toBe("John");
      expect(lastNameField.value).toBe("Doe");
    });

    it("shows program selection when prefillRole is program_admin", () => {
      admin.openInviteModal({ prefillRole: "program_admin" });

      const programSelection = document.getElementById("programSelection");
      expect(programSelection.style.display).toBe("block");
    });

    it("applies programId selection when provided", (done) => {
      const programsSelect = document.getElementById("invitePrograms");
      programsSelect.options.add(new Option("Program 1", "prog-1"));
      programsSelect.options.add(new Option("Program 2", "prog-2"));

      admin.openInviteModal({
        programId: "prog-1",
        prefillRole: "program_admin",
      });

      setTimeout(() => {
        const selected = Array.from(programsSelect.selectedOptions).map(
          (o) => o.value,
        );
        expect(selected).toContain("prog-1");
        done();
      }, 10);
    });

    it("delays programId selection if select options not yet loaded", (done) => {
      const programsSelect = document.getElementById("invitePrograms");

      admin.openInviteModal({
        programId: "prog-1",
        prefillRole: "program_admin",
      });

      setTimeout(() => {
        programsSelect.options.add(new Option("Program 1", "prog-1"));
        programsSelect.options.add(new Option("Program 2", "prog-2"));
      }, 10);

      setTimeout(() => {
        const selected = Array.from(programsSelect.selectedOptions).map(
          (o) => o.value,
        );
        expect(selected).toContain("prog-1");
        done();
      }, 100);
    });
  });

  describe("handleRoleSelectionChange", () => {
    beforeEach(() => {
      setBody(`
        <div id="programSelection" style="display: none;"></div>
        <select id="invitePrograms"></select>
      `);
    });

    it("shows program selection for program_admin role", () => {
      const event = { target: { value: "program_admin" } };
      admin.handleRoleSelectionChange(event);

      const programSelection = document.getElementById("programSelection");
      const invitePrograms = document.getElementById("invitePrograms");

      expect(programSelection.style.display).toBe("block");
      expect(invitePrograms.required).toBe(true);
    });

    it("hides program selection for non-program_admin roles", () => {
      const event = { target: { value: "instructor" } };
      admin.handleRoleSelectionChange(event);

      const programSelection = document.getElementById("programSelection");
      const invitePrograms = document.getElementById("invitePrograms");

      expect(programSelection.style.display).toBe("none");
      expect(invitePrograms.required).toBe(false);
    });

    it("hides program selection for faculty role", () => {
      const event = { target: { value: "faculty" } };
      admin.handleRoleSelectionChange(event);

      const programSelection = document.getElementById("programSelection");
      expect(programSelection.style.display).toBe("none");
    });
  });

  describe("setProgramSelectionVisibility", () => {
    beforeEach(() => {
      setBody(`
        <div id="programSelection" style="display: none;"></div>
        <select id="invitePrograms"></select>
      `);
    });

    it("shows and requires programs for program_admin", () => {
      admin.setProgramSelectionVisibility("program_admin");

      const programSelection = document.getElementById("programSelection");
      const invitePrograms = document.getElementById("invitePrograms");

      expect(programSelection.style.display).toBe("block");
      expect(invitePrograms.required).toBe(true);
    });

    it("hides and unrequires programs for other roles", () => {
      admin.setProgramSelectionVisibility("instructor");

      const programSelection = document.getElementById("programSelection");
      const invitePrograms = document.getElementById("invitePrograms");

      expect(programSelection.style.display).toBe("none");
      expect(invitePrograms.required).toBe(false);
    });

    it("handles missing DOM elements gracefully", () => {
      setBody("<div></div>");
      expect(() =>
        admin.setProgramSelectionVisibility("program_admin"),
      ).not.toThrow();
    });
  });

  describe("applyUserStatusFilter", () => {
    it("filters for pending status", () => {
      admin.__setAdminState({
        filters: { status: "pending" },
      });

      const item = { account_status: "pending_verification" };
      const result = admin.applyUserStatusFilter(item);

      expect(result).toBe(true);
    });

    it("filters for inactive status", () => {
      admin.__setAdminState({
        filters: { status: "inactive" },
      });

      const item = { account_status: "inactive" };
      const result = admin.applyUserStatusFilter(item);

      expect(result).toBe(true);
    });

    it("returns false when status does not match pending filter", () => {
      admin.__setAdminState({
        filters: { status: "pending" },
      });

      const item = { account_status: "active" };
      const result = admin.applyUserStatusFilter(item);

      expect(result).toBe(false);
    });

    it("returns false when status does not match inactive filter", () => {
      admin.__setAdminState({
        filters: { status: "inactive" },
      });

      const item = { account_status: "active" };
      const result = admin.applyUserStatusFilter(item);

      expect(result).toBe(false);
    });
  });

  describe("displayInvitations", () => {
    beforeEach(() => {
      setBody(`
        <div id="invitationsLoading" class="d-none"></div>
        <div id="invitationsEmpty" class="d-none"></div>
        <table>
          <tbody id="invitationsTableBody"></tbody>
        </table>
      `);
    });

    it("displays pending invitation with resend and cancel buttons", () => {
      const invitations = [
        {
          id: "inv-123",
          email: "test@example.com",
          role: "instructor",
          status: "pending",
          invited_by: "Admin User",
          invited_at: "2024-01-01T10:00:00Z",
          expires_at: "2024-01-15T10:00:00Z",
        },
      ];

      admin.displayInvitations(invitations);

      const tbody = document.getElementById("invitationsTableBody");
      const rows = tbody.querySelectorAll("tr");

      expect(rows.length).toBe(1);
      expect(tbody.innerHTML).toContain("test@example.com");
      expect(tbody.innerHTML).toContain("pending");
      expect(tbody.innerHTML).toContain('data-invitation-id="inv-123"');
      expect(tbody.innerHTML).toContain("fa-paper-plane");
      expect(tbody.innerHTML).toContain("fa-times");
    });

    it("displays non-pending invitation without action buttons", () => {
      const invitations = [
        {
          id: "inv-456",
          email: "accepted@example.com",
          role: "faculty",
          status: "accepted",
          invited_by: "Admin User",
          invited_at: "2024-01-01T10:00:00Z",
        },
      ];

      admin.displayInvitations(invitations);

      const tbody = document.getElementById("invitationsTableBody");

      expect(tbody.innerHTML).toContain("accepted@example.com");
      expect(tbody.innerHTML).toContain("No actions");
      expect(tbody.innerHTML).not.toContain("fa-paper-plane");
      expect(tbody.innerHTML).not.toContain("fa-times");
    });

    it("hides loading and shows empty state when no invitations", () => {
      admin.displayInvitations([]);

      const loading = document.getElementById("invitationsLoading");
      const empty = document.getElementById("invitationsEmpty");
      const tbody = document.getElementById("invitationsTableBody");

      expect(loading.classList.contains("d-none")).toBe(true);
      expect(empty.classList.contains("d-none")).toBe(false);
      expect(tbody.innerHTML).toBe("");
    });

    it("displays multiple invitations with mixed statuses", () => {
      const invitations = [
        {
          id: "inv-1",
          email: "pending1@example.com",
          role: "instructor",
          status: "pending",
          invited_by: "Admin",
          invited_at: "2024-01-01T10:00:00Z",
          expires_at: "2024-01-15T10:00:00Z",
        },
        {
          id: "inv-2",
          email: "accepted@example.com",
          role: "faculty",
          status: "accepted",
          invited_by: "Admin",
          invited_at: "2024-01-02T10:00:00Z",
        },
      ];

      admin.displayInvitations(invitations);

      const tbody = document.getElementById("invitationsTableBody");
      const rows = tbody.querySelectorAll("tr");

      expect(rows.length).toBe(2);

      const firstRow = rows[0];
      expect(firstRow.innerHTML).toContain("fa-paper-plane");
      expect(firstRow.innerHTML).toContain("fa-times");

      const secondRow = rows[1];
      expect(secondRow.innerHTML).toContain("No actions");
    });
  });
});

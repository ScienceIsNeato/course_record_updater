const { setBody, flushPromises } = require("../helpers/dom");

describe("userManagement.js Coverage Boost", () => {
  let mockLoadUsers;

  beforeEach(() => {
    jest.resetModules();
    setBody(`
      <form id="inviteUserForm">
        <input id="inviteEmail" value="test@test.com">
        <select id="inviteRole"><option value="instructor">Instructor</option></select>
        <div id="programSelection">
            <select id="invitePrograms"></select>
        </div>
        <textarea id="inviteMessage"></textarea>
        <button id="sendInviteBtn">
            <span class="btn-text">Send</span>
            <span class="btn-spinner d-none"></span>
        </button>
      </form>
      <div id="inviteUserModal"></div>
      
      <form id="editUserForm">
        <input id="editUserId" value="u1">
        <input id="editFirstName" value="First">
        <input id="editLastName" value="Last">
        <input id="editDisplayName" value="Display">
        <button type="submit">
            <span class="btn-text">Save</span>
            <span class="btn-spinner d-none"></span>
        </button>
      </form>
      <div id="editUserModal"></div>
      
      <div class="alert-container"></div>
      <meta name="csrf-token" content="token">
    `);

    global.bootstrap = {
      Modal: jest.fn().mockImplementation(() => ({
        show: jest.fn(),
        hide: jest.fn(),
      })),
    };
    global.bootstrap.Modal.getInstance = jest.fn(() => ({ hide: jest.fn() }));

    mockLoadUsers = jest.fn();
    global.loadUsers = mockLoadUsers;

    jest.spyOn(window, "alert").mockImplementation(() => {});
    jest.spyOn(window, "confirm").mockReturnValue(true);
    jest.spyOn(window, "prompt").mockReturnValue("DELETE Test User");
    jest.spyOn(console, "error").mockImplementation(() => {});

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, message: "Success" }),
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
    delete global.loadUsers;
  });

  test("inviteUserForm calls loadUsers on success", async () => {
    require("../../../static/userManagement.js");
    document.dispatchEvent(new Event("DOMContentLoaded"));

    const form = document.getElementById("inviteUserForm");
    form.dispatchEvent(new Event("submit"));

    await flushPromises();

    expect(mockLoadUsers).toHaveBeenCalled();
  });

  test("editUserForm calls loadUsers on success", async () => {
    require("../../../static/userManagement.js");
    document.dispatchEvent(new Event("DOMContentLoaded"));

    const form = document.getElementById("editUserForm");
    form.dispatchEvent(new Event("submit"));

    await flushPromises();

    expect(mockLoadUsers).toHaveBeenCalled();
  });

  test("deactivateUser calls loadUsers on success", async () => {
    require("../../../static/userManagement.js");
    await global.deactivateUser("u1", "Test User");
    await flushPromises();
    expect(mockLoadUsers).toHaveBeenCalled();
  });

  test("deleteUser calls loadUsers on success", async () => {
    require("../../../static/userManagement.js");
    await global.deleteUser("u1", "Test User");
    await flushPromises();
    expect(mockLoadUsers).toHaveBeenCalled();
  });
});

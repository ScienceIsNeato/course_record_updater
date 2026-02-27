const { setBody } = require("../helpers/dom");

describe("programManagement.js", () => {
  let mockFetch;
  let alertSpy;
  let confirmSpy;
  let consoleErrorSpy;
  let consoleLogSpy;
  let loadProgramsSpy;
  let institutionDashboardRefreshSpy;

  const loadAndInit = () => {
    jest.resetModules();
    require("../../../static/programManagement");
    // Manually trigger init if needed, or rely on DOMContentLoaded
    document.dispatchEvent(new Event("DOMContentLoaded"));
  };

  beforeEach(() => {
    // Setup DOM
    setBody(`
      <form id="createProgramForm">
        <input id="programName" value="New Program">
        <input id="programShortName" value="NEW">
        <select id="programInstitutionId"><option value="">Select</option></select>
        <input type="checkbox" id="programActive" checked>
        <button id="createProgramBtn" type="submit">
            <span class="btn-text">Create</span>
            <span class="btn-spinner d-none"></span>
        </button>
      </form>
      <div id="createProgramModal" class="modal"></div>

      <form id="editProgramForm">
        <input type="hidden" id="editProgramId" value="prog-1">
        <input id="editProgramName" value="Updated Program">
        <input type="checkbox" id="editProgramActive" checked>
        <button type="submit">
            <span class="btn-text">Save</span>
            <span class="btn-spinner d-none"></span>
        </button>
      </form>
      <div id="editProgramModal" class="modal"></div>
      
      <meta name="csrf-token" content="test-token">
    `);

    // Mocks
    mockFetch = jest.fn();
    global.fetch = mockFetch;
    alertSpy = jest.spyOn(window, "alert").mockImplementation();
    confirmSpy = jest.spyOn(window, "confirm").mockImplementation();
    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();
    consoleLogSpy = jest.spyOn(console, "log").mockImplementation();

    // Global function mocks
    loadProgramsSpy = jest.fn();
    global.loadPrograms = loadProgramsSpy;

    institutionDashboardRefreshSpy = jest.fn();
    global.InstitutionDashboard = { refresh: institutionDashboardRefreshSpy };

    global.userContext = {
      institutionId: "inst-1",
      institutionName: "Test Inst",
    };

    // Bootstrap mock
    global.bootstrap = {
      Modal: class {
        constructor(element) {
          this.element = element;
        }
        show() {}
        hide() {}
        static getInstance() {
          return { hide: jest.fn() };
        }
      },
    };
  });

  afterEach(() => {
    jest.restoreAllMocks();
    delete global.loadPrograms;
    delete global.InstitutionDashboard;
    delete global.userContext;
    delete global.bootstrap;
  });

  test("loadInstitutionsForDropdown populates from userContext", () => {
    loadAndInit();

    // Wait for async operations (though loadInstitutionsForDropdown is technically async, it just does DOM ops here)
    const select = document.getElementById("programInstitutionId");
    expect(select.options.length).toBe(2);
    expect(select.options[1].value).toBe("inst-1");
    expect(select.options[1].text).toBe("Test Inst");
  });

  test("createProgram calls loadPrograms on success", async () => {
    loadAndInit();

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: "Created" }),
    });

    const form = document.getElementById("createProgramForm");
    form.dispatchEvent(new Event("submit"));

    // Wait for promise resolution
    await Promise.resolve();
    await Promise.resolve();

    expect(loadProgramsSpy).toHaveBeenCalled();
  });

  test("updateProgram calls loadPrograms on success", async () => {
    loadAndInit();

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: "Updated" }),
    });

    const form = document.getElementById("editProgramForm");
    form.dispatchEvent(new Event("submit"));

    await Promise.resolve();
    await Promise.resolve();

    expect(loadProgramsSpy).toHaveBeenCalled();
  });

  test("deleteProgram calls InstitutionDashboard.refresh on success", async () => {
    loadAndInit();
    confirmSpy.mockReturnValue(true);

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: "Deleted" }),
    });

    await global.deleteProgram("prog-1", "Test Program");

    expect(institutionDashboardRefreshSpy).toHaveBeenCalled();
  });

  test("deleteProgram calls loadPrograms if InstitutionDashboard missing", async () => {
    loadAndInit();
    confirmSpy.mockReturnValue(true);
    delete global.InstitutionDashboard; // Remove dashboard mock

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: "Deleted" }),
    });

    await global.deleteProgram("prog-1", "Test Program");

    expect(loadProgramsSpy).toHaveBeenCalled();
  });
});

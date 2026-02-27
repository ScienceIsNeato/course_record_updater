const { setBody } = require("../helpers/dom");
const managementUtils = require("../../../static/management_utils");

describe("management_utils.js", () => {
  let showMessageSpy;
  let alertSpy;
  let consoleErrorSpy;
  let loadTableDataSpy;
  let locationReloadSpy;

  beforeEach(() => {
    setBody(""); // Reset DOM

    showMessageSpy = jest.fn();
    global.showMessage = showMessageSpy;

    alertSpy = jest.spyOn(window, "alert").mockImplementation();
    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();

    loadTableDataSpy = jest.fn();
    global.loadTableData = loadTableDataSpy;

    // Mock location.reload
    delete global.location;
    global.location = { reload: jest.fn() };
    locationReloadSpy = global.location.reload;

    // Clear fetch mocks
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
    delete global.showMessage;
    delete global.loadTableData;
  });

  describe("loadSelectOptions", () => {
    beforeEach(() => {
      setBody('<select id="testSelect"></select>');
    });

    test("loads options successfully", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          data: [
            { id: 1, name: "Option 1" },
            { id: 2, name: "Option 2" },
          ],
        }),
      });

      await managementUtils.loadSelectOptions(
        "testSelect",
        "/api/test",
        (item) => ({ value: item.id, label: item.name }),
      );

      const select = document.getElementById("testSelect");
      expect(select.options.length).toBe(3); // -- Select -- + 2 options
      expect(select.options[0].value).toBe("");
      expect(select.options[1].value).toBe("1");
      expect(select.options[2].value).toBe("2");
      expect(select.disabled).toBe(false);
    });

    test("handles empty data", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          data: [],
        }),
      });

      await managementUtils.loadSelectOptions(
        "testSelect",
        "/api/test",
        (item) => ({ value: item.id, label: item.name }),
        "Custom empty text",
      );

      const select = document.getElementById("testSelect");
      expect(select.options.length).toBe(1);
      expect(select.options[0].textContent).toBe("Custom empty text");
    });

    test("handles fetch error", async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        json: async () => ({ success: false, error: "API Error" }),
      });

      await managementUtils.loadSelectOptions(
        "testSelect",
        "/api/test",
        (item) => ({ value: item.id, label: item.name }),
      );

      const select = document.getElementById("testSelect");
      expect(select.options[0].textContent).toBe("Error loading options");
      expect(consoleErrorSpy).toHaveBeenCalled();
    });

    test("handles network error", async () => {
      global.fetch.mockRejectedValue(new Error("Network failure"));

      await managementUtils.loadSelectOptions(
        "testSelect",
        "/api/test",
        (item) => ({ value: item.id, label: item.name }),
      );

      const select = document.getElementById("testSelect");
      expect(select.options[0].textContent).toBe("Error loading options");
      expect(consoleErrorSpy).toHaveBeenCalled();
    });

    test("handles missing select element", async () => {
      await managementUtils.loadSelectOptions(
        "nonexistent",
        "/api/test",
        (item) => ({ value: item.id, label: item.name }),
      );
      // Should not throw
      expect(global.fetch).not.toHaveBeenCalled();
    });
  });

  describe("submitCRUDForm", () => {
    test("successful submission", async () => {
      const onSuccess = jest.fn();
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, message: "Created" }),
      });

      setBody('<meta name="csrf-token" content="test-token">');

      await managementUtils.submitCRUDForm({
        endpoint: "/api/test",
        method: "POST",
        data: { name: "Test" },
        onSuccess,
      });

      expect(onSuccess).toHaveBeenCalledWith({
        success: true,
        message: "Created",
      });
    });

    test("handles API error with custom onError", async () => {
      const onError = jest.fn();
      global.fetch.mockResolvedValue({
        ok: false,
        json: async () => ({ success: false, error: "Invalid data" }),
      });

      setBody('<meta name="csrf-token" content="test-token">');

      await managementUtils.submitCRUDForm({
        endpoint: "/api/test",
        method: "POST",
        data: { name: "Test" },
        onSuccess: jest.fn(),
        onError,
      });

      expect(onError).toHaveBeenCalled();
    });

    test("handles network error", async () => {
      const onError = jest.fn();
      global.fetch.mockRejectedValue(new Error("Network error"));

      setBody('<meta name="csrf-token" content="test-token">');

      await managementUtils.submitCRUDForm({
        endpoint: "/api/test",
        data: {},
        onSuccess: jest.fn(),
        onError,
      });

      expect(onError).toHaveBeenCalledWith(null, { error: "Network error" });
    });

    test("shows default error when no onError callback", async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        json: async () => ({ success: false, error: "Failed" }),
      });

      setBody('<meta name="csrf-token" content="test-token">');

      await managementUtils.submitCRUDForm({
        endpoint: "/api/test",
        data: {},
        onSuccess: jest.fn(),
      });

      expect(showMessageSpy).toHaveBeenCalledWith("Failed", "danger");
    });
  });

  describe("getCSRFToken", () => {
    test("gets token from meta tag", () => {
      setBody('<meta name="csrf-token" content="meta-token">');
      expect(managementUtils.getCSRFToken()).toBe("meta-token");
    });

    test("falls back to cookie", () => {
      setBody("");
      // Clear existing cookies first
      document.cookie.split(";").forEach((c) => {
        document.cookie = c
          .replace(/^ +/, "")
          .replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
      });
      document.cookie = "csrf_token=cookie-token";
      expect(managementUtils.getCSRFToken()).toBe("cookie-token");
    });

    test("returns empty string when no token found", () => {
      setBody("");
      // Clear all cookies
      document.cookie.split(";").forEach((c) => {
        document.cookie = c
          .replace(/^ +/, "")
          .replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
      });
      const token = managementUtils.getCSRFToken();
      expect(token).toBe("");
    });
  });

  test("showSuccess uses global.showMessage if available", () => {
    managementUtils.showSuccess("Success!");
    expect(showMessageSpy).toHaveBeenCalledWith("Success!", "success");
    expect(alertSpy).not.toHaveBeenCalled();
  });

  test("showSuccess falls back to alert", () => {
    delete global.showMessage;
    managementUtils.showSuccess("Success!");
    expect(alertSpy).toHaveBeenCalledWith("Success!");
  });

  test("showError uses global.showMessage if available", () => {
    managementUtils.showError("Error!");
    expect(showMessageSpy).toHaveBeenCalledWith("Error!", "danger");
    expect(alertSpy).not.toHaveBeenCalled();
  });

  test("showError falls back to alert", () => {
    delete global.showMessage;
    managementUtils.showError("Error!");
    expect(consoleErrorSpy).toHaveBeenCalledWith("Error!");
    expect(alertSpy).toHaveBeenCalledWith("Error: Error!");
  });

  test("reloadDataTable uses global.loadTableData if available", () => {
    managementUtils.reloadDataTable();
    expect(loadTableDataSpy).toHaveBeenCalled();
    expect(locationReloadSpy).not.toHaveBeenCalled();
  });

  test("reloadDataTable falls back to location.reload if loadTableData missing", () => {
    delete global.loadTableData;
    managementUtils.reloadDataTable();
    expect(locationReloadSpy).toHaveBeenCalled();
  });

  describe("closeModal", () => {
    test("closes modal when bootstrap is available", () => {
      const hideSpy = jest.fn();
      setBody('<div id="testModal" class="modal"></div>');

      global.bootstrap = {
        Modal: {
          getInstance: jest.fn(() => ({ hide: hideSpy })),
        },
      };

      managementUtils.closeModal("testModal");
      expect(hideSpy).toHaveBeenCalled();
    });

    test("handles missing modal", () => {
      global.bootstrap = {
        Modal: {
          getInstance: jest.fn(),
        },
      };

      managementUtils.closeModal("nonexistent");
      expect(global.bootstrap.Modal.getInstance).not.toHaveBeenCalled();
    });

    test("handles missing bootstrap", () => {
      setBody('<div id="testModal" class="modal"></div>');
      delete global.bootstrap;

      // Validates graceful degradation when bootstrap is missing
      expect(() => managementUtils.closeModal("testModal")).not.toThrow();
    });
  });

  describe("resetForm", () => {
    test("resets form and clears validation", () => {
      setBody(`
        <form id="testForm" class="was-validated">
          <input type="text" class="is-invalid" value="test">
          <input type="text" class="is-valid">
        </form>
      `);

      const form = document.getElementById("testForm");
      const resetSpy = jest.spyOn(form, "reset");

      managementUtils.resetForm("testForm");

      expect(resetSpy).toHaveBeenCalled();
      expect(form.classList.contains("was-validated")).toBe(false);
      expect(form.querySelectorAll(".is-invalid").length).toBe(0);
      expect(form.querySelectorAll(".is-valid").length).toBe(0);
    });

    test("handles missing form", () => {
      // Validates graceful degradation when form doesn't exist
      expect(() => managementUtils.resetForm("nonexistent")).not.toThrow();
    });
  });
});

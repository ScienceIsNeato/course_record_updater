const { setBody, flushPromises } = require("../helpers/dom");

describe("script.js Import Helper Functions", () => {
  beforeEach(() => {
    jest.resetModules();
    window.alert = jest.fn();
    global.confirm.mockReturnValue(true);
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, count: 0 }),
    });
  });

  const setupImportDom = () => {
    setBody(`
      <form id="excelImportForm">
        <input type="file" id="excel_file" />
        <select id="import_adapter">
          <option value="adapter_a">Adapter A</option>
        </select>
        <input type="checkbox" id="dry_run" />
        <div id="importBtnText"></div>
        <div id="importProgress"></div>
        <div id="importStatus"></div>
        <div id="importResults"></div>
        <div>
          <input type="radio" name="conflict_strategy" value="use_theirs" checked />
        </div>
        <button id="validateImportBtn" type="button"></button>
        <button id="executeImportBtn" type="submit"></button>
      </form>
      <table class="table"><tbody></tbody></table>
    `);
  };

  const loadScript = () => {
    const domReadyHandlers = [];
    const originalAddEventListener = document.addEventListener.bind(document);

    document.addEventListener = function (event, handler, options) {
      if (event === "DOMContentLoaded") {
        domReadyHandlers.push(handler);
      } else {
        originalAddEventListener(event, handler, options);
      }
    };

    jest.isolateModules(() => {
      require("../../../static/script");
    });

    document.addEventListener = originalAddEventListener;

    const handler = domReadyHandlers.pop();
    if (handler) {
      handler.call(document, new Event("DOMContentLoaded"));
    }
  };

  describe("validateImportForm()", () => {
    it("returns false when no file is selected", () => {
      setupImportDom();
      loadScript();

      window.alert.mockClear();
      const validateBtn = document.getElementById("validateImportBtn");
      validateBtn.click();

      expect(window.alert).toHaveBeenCalledWith(
        "Please select an Excel file first.",
      );
    });

    it("returns false when no conflict strategy is selected", () => {
      // Setup DOM without conflict strategy radio button
      setBody(`
        <form id="excelImportForm">
          <input type="file" id="excel_file" />
          <select id="import_adapter">
            <option value="adapter_a">Adapter A</option>
          </select>
          <input type="checkbox" id="dry_run" />
          <div id="importBtnText"></div>
          <div id="importProgress"></div>
          <div id="importStatus"></div>
          <div id="importResults"></div>
          <button id="validateImportBtn" type="button"></button>
          <button id="executeImportBtn" type="submit"></button>
        </form>
        <table class="table"><tbody></tbody></table>
      `);
      loadScript();

      const fileInput = document.getElementById("excel_file");
      const fakeFile = { name: "test.xlsx" };
      Object.defineProperty(fileInput, "files", {
        value: [fakeFile],
        configurable: true,
      });

      window.alert.mockClear();
      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );

      expect(window.alert).toHaveBeenCalledWith(
        "Please select a conflict resolution strategy.",
      );
    });

    it("returns true when file and strategy are selected", async () => {
      setupImportDom();
      loadScript();

      const fileInput = document.getElementById("excel_file");
      const fakeFile = { name: "test.xlsx" };
      Object.defineProperty(fileInput, "files", {
        value: [fakeFile],
        configurable: true,
      });

      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, validation: { rows: 10 } }),
      });

      window.alert.mockClear();
      const validateBtn = document.getElementById("validateImportBtn");
      validateBtn.click();
      await flushPromises();

      // Should not show validation error alerts
      expect(window.alert).not.toHaveBeenCalledWith(
        expect.stringContaining("Please select"),
      );
    });
  });

  describe("buildConfirmationMessage()", () => {
    it("builds message for use_theirs strategy without delete", () => {
      setupImportDom();
      loadScript();

      const fileInput = document.getElementById("excel_file");
      const fakeFile = { name: "test.xlsx" };
      Object.defineProperty(fileInput, "files", {
        value: [fakeFile],
        configurable: true,
      });

      global.confirm.mockReturnValueOnce(true);
      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );

      expect(global.confirm).toHaveBeenCalledWith(
        expect.stringContaining("modify"),
      );
    });

    it("includes delete warning when deleteExistingDb is checked", () => {
      setBody(`
        <form id="excelImportForm">
          <input type="file" id="excel_file" />
          <select id="import_adapter">
            <option value="adapter_a">Adapter A</option>
          </select>
          <input type="checkbox" id="dry_run" />
          <input type="checkbox" id="delete_existing_db" checked />
          <div id="importBtnText"></div>
          <div id="importProgress"></div>
          <div id="importStatus"></div>
          <div id="importResults"></div>
          <div>
            <input type="radio" name="conflict_strategy" value="use_theirs" checked />
          </div>
          <button id="validateImportBtn" type="button"></button>
          <button id="executeImportBtn" type="submit"></button>
        </form>
        <table class="table"><tbody></tbody></table>
      `);
      loadScript();

      const fileInput = document.getElementById("excel_file");
      const fakeFile = { name: "test.xlsx" };
      Object.defineProperty(fileInput, "files", {
        value: [fakeFile],
        configurable: true,
      });

      global.confirm.mockReturnValueOnce(true);
      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );

      expect(global.confirm).toHaveBeenCalledWith(
        expect.stringContaining("DELETE ALL EXISTING DATA"),
      );
    });
  });

  describe("buildImportFormData()", () => {
    it("builds FormData with all required fields", async () => {
      jest.useFakeTimers();
      setBody(`
        <form id="excelImportForm">
          <input type="file" id="excel_file" />
          <select id="import_adapter">
            <option value="mocku_excel_adapter" selected>MockU Excel Adapter</option>
          </select>
          <input type="checkbox" id="dry_run" />
          <div id="importBtnText"></div>
          <div id="importProgress"></div>
          <div id="importStatus"></div>
          <div id="importResults"></div>
          <div>
            <input type="radio" name="conflict_strategy" value="use_theirs" checked />
          </div>
          <button id="validateImportBtn" type="button"></button>
          <button id="executeImportBtn" type="submit"></button>
        </form>
        <table class="table"><tbody></tbody></table>
      `);

      const file = new File(["data"], "courses.xlsx");
      Object.defineProperty(document.getElementById("excel_file"), "files", {
        value: [file],
        configurable: true,
      });

      global.fetch.mockImplementation((url) => {
        if (url === "/api/import/excel") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true, progress_id: "test" }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, count: 0 }),
        });
      });

      loadScript();

      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await flushPromises();

      expect(global.fetch).toHaveBeenCalledWith(
        "/api/import/excel",
        expect.objectContaining({
          method: "POST",
          body: expect.any(FormData),
        }),
      );

      const fetchCall = global.fetch.mock.calls.find(
        (call) => call[0] === "/api/import/excel",
      );
      const formData = fetchCall[1].body;

      // Verify FormData contents (note: FormData.get() is available in jsdom)
      expect(formData.get("adapter_name")).toBe("mocku_excel_adapter");
      expect(formData.get("conflict_strategy")).toBe("use_theirs");
      expect(formData.get("dry_run")).toBe("false");

      jest.useRealTimers();
    });

    it("includes dry_run flag when checked", async () => {
      jest.useFakeTimers();
      setupImportDom();

      const file = new File(["data"], "courses.xlsx");
      Object.defineProperty(document.getElementById("excel_file"), "files", {
        value: [file],
        configurable: true,
      });

      document.getElementById("dry_run").checked = true;

      global.fetch.mockImplementation((url) => {
        if (url === "/api/import/excel") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true, progress_id: "test" }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, count: 0 }),
        });
      });

      loadScript();

      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await flushPromises();

      const fetchCall = global.fetch.mock.calls.find(
        (call) => call[0] === "/api/import/excel",
      );
      const formData = fetchCall[1].body;

      expect(formData.get("dry_run")).toBe("true");

      jest.useRealTimers();
    });

    it("includes delete_existing_db flag when checked", async () => {
      jest.useFakeTimers();
      setBody(`
        <form id="excelImportForm">
          <input type="file" id="excel_file" />
          <select id="import_adapter">
            <option value="adapter_a">Adapter A</option>
          </select>
          <input type="checkbox" id="dry_run" />
          <input type="checkbox" id="delete_existing_db" checked />
          <div id="importBtnText"></div>
          <div id="importProgress"></div>
          <div id="importStatus"></div>
          <div id="importResults"></div>
          <div>
            <input type="radio" name="conflict_strategy" value="use_theirs" checked />
          </div>
          <button id="validateImportBtn" type="button"></button>
          <button id="executeImportBtn" type="submit"></button>
        </form>
        <table class="table"><tbody></tbody></table>
      `);

      const file = new File(["data"], "courses.xlsx");
      Object.defineProperty(document.getElementById("excel_file"), "files", {
        value: [file],
        configurable: true,
      });

      global.fetch.mockImplementation((url) => {
        if (url === "/api/import/excel") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true, progress_id: "test" }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, count: 0 }),
        });
      });

      loadScript();

      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await flushPromises();

      const fetchCall = global.fetch.mock.calls.find(
        (call) => call[0] === "/api/import/excel",
      );
      const formData = fetchCall[1].body;

      expect(formData.get("delete_existing_db")).toBe("true");

      jest.useRealTimers();
    });

    it("handles missing delete_existing_db checkbox gracefully", async () => {
      jest.useFakeTimers();
      setupImportDom(); // Default DOM doesn't have delete_existing_db

      const file = new File(["data"], "courses.xlsx");
      Object.defineProperty(document.getElementById("excel_file"), "files", {
        value: [file],
        configurable: true,
      });

      global.fetch.mockImplementation((url) => {
        if (url === "/api/import/excel") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true, progress_id: "test" }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, count: 0 }),
        });
      });

      loadScript();

      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await flushPromises();

      const fetchCall = global.fetch.mock.calls.find(
        (call) => call[0] === "/api/import/excel",
      );
      const formData = fetchCall[1].body;

      expect(formData.get("delete_existing_db")).toBe("false");

      jest.useRealTimers();
    });
  });

  describe("buildImportHeader()", () => {
    it("builds success header with green styling", async () => {
      jest.useFakeTimers();
      setupImportDom();

      const file = new File(["data"], "courses.xlsx");
      Object.defineProperty(document.getElementById("excel_file"), "files", {
        value: [file],
        configurable: true,
      });

      global.fetch.mockImplementation((url) => {
        if (url === "/api/import/excel") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true, progress_id: "test" }),
          });
        }
        if (url === "/api/import/progress/test") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              status: "completed",
              percentage: 100,
              result: {
                success: true,
                records_processed: 10,
                records_created: 5,
                dry_run: false,
              },
            }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, count: 0 }),
        });
      });

      loadScript();

      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await flushPromises();
      jest.runOnlyPendingTimers();
      await flushPromises();

      const importResults = document.getElementById("importResults");
      expect(importResults.innerHTML).toContain("alert-success");
      expect(importResults.innerHTML).toContain("fa-check-circle");

      jest.useRealTimers();
    });

    it("builds failure header with red styling", async () => {
      jest.useFakeTimers();
      setupImportDom();

      const file = new File(["data"], "courses.xlsx");
      Object.defineProperty(document.getElementById("excel_file"), "files", {
        value: [file],
        configurable: true,
      });

      global.fetch.mockImplementation((url) => {
        if (url === "/api/import/excel") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true, progress_id: "test" }),
          });
        }
        if (url === "/api/import/progress/test") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              status: "error",
              message: "Import failed",
              result: { success: false, dry_run: false },
            }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, count: 0 }),
        });
      });

      loadScript();

      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await flushPromises();
      jest.runOnlyPendingTimers();
      await flushPromises();

      const importResults = document.getElementById("importResults");
      expect(importResults.innerHTML).toContain("alert-danger");
      expect(importResults.innerHTML).toContain("fa-exclamation-circle");

      jest.useRealTimers();
    });

    it("displays DRY RUN mode correctly", async () => {
      jest.useFakeTimers();
      setupImportDom();

      const file = new File(["data"], "courses.xlsx");
      Object.defineProperty(document.getElementById("excel_file"), "files", {
        value: [file],
        configurable: true,
      });

      document.getElementById("dry_run").checked = true;

      global.fetch.mockImplementation((url) => {
        if (url === "/api/import/excel") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true, progress_id: "test" }),
          });
        }
        if (url === "/api/import/progress/test") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              status: "completed",
              percentage: 100,
              result: {
                success: true,
                records_processed: 10,
                dry_run: true,
              },
            }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, count: 0 }),
        });
      });

      loadScript();

      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await flushPromises();
      jest.runOnlyPendingTimers();
      await flushPromises();

      expect(document.getElementById("importResults").innerHTML).toContain(
        "DRY RUN",
      );

      jest.useRealTimers();
    });
  });

  describe("buildErrorsSection()", () => {
    it("returns empty string when no errors", async () => {
      jest.useFakeTimers();
      setupImportDom();

      const file = new File(["data"], "courses.xlsx");
      Object.defineProperty(document.getElementById("excel_file"), "files", {
        value: [file],
        configurable: true,
      });

      global.fetch.mockImplementation((url) => {
        if (url === "/api/import/excel") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true, progress_id: "test" }),
          });
        }
        if (url === "/api/import/progress/test") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              status: "completed",
              percentage: 100,
              result: {
                success: true,
                errors: [],
              },
            }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, count: 0 }),
        });
      });

      loadScript();

      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await flushPromises();
      jest.runOnlyPendingTimers();
      await flushPromises();

      const importResults = document.getElementById("importResults");
      expect(importResults.innerHTML).not.toContain("Errors (");

      jest.useRealTimers();
    });

    it("displays first 10 errors with more count", async () => {
      jest.useFakeTimers();
      setupImportDom();

      const errors = Array.from({ length: 15 }).map((_, idx) => `Error ${idx}`);

      global.fetch.mockImplementation((url) => {
        if (url === "/api/import/excel") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true, progress_id: "test" }),
          });
        }
        if (url === "/api/import/progress/test") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              status: "completed",
              percentage: 100,
              result: {
                success: true,
                errors: errors,
              },
            }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, count: 0 }),
        });
      });

      loadScript();

      const file = new File(["data"], "courses.xlsx");
      Object.defineProperty(document.getElementById("excel_file"), "files", {
        value: [file],
        configurable: true,
      });

      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await flushPromises();
      jest.runOnlyPendingTimers();
      await flushPromises();

      const importResults = document.getElementById("importResults");
      expect(importResults.innerHTML).toContain("Errors (15)");
      expect(importResults.innerHTML).toContain("and 5 more errors");

      jest.useRealTimers();
    });
  });

  describe("buildWarningsSection()", () => {
    it("returns empty string when no warnings", async () => {
      jest.useFakeTimers();
      setupImportDom();

      const file = new File(["data"], "courses.xlsx");
      Object.defineProperty(document.getElementById("excel_file"), "files", {
        value: [file],
        configurable: true,
      });

      global.fetch.mockImplementation((url) => {
        if (url === "/api/import/excel") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true, progress_id: "test" }),
          });
        }
        if (url === "/api/import/progress/test") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              status: "completed",
              percentage: 100,
              result: {
                success: true,
                warnings: [],
              },
            }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, count: 0 }),
        });
      });

      loadScript();

      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await flushPromises();
      jest.runOnlyPendingTimers();
      await flushPromises();

      const importResults = document.getElementById("importResults");
      expect(importResults.innerHTML).not.toContain("Warnings (");

      jest.useRealTimers();
    });

    it("displays first 5 warnings with more count", async () => {
      jest.useFakeTimers();
      setupImportDom();

      const warnings = Array.from({ length: 8 }).map(
        (_, idx) => `Warning ${idx}`,
      );

      global.fetch.mockImplementation((url) => {
        if (url === "/api/import/excel") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true, progress_id: "test" }),
          });
        }
        if (url === "/api/import/progress/test") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              status: "completed",
              percentage: 100,
              result: {
                success: true,
                warnings: warnings,
              },
            }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, count: 0 }),
        });
      });

      loadScript();

      const file = new File(["data"], "courses.xlsx");
      Object.defineProperty(document.getElementById("excel_file"), "files", {
        value: [file],
        configurable: true,
      });

      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await flushPromises();
      jest.runOnlyPendingTimers();
      await flushPromises();

      const importResults = document.getElementById("importResults");
      expect(importResults.innerHTML).toContain("Warnings (8)");
      expect(importResults.innerHTML).toContain("and 3 more warnings");

      jest.useRealTimers();
    });
  });

  describe("buildConflictsSection()", () => {
    it("returns empty string when no conflicts", async () => {
      jest.useFakeTimers();
      setupImportDom();

      const file = new File(["data"], "courses.xlsx");
      Object.defineProperty(document.getElementById("excel_file"), "files", {
        value: [file],
        configurable: true,
      });

      global.fetch.mockImplementation((url) => {
        if (url === "/api/import/excel") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true, progress_id: "test" }),
          });
        }
        if (url === "/api/import/progress/test") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              status: "completed",
              percentage: 100,
              result: {
                success: true,
                conflicts: [],
              },
            }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, count: 0 }),
        });
      });

      loadScript();

      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await flushPromises();
      jest.runOnlyPendingTimers();
      await flushPromises();

      const importResults = document.getElementById("importResults");
      expect(importResults.innerHTML).not.toContain("Conflicts Resolved (");

      jest.useRealTimers();
    });

    it("displays first 20 conflicts with more count", async () => {
      jest.useFakeTimers();
      setupImportDom();

      const conflicts = Array.from({ length: 25 }).map((_, idx) => ({
        entity_type: "Course",
        entity_key: `C-${idx}`,
        field_name: "name",
        existing_value: "Old",
        import_value: "New",
        resolution: "kept_new",
      }));

      global.fetch.mockImplementation((url) => {
        if (url === "/api/import/excel") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true, progress_id: "test" }),
          });
        }
        if (url === "/api/import/progress/test") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              status: "completed",
              percentage: 100,
              result: {
                success: true,
                conflicts: conflicts,
              },
            }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, count: 0 }),
        });
      });

      loadScript();

      const file = new File(["data"], "courses.xlsx");
      Object.defineProperty(document.getElementById("excel_file"), "files", {
        value: [file],
        configurable: true,
      });

      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await flushPromises();
      jest.runOnlyPendingTimers();
      await flushPromises();

      const importResults = document.getElementById("importResults");
      expect(importResults.innerHTML).toContain("Conflicts Resolved (25)");
      expect(importResults.innerHTML).toContain("and 5 more conflicts");

      jest.useRealTimers();
    });

    it("displays conflict table with all required columns", async () => {
      jest.useFakeTimers();
      setupImportDom();

      const conflicts = [
        {
          entity_type: "Course",
          entity_key: "MATH101",
          field_name: "title",
          existing_value: "Algebra I",
          import_value: "Algebra 1",
          resolution: "use_theirs",
        },
      ];

      global.fetch.mockImplementation((url) => {
        if (url === "/api/import/excel") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ success: true, progress_id: "test" }),
          });
        }
        if (url === "/api/import/progress/test") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              status: "completed",
              percentage: 100,
              result: {
                success: true,
                conflicts: conflicts,
              },
            }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, count: 0 }),
        });
      });

      loadScript();

      const file = new File(["data"], "courses.xlsx");
      Object.defineProperty(document.getElementById("excel_file"), "files", {
        value: [file],
        configurable: true,
      });

      const form = document.getElementById("excelImportForm");
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await flushPromises();
      jest.runOnlyPendingTimers();
      await flushPromises();

      const importResults = document.getElementById("importResults");
      expect(importResults.innerHTML).toContain("Course");
      expect(importResults.innerHTML).toContain("MATH101");
      expect(importResults.innerHTML).toContain("title");
      expect(importResults.innerHTML).toContain("Algebra I");
      expect(importResults.innerHTML).toContain("Algebra 1");
      expect(importResults.innerHTML).toContain("use_theirs");

      jest.useRealTimers();
    });
  });
});

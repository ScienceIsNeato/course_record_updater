/** @jest-environment jsdom */

const {
  loadTerms,
  loadOfferings,
  loadInstructors,
  fetchJson,
} = require("../../../static/sectionManagement.js");

describe("sectionManagement helper functions", () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = global.fetch;
    document.body.innerHTML = `
      <select id="terms"></select>
      <select id="offerings"></select>
      <select id="instructors"></select>
    `;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.resetAllMocks();
  });

  test("fetchJson throws on non-ok response", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ error: "bad" }),
    });
    await expect(fetchJson("/bad")).rejects.toThrow("bad");
  });

  test("loadTerms sets active term and options", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        terms: [
          { term_id: "t1", name: "Fall", status: "inactive" },
          { term_id: "t2", name: "Spring", status: "active" },
        ],
      }),
    });

    const select = document.getElementById("terms");
    const result = await loadTerms(select);
    expect(select.options.length).toBe(3); // placeholder + 2
    expect(select.value).toBe("t2"); // active
    expect(result.selected).toBe("t2");
  });

  test("loadTerms handles error", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ error: "fail" }),
    });
    const select = document.getElementById("terms");
    const result = await loadTerms(select);
    expect(select.options[0].textContent).toContain("Error");
    expect(result.selected).toBeNull();
  });

  test("loadOfferings filters by term and populates options", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        offerings: [
          {
            offering_id: "o1",
            course_number: "CS101",
            course_title: "Intro",
            term_name: "Fall",
            status: "active",
          },
        ],
      }),
    });
    const select = document.getElementById("offerings");
    await loadOfferings(select, "t1");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("term_id=t1"),
    );
    expect(select.options.length).toBe(2); // placeholder + data
    expect(select.options[1].textContent).toContain("CS101");
  });

  test("loadOfferings handles fetch error gracefully", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ error: "nope" }),
    });
    const select = document.getElementById("offerings");
    await loadOfferings(select, null);
    expect(select.options[0].textContent).toContain("Error");
  });

  test("loadInstructors populates options and preserves Unassigned", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        users: [
          {
            user_id: "i1",
            first_name: "Ada",
            last_name: "Lovelace",
            email: "ada@example.com",
          },
        ],
      }),
    });
    const select = document.getElementById("instructors");
    await loadInstructors(select);
    expect(select.options[0].textContent).toBe("Unassigned");
    expect(select.options[1].textContent).toContain("Ada Lovelace");
  });

  test("loadInstructors logs on error", async () => {
    const errorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ error: "bad" }),
    });
    const select = document.getElementById("instructors");
    await loadInstructors(select);
    expect(errorSpy).toHaveBeenCalled();
    errorSpy.mockRestore();
  });
});

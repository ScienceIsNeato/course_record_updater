/**
 * Unit Tests for Institution Management UI
 *
 * Tests modal behavior, form validation, and API interactions for:
 * - Create Institution modal
 * - Edit Institution modal
 * - Delete Institution confirmation
 *
 * TDD Approach: Tests written before implementation
 */

// Load the implementation
require("../../../static/institutionManagement.js");

describe("Institution Management - Create Institution Modal", () => {
  let mockFetch;
  let consoleErrorSpy;

  beforeEach(() => {
    // Set up DOM
    document.body.innerHTML = `
            <form id="createInstitutionForm">
                <input type="text" id="institutionName" name="name" required />
                <input type="text" id="institutionShortName" name="short_name" required />
                <input type="text" id="institutionAddress" name="address" />
                <input type="tel" id="institutionPhone" name="phone" />
                <input type="url" id="institutionWebsite" name="website" />
                <input type="email" id="adminEmail" name="admin_email" required />
                <input type="text" id="adminFirstName" name="admin_first_name" required />
                <input type="text" id="adminLastName" name="admin_last_name" required />
                <button type="submit" id="createInstitutionBtn">
                    <span class="btn-text">Create Institution</span>
                    <span class="btn-spinner d-none">Creating...</span>
                </button>
            </form>
            <div class="modal" id="createInstitutionModal"></div>
            <meta name="csrf-token" content="test-csrf-token">
        `;

    // Mock fetch
    mockFetch = jest.fn();
    global.fetch = mockFetch;

    // Mock console.error
    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();

    // Mock Bootstrap Modal
    global.bootstrap = {
      Modal: {
        getInstance: jest.fn(() => ({
          hide: jest.fn(),
        })),
      },
    };

    global.loadInstitutions = jest.fn();

    // Trigger DOMContentLoaded to initialize event listeners
    document.dispatchEvent(new Event("DOMContentLoaded"));
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe("Form Validation", () => {
    test("should require institution name", () => {
      const nameInput = document.getElementById("institutionName");

      nameInput.value = "";
      expect(nameInput.validity.valid).toBe(false);

      nameInput.value = "Test University";
      expect(nameInput.validity.valid).toBe(true);
    });

    test("should require short name", () => {
      const shortNameInput = document.getElementById("institutionShortName");

      shortNameInput.value = "";
      expect(shortNameInput.validity.valid).toBe(false);

      shortNameInput.value = "TU";
      expect(shortNameInput.validity.valid).toBe(true);
    });

    test("should require admin email", () => {
      const emailInput = document.getElementById("adminEmail");

      emailInput.value = "";
      expect(emailInput.validity.valid).toBe(false);

      emailInput.value = "admin@test.edu";
      expect(emailInput.validity.valid).toBe(true);
    });

    test("should validate email format", () => {
      const emailInput = document.getElementById("adminEmail");

      emailInput.value = "not-an-email";
      expect(emailInput.validity.typeMismatch).toBe(true);

      emailInput.value = "admin@test.edu";
      expect(emailInput.validity.valid).toBe(true);
    });

    test("should validate website URL format", () => {
      const websiteInput = document.getElementById("institutionWebsite");

      websiteInput.value = "not-a-url";
      expect(websiteInput.validity.typeMismatch).toBe(true);

      websiteInput.value = "https://test.edu";
      expect(websiteInput.validity.valid).toBe(true);
    });
  });

  describe("Form Submission - API Call", () => {
    test("should POST institution data to /api/institutions on form submit", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          institution_id: "inst-123",
          message: "Institution created",
        }),
      });

      const form = document.getElementById("createInstitutionForm");
      document.getElementById("institutionName").value = "Test University";
      document.getElementById("institutionShortName").value = "TU";
      document.getElementById("institutionAddress").value = "123 Test St";
      document.getElementById("institutionPhone").value = "555-1234";
      document.getElementById("institutionWebsite").value = "https://test.edu";
      document.getElementById("adminEmail").value = "admin@test.edu";
      document.getElementById("adminFirstName").value = "John";
      document.getElementById("adminLastName").value = "Doe";

      // Manually trigger form submission
      const submitEvent = new Event("submit", {
        bubbles: true,
        cancelable: true,
      });
      form.dispatchEvent(submitEvent);

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/institutions",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
            "X-CSRFToken": "test-csrf-token",
          }),
          body: expect.stringContaining("Test University"),
        }),
      );
    });

    test("should include all institution and admin fields in POST body", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, institution_id: "inst-123" }),
      });

      const form = document.getElementById("createInstitutionForm");
      document.getElementById("institutionName").value = "Test University";
      document.getElementById("institutionShortName").value = "TU";
      document.getElementById("institutionAddress").value = "123 Test St";
      document.getElementById("adminEmail").value = "admin@test.edu";
      document.getElementById("adminFirstName").value = "John";
      document.getElementById("adminLastName").value = "Doe";

      const submitEvent = new Event("submit", {
        bubbles: true,
        cancelable: true,
      });
      form.dispatchEvent(submitEvent);

      await new Promise((resolve) => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body).toMatchObject({
        name: "Test University",
        short_name: "TU",
        address: "123 Test St",
        admin_email: "admin@test.edu",
        admin_first_name: "John",
        admin_last_name: "Doe",
      });
    });

    test("should show loading state during API call", async () => {
      mockFetch.mockImplementationOnce(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: async () => ({ success: true }),
                }),
              100,
            ),
          ),
      );

      const form = document.getElementById("createInstitutionForm");
      document.getElementById("institutionName").value = "Test";
      document.getElementById("institutionShortName").value = "T";
      document.getElementById("adminEmail").value = "admin@test.edu";
      document.getElementById("adminFirstName").value = "John";
      document.getElementById("adminLastName").value = "Doe";

      const btnText = document.querySelector(".btn-text");
      const btnSpinner = document.querySelector(".btn-spinner");

      const submitEvent = new Event("submit", {
        bubbles: true,
        cancelable: true,
      });
      form.dispatchEvent(submitEvent);

      await new Promise((resolve) => setTimeout(resolve, 10));

      // Loading state should be active
      expect(btnText.classList.contains("d-none")).toBe(true);
      expect(btnSpinner.classList.contains("d-none")).toBe(false);

      // Wait for completion
      await new Promise((resolve) => setTimeout(resolve, 150));

      // Should return to normal
      expect(btnText.classList.contains("d-none")).toBe(false);
      expect(btnSpinner.classList.contains("d-none")).toBe(true);
    });

    test("should close modal and reset form on success", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          institution_id: "inst-123",
          message: "Institution created",
        }),
      });

      const form = document.getElementById("createInstitutionForm");
      const nameInput = document.getElementById("institutionName");

      nameInput.value = "Test University";
      document.getElementById("institutionShortName").value = "TU";
      document.getElementById("adminEmail").value = "admin@test.edu";
      document.getElementById("adminFirstName").value = "John";
      document.getElementById("adminLastName").value = "Doe";

      const submitEvent = new Event("submit", {
        bubbles: true,
        cancelable: true,
      });
      form.dispatchEvent(submitEvent);

      await new Promise((resolve) => setTimeout(resolve, 100));

      // Modal should be closed
      expect(bootstrap.Modal.getInstance).toHaveBeenCalled();

      // Form should be reset
      expect(nameInput.value).toBe("");

      expect(global.loadInstitutions).toHaveBeenCalled();
    });

    test("should display error message on API failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: "Institution name already exists" }),
      });

      global.alert = jest.fn();

      const form = document.getElementById("createInstitutionForm");
      document.getElementById("institutionName").value = "Existing";
      document.getElementById("institutionShortName").value = "E";
      document.getElementById("adminEmail").value = "admin@test.edu";
      document.getElementById("adminFirstName").value = "John";
      document.getElementById("adminLastName").value = "Doe";

      const submitEvent = new Event("submit", {
        bubbles: true,
        cancelable: true,
      });
      form.dispatchEvent(submitEvent);

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining("Institution name already exists"),
      );
    });

    test("should handle network errors gracefully", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      global.alert = jest.fn();

      const form = document.getElementById("createInstitutionForm");
      document.getElementById("institutionName").value = "Test";
      document.getElementById("institutionShortName").value = "T";
      document.getElementById("adminEmail").value = "admin@test.edu";
      document.getElementById("adminFirstName").value = "John";
      document.getElementById("adminLastName").value = "Doe";

      const submitEvent = new Event("submit", {
        bubbles: true,
        cancelable: true,
      });
      form.dispatchEvent(submitEvent);

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining("Failed to create institution"),
      );
      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });

  describe("CSRF Token Handling", () => {
    test("should include CSRF token in headers", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, institution_id: "inst-123" }),
      });

      const form = document.getElementById("createInstitutionForm");
      document.getElementById("institutionName").value = "Test";
      document.getElementById("institutionShortName").value = "T";
      document.getElementById("adminEmail").value = "admin@test.edu";
      document.getElementById("adminFirstName").value = "John";
      document.getElementById("adminLastName").value = "Doe";

      const submitEvent = new Event("submit", {
        bubbles: true,
        cancelable: true,
      });
      form.dispatchEvent(submitEvent);

      await new Promise((resolve) => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      expect(callArgs[1].headers["X-CSRFToken"]).toBe("test-csrf-token");
    });
  });
});

describe("Institution Management - Edit Institution Modal", () => {
  let mockFetch;

  beforeEach(() => {
    document.body.innerHTML = `
            <form id="editInstitutionForm">
                <input type="hidden" id="editInstitutionId" />
                <input type="text" id="editInstitutionName" required />
                <input type="text" id="editInstitutionShortName" required />
                <input type="text" id="editInstitutionAddress" />
                <input type="tel" id="editInstitutionPhone" />
                <input type="url" id="editInstitutionWebsite" />
                <button type="submit">
                    <span class="btn-text">Update</span>
                    <span class="btn-spinner d-none">Updating...</span>
                </button>
            </form>
            <div class="modal" id="editInstitutionModal"></div>
            <meta name="csrf-token" content="test-csrf-token">
        `;

    mockFetch = jest.fn();
    global.fetch = mockFetch;

    global.bootstrap = {
      Modal: {
        getInstance: jest.fn(() => ({
          hide: jest.fn(),
        })),
        prototype: {
          show: jest.fn(),
        },
      },
    };

    global.loadInstitutions = jest.fn();

    // Trigger DOMContentLoaded to initialize event listeners
    document.dispatchEvent(new Event("DOMContentLoaded"));
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test("openEditInstitutionModal should populate form and show modal", () => {
    const mockModal = { show: jest.fn() };
    global.bootstrap.Modal = jest.fn(() => mockModal);

    window.openEditInstitutionModal("inst-123", {
      name: "Test University",
      short_name: "TU",
      address: "123 Test St",
      phone: "555-1234",
      website: "https://test.edu",
    });

    expect(document.getElementById("editInstitutionId").value).toBe("inst-123");
    expect(document.getElementById("editInstitutionName").value).toBe(
      "Test University",
    );
    expect(document.getElementById("editInstitutionShortName").value).toBe(
      "TU",
    );
    expect(document.getElementById("editInstitutionAddress").value).toBe(
      "123 Test St",
    );
    expect(mockModal.show).toHaveBeenCalled();
  });

  test("should PUT updated institution data to /api/institutions/<id>", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, message: "Institution updated" }),
    });

    const form = document.getElementById("editInstitutionForm");
    document.getElementById("editInstitutionId").value = "inst-123";
    document.getElementById("editInstitutionName").value = "Updated University";
    document.getElementById("editInstitutionShortName").value = "UU";

    const submitEvent = new Event("submit", {
      bubbles: true,
      cancelable: true,
    });
    form.dispatchEvent(submitEvent);

    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/institutions/inst-123",
      expect.objectContaining({
        method: "PUT",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          "X-CSRFToken": "test-csrf-token",
        }),
        body: expect.stringContaining("Updated University"),
      }),
    );
    expect(global.loadInstitutions).toHaveBeenCalled();
  });
});

describe("Institution Management - Delete Institution", () => {
  let mockFetch;
  let promptSpy;
  let alertSpy;
  let consoleErrorSpy;

  beforeEach(() => {
    document.body.innerHTML =
      '<meta name="csrf-token" content="test-csrf-token">';
    mockFetch = jest.fn();
    global.fetch = mockFetch;
    promptSpy = jest.spyOn(window, "prompt");
    alertSpy = jest.spyOn(window, "alert").mockImplementation();
    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();
    global.loadInstitutions = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test("should DELETE institution with correct confirmation", async () => {
    promptSpy.mockReturnValue("i know what I'm doing");
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    });

    await window.deleteInstitution("inst-123", "Test University");

    expect(promptSpy).toHaveBeenCalledWith(
      expect.stringContaining("i know what I'm doing"),
    );
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/institutions/inst-123",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining({
          "X-CSRFToken": "test-csrf-token",
        }),
      }),
    );
    expect(alertSpy).toHaveBeenCalledWith(
      expect.stringContaining("permanently deleted"),
    );
    expect(global.loadInstitutions).toHaveBeenCalled();
  });

  test("should not delete if confirmation text does not match", async () => {
    promptSpy.mockReturnValue("wrong text");

    await window.deleteInstitution("inst-123", "Test University");

    expect(mockFetch).not.toHaveBeenCalled();
    expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("cancelled"));
  });

  test("should not delete if user cancels prompt", async () => {
    promptSpy.mockReturnValue(null);

    await window.deleteInstitution("inst-123", "Test University");

    expect(mockFetch).not.toHaveBeenCalled();
    expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("cancelled"));
  });

  test("should handle API errors gracefully", async () => {
    promptSpy.mockReturnValue("i know what I'm doing");
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: "Institution has active users" }),
    });

    await window.deleteInstitution("inst-123", "Test University");

    expect(alertSpy).toHaveBeenCalledWith(
      expect.stringContaining("Institution has active users"),
    );
  });

  test("should handle network errors during delete", async () => {
    promptSpy.mockReturnValue("i know what I'm doing");
    mockFetch.mockRejectedValueOnce(new Error("Network error"));

    await window.deleteInstitution("inst-123", "Test University");

    expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("try again"));
    expect(consoleErrorSpy).toHaveBeenCalled();
  });
});

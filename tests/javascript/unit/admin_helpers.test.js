const adminHelpers = require("../../../static/admin.js");

describe("Admin formatting helpers", () => {
  afterEach(() => {
    jest.useRealTimers();
  });

  test("getInitials handles missing names", () => {
    expect(adminHelpers.getInitials("Ada", "Lovelace")).toBe("AL");
    expect(adminHelpers.getInitials("Ada", "")).toBe("A");
    expect(adminHelpers.getInitials("", "")).toBe("");
  });

  test("formatRole and formatStatus convert underscores to title case", () => {
    expect(adminHelpers.formatRole("institution_admin")).toBe(
      "Institution Admin",
    );
    expect(adminHelpers.formatStatus("pending_verification")).toBe(
      "Pending Verification",
    );
  });

  test("getDisplayStatus maps pending verification to pending", () => {
    expect(
      adminHelpers.getDisplayStatus({ account_status: "pending_verification" }),
    ).toBe("pending");
    expect(adminHelpers.getDisplayStatus({ account_status: "active" })).toBe(
      "active",
    );
  });

  test("getActivityStatus differentiates online, recent, inactive", () => {
    const now = new Date("2025-01-01T12:00:00Z");
    jest.useFakeTimers().setSystemTime(now);

    expect(adminHelpers.getActivityStatus("2025-01-01T11:30:00Z")).toBe(
      "online",
    );
    expect(adminHelpers.getActivityStatus("2025-01-01T05:00:00Z")).toBe(
      "recent",
    );
    expect(adminHelpers.getActivityStatus("2023-01-01T00:00:00Z")).toBe(
      "inactive",
    );
  });

  test("formatLastActive returns human friendly strings", () => {
    const now = new Date("2025-01-10T12:00:00Z");
    jest.useFakeTimers().setSystemTime(now);

    expect(adminHelpers.formatLastActive("2025-01-10T11:30:00Z")).toBe(
      "Just now",
    );
    expect(adminHelpers.formatLastActive("2025-01-10T02:00:00Z")).toBe(
      "10h ago",
    );
    expect(adminHelpers.formatLastActive("2025-01-05T00:00:00Z")).toBe(
      "5d ago",
    );
    const explicitDate = adminHelpers.formatLastActive("2024-12-01T00:00:00Z");
    expect(explicitDate).toEqual(
      new Date("2024-12-01T00:00:00Z").toLocaleDateString(),
    );
  });

  test("formatExpiryDate handles past, today, and future dates", () => {
    const now = new Date("2025-01-01T00:00:00Z");
    jest.useFakeTimers().setSystemTime(now);

    expect(adminHelpers.formatExpiryDate("2024-12-31T23:59:00Z")).toBe(
      "Expired",
    );
    expect(adminHelpers.formatExpiryDate("2025-01-01T23:59:00Z")).toBe("Today");
    expect(adminHelpers.formatExpiryDate("2025-01-02T00:00:00Z")).toBe(
      "Tomorrow",
    );
    expect(adminHelpers.formatExpiryDate("2025-01-05T00:00:00Z")).toBe(
      "4 days",
    );
  });
});

/**
 * Unit Test for renderHistoryCellContent in audit_clo.js
 * 
 * Uses direct requirement of the module now that logic is extracted and exported.
 * This ensures proper code coverage instrumentation by Jest.
 */
const auditCloModule = require("../../../static/audit_clo.js");
const { renderHistoryCellContent } = auditCloModule;

describe("audit_clo.js - renderHistoryCellContent", () => {

    it("should render history events correctly", () => {
        const clo = {
            history: [
                { event: "Assigned", occurred_at: "2025-01-01T12:00:00Z" },
                { event: "Submitted", occurred_at: "2025-01-02T12:00:00Z" }
            ]
        };

        const container = renderHistoryCellContent(clo);
        const eventDivs = container.querySelectorAll(".history-event");

        expect(eventDivs.length).toBe(2);
        expect(eventDivs[0].textContent).toContain("Assigned");
        expect(eventDivs[1].textContent).toContain("Submitted");
    });

    it("should render 'and more' link when > 2 events", () => {
        const clo = {
            history: [
                { event: "A", occurred_at: "2025-01-01" },
                { event: "B", occurred_at: "2025-01-02" },
                { event: "C", occurred_at: "2025-01-03" }
            ]
        };

        const container = renderHistoryCellContent(clo);
        const eventDivs = container.querySelectorAll(".history-event");
        const moreLink = container.querySelector(".text-primary");

        expect(eventDivs.length).toBe(2); // Only shows 2
        expect(moreLink).not.toBeNull();
        expect(moreLink.textContent).toContain("and 1 more...");
    });

    it("should render 'No history' when history is empty", () => {
        const clo = { history: [] };
        const container = renderHistoryCellContent(clo);

        expect(container.textContent).toBe("No history");
    });

    it("should render 'No history' when history is undefined", () => {
        const clo = {};
        const container = renderHistoryCellContent(clo);

        expect(container.textContent).toBe("No history");
    });
});

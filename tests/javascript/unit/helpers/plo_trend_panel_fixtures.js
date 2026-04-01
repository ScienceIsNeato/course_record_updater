/**
 * Test fixtures for plo_trend_panel.test.js.
 *
 * Provides mock trend points, terms, opts, and deps objects that mirror
 * the shapes passed by plo_trend.js → createTrendPanel().
 */

const MOCK_TERMS = [
  { term_id: "t-fa24", term_name: "Fall 2024", is_current: false },
  { term_id: "t-sp25", term_name: "Spring 2025", is_current: false },
  { term_id: "t-fa25", term_name: "Fall 2025", is_current: true },
];

const MOCK_TREND_POINTS = [
  { pass_rate: 72, students_took: 40, students_passed: 29 },
  { pass_rate: 78, students_took: 45, students_passed: 35 },
  { pass_rate: 85, students_took: 50, students_passed: 43 },
];

const MOCK_CLO = {
  outcome_id: "clo-1",
  clo_number: "3",
  course_number: "BIOL-301",
  description: "Formulate a testable hypothesis.",
  trend: [
    { pass_rate: 68, students_took: 20, students_passed: 14 },
    { pass_rate: 75, students_took: 22, students_passed: 17 },
    { pass_rate: 82, students_took: 25, students_passed: 21 },
  ],
};

const MOCK_OPTS = {
  threshold: 70,
  title: "PLO 1 – Pass Rate Trend",
  clos: [MOCK_CLO],
  discontinuities: [],
};

const MOCK_OPTS_NO_CLOS = {
  threshold: 70,
  title: "PLO 2 – Pass Rate Trend",
  clos: [],
  discontinuities: [],
};

function makeMockDeps() {
  return {
    CLO_COLORS: ["#ff6384", "#36a2eb", "#ffce56"],
    TREND_FILL_COLOR: "rgba(13, 110, 253, 0.08)",
    TREND_LINE_COLOR: "#0d6efd",
    TREND_LINE_COLOR_FAIL: "#dc3545",
    TREND_NULL_DASH: [4, 4],
    cloLabel: (clo) => `${clo.course_number} CLO ${clo.clo_number}`,
    computeYRange: () => ({ min: 0, max: 100 }),
    createCompositionBar: jest.fn(() => {
      const el = document.createElement("div");
      el.className = "plo-composition-bar";
      return el;
    }),
  };
}

module.exports = {
  MOCK_CLO,
  MOCK_OPTS,
  MOCK_OPTS_NO_CLOS,
  MOCK_TERMS,
  MOCK_TREND_POINTS,
  makeMockDeps,
};

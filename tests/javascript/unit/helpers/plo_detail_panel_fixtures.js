/**
 * Test fixtures for plo_detail_panel.test.js.
 *
 * Provides mock PLO data matching the shape returned by
 * /api/programs/<id>/plo-dashboard?plo_id=<id>&term_id=<id>
 */

const MOCK_PLO_DATA = {
  id: "plo-1",
  plo_number: 1,
  description: "Students will design controlled experiments.",
  clo_count: 2,
  aggregate: {
    students_took: 80,
    students_passed: 64,
    pass_rate: 80.0,
    section_count: 3,
  },
  clos: [
    {
      outcome_id: "clo-A",
      clo_number: "3",
      description: "Formulate a testable hypothesis.",
      course_number: "BIOL-301",
      course_title: "Biology Lab",
      aggregate: {
        students_took: 50,
        students_passed: 40,
        pass_rate: 80.0,
        section_count: 2,
      },
      sections: [
        {
          students_took: 30,
          students_passed: 27,
          assessment_tool: "Lab Report",
          _section: { section_number: "001" },
          _term: { name: "Fall 2025" },
          _instructor: { first_name: "Ada", last_name: "Lovelace" },
          _offering: { offering_id: "off-1" },
        },
        {
          students_took: 20,
          students_passed: 13,
          assessment_tool: "Final Exam",
          _section: { section_number: "002" },
          _term: { name: "Fall 2025" },
          _instructor: { first_name: "Grace", last_name: "Hopper" },
          _offering: { offering_id: "off-2" },
        },
      ],
    },
    {
      outcome_id: "clo-B",
      clo_number: "1",
      description: "Analyze experimental data using statistics.",
      course_number: "STAT-201",
      course_title: "Applied Statistics",
      aggregate: {
        students_took: 30,
        students_passed: 24,
        pass_rate: 80.0,
        section_count: 1,
      },
      sections: [
        {
          students_took: 30,
          students_passed: 24,
          assessment_tool: "Midterm",
          _section: { section_number: "001" },
          _term: { name: "Fall 2025" },
          _instructor: { first_name: "Alan", last_name: "Turing" },
          _offering: { offering_id: "off-3" },
        },
      ],
    },
  ],
};

const MOCK_PLO_NO_CLOS = {
  id: "plo-2",
  plo_number: 2,
  description: "Students will communicate research findings.",
  clo_count: 0,
  aggregate: {
    students_took: 0,
    students_passed: 0,
    pass_rate: null,
    section_count: 0,
  },
  clos: [],
};

const MOCK_TERM_LABEL = "Fall 2025";

module.exports = {
  MOCK_PLO_DATA,
  MOCK_PLO_NO_CLOS,
  MOCK_TERM_LABEL,
};

const SKELETON = `
  <meta name="csrf-token" content="test-csrf-token">

  <select id="ploProgramFilter"></select>
  <select id="ploTermFilter"><option value="">All Terms</option></select>
  <select id="ploDisplayMode">
    <option value="both">Both</option>
    <option value="percentage">Percentage</option>
    <option value="binary">Binary</option>
  </select>

  <button id="createPloBtn"></button>
  <button id="mapCloBtn"></button>
  <button id="expandAllBtn"></button>
  <button id="collapseAllBtn"></button>

  <span id="ploTreeProgramName"></span>
  <span id="ploTreeVersionBadge"></span>
  <div id="ploTreeContainer"></div>

  <div id="ploModal">
    <form id="ploForm" method="dialog">
      <input id="ploModalId" type="hidden">
      <div id="ploModalNumberGroup">
        <input id="ploModalNumber">
      </div>
      <textarea id="ploModalDescription"></textarea>
      <span id="ploModalLabel"></span>
      <div id="ploModalAlert"></div>
    </form>
  </div>

  <div id="mapCloModal">
    <form id="mapCloForm" method="dialog">
      <select id="mapCloModalPlo"></select>
      <select id="mapCloModalClo"></select>
      <div id="mapCloModalAlert"></div>
      <button id="mapCloPublishBtn" type="button"></button>
    </form>
  </div>
`;

function resetDashboardState(ploDashboardArg) {
  const dashboard =
    ploDashboardArg || require("../../../../static/plo_dashboard").PloDashboard;
  dashboard.programs = [];
  dashboard.terms = [];
  dashboard.tree = null;
  dashboard.currentProgramId = null;
  dashboard.currentTermId = null;
  dashboard.displayMode = "both";
  dashboard.draftMappingId = null;
  delete global.bootstrap;
}

const SAMPLE_TREE = {
  success: true,
  program_id: "prog-1",
  term_id: "t-active",
  mapping_status: "published",
  mapping: { id: "m-1", version: 2, status: "published" },
  assessment_display_mode: "both",
  plos: [
    {
      id: "plo-1",
      plo_number: 1,
      description: "Students will design experiments.",
      clo_count: 1,
      aggregate: {
        students_took: 50,
        students_passed: 40,
        pass_rate: 80.0,
        section_count: 2,
      },
      clos: [
        {
          outcome_id: "clo-A",
          clo_number: "3",
          description: "Formulate a testable hypothesis.",
          course_number: "BIOL-301",
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
              _section: { section_number: "002" },
              _term: { name: "Fall 2025" },
              _instructor: {},
              _offering: {},
            },
          ],
        },
      ],
    },
    {
      id: "plo-2",
      plo_number: 2,
      description: "Students will communicate findings.",
      clo_count: 0,
      aggregate: {
        students_took: 0,
        students_passed: 0,
        pass_rate: null,
        section_count: 0,
      },
      clos: [],
    },
  ],
};

function routeFetch(routes) {
  return jest.fn((url) => {
    for (const [pattern, payload] of routes) {
      if (url.includes(pattern)) {
        return Promise.resolve({
          ok: payload.ok !== false,
          status: payload.status || 200,
          json: async () => payload.body,
        });
      }
    }
    return Promise.reject(new Error(`unhandled fetch: ${url}`));
  });
}

module.exports = {
  resetDashboardState,
  routeFetch,
  SAMPLE_TREE,
  SKELETON,
};

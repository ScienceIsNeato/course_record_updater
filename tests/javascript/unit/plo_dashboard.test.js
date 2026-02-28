/**
 * Unit tests for static/plo_dashboard.js.
 *
 * Two tiers:
 *  - Pure helpers (formatAssessment, pickDefaultTerm): table-driven
 *    coverage of the display-mode render rules and term-default logic.
 *  - PloDashboard DOM flow: mocked-fetch + jsdom coverage of
 *    loadTree → renderTree → node builders → stats aggregation, plus
 *    the modal plumbing. These are fast (no network, no real fetch)
 *    but exercise the same code paths the browser hits.
 */

// dashboard_utils helpers are loaded as browser globals at runtime;
// replicate that here so plo_dashboard.js's setLoadingState/etc calls
// resolve. Same pattern as program_dashboard.test.js.
const {
  setLoadingState,
  setErrorState,
  setEmptyState,
} = require('../../../static/dashboard_utils');
global.setLoadingState = setLoadingState;
global.setErrorState = setErrorState;
global.setEmptyState = setEmptyState;

const {
  PloDashboard,
  formatAssessment,
  pickDefaultTerm,
  DEFAULT_PASS_THRESHOLD,
} = require('../../../static/plo_dashboard');
const { setBody } = require('../helpers/dom');

describe('plo_dashboard.js — formatAssessment', () => {
  describe('no-data sentinel', () => {
    test('null → em dash, nodata class (regardless of mode)', () => {
      for (const mode of ['binary', 'percentage', 'both']) {
        const r = formatAssessment(null, mode);
        expect(r).toEqual({ text: '—', cssClass: 'nodata' });
      }
    });

    test('undefined → em dash, nodata class', () => {
      expect(formatAssessment(undefined, 'both')).toEqual({
        text: '—',
        cssClass: 'nodata',
      });
    });

    test('0 is real data (0% passed), not the no-data sentinel', () => {
      // 0 !== null — a section where everyone failed is still a data point.
      const r = formatAssessment(0, 'percentage');
      expect(r.text).toBe('0%');
      expect(r.cssClass).toBe('fail');
    });
  });

  describe('mode: binary', () => {
    test('at threshold → S', () => {
      // >= is inclusive: exactly hitting the bar is a pass.
      const r = formatAssessment(DEFAULT_PASS_THRESHOLD, 'binary');
      expect(r).toEqual({ text: 'S', cssClass: 'pass' });
    });

    test('above threshold → S', () => {
      expect(formatAssessment(95, 'binary')).toEqual({
        text: 'S',
        cssClass: 'pass',
      });
    });

    test('just below threshold → U', () => {
      const r = formatAssessment(DEFAULT_PASS_THRESHOLD - 0.1, 'binary');
      expect(r).toEqual({ text: 'U', cssClass: 'fail' });
    });
  });

  describe('mode: percentage', () => {
    test('rounds to nearest whole percent', () => {
      expect(formatAssessment(71.7, 'percentage').text).toBe('72%');
      expect(formatAssessment(71.4, 'percentage').text).toBe('71%');
    });

    test('cssClass still respects pass/fail threshold', () => {
      expect(formatAssessment(90, 'percentage').cssClass).toBe('pass');
      expect(formatAssessment(40, 'percentage').cssClass).toBe('fail');
    });
  });

  describe('mode: both (default)', () => {
    test('formats as "S (NN%)"', () => {
      expect(formatAssessment(78.3, 'both').text).toBe('S (78%)');
    });

    test('failing grade shows U + percent', () => {
      expect(formatAssessment(54.6, 'both').text).toBe('U (55%)');
    });

    test('unknown mode string falls through to "both" behaviour', () => {
      // Any mode other than binary/percentage hits the else branch.
      const r = formatAssessment(80, 'garbage');
      expect(r.text).toBe('S (80%)');
      expect(r.cssClass).toBe('pass');
    });
  });

  describe('custom threshold', () => {
    test('explicit threshold overrides default', () => {
      // With threshold=85, an 80% pass rate is a fail.
      const r = formatAssessment(80, 'binary', 85);
      expect(r).toEqual({ text: 'U', cssClass: 'fail' });
    });

    test('non-numeric threshold falls back to DEFAULT_PASS_THRESHOLD', () => {
      // A caller passing nonsense shouldn't break the render — just
      // use the constant. 71 passes against default 70.
      const r = formatAssessment(71, 'binary', 'not-a-number');
      expect(r.text).toBe('S');
    });

    test('threshold=0 means everything passes', () => {
      expect(formatAssessment(0, 'binary', 0).text).toBe('S');
    });
  });

  test('DEFAULT_PASS_THRESHOLD is exported and reasonable', () => {
    expect(typeof DEFAULT_PASS_THRESHOLD).toBe('number');
    expect(DEFAULT_PASS_THRESHOLD).toBe(70);
  });
});

describe('plo_dashboard.js — pickDefaultTerm', () => {
  describe('empty / degenerate inputs', () => {
    test('empty array → empty string', () => {
      expect(pickDefaultTerm([])).toBe('');
    });

    test('null → empty string', () => {
      expect(pickDefaultTerm(null)).toBe('');
    });

    test('not-an-array → empty string', () => {
      expect(pickDefaultTerm({ term_id: 't1' })).toBe('');
    });
  });

  describe('active-term preference', () => {
    test('prefers term_status === "ACTIVE"', () => {
      const terms = [
        { term_id: 't-old', term_status: 'CLOSED', start_date: '2025-01-01' },
        { term_id: 't-active', term_status: 'ACTIVE', start_date: '2024-09-01' },
        { term_id: 't-future', term_status: 'PLANNED', start_date: '2026-01-01' },
      ];
      // Active wins even though t-future has the latest start_date.
      expect(pickDefaultTerm(terms)).toBe('t-active');
    });

    test('accepts status alias (status === "ACTIVE")', () => {
      const terms = [{ id: 't1', status: 'ACTIVE' }];
      expect(pickDefaultTerm(terms)).toBe('t1');
    });

    test('accepts is_active boolean alias', () => {
      const terms = [
        { term_id: 't-off', is_active: false },
        { term_id: 't-on', is_active: true },
      ];
      expect(pickDefaultTerm(terms)).toBe('t-on');
    });

    test('accepts active boolean alias', () => {
      const terms = [{ term_id: 't1', active: true }];
      expect(pickDefaultTerm(terms)).toBe('t1');
    });

    test('first active wins when multiple are active', () => {
      const terms = [
        { term_id: 't-a', term_status: 'ACTIVE' },
        { term_id: 't-b', term_status: 'ACTIVE' },
      ];
      // Array.find returns first match — t-a wins. No tie-breaking
      // logic beyond that (intentionally simple).
      expect(pickDefaultTerm(terms)).toBe('t-a');
    });
  });

  describe('start_date fallback (no active term)', () => {
    test('picks most-recent by start_date', () => {
      const terms = [
        { term_id: 't-2024s', start_date: '2024-01-10' },
        { term_id: 't-2025s', start_date: '2025-01-10' },
        { term_id: 't-2023f', start_date: '2023-09-01' },
      ];
      expect(pickDefaultTerm(terms)).toBe('t-2025s');
    });

    test('does not mutate the input array', () => {
      const terms = [
        { term_id: 't-a', start_date: '2024-01-01' },
        { term_id: 't-b', start_date: '2025-01-01' },
      ];
      const snapshot = terms.map((t) => t.term_id);
      pickDefaultTerm(terms);
      // The internal sort uses [...terms] — original order preserved.
      expect(terms.map((t) => t.term_id)).toEqual(snapshot);
    });

    test('missing start_date treated as epoch (0)', () => {
      const terms = [
        { term_id: 't-no-date' }, // no start_date → Date(0)
        { term_id: 't-dated', start_date: '2025-01-01' },
      ];
      expect(pickDefaultTerm(terms)).toBe('t-dated');
    });
  });

  describe('id-field aliases', () => {
    test('falls through term_id → id', () => {
      // The "All Terms" option and some API payloads use `id` not `term_id`.
      expect(pickDefaultTerm([{ id: 'x', term_status: 'ACTIVE' }])).toBe('x');
    });

    test('prefers term_id over id when both present', () => {
      const terms = [{ term_id: 'prefer-me', id: 'not-me', term_status: 'ACTIVE' }];
      expect(pickDefaultTerm(terms)).toBe('prefer-me');
    });

    test('term with neither id key → empty string (not crash)', () => {
      const terms = [{ term_status: 'ACTIVE', name: 'Spring 2025' }];
      expect(pickDefaultTerm(terms)).toBe('');
    });
  });
});

// ===========================================================================
// PloDashboard — DOM + fetch-mocked integration-style tests
// ===========================================================================

/**
 * Minimal DOM skeleton matching the element IDs _cacheSelectors() expects.
 * Only the elements exercised by a given test *need* to exist (the code
 * null-guards each), but having the full set means _bindEvents() can wire
 * everything without blowing up.
 */
const SKELETON = `
  <meta name="csrf-token" content="test-csrf-token">

  <select id="ploProgramFilter"></select>
  <select id="ploTermFilter"><option value="">All Terms</option></select>
  <select id="ploDisplayMode">
    <option value="both">Both</option>
    <option value="percentage">Percentage</option>
    <option value="binary">Binary</option>
  </select>

  <span id="statPloCount">-</span>
  <span id="statMappedCloCount">-</span>
  <span id="statOverallPassRate">-</span>
  <span id="statMappingStatus">-</span>

  <button id="createPloBtn"></button>
  <button id="mapCloBtn"></button>
  <button id="expandAllBtn"></button>
  <button id="collapseAllBtn"></button>

  <span id="ploTreeProgramName"></span>
  <span id="ploTreeVersionBadge"></span>
  <div id="ploTreeContainer"></div>

  <div id="ploModal">
    <form id="ploForm">
      <input id="ploModalId" type="hidden">
      <input id="ploModalNumber">
      <textarea id="ploModalDescription"></textarea>
      <span id="ploModalLabel"></span>
      <div id="ploModalAlert"></div>
    </form>
  </div>

  <div id="mapCloModal">
    <form id="mapCloForm">
      <select id="mapCloModalPlo"></select>
      <select id="mapCloModalClo"></select>
      <div id="mapCloModalAlert"></div>
      <button id="mapCloPublishBtn" type="button"></button>
    </form>
  </div>
`;

/** Reset PloDashboard's mutable state between tests. Shared singleton! */
function resetDashboardState() {
  PloDashboard.programs = [];
  PloDashboard.terms = [];
  PloDashboard.tree = null;
  PloDashboard.currentProgramId = null;
  PloDashboard.currentTermId = null;
  PloDashboard.displayMode = 'both';
  PloDashboard.draftMappingId = null;
  // setupTests.js installs a global bootstrap mock but it lacks
  // getOrCreateInstance (Bootstrap 5 API our _showModal uses). Drop it
  // so the class-toggle fallback path runs — that's the one we assert on.
  delete global.bootstrap;
}

/**
 * A realistic tree payload: 2 PLOs, one with a mapped CLO carrying two
 * section records (one passing, one failing), the other unmapped. Enough
 * structure to exercise every branch of _buildPloNode/_buildCloNode/
 * _buildSectionNode plus the three distinct empty states.
 */
const SAMPLE_TREE = {
  success: true,
  program_id: 'prog-1',
  term_id: 't-active',
  mapping_status: 'published',
  mapping: { id: 'm-1', version: 2, status: 'published' },
  assessment_display_mode: 'both',
  plos: [
    {
      id: 'plo-1',
      plo_number: 1,
      description: 'Students will design experiments.',
      clo_count: 1,
      aggregate: {
        students_took: 50,
        students_passed: 40,
        pass_rate: 80.0,
        section_count: 2,
      },
      clos: [
        {
          outcome_id: 'clo-A',
          clo_number: '3',
          description: 'Formulate a testable hypothesis.',
          course_number: 'BIOL-301',
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
              assessment_tool: 'Lab Report',
              _section: { section_number: '001' },
              _term: { name: 'Fall 2025' },
              _instructor: { first_name: 'Ada', last_name: 'Lovelace' },
              _offering: { offering_id: 'off-1' },
            },
            {
              // Failing section: 13/20 = 65% < 70 threshold → "U" badge
              students_took: 20,
              students_passed: 13,
              _section: { section_number: '002' },
              _term: { name: 'Fall 2025' },
              _instructor: {},
              _offering: {},
            },
          ],
        },
      ],
    },
    {
      // PLO with zero CLOs → triggers the "No CLOs mapped" leaf message
      id: 'plo-2',
      plo_number: 2,
      description: 'Students will communicate findings.',
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

/** fetch mock that routes by URL — lets one test drive a full init(). */
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

describe('PloDashboard — filter loading', () => {
  beforeEach(() => {
    setBody(SKELETON);
    resetDashboardState();
    PloDashboard._cacheSelectors();
  });

  afterEach(() => {
    delete global.fetch;
    localStorage.clear();
  });

  test('_loadPrograms populates dropdown and picks first program', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        programs: [
          { program_id: 'prog-1', name: 'Biology BS' },
          { program_id: 'prog-2', name: 'Zoology BS' },
        ],
      }),
    });

    await PloDashboard._loadPrograms();

    const sel = document.getElementById('ploProgramFilter');
    expect(sel.options.length).toBe(2);
    expect(sel.options[0].textContent).toBe('Biology BS');
    // No localStorage entry → first program is default
    expect(PloDashboard.currentProgramId).toBe('prog-1');
    expect(sel.value).toBe('prog-1');
  });

  test('_loadPrograms honours localStorage when the stored id is still valid', async () => {
    localStorage.setItem('ploDashboard.lastProgramId', 'prog-2');
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        programs: [
          { program_id: 'prog-1', name: 'Biology' },
          { program_id: 'prog-2', name: 'Zoology' },
        ],
      }),
    });
    await PloDashboard._loadPrograms();
    expect(PloDashboard.currentProgramId).toBe('prog-2');
  });

  test('_loadPrograms ignores stale localStorage id not in the list', async () => {
    localStorage.setItem('ploDashboard.lastProgramId', 'deleted-prog');
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ programs: [{ id: 'prog-1', name: 'Only One' }] }),
    });
    await PloDashboard._loadPrograms();
    // Falls back to first valid id (using the `id` alias, not `program_id`)
    expect(PloDashboard.currentProgramId).toBe('prog-1');
  });

  test('_loadPrograms handles empty list gracefully', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ programs: [] }) });
    await PloDashboard._loadPrograms();
    const sel = document.getElementById('ploProgramFilter');
    expect(sel.options[0].textContent).toMatch(/no programs/i);
    expect(PloDashboard.currentProgramId).toBeNull();
  });

  test('_loadPrograms bails silently on non-OK response', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 });
    await PloDashboard._loadPrograms();
    // State untouched, no throw
    expect(PloDashboard.programs).toEqual([]);
  });

  test('_loadTerms appends sorted terms after the "All Terms" option', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        terms: [
          { term_id: 't-2024', term_name: 'Spring 2024', start_date: '2024-01-10' },
          { term_id: 't-2025', term_name: 'Spring 2025', start_date: '2025-01-10' },
        ],
      }),
    });
    await PloDashboard._loadTerms();
    const sel = document.getElementById('ploTermFilter');
    // 1 existing "All Terms" + 2 appended
    expect(sel.options.length).toBe(3);
    // most-recent first (2025 before 2024)
    expect(sel.options[1].textContent).toBe('Spring 2025');
    // No active term → pickDefaultTerm falls back to most-recent start_date
    expect(PloDashboard.currentTermId).toBe('t-2025');
  });

  test('_loadTerms selects active term when present', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        terms: [
          { term_id: 't-old', term_status: 'CLOSED', start_date: '2024-01-01' },
          { term_id: 't-now', term_status: 'ACTIVE', start_date: '2024-09-01' },
        ],
      }),
    });
    await PloDashboard._loadTerms();
    expect(PloDashboard.currentTermId).toBe('t-now');
  });
});

describe('PloDashboard — loadTree + render', () => {
  beforeEach(() => {
    setBody(SKELETON);
    resetDashboardState();
    PloDashboard._cacheSelectors();
    PloDashboard.programs = [{ program_id: 'prog-1', name: 'Biology BS' }];
    PloDashboard.currentProgramId = 'prog-1';
    PloDashboard.currentTermId = 't-active';
  });

  afterEach(() => {
    delete global.fetch;
  });

  test('no program selected → empty-state message, no fetch', async () => {
    PloDashboard.currentProgramId = null;
    global.fetch = jest.fn();
    await PloDashboard.loadTree();
    expect(global.fetch).not.toHaveBeenCalled();
    expect(
      document.getElementById('ploTreeContainer').textContent,
    ).toMatch(/select a program/i);
  });

  test('successful load renders tree + populates stats', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => SAMPLE_TREE,
    });

    await PloDashboard.loadTree();

    // Fetch URL includes program + term filter
    expect(global.fetch.mock.calls[0][0]).toMatch(
      /\/api\/programs\/prog-1\/plo-dashboard\?term_id=t-active/,
    );

    // Tree rendered
    const tree = document.querySelector('ul.plo-tree');
    expect(tree).toBeTruthy();
    const ploNodes = tree.querySelectorAll(':scope > li.plo-tree-node');
    expect(ploNodes.length).toBe(2);

    // PLO-1 header carries the number + CLO count pill
    const plo1Num = ploNodes[0].querySelector('.plo-tree-number');
    expect(plo1Num.textContent).toContain('PLO-1');
    expect(plo1Num.textContent).toContain('1 CLO');

    // PLO-2 has empty clos → leaf message + auto-expanded
    expect(ploNodes[1].classList.contains('expanded')).toBe(true);
    expect(ploNodes[1].textContent).toMatch(/no clos mapped/i);

    // Section leaves under PLO-1: 2 sections
    const sectionLeaves = ploNodes[0].querySelectorAll('li.plo-tree-node.leaf');
    expect(sectionLeaves.length).toBe(2);
    // First section shows instructor name + pass count detail
    expect(sectionLeaves[0].textContent).toContain('Ada Lovelace');
    expect(sectionLeaves[0].textContent).toContain('27/30 passed');

    // Stats populated
    expect(document.getElementById('statPloCount').textContent).toBe('2');
    expect(document.getElementById('statMappedCloCount').textContent).toBe('1');
    expect(document.getElementById('statOverallPassRate').textContent).toBe(
      '80%',
    );
    expect(document.getElementById('statMappingStatus').textContent).toBe(
      'Published',
    );

    // Version badge shows v2
    expect(
      document.getElementById('ploTreeVersionBadge').textContent,
    ).toMatch(/v2/);

    // Display mode picked up from API response
    expect(PloDashboard.displayMode).toBe('both');
    expect(document.getElementById('ploDisplayMode').value).toBe('both');
  });

  test('assessment badges honour display mode', async () => {
    // Same tree, but program says "binary"
    const binaryTree = { ...SAMPLE_TREE, assessment_display_mode: 'binary' };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => binaryTree,
    });
    await PloDashboard.loadTree();

    const badges = document.querySelectorAll('.plo-assessment-badge');
    // PLO-1 (80% → S), CLO-A (80% → S), Section 001 (90% → S),
    // Section 002 (65% → U), PLO-2 (null → —)
    const texts = Array.from(badges).map((b) => b.textContent);
    expect(texts).toContain('S');
    expect(texts).toContain('U');
    expect(texts).toContain('—');
    // In binary mode no percent sign anywhere
    expect(texts.join('')).not.toContain('%');
  });

  test('CLO with zero sections → "no section assessments" leaf message', async () => {
    const treeNoSections = {
      ...SAMPLE_TREE,
      plos: [
        {
          id: 'plo-x',
          plo_number: 1,
          description: 'x',
          clo_count: 1,
          aggregate: { pass_rate: null },
          clos: [
            {
              outcome_id: 'clo-x',
              clo_number: '1',
              course_number: 'X-100',
              description: 'x',
              aggregate: { pass_rate: null },
              sections: [], // <-- the empty state under test
            },
          ],
        },
      ],
    };
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => treeNoSections });
    await PloDashboard.loadTree();
    expect(
      document.getElementById('ploTreeContainer').textContent,
    ).toMatch(/no section assessments/i);
  });

  test('empty plos array → "no PLOs defined" empty state', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...SAMPLE_TREE,
        plos: [],
        mapping: null,
        mapping_status: 'none',
      }),
    });
    await PloDashboard.loadTree();
    expect(
      document.getElementById('ploTreeContainer').textContent,
    ).toMatch(/no program learning outcomes/i);
    // version badge hidden when no mapping version
    expect(
      document.getElementById('ploTreeVersionBadge').style.display,
    ).toBe('none');
  });

  test('HTTP error → setErrorState message with status code', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 });
    await PloDashboard.loadTree();
    expect(
      document.getElementById('ploTreeContainer').textContent,
    ).toMatch(/500/);
  });

  test('fetch throws → error state with exception message', async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error('network down'));
    await PloDashboard.loadTree();
    expect(
      document.getElementById('ploTreeContainer').textContent,
    ).toMatch(/network down/);
  });

  test('_updateStats(null) resets all stat cards to "-"', () => {
    document.getElementById('statPloCount').textContent = 'old';
    PloDashboard._updateStats(null);
    expect(document.getElementById('statPloCount').textContent).toBe('-');
    expect(document.getElementById('statOverallPassRate').textContent).toBe(
      '-',
    );
  });

  test('_updateStats shows em dash when no students_took anywhere', () => {
    // Both PLOs have zero aggregate data → no pass rate to compute
    PloDashboard._updateStats({
      plos: [
        { aggregate: { students_took: 0, students_passed: 0 } },
        { aggregate: {} },
      ],
      mapping_status: 'draft',
    });
    expect(document.getElementById('statOverallPassRate').textContent).toBe(
      '—',
    );
    expect(document.getElementById('statMappingStatus').textContent).toBe(
      'Draft',
    );
  });
});

describe('PloDashboard — expand/collapse + event wiring', () => {
  beforeEach(() => {
    setBody(SKELETON);
    resetDashboardState();
    PloDashboard._cacheSelectors();
    PloDashboard._bindEvents();
    PloDashboard.programs = [{ program_id: 'prog-1', name: 'Biology' }];
    PloDashboard.currentProgramId = 'prog-1';
  });

  afterEach(() => {
    delete global.fetch;
  });

  test('expandAll / collapseAll toggle .expanded on every node', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => SAMPLE_TREE });
    await PloDashboard.loadTree();

    // After render: PLO-2 is auto-expanded (empty), PLO-1 is collapsed
    let expanded = document.querySelectorAll('.plo-tree-node.expanded');
    const initialCount = expanded.length;

    document.getElementById('expandAllBtn').click();
    expanded = document.querySelectorAll('.plo-tree-node.expanded');
    expect(expanded.length).toBeGreaterThan(initialCount);

    document.getElementById('collapseAllBtn').click();
    expanded = document.querySelectorAll('.plo-tree-node.expanded');
    expect(expanded.length).toBe(0);
  });

  test('clicking a PLO header toggles its expanded state', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => SAMPLE_TREE });
    await PloDashboard.loadTree();

    const plo1 = document.querySelector('ul.plo-tree > li.plo-tree-node');
    const header = plo1.querySelector('.plo-tree-header');
    expect(plo1.classList.contains('expanded')).toBe(false);
    header.click();
    expect(plo1.classList.contains('expanded')).toBe(true);
    header.click();
    expect(plo1.classList.contains('expanded')).toBe(false);
  });

  test('term filter change triggers loadTree with new term', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => SAMPLE_TREE });

    const termSel = document.getElementById('ploTermFilter');
    // add an option we can switch to
    termSel.innerHTML += '<option value="t-spring">Spring</option>';
    termSel.value = 't-spring';
    termSel.dispatchEvent(new Event('change'));

    // event handler updates state then calls loadTree → awaits fetch
    await Promise.resolve(); // let the async loadTree settle its first tick
    await Promise.resolve();

    expect(PloDashboard.currentTermId).toBe('t-spring');
    expect(global.fetch).toHaveBeenCalled();
    expect(global.fetch.mock.calls[0][0]).toMatch(/term_id=t-spring/);
  });

  test('display-mode change re-renders without re-fetching', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => SAMPLE_TREE });
    await PloDashboard.loadTree();
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // swap fetch for a PUT-capture mock (display mode persists via PUT)
    const putMock = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    global.fetch = putMock;

    const modeSel = document.getElementById('ploDisplayMode');
    modeSel.value = 'percentage';
    modeSel.dispatchEvent(new Event('change'));
    await Promise.resolve();

    expect(PloDashboard.displayMode).toBe('percentage');
    // PUT was fired to persist the setting, but no GET for the tree
    expect(putMock).toHaveBeenCalledTimes(1);
    const [putUrl, putOpts] = putMock.mock.calls[0];
    expect(putOpts.method).toBe('PUT');
    expect(putUrl).toMatch(/\/api\/programs\/prog-1$/);
    expect(putOpts.headers['X-CSRFToken']).toBe('test-csrf-token');
    expect(JSON.parse(putOpts.body)).toEqual({
      assessment_display_mode: 'percentage',
    });

    // badges now show percentages
    const badges = document.querySelectorAll('.plo-assessment-badge');
    expect(Array.from(badges).some((b) => b.textContent.includes('%'))).toBe(
      true,
    );
  });

  test('program filter change persists to localStorage', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => SAMPLE_TREE });

    const sel = document.getElementById('ploProgramFilter');
    sel.innerHTML = '<option value="prog-X">X</option>';
    sel.value = 'prog-X';
    sel.dispatchEvent(new Event('change'));

    expect(localStorage.getItem('ploDashboard.lastProgramId')).toBe('prog-X');
    expect(PloDashboard.currentProgramId).toBe('prog-X');
  });
});

describe('PloDashboard — PLO create/edit modal', () => {
  beforeEach(() => {
    setBody(SKELETON);
    resetDashboardState();
    PloDashboard._cacheSelectors();
    PloDashboard.currentProgramId = 'prog-1';
  });

  afterEach(() => {
    delete global.fetch;
  });

  test('_openPloModal(undefined) prepares for "create" mode', () => {
    PloDashboard._openPloModal();
    expect(document.getElementById('ploModalLabel').textContent).toMatch(
      /new/i,
    );
    expect(document.getElementById('ploModalId').value).toBe('');
    // No bootstrap present → fallback adds .show
    expect(
      document.getElementById('ploModal').classList.contains('show'),
    ).toBe(true);
  });

  test('_openPloModal(plo) prefills for "edit" mode', () => {
    PloDashboard._openPloModal({
      id: 'plo-abc',
      plo_number: 5,
      description: 'Capstone assessment.',
    });
    expect(document.getElementById('ploModalLabel').textContent).toMatch(
      /edit/i,
    );
    expect(document.getElementById('ploModalId').value).toBe('plo-abc');
    expect(document.getElementById('ploModalNumber').value).toBe('5');
    expect(document.getElementById('ploModalDescription').value).toBe(
      'Capstone assessment.',
    );
  });

  test('_submitPloForm POSTs, coerces plo_number to int, hides modal on success', async () => {
    document.getElementById('ploModalId').value = ''; // create mode
    document.getElementById('ploModalNumber').value = '7';
    document.getElementById('ploModalDescription').value = 'New outcome';

    // Two fetches: POST for save, then GET from loadTree()
    global.fetch = routeFetch([
      ['/plos', { body: { success: true, plo: { id: 'new-id' } } }],
      ['/plo-dashboard', { body: { ...SAMPLE_TREE } }],
    ]);

    const evt = { preventDefault: jest.fn() };
    await PloDashboard._submitPloForm(evt);

    expect(evt.preventDefault).toHaveBeenCalled();
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toMatch(/\/api\/programs\/prog-1\/plos$/);
    expect(opts.method).toBe('POST');
    // String "7" should have been parsed to integer 7 for the unique constraint
    expect(JSON.parse(opts.body)).toEqual({
      plo_number: 7,
      description: 'New outcome',
    });
    expect(opts.headers['X-CSRFToken']).toBe('test-csrf-token');

    // Modal hidden on success
    expect(
      document.getElementById('ploModal').classList.contains('show'),
    ).toBe(false);
  });

  test('_submitPloForm PUTs when ploModalId is set', async () => {
    document.getElementById('ploModalId').value = 'existing-plo';
    document.getElementById('ploModalNumber').value = '3';
    document.getElementById('ploModalDescription').value = 'edited';

    global.fetch = routeFetch([
      ['/plos/existing-plo', { body: { success: true } }],
      ['/plo-dashboard', { body: SAMPLE_TREE }],
    ]);

    await PloDashboard._submitPloForm({ preventDefault: jest.fn() });
    const [url, opts] = global.fetch.mock.calls[0];
    expect(opts.method).toBe('PUT');
    expect(url).toMatch(/\/plos\/existing-plo$/);
  });

  test('_submitPloForm shows danger alert on API error', async () => {
    document.getElementById('ploModalNumber').value = '1';
    document.getElementById('ploModalDescription').value = 'dup';
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ success: false, error: 'PLO number already exists' }),
    });

    await PloDashboard._submitPloForm({ preventDefault: jest.fn() });

    const alert = document.getElementById('ploModalAlert');
    expect(alert.className).toContain('alert-danger');
    expect(alert.textContent).toContain('PLO number already exists');
    // Modal stays open on error
    // (it was never shown in this test so just verify no hide was forced)
  });
});

describe('PloDashboard — Map CLO modal + publish', () => {
  beforeEach(() => {
    setBody(SKELETON);
    resetDashboardState();
    PloDashboard._cacheSelectors();
    PloDashboard.currentProgramId = 'prog-1';
    PloDashboard.tree = SAMPLE_TREE; // for PLO-dropdown population
  });

  afterEach(() => {
    delete global.fetch;
  });

  test('_openMapCloModal populates PLOs + unmapped CLOs', async () => {
    global.fetch = routeFetch([
      [
        '/plo-mappings/draft',
        { body: { success: true, mapping: { id: 'draft-1' } } },
      ],
      [
        '/unmapped-clos',
        {
          body: {
            unmapped_clos: [
              {
                outcome_id: 'clo-1',
                clo_number: '4',
                description: 'Analyze data',
                course: { course_number: 'BIOL-201' },
              },
            ],
          },
        },
      ],
    ]);

    await PloDashboard._openMapCloModal('plo-1');

    expect(PloDashboard.draftMappingId).toBe('draft-1');

    // PLO select: placeholder + 2 PLOs from SAMPLE_TREE
    const ploSel = document.getElementById('mapCloModalPlo');
    expect(ploSel.options.length).toBe(3);
    expect(ploSel.value).toBe('plo-1'); // prefill honoured

    // CLO select: placeholder + 1 unmapped CLO
    const cloSel = document.getElementById('mapCloModalClo');
    expect(cloSel.options.length).toBe(2);
    expect(cloSel.options[1].textContent).toContain('BIOL-201');
  });

  test('_openMapCloModal shows "all mapped" when list is empty', async () => {
    global.fetch = routeFetch([
      ['/plo-mappings/draft', { body: { mapping: { id: 'd-2' } } }],
      ['/unmapped-clos', { body: { unmapped_clos: [] } }],
    ]);
    await PloDashboard._openMapCloModal();
    expect(
      document.getElementById('mapCloModalClo').textContent,
    ).toMatch(/all clos are already mapped/i);
  });

  test('_submitMapCloForm warns when PLO or CLO missing', async () => {
    PloDashboard.draftMappingId = 'draft-x';
    document.getElementById('mapCloModalPlo').innerHTML =
      '<option value="">-</option>';
    document.getElementById('mapCloModalClo').innerHTML =
      '<option value="clo-1">CLO</option>';
    document.getElementById('mapCloModalClo').value = 'clo-1';

    global.fetch = jest.fn(); // should NOT be called
    await PloDashboard._submitMapCloForm({ preventDefault: jest.fn() });

    expect(global.fetch).not.toHaveBeenCalled();
    const alert = document.getElementById('mapCloModalAlert');
    expect(alert.className).toContain('alert-warning');
    expect(alert.textContent).toMatch(/select both/i);
  });

  test('_submitMapCloForm POSTs entry with selected ids', async () => {
    PloDashboard.draftMappingId = 'draft-y';
    document.getElementById('mapCloModalPlo').innerHTML =
      '<option value="plo-1">PLO-1</option>';
    document.getElementById('mapCloModalClo').innerHTML =
      '<option value="clo-A">CLO-A</option>';

    // The submit path re-opens the modal on success, which fires two more
    // fetches (draft + unmapped-clos). Route all three.
    global.fetch = routeFetch([
      [
        '/plo-mappings/draft-y/entries',
        { body: { success: true, entry: { id: 'e-1' } } },
      ],
      ['/plo-mappings/draft', { body: { mapping: { id: 'draft-y' } } }],
      ['/unmapped-clos', { body: { unmapped_clos: [] } }],
    ]);

    await PloDashboard._submitMapCloForm({ preventDefault: jest.fn() });

    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toMatch(/draft-y\/entries$/);
    expect(JSON.parse(opts.body)).toEqual({
      program_outcome_id: 'plo-1',
      course_outcome_id: 'clo-A',
    });

    // On success the modal re-opens itself (fire-and-forget, not awaited)
    // to refresh the unmapped-CLO list. That re-open resets the alert to
    // "alert d-none" before its own fetches complete, so we don't assert
    // on the transient success message — the POST body above is the
    // contract under test.
  });

  test('_publishDraft no-ops without a draft id', async () => {
    PloDashboard.draftMappingId = null;
    global.fetch = jest.fn();
    await PloDashboard._publishDraft();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test('_publishDraft POSTs and refreshes tree on success', async () => {
    PloDashboard.draftMappingId = 'draft-z';
    global.fetch = routeFetch([
      ['/draft-z/publish', { body: { success: true, mapping: { version: 3 } } }],
      ['/plo-dashboard', { body: SAMPLE_TREE }],
    ]);

    await PloDashboard._publishDraft();

    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toMatch(/\/plo-mappings\/draft-z\/publish$/);
    expect(opts.method).toBe('POST');
    // Modal hidden after publish
    expect(
      document.getElementById('mapCloModal').classList.contains('show'),
    ).toBe(false);
    // Tree was reloaded
    expect(global.fetch.mock.calls[1][0]).toMatch(/\/plo-dashboard/);
  });

  test('_publishDraft shows error alert on API failure', async () => {
    PloDashboard.draftMappingId = 'draft-err';
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ success: false, error: 'Nothing to publish' }),
    });
    await PloDashboard._publishDraft();
    const alert = document.getElementById('mapCloModalAlert');
    expect(alert.className).toContain('alert-danger');
    expect(alert.textContent).toContain('Nothing to publish');
  });
});

describe('PloDashboard — small helpers', () => {
  test('_csrf reads from meta tag', () => {
    setBody('<meta name="csrf-token" content="abc123">');
    PloDashboard._cacheSelectors();
    expect(PloDashboard._csrf()).toBe('abc123');
  });

  test('_csrf returns empty string when meta missing', () => {
    setBody('');
    expect(PloDashboard._csrf()).toBe('');
  });

  test('_modalAlert sets class + text; tolerates null element', () => {
    setBody('<div id="a"></div>');
    const el = document.getElementById('a');
    PloDashboard._modalAlert(el, 'hello', 'warning');
    expect(el.className).toBe('alert alert-warning');
    expect(el.textContent).toBe('hello');

    // null element → no throw
    expect(() => PloDashboard._modalAlert(null, 'x', 'info')).not.toThrow();
  });

  test('_showModal/_hideModal use class-toggle fallback when no bootstrap', () => {
    setBody('<div id="m" style="display:none"></div>');
    const m = document.getElementById('m');
    PloDashboard._showModal(m);
    expect(m.classList.contains('show')).toBe(true);
    expect(m.style.display).toBe('block');
    PloDashboard._hideModal(m);
    expect(m.classList.contains('show')).toBe(false);
    expect(m.style.display).toBe('none');
  });
});

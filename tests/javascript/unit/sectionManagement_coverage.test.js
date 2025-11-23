const { setBody, flushPromises } = require('../helpers/dom');

describe('sectionManagement.js Coverage Boost', () => {
  let mockLoadSections;

  beforeEach(() => {
    jest.resetModules();
    setBody(`
      <form id="createSectionForm">
        <input id="sectionNumber" value="001">
        <input id="sectionOfferingId" value="off1">
        <select id="sectionCourseId"><option value="c1">Course</option></select>
        <select id="sectionTermId"><option value="t1">Term</option></select>
        <select id="sectionInstructorId"><option value="i1">Instructor</option></select>
        <input id="sectionSchedule" value="MWF">
        <input id="sectionRoom" value="101">
        <input id="sectionCapacity" value="30">
        <input id="sectionEnrollment" value="0">
        <input id="sectionStatus" value="active">
        <button type="submit" id="createSectionBtn">
            <span class="btn-text">Save</span>
            <span class="btn-spinner d-none"></span>
        </button>
      </form>
      <div id="createSectionModal"></div>
      
      <form id="editSectionForm">
        <input id="editSectionId" value="s1">
        <input id="editSectionNumber" value="001">
        <select id="editSectionCourseId"><option value="c1">Course</option></select>
        <select id="editSectionTermId"><option value="t1">Term</option></select>
        <select id="editSectionInstructorId"><option value="i1">Instructor</option></select>
        <input id="editSectionSchedule" value="MWF">
        <input id="editSectionRoom" value="101">
        <input id="editSectionCapacity" value="30">
        <input id="editSectionEnrollment" value="0">
        <input id="editSectionStatus" value="active">
        <button type="submit" id="editSectionBtn">
            <span class="btn-text">Save</span>
            <span class="btn-spinner d-none"></span>
        </button>
      </form>
      <div id="editSectionModal"></div>
      
      <meta name="csrf-token" content="token">
    `);

    global.bootstrap = {
      Modal: jest.fn().mockImplementation(() => ({
        show: jest.fn(),
        hide: jest.fn()
      }))
    };
    global.bootstrap.Modal.getInstance = jest.fn(() => ({ hide: jest.fn() }));

    mockLoadSections = jest.fn();
    global.loadSections = mockLoadSections;
    
    jest.spyOn(window, 'alert').mockImplementation(() => {});
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    jest.spyOn(console, 'error').mockImplementation(() => {});

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, message: 'Success' })
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
    delete global.loadSections;
  });

  test('createSectionForm calls loadSections on success', async () => {
    require('../../../static/sectionManagement.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
    
    const form = document.getElementById('createSectionForm');
    form.dispatchEvent(new Event('submit'));
    
    await flushPromises();
    expect(mockLoadSections).toHaveBeenCalled();
  });

  test('editSectionForm calls loadSections on success', async () => {
    require('../../../static/sectionManagement.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
    
    const form = document.getElementById('editSectionForm');
    form.dispatchEvent(new Event('submit'));
    
    await flushPromises();
    expect(mockLoadSections).toHaveBeenCalled();
  });

  test('deleteSection calls loadSections on success', async () => {
    require('../../../static/sectionManagement.js');
    await global.deleteSection('s1');
    await flushPromises();
    expect(mockLoadSections).toHaveBeenCalled();
  });
});


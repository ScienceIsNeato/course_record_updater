const { initOfferingManagement } = require('../../../static/offeringManagement.js');

describe('Offering Management - Loading Data', () => {
    let mockFetch;
    let consoleErrorSpy;

    beforeEach(() => {
        mockFetch = jest.fn();
        global.fetch = mockFetch;
        consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    describe('loadOfferings', () => {
        beforeEach(() => {
            document.body.innerHTML = '<div id="offeringsTableContainer"></div>';
        });

        test('should display offerings in table', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    offerings: [
                        {
                            offering_id: 'o1',
                            course_name: 'CS101',
                            term_name: 'Fall 2024',
                            status: 'active',
                            section_count: 2,
                            total_enrollment: 50
                        }
                    ]
                })
            });

            await window.loadOfferings();

            const container = document.getElementById('offeringsTableContainer');
            expect(container.innerHTML).toContain('CS101');
            expect(container.innerHTML).toContain('Fall 2024');
            expect(container.innerHTML).toContain('50');
            expect(container.querySelectorAll('tr').length).toBe(2); // Header + 1 row
        });

        test('should display empty state if no offerings', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ offerings: [] })
            });

            await window.loadOfferings();

            const container = document.getElementById('offeringsTableContainer');
            expect(container.innerHTML).toContain('No course offerings found');
        });

        test('should handle error', async () => {
            mockFetch.mockResolvedValueOnce({ ok: false });

            await window.loadOfferings();

            const container = document.getElementById('offeringsTableContainer');
            expect(container.innerHTML).toContain('Error loading offerings');
        });
    });

    describe('Dropdown Loading', () => {
        beforeEach(() => {
            document.body.innerHTML = `
            <form id="createOfferingForm">
                <select id="offeringCourseId"></select>
                <select id="offeringTermId"></select>
                <select id="offeringProgramId"></select>
            </form>
            <div id="createOfferingModal"></div>
            <div id="editOfferingModal"></div>
        `;
            initOfferingManagement(); // Setup listeners
        });

        test('should populate create dropdowns when modal shows', async () => {
            mockFetch
                .mockResolvedValueOnce({ ok: true, json: async () => ({ courses: [{ course_id: 'c1', course_number: 'CS101', course_title: 'Intro' }] }) })
                .mockResolvedValueOnce({ ok: true, json: async () => ({ terms: [{ term_id: 't1', name: 'Fall 24' }] }) })
                .mockResolvedValueOnce({ ok: true, json: async () => ({ programs: [{ program_id: 'p1', name: 'CS' }] }) });

            const modal = document.getElementById('createOfferingModal');
            const event = new Event('show.bs.modal');
            modal.dispatchEvent(event);

            await new Promise(resolve => setTimeout(resolve, 300));

            const courseSelect = document.getElementById('offeringCourseId');
            // logger.log(courseSelect.innerHTML); 
            expect(courseSelect.innerHTML).toContain('Select Course'); // Check text content first
            expect(courseSelect.options.length).toBeGreaterThan(0);
            expect(courseSelect.innerHTML).toContain('CS101');
        });
    });
});

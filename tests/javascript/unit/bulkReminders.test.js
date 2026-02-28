/**
 * Unit Tests for Bulk Reminders UI
 *
 * Tests modal behavior, instructor selection, API interactions, and progress tracking for:
 * - Instructor list loading and rendering
 * - Selection/deselection functionality
 * - Sending bulk reminders
 * - Progress polling and status updates
 * - Job completion handling
 */

// Load the implementation
const { BulkReminderManager, openBulkReminderModal } = require('../../../static/bulk_reminders.js');

describe('BulkReminderManager', () => {
    let mockFetch;
    let consoleErrorSpy;
    let consoleLogSpy;
    let manager;

    beforeEach(() => {
        // Set up comprehensive DOM structure
        document.body.innerHTML = `
            <div class="modal" id="bulkReminderModal">
                <div id="reminderStep1">
                    <div id="instructorListContainer"></div>
                    <div>
                        <span id="selectedInstructorCount">0</span>
                    </div>
                    <button id="selectAllInstructors">Select All</button>
                    <button id="deselectAllInstructors">Deselect All</button>
                    <input type="text" id="reminderTerm" />
                    <input type="date" id="reminderDeadline" />
                    <textarea id="reminderMessage"></textarea>
                    <span id="messageCharCount">0</span>
                </div>
                <div id="reminderStep2" style="display: none;">
                    <div class="progress">
                        <progress id="reminderProgressBar" class="progress-bar progress-bar-striped progress-bar-animated" 
                             value="0" max="100">
                            <span id="reminderProgressText">0%</span>
                        </progress>
                    </div>
                    <div id="reminderStatusMessages"></div>
                    <div>
                        Sent: <span id="reminderSentCount">0</span>
                        Failed: <span id="reminderFailedCount">0</span>
                        Pending: <span id="reminderPendingCount">0</span>
                    </div>
                    <div id="reminderComplete" style="display: none;"></div>
                    <div id="reminderFailedRecipients" style="display: none;">
                        <div id="reminderFailedList"></div>
                    </div>
                </div>
                <div id="reminderFooter1">
                    <button id="sendRemindersButton" disabled>Send Reminders</button>
                </div>
                <div id="reminderFooter2" style="display: none;">
                    <button id="closeProgressButton" disabled>Close</button>
                </div>
            </div>
        `;

        // Mock fetch
        mockFetch = jest.fn();
        global.fetch = mockFetch;

        // Mock console methods
        consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
        consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();

        // Mock Bootstrap Modal
        global.bootstrap = {
            Modal: jest.fn().mockImplementation(() => ({
                show: jest.fn(),
                hide: jest.fn()
            }))
        };

        // Mock setInterval/clearInterval
        jest.useFakeTimers();

        // Create manager instance
        manager = new BulkReminderManager();
    });

    afterEach(() => {
        jest.restoreAllMocks();
        jest.clearAllTimers();
        jest.useRealTimers();
    });

    describe('Initialization', () => {
        test('should initialize with default state', () => {
            expect(manager.modal).toBeNull();
            expect(manager.selectedInstructors).toEqual(new Set());
            expect(manager.allInstructors).toEqual([]);
            expect(manager.currentJobId).toBeNull();
            expect(manager.pollingInterval).toBeNull();
            expect(manager.pollingIntervalMs).toBe(2000);
        });

        test('should initialize modal and setup event listeners', () => {
            manager.init();

            expect(global.bootstrap.Modal).toHaveBeenCalled();
            expect(manager.modal).toBeDefined();
        });

        test('should handle missing modal element gracefully', () => {
            document.body.innerHTML = '';
            manager.init();

            expect(consoleErrorSpy).toHaveBeenCalledWith('[BulkReminders] Modal not found');
            expect(manager.modal).toBeNull();
        });
    });

    describe('Event Listeners', () => {
        beforeEach(() => {
            manager.init();
        });

        test('should handle select all button click', () => {
            // Add some checkboxes
            document.getElementById('instructorListContainer').innerHTML = `
                <input class="instructor-checkbox" type="checkbox" value="1" />
                <input class="instructor-checkbox" type="checkbox" value="2" />
            `;

            const selectAllBtn = document.getElementById('selectAllInstructors');
            selectAllBtn.click();

            const checkboxes = document.querySelectorAll('.instructor-checkbox');
            checkboxes.forEach(cb => {
                expect(cb.checked).toBe(true);
            });
        });

        test('should handle deselect all button click', () => {
            // Add some checked checkboxes
            document.getElementById('instructorListContainer').innerHTML = `
                <input class="instructor-checkbox" type="checkbox" value="1" checked />
                <input class="instructor-checkbox" type="checkbox" value="2" checked />
            `;
            manager.selectedInstructors.add('1');
            manager.selectedInstructors.add('2');

            const deselectAllBtn = document.getElementById('deselectAllInstructors');
            deselectAllBtn.click();

            const checkboxes = document.querySelectorAll('.instructor-checkbox');
            checkboxes.forEach(cb => {
                expect(cb.checked).toBe(false);
            });
        });

        test('should update character count for message input', () => {
            const messageInput = document.getElementById('reminderMessage');
            const charCount = document.getElementById('messageCharCount');

            messageInput.value = 'Hello';
            messageInput.dispatchEvent(new Event('input'));

            expect(charCount.textContent).toBe('5');
        });
    });

    describe('Instructor Loading', () => {
        beforeEach(() => {
            manager.init();
        });

        test('should show loading state initially', () => {
            manager.loadInstructors();

            const container = document.getElementById('instructorListContainer');
            expect(container.innerHTML).toContain('Loading instructors');
            expect(container.innerHTML).toContain('spinner-border');
        });

        test('should fetch and render instructors successfully', async () => {
            const mockInstructors = [
                {
                    user_id: '1',
                    first_name: 'John',
                    last_name: 'Doe',
                    email: 'john@example.com'
                },
                {
                    user_id: '2',
                    first_name: 'Jane',
                    last_name: 'Smith',
                    email: 'jane@example.com'
                }
            ];

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true, instructors: mockInstructors })
            });

            await manager.loadInstructors();

            expect(mockFetch).toHaveBeenCalledWith('/api/instructors');
            expect(manager.allInstructors).toHaveLength(2);
            expect(manager.allInstructors[0].name).toBe('John Doe');
            expect(manager.allInstructors[1].email).toBe('jane@example.com');
        });

        test('should handle fetch error gracefully', async () => {
            mockFetch.mockRejectedValueOnce(new Error('Network error'));

            await manager.loadInstructors();

            const container = document.getElementById('instructorListContainer');
            expect(container.innerHTML).toContain('Failed to load instructors');
            expect(consoleErrorSpy).toHaveBeenCalled();
        });

        test('should handle API error response', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: false,
                status: 500
            });

            await manager.loadInstructors();

            const container = document.getElementById('instructorListContainer');
            expect(container.innerHTML).toContain('Failed to load instructors');
        });
    });

    describe('Instructor Rendering', () => {
        test('should render instructor list with checkboxes', () => {
            const instructors = [
                { id: '1', name: 'John Doe', email: 'john@example.com', courses: ['CS101'] },
                { id: '2', name: 'Jane Smith', email: 'jane@example.com', courses: [] }
            ];

            manager.renderInstructorList(instructors);

            const container = document.getElementById('instructorListContainer');
            expect(container.innerHTML).toContain('John Doe');
            expect(container.innerHTML).toContain('john@example.com');
            expect(container.innerHTML).toContain('Jane Smith');
            expect(container.innerHTML).toContain('CS101');
        });

        test('should show empty state when no instructors', () => {
            manager.renderInstructorList([]);

            const container = document.getElementById('instructorListContainer');
            expect(container.innerHTML).toContain('No instructors found');
        });

        test('should attach change listeners to checkboxes', () => {
            const instructors = [
                { id: '1', name: 'John Doe', email: 'john@example.com', courses: [] }
            ];

            manager.renderInstructorList(instructors);

            const checkbox = document.querySelector('.instructor-checkbox');
            checkbox.checked = true;
            checkbox.dispatchEvent(new Event('change'));

            expect(manager.selectedInstructors.has('1')).toBe(true);
        });
    });

    describe('Selection Management', () => {
        beforeEach(() => {
            document.getElementById('instructorListContainer').innerHTML = `
                <input class="instructor-checkbox" type="checkbox" value="1" />
                <input class="instructor-checkbox" type="checkbox" value="2" />
                <input class="instructor-checkbox" type="checkbox" value="3" />
            `;
        });

        test('should update selection count when checkboxes change', () => {
            const checkboxes = document.querySelectorAll('.instructor-checkbox');
            checkboxes[0].checked = true;
            checkboxes[1].checked = true;

            manager.updateSelection();

            expect(manager.selectedInstructors.size).toBe(2);
            expect(document.getElementById('selectedInstructorCount').textContent).toBe('2');
            expect(document.getElementById('sendRemindersButton').disabled).toBe(false);
        });

        test('should disable send button when no selection', () => {
            manager.updateSelection();

            expect(document.getElementById('sendRemindersButton').disabled).toBe(true);
        });

        test('should select all instructors', () => {
            manager.selectAll();

            const checkboxes = document.querySelectorAll('.instructor-checkbox');
            expect(checkboxes[0].checked).toBe(true);
            expect(checkboxes[1].checked).toBe(true);
            expect(checkboxes[2].checked).toBe(true);
            expect(manager.selectedInstructors.size).toBe(3);
        });

        test('should deselect all instructors', () => {
            // First select all
            manager.selectAll();
            expect(manager.selectedInstructors.size).toBe(3);

            // Then deselect all
            manager.deselectAll();

            const checkboxes = document.querySelectorAll('.instructor-checkbox');
            expect(checkboxes[0].checked).toBe(false);
            expect(checkboxes[1].checked).toBe(false);
            expect(checkboxes[2].checked).toBe(false);
            expect(manager.selectedInstructors.size).toBe(0);
        });
    });

    describe('Sending Reminders', () => {
        beforeEach(() => {
            manager.init();
            manager.selectedInstructors.add('1');
            manager.selectedInstructors.add('2');
            document.getElementById('reminderTerm').value = 'Fall 2024';
            document.getElementById('reminderDeadline').value = '2024-12-31';
            document.getElementById('reminderMessage').value = 'Please submit';
        });

        test('should not send when no instructors selected', async () => {
            manager.selectedInstructors.clear();

            await manager.sendReminders();

            expect(mockFetch).not.toHaveBeenCalled();
        });

        test('should send reminder request with correct data', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    job_id: 'job-123',
                    recipient_count: 2
                })
            });

            await manager.sendReminders();

            expect(mockFetch).toHaveBeenCalledWith('/api/bulk-email/send-instructor-reminders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    instructor_ids: ['1', '2'],
                    personal_message: 'Please submit',
                    term: 'Fall 2024',
                    deadline: '2024-12-31',
                    course_id: null
                })
            });
        });

        test('should switch to progress view and start polling', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    job_id: 'job-123',
                    recipient_count: 2
                })
            });

            await manager.sendReminders();

            expect(document.getElementById('reminderStep1').style.display).toBe('none');
            expect(document.getElementById('reminderStep2').style.display).toBe('block');
            expect(manager.currentJobId).toBe('job-123');
        });

        test('should handle send error gracefully', async () => {
            mockFetch.mockRejectedValueOnce(new Error('Network error'));

            await manager.sendReminders();

            expect(consoleErrorSpy).toHaveBeenCalled();
            expect(document.getElementById('closeProgressButton').disabled).toBe(false);
        });

        test('should handle API error response', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: false,
                    error: 'Invalid request'
                })
            });

            await manager.sendReminders();

            const messages = document.getElementById('reminderStatusMessages');
            expect(messages.innerHTML).toContain('Invalid request');
        });
    });

    describe('Progress Tracking', () => {
        beforeEach(() => {
            manager.init();
            manager.currentJobId = 'job-123';
        });

        test('should check job status via API', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    job: {
                        status: 'running',
                        progress_percentage: 50,
                        emails_sent: 5,
                        emails_failed: 0,
                        emails_pending: 5,
                        recipient_count: 10
                    }
                })
            });

            await manager.checkJobStatus();

            expect(mockFetch).toHaveBeenCalledWith('/api/bulk-email/job-status/job-123');
        });

        test('should update progress bar and counts', () => {
            const job = {
                status: 'running',
                progress_percentage: 75,
                emails_sent: 15,
                emails_failed: 2,
                emails_pending: 3,
                recipient_count: 20
            };

            manager.updateProgress(job);

            expect(document.getElementById('reminderProgressBar').value).toBe(75);
            expect(document.getElementById('reminderProgressText').textContent).toBe('75%');
            expect(document.getElementById('reminderSentCount').textContent).toBe('15');
            expect(document.getElementById('reminderFailedCount').textContent).toBe('2');
            expect(document.getElementById('reminderPendingCount').textContent).toBe('3');
        });

        test('should stop polling when job completes', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    job: {
                        status: 'completed',
                        progress_percentage: 100,
                        emails_sent: 10,
                        emails_failed: 0,
                        emails_pending: 0,
                        recipient_count: 10
                    }
                })
            });

            manager.pollingInterval = setInterval(() => {}, 1000);

            await manager.checkJobStatus();

            expect(manager.pollingInterval).toBeNull();
        });

        test('should show failed recipients when present', () => {
            const job = {
                status: 'running',
                progress_percentage: 90,
                emails_sent: 9,
                emails_failed: 1,
                emails_pending: 0,
                recipient_count: 10,
                failed_recipients: [
                    { email: 'failed@example.com', error: 'SMTP error' }
                ]
            };

            manager.updateProgress(job);

            const failedContainer = document.getElementById('reminderFailedRecipients');
            const failedList = document.getElementById('reminderFailedList');

            expect(failedContainer.style.display).toBe('block');
            expect(failedList.innerHTML).toContain('failed@example.com');
            expect(failedList.innerHTML).toContain('SMTP error');
        });
    });

    describe('Job Completion', () => {
        test('should show success message on completion', () => {
            const job = {
                status: 'completed',
                emails_sent: 10,
                emails_failed: 0
            };

            manager.showCompletion(job);

            const completeDiv = document.getElementById('reminderComplete');
            expect(completeDiv.style.display).toBe('block');
            expect(completeDiv.innerHTML).toContain('Complete!');
            expect(completeDiv.innerHTML).toContain('Successfully sent 10');
            expect(document.getElementById('closeProgressButton').disabled).toBe(false);
        });

        test('should show error message on failure', () => {
            const job = {
                status: 'failed',
                error_message: 'SMTP connection failed'
            };

            manager.showCompletion(job);

            const completeDiv = document.getElementById('reminderComplete');
            expect(completeDiv.className).toContain('alert-danger');
            expect(completeDiv.innerHTML).toContain('Failed!');
            expect(completeDiv.innerHTML).toContain('SMTP connection failed');
        });

        test('should update progress bar styling on completion', () => {
            const job = {
                status: 'completed',
                emails_sent: 10,
                emails_failed: 0
            };

            manager.showCompletion(job);

            const progressBar = document.getElementById('reminderProgressBar');
            expect(progressBar.classList.contains('progress-bar-animated')).toBe(false);
            expect(progressBar.classList.contains('bg-success')).toBe(true);
        });
    });

    describe('Status Messages', () => {
        test('should add status message with correct styling', () => {
            manager.addStatusMessage('Test message', 'success');

            const messages = document.getElementById('reminderStatusMessages');
            expect(messages.innerHTML).toContain('Test message');
            expect(messages.innerHTML).toContain('text-success');
            expect(messages.innerHTML).toContain('fa-check-circle');
        });

        test('should add timestamp to message', () => {
            manager.addStatusMessage('Test', 'info');

            const messages = document.getElementById('reminderStatusMessages');
            // Timestamp format can include AM/PM
            expect(messages.innerHTML).toMatch(/\[\d{1,2}:\d{2}:\d{2}/);
        });

        test('should limit messages to 50', () => {
            // Add 60 messages
            for (let i = 0; i < 60; i++) {
                manager.addStatusMessage(`Message ${i}`, 'info');
            }

            const messages = document.getElementById('reminderStatusMessages');
            expect(messages.children.length).toBe(50);
        });

        test('should auto-scroll to bottom', () => {
            const messages = document.getElementById('reminderStatusMessages');
            messages.scrollTop = 0;
            messages.scrollHeight = 1000;

            manager.addStatusMessage('New message', 'info');

            expect(messages.scrollTop).toBe(messages.scrollHeight);
        });
    });

    describe('Modal Reset', () => {
        beforeEach(() => {
            manager.init();
            manager.selectedInstructors.add('1');
            manager.currentJobId = 'job-123';
            manager.pollingInterval = setInterval(() => {}, 1000);
            document.getElementById('reminderMessage').value = 'Test message';
        });

        test('should reset all state and UI', () => {
            manager.resetModal();

            expect(manager.selectedInstructors.size).toBe(0);
            expect(manager.currentJobId).toBeNull();
            expect(manager.pollingInterval).toBeNull();
            expect(document.getElementById('reminderMessage').value).toBe('');
            expect(document.getElementById('selectedInstructorCount').textContent).toBe('0');
            expect(document.getElementById('sendRemindersButton').disabled).toBe(true);
        });

        test('should reset progress view', () => {
            manager.resetModal();

            expect(document.getElementById('reminderProgressBar').value).toBe(0);
            expect(document.getElementById('reminderSentCount').textContent).toBe('0');
            expect(document.getElementById('reminderStatusMessages').innerHTML).toBe('');
            expect(document.getElementById('reminderComplete').style.display).toBe('none');
        });

        test('should show selection view and hide progress view', () => {
            document.getElementById('reminderStep1').style.display = 'none';
            document.getElementById('reminderStep2').style.display = 'block';

            manager.resetModal();

            expect(document.getElementById('reminderStep1').style.display).toBe('block');
            expect(document.getElementById('reminderStep2').style.display).toBe('none');
        });
    });

    describe('Polling Management', () => {
        beforeEach(() => {
            manager.init();
            manager.currentJobId = 'job-123';
        });

        test('should start polling interval', () => {
            mockFetch.mockResolvedValue({
                ok: true,
                json: async () => ({
                    success: true,
                    job: { status: 'running', progress_percentage: 50, emails_sent: 5, emails_failed: 0, emails_pending: 5, recipient_count: 10 }
                })
            });

            manager.startPolling();

            expect(manager.pollingInterval).not.toBeNull();
        });

        test('should stop polling', () => {
            manager.pollingInterval = setInterval(() => {}, 1000);

            manager.stopPolling();

            expect(manager.pollingInterval).toBeNull();
        });

        test('should check status immediately when polling starts', async () => {
            mockFetch.mockResolvedValue({
                ok: true,
                json: async () => ({
                    success: true,
                    job: { status: 'running', progress_percentage: 50, emails_sent: 5, emails_failed: 0, emails_pending: 5, recipient_count: 10 }
                })
            });

            manager.startPolling();

            // Check was called immediately (not just after interval)
            expect(mockFetch).toHaveBeenCalled();
        });
    });

    describe('Global Functions', () => {
        test('should expose global openBulkReminderModal function', () => {
            expect(typeof openBulkReminderModal).toBe('function');
        });

        test('openBulkReminderModal should call manager.show()', () => {
            manager.init();
            const mockShow = jest.fn();
            manager.show = mockShow;
            
            // Set the global instance to our test manager
            // Note: In the actual file, bulkReminderManager is a module-level var
            // We need to call openBulkReminderModal directly with a truthy manager
            // Since we can't easily mock the module-level variable, we'll test the condition
            const originalManager = global.bulkReminderManager;
            global.bulkReminderManager = manager;

            openBulkReminderModal();

            expect(mockShow).toHaveBeenCalled();
            
            // Restore
            global.bulkReminderManager = originalManager;
        });

        test('openBulkReminderModal should handle uninitialized manager', () => {
            global.bulkReminderManager = null;

            openBulkReminderModal();

            expect(consoleErrorSpy).toHaveBeenCalledWith('[BulkReminders] Manager not initialized');
        });
    });
});


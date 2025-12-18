/**
 * @jest-environment jsdom
 */

const {
    getStatusBadge,
    formatDate,
    truncateText,
    escapeHtml,
    formatStatusLabel,
    formatDateForCsv,
    escapeForCsv,
    calculateSuccessRate,
    exportCurrentViewToCsv
} = require('../../../static/audit_clo.js');

describe('audit_clo.js', () => {
    describe('getStatusBadge', () => {
        test('returns correct badge for known statuses', () => {
            expect(getStatusBadge('approved')).toContain('bg-success');
            expect(getStatusBadge('awaiting_approval')).toContain('bg-warning');
            expect(getStatusBadge('never_coming_in')).toContain('bg-dark');
        });

        test('returns correct badge for all status types', () => {
            expect(getStatusBadge('unassigned')).toContain('bg-secondary');
            expect(getStatusBadge('assigned')).toContain('bg-info');
            expect(getStatusBadge('in_progress')).toContain('bg-primary');
            expect(getStatusBadge('approval_pending')).toContain('bg-danger');
        });

        test('returns unknown badge for invalid status', () => {
            expect(getStatusBadge('invalid_status')).toContain('Unknown');
            expect(getStatusBadge('')).toContain('Unknown');
            expect(getStatusBadge(null)).toContain('Unknown');
        });
    });

    describe('formatStatusLabel', () => {
        test('returns readable label for CSV', () => {
            expect(formatStatusLabel('awaiting_approval')).toBe('Awaiting Approval');
            expect(formatStatusLabel('approval_pending')).toBe('Needs Rework');
            expect(formatStatusLabel('never_coming_in')).toBe('Never Coming In');
        });

        test('handles all known statuses', () => {
            expect(formatStatusLabel('approved')).toBe('Approved');
            expect(formatStatusLabel('assigned')).toBe('Assigned');
            expect(formatStatusLabel('unassigned')).toBe('Unassigned');
            expect(formatStatusLabel('in_progress')).toBe('In Progress');
        });

        test('returns raw status if unknown', () => {
            expect(formatStatusLabel('custom_status')).toBe('custom_status');
        });
    });

    describe('formatDateForCsv', () => {
        test('returns ISO string for valid date', () => {
            const date = new Date('2024-01-01T12:00:00Z');
            expect(formatDateForCsv(date.toISOString())).toBe(date.toISOString());
        });

        test('returns empty string for invalid/null date', () => {
            expect(formatDateForCsv(null)).toBe('');
            expect(formatDateForCsv('invalid-date')).toBe('');
        });
    });

    describe('escapeForCsv', () => {
        test('wraps string in quotes', () => {
            expect(escapeForCsv('hello')).toBe('"hello"');
        });

        test('escapes existing quotes', () => {
            expect(escapeForCsv('hello "world"')).toBe('"hello ""world"""');
        });

        test('handles numbers', () => {
            expect(escapeForCsv(123)).toBe('"123"');
        });

        test('handles null/undefined', () => {
            expect(escapeForCsv(null)).toBe('""');
            expect(escapeForCsv(undefined)).toBe('""');
        });
    });

    describe('calculateSuccessRate', () => {
        test('calculates percentage correctly', () => {
            const clo = { students_took: 10, students_passed: 8 };
            expect(calculateSuccessRate(clo)).toBe(80);
        });

        test('rounds to nearest integer', () => {
            const clo = { students_took: 3, students_passed: 1 }; // 33.33...
            expect(calculateSuccessRate(clo)).toBe(33);
        });

        test('returns empty string for invalid input', () => {
            expect(calculateSuccessRate({})).toBeNull();
            expect(calculateSuccessRate({ students_took: 0 })).toBeNull();
            expect(calculateSuccessRate({ students_took: 10, students_passed: null })).toBeNull();
        });
    });

    describe('formatDate', () => {
        test('formats valid date string', () => {
            const result = formatDate('2024-01-15T10:30:00Z');
            expect(result).toContain('2024');
            expect(result).not.toBe('N/A');
        });

        test('returns N/A for null or undefined', () => {
            expect(formatDate(null)).toBe('N/A');
            expect(formatDate(undefined)).toBe('N/A');
            expect(formatDate('')).toBe('N/A');
        });

        test('formats various date formats', () => {
            expect(formatDate('2024-06-15')).not.toBe('N/A');
            expect(formatDate('2024-06-15T00:00:00')).not.toBe('N/A');
        });

        test('handles ISO date strings', () => {
            const isoDate = new Date().toISOString();
            const result = formatDate(isoDate);
            expect(result).not.toBe('N/A');
            expect(typeof result).toBe('string');
        });
    });

    describe('truncateText', () => {
        test('truncates long text with ellipsis', () => {
            // substring(0, 10) = "This is a ", then adds "..."
            expect(truncateText('This is a very long text', 10)).toBe('This is a ...');
        });

        test('returns full text if shorter than maxLength', () => {
            expect(truncateText('Short', 10)).toBe('Short');
        });

        test('handles null/undefined/empty', () => {
            expect(truncateText(null, 10)).toBe('');
            expect(truncateText(undefined, 10)).toBe('');
            expect(truncateText('', 10)).toBe('');
        });

        test('handles exact length', () => {
            expect(truncateText('ExactlyTen', 10)).toBe('ExactlyTen');
        });
    });

    describe('escapeHtml', () => {
        test('escapes HTML special characters', () => {
            const result = escapeHtml('<script>alert("xss")</script>');
            // The browser's textContent/innerHTML will properly escape these
            expect(result).toContain('&lt;');
            expect(result).toContain('&gt;');
            expect(result).not.toContain('<script>');
        });

        test('escapes ampersand', () => {
            const result = escapeHtml('A & B');
            expect(result).toContain('&amp;');
        });

        test('handles null/undefined/empty', () => {
            expect(escapeHtml(null)).toBe('');
            expect(escapeHtml(undefined)).toBe('');
            expect(escapeHtml('')).toBe('');
        });

        test('handles plain text', () => {
            expect(escapeHtml('Hello World')).toBe('Hello World');
        });
    });

    describe('exportCurrentViewToCsv', () => {
        test('handles empty or invalid input gracefully', () => {
            // Function doesn't return anything, but shouldn't throw
            expect(() => exportCurrentViewToCsv([])).not.toThrow();
            expect(() => exportCurrentViewToCsv(null)).not.toThrow();
            expect(() => exportCurrentViewToCsv(undefined)).not.toThrow();
        });

        // Note: Full CSV generation testing requires complex DOM mocking
        // and is better tested via E2E/integration tests where real DOM exists
    });
});


/**
 * @jest-environment jsdom
 */

const {
    getStatusBadge,
    formatDate,
    truncateText,
    formatStatusLabel,
    formatDateForCsv,
    escapeForCsv,
    calculateSuccessRate
} = require('../../../static/audit_clo.js');

describe('audit_clo.js', () => {
    describe('getStatusBadge', () => {
        test('returns correct badge for known statuses', () => {
            expect(getStatusBadge('approved')).toContain('bg-success');
            expect(getStatusBadge('awaiting_approval')).toContain('bg-warning');
            expect(getStatusBadge('never_coming_in')).toContain('bg-dark');
        });

        test('returns unknown badge for invalid status', () => {
            expect(getStatusBadge('invalid_status')).toContain('Unknown');
        });
    });

    describe('formatStatusLabel', () => {
        test('returns readable label for CSV', () => {
            expect(formatStatusLabel('awaiting_approval')).toBe('Awaiting Approval');
            expect(formatStatusLabel('approval_pending')).toBe('Needs Rework');
            expect(formatStatusLabel('never_coming_in')).toBe('Never Coming In');
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
            expect(calculateSuccessRate({})).toBe('');
            expect(calculateSuccessRate({ students_took: 0 })).toBe('');
            expect(calculateSuccessRate({ students_took: 10, students_passed: null })).toBe('');
        });
    });
});


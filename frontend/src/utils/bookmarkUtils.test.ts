import { describe, expect, it } from 'vitest';
import { injectIndices, parseLines } from './bookmarkUtils';

describe('bookmarkUtils', () => {
    it('parses indentation and @ page separators', () => {
        const parsed = parseLines('Intro @ 1\n    Child @ 2');

        expect(parsed[0]).toMatchObject({
            title: 'Intro',
            page: '1',
            level: 0,
            computedIndex: '1',
        });
        expect(parsed[1]).toMatchObject({
            title: 'Child',
            page: '2',
            level: 1,
            computedIndex: '1.1',
        });
    });

    it('injects hierarchical indices without dropping page numbers', () => {
        const result = injectIndices('Intro @ 1\n    Child @ 2');

        expect(result).toBe('1 Intro @ 1\n    1.1 Child @ 2');
    });
});

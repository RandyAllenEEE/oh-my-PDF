
export interface ParsedLine {
    original: string;
    title: string;
    page: string;
    level: number;
    computedIndex: string;
}

export const parseLines = (text: string): ParsedLine[] => {
    const rawLines = text.split('\n');
    const parsed: ParsedLine[] = [];
    const counters: number[] = [0]; // Level 0 counter

    rawLines.forEach((line) => {
        if (!line.trim()) {
            parsed.push({ original: line, title: '', page: '', level: 0, computedIndex: '' });
            return;
        }

        // Detect level (4 spaces = 1 level)
        const leadingSpaces = line.match(/^ */)?.[0].length || 0;
        const level = Math.floor(leadingSpaces / 4);

        // Update counters
        if (level >= counters.length) {
            // Fill gaps
            while (counters.length <= level) counters.push(0);
        }
        // Reset deeper counters
        for (let i = level + 1; i < counters.length; i++) counters[i] = 0;

        counters[level]++;
        const currentIndex = counters.slice(0, level + 1).join('.');

        // Extract Page and Title
        // Pattern: (Title)(Separators)(PageNumber)
        const match = line.trim().match(/^(.*?)(?:\s+)(\d+)$/);
        let title = line.trim();
        let page = '';

        if (match) {
            title = match[1];
            page = match[2];
        }

        parsed.push({
            original: line,
            title: title,
            page: page,
            level: level,
            computedIndex: currentIndex
        });
    });
    return parsed;
};

export const injectIndices = (text: string): string => {
    const parsed = parseLines(text);
    return parsed.map(p => {
        if (!p.original.trim()) return p.original;
        // Reconstruct: Indent + Index + Space + Title + Space + Page
        const indent = ' '.repeat(p.level * 4);
        return `${indent}${p.computedIndex} ${p.title} ${p.page}`;
    }).join('\n');
};

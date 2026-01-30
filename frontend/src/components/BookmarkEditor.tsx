
import React, { useState, useRef } from 'react';
import { Indent, Outdent, Eye, Edit } from 'lucide-react';
import { t } from '../utils/i18n';
import { parseLines, ParsedLine, injectIndices } from '../utils/bookmarkUtils';

interface BookmarkEditorProps {
    value: string;
    onChange: (value: string) => void;
    autoNumbering: boolean; // Used for preview mode
    language: 'en' | 'zh';
}

const BookmarkEditor: React.FC<BookmarkEditorProps> = ({ value, onChange, autoNumbering, language }) => {
    const [viewMode, setViewMode] = useState<'edit' | 'preview'>('edit');
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const backdropRef = useRef<HTMLDivElement>(null);

    // Sync scroll
    const handleScroll = () => {
        if (backdropRef.current && textareaRef.current) {
            backdropRef.current.scrollTop = textareaRef.current.scrollTop;
        }
    };

    const handleIndent = (direction: 'increase' | 'decrease') => {
        if (!textareaRef.current) return;

        const start = textareaRef.current.selectionStart;
        const end = textareaRef.current.selectionEnd;
        const lines = value.split('\n');

        // Find start and end line indices
        let startLineIndex = value.substring(0, start).split('\n').length - 1;
        let endLineIndex = value.substring(0, end).split('\n').length - 1;

        // selectionEnd is at beginning of next line?
        if (value[end - 1] === '\n' && start !== end) {
            endLineIndex--;
        }

        const newLines = lines.map((line, index) => {
            if (index >= startLineIndex && index <= endLineIndex) {
                if (direction === 'increase') {
                    return '    ' + line; // 4 spaces
                } else {
                    return line.replace(/^ {1,4}/, ''); // Remove up to 4 spaces
                }
            }
            return line;
        });

        const newValue = newLines.join('\n');
        onChange(newValue);

        // Restore selection (approximate)
        setTimeout(() => {
            if (textareaRef.current) {
                textareaRef.current.focus();
                textareaRef.current.setSelectionRange(start, end); // Simple restore, ideally adjust for added spaces
            }
        }, 0);
    };

    const renderBackdrop = () => {
        const lines = value.split('\n');
        return lines.map((line, i) => {
            const leadingSpaces = line.match(/^ */)?.[0].length || 0;
            const level = Math.floor(leadingSpaces / 4);
            let bgClass = 'bg-transparent';
            // Subtle pastel colors for levels
            if (level === 0) bgClass = 'bg-gray-50'; // Level 1 (0 indent) - Most prominent? User said Level 1 most significant. 0 indent is root.
            else if (level === 1) bgClass = 'bg-orange-50';
            else if (level === 2) bgClass = 'bg-yellow-50';
            else if (level === 3) bgClass = 'bg-green-50';
            else if (level === 4) bgClass = 'bg-blue-50';
            else if (level === 5) bgClass = 'bg-blue-50';

            return (
                <div key={i} className={`${bgClass} w-full text-transparent px-4 whitespace-pre-wrap min-h-[24px]`}>
                    {line || ' '} {/* Ensure empty lines have height */}
                </div>
            );
        });
    };

    const parsedPreview = viewMode === 'preview' ? parseLines(autoNumbering ? injectIndices(value) : value) : [];

    return (
        <div className="flex flex-col h-full bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            {/* Toolbar */}
            <div className="flex items-center justify-between px-2 py-1 bg-gray-50 border-b border-gray-200">
                <div className="flex items-center space-x-1">
                    <button
                        onClick={() => handleIndent('increase')}
                        className="p-1.5 hover:bg-gray-200 rounded text-gray-600"
                        title={t('editor_indent_increase', language)}
                    >
                        <Indent size={16} />
                    </button>
                    <button
                        onClick={() => handleIndent('decrease')}
                        className="p-1.5 hover:bg-gray-200 rounded text-gray-600"
                        title={t('editor_indent_decrease', language)}
                    >
                        <Outdent size={16} />
                    </button>
                </div>

                <div className="flex items-center space-x-2">
                    <button
                        onClick={() => setViewMode(prev => prev === 'edit' ? 'preview' : 'edit')}
                        className="flex items-center space-x-1 px-2 py-1 hover:bg-gray-200 rounded text-gray-600 text-xs font-medium"
                    >
                        {viewMode === 'edit' ? <Eye size={16} /> : <Edit size={16} />}
                        <span>{viewMode === 'edit' ? t('editor_preview_mode', language) : t('editor_edit_mode', language)}</span>
                    </button>
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 relative overflow-hidden text-sm font-mono">
                {viewMode === 'edit' ? (
                    <>
                        {/* Backdrop for coloring */}
                        <div
                            ref={backdropRef}
                            className="absolute inset-0 pointer-events-none overflow-hidden pb-8 font-mono leading-6"
                            aria-hidden="true"
                        >
                            {renderBackdrop()}
                        </div>

                        {/* Interactive Textarea */}
                        <textarea
                            ref={textareaRef}
                            className="absolute inset-0 w-full h-full bg-transparent p-0 px-0 resize-none outline-none leading-6 font-mono text-gray-800"
                            placeholder={t('dir_text_ph', language)}
                            value={value}
                            onChange={(e) => onChange(e.target.value)}
                            onScroll={handleScroll}
                            spellCheck={false}
                            style={{
                                whiteSpace: 'pre-wrap',
                                overflowY: 'auto',
                                paddingLeft: '0',
                                paddingRight: '0'
                            }}
                        />
                        {/* 
                            Note: textarea default padding vs div padding must match exactly.
                            We set padding 0 here and use div inside styling or explicit padding-left on both.
                            For simplicity, let's remove padding on textarea and rely on the rendered lines matching.
                            Actually, `px-4` on backdrop divs means textarea needs `pl-4`.
                         */}
                        <style>{`
                            textarea {
                                padding-left: 1rem !important; 
                                padding-right: 1rem !important; 
                            }
                        `}</style>
                    </>
                ) : (
                    // Preview Mode Table
                    <div className="absolute inset-0 w-full h-full overflow-y-auto bg-white p-4">
                        <table className="min-w-full text-xs text-left">
                            <thead className="bg-gray-50 border-b border-gray-100 sticky top-0">
                                <tr>
                                    <th className="py-2 px-2 font-medium text-gray-500 w-16">{t('preview_col_index', language)}</th>
                                    <th className="py-2 px-2 font-medium text-gray-500">{t('preview_col_title', language)}</th>
                                    <th className="py-2 px-2 font-medium text-gray-500 w-16 text-right">{t('preview_col_page', language)}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {parsedPreview.map((row: ParsedLine, i: number) => (
                                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                                        <td className="py-2 px-2 text-gray-400 select-all">{row.computedIndex}</td>
                                        <td className="py-2 px-2 font-medium text-gray-800">{row.title}</td>
                                        <td className="py-2 px-2 text-gray-600 text-right">{row.page}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
            <div className="h-6 bg-gray-50 border-t border-gray-200 text-[10px] text-gray-400 flex items-center px-4">
                {t('dir_text_help', language)}
            </div>
        </div>
    );
};

export default BookmarkEditor;

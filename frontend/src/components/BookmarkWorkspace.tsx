
import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { t } from '../utils/i18n';
import BookmarkEditor from './BookmarkEditor';
import { Config } from './SettingsPanel';
import { FileText, Download } from 'lucide-react';
import { apiUrl, downloadUrl, uploadPdf, waitForTask, type UploadedPdf } from '../utils/api';

interface BookmarkWorkspaceProps {
    language: 'en' | 'zh';
    config: Config | null;
}

import { injectIndices } from '../utils/bookmarkUtils';

const BookmarkWorkspace: React.FC<BookmarkWorkspaceProps> = ({ language, config }) => {
    const [file, setFile] = useState<File | null>(null);
    const [tocText, setTocText] = useState('');
    const [offset, setOffset] = useState(0);
    const [isProcessing, setIsProcessing] = useState(false);
    const [logs, setLogs] = useState<string[]>([]);
    const [autoNumbering, setAutoNumbering] = useState(false);
    const [serverFile, setServerFile] = useState<UploadedPdf | null>(null);
    const [resultUrl, setResultUrl] = useState<string | null>(null);

    // VLM Range State
    const [vlmStart, setVlmStart] = useState<string>('');
    const [vlmEnd, setVlmEnd] = useState<string>('');

    const onDrop = async (acceptedFiles: File[]) => {
        if (acceptedFiles.length > 0) {
            const selectedFile = acceptedFiles[0];

            // Explicit check even though Dropzone filters
            if (selectedFile.type !== 'application/pdf' && !selectedFile.name.toLowerCase().endsWith('.pdf')) {
                setLogs(prev => [...prev, `${t('log_error', language)} Invalid file format. PDF only.`]);
                return;
            }

            setFile(selectedFile);
            setServerFile(null);
            setResultUrl(null);
            setTocText(''); // Clear previous text immediately
            setLogs(prev => [...prev, `${t('log_file_loaded', language)}${selectedFile.name}`]);

            // Auto-extract bookmarks
            try {
                setLogs(prev => [...prev, t('uploading', language)]);
                const uploaded = await uploadPdf(selectedFile);
                setServerFile(uploaded);

                setLogs(prev => [...prev, t('log_extracting', language)]);
                const response = await fetch(apiUrl('/api/bookmarks/extract'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ input_path: uploaded.path })
                });

                if (!response.ok) throw new Error(response.statusText);

                const data = await response.json();
                if (data.status === 'success' && data.toc_text) {
                    setTocText(data.toc_text);
                    setLogs(prev => [...prev, t('log_extract_success', language)]);
                } else {
                    setLogs(prev => [...prev, t('log_no_bookmarks', language)]);
                }
            } catch (error) {
                console.error(error);
                setLogs(prev => [...prev, `${t('log_extract_fail', language)}${error}`]);
            }
        }
    };

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'application/pdf': ['.pdf']
        },
        maxFiles: 1
    });

    const handleStart = async () => {
        if (!file) return;

        setIsProcessing(true);
        setResultUrl(null);
        setLogs(prev => [...prev, t('log_task_start', language)]);

        try {
            const source = serverFile || await uploadPdf(file);
            if (!serverFile) setServerFile(source);

            // Optional: Inject indices if auto-numbering is enabled
            let finalTocText = tocText;
            if (autoNumbering) {
                finalTocText = injectIndices(tocText);
                setLogs(prev => [...prev, 'Auto-numbering applied to bookmarks.']);
            }

            const response = await fetch(apiUrl('/api/bookmarks/add'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    input_path: source.path,
                    toc_text: finalTocText,
                    page_offset: offset
                })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || `API Error: ${response.statusText}`);

            const task = await waitForTask(data.task_id);
            if (task.download_url) {
                setResultUrl(task.download_url);
            }
            setLogs(prev => [...prev, t('log_task_success', language)]);
        } catch (error) {
            console.error(error);
            setLogs(prev => [...prev, `${t('log_error', language)}${error}`]);
        } finally {
            setIsProcessing(false);
        }
    };

    // --- AI Logic ---

    const log = (msg: string) => setLogs(prev => [...prev, msg]);

    const handleClipboardRec = async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (!text || !text.trim()) {
                log('Clipboard is empty.');
                return;
            }

            log('Sending clipboard text to LLM for cleaning...');
            setIsProcessing(true);

            // Get LLM Config
            const llmConfig = config?.bookmark_models?.llm;
            if (!llmConfig?.enabled) {
                log('Error: LLM model is not enabled in settings.');
                setIsProcessing(false);
                return;
            }

            const response = await fetch(apiUrl('/api/bookmarks/clean_text'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    config: llmConfig
                })
            });

            const data = await response.json();
            if (response.ok && data.status === 'success') {
                setTocText(data.text);
                log('Clipboard text cleaned and inserted.');
            } else {
                throw new Error(data.detail || response.statusText);
            }

        } catch (error) {
            log(`Clipboard Rec Failed: ${error}`);
        } finally {
            setIsProcessing(false);
        }
    };

    const handleVLMRec = async () => {
        if (!file) {
            log('Please upload a PDF file first.');
            return;
        }

        const start = parseInt(vlmStart);
        const end = parseInt(vlmEnd);

        if (isNaN(start) || isNaN(end) || start < 1 || end < start) {
            log('Invalid page range for VLM.');
            return;
        }

        // Get VLM Config
        const vlmConfig = config?.bookmark_models?.vlm;
        if (!vlmConfig?.enabled) {
            log('Error: VLM model is not enabled in settings.');
            return;
        }

        log(`Sending pages ${start}-${end} to VLM...`);
        setIsProcessing(true);

        try {
            const source = serverFile || await uploadPdf(file);
            if (!serverFile) setServerFile(source);

            const response = await fetch(apiUrl('/api/bookmarks/ocr_page'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    input_path: source.path,
                    start_page: start,
                    end_page: end,
                    config: vlmConfig
                })
            });

            const data = await response.json();
            if (response.ok && data.status === 'success') {
                // Ensure we handle markdown code blocks if VLM returns them
                let raw = data.text;
                // Basic cleanup for ```json ... ```
                raw = raw.replace(/^```json/g, '').replace(/^```/g, '').replace(/```$/g, '').trim();

                setTocText(raw);
                log('VLM recognition completed.');
            } else {
                throw new Error(data.detail || response.statusText);
            }
        } catch (error) {
            log(`VLM Rec Failed: ${error}`);
        } finally {
            setIsProcessing(false);
        }
    };

    return (
        <div className="flex flex-col h-full space-y-4">
            {/* Header */}
            <h1 className="text-2xl font-bold mb-2 text-gray-800 tracking-tight">
                {t('sidebar_bookmark', language)}
            </h1>

            {/* Main Content Split: Left (Editor) - Right (Source/Controls/Logs) */}
            <div className="flex-1 flex space-x-4 min-h-0">

                {/* Left: Bookmark Editor */}
                <div className="w-1/2 flex flex-col min-h-0">
                    <BookmarkEditor
                        value={tocText}
                        onChange={setTocText}
                        autoNumbering={autoNumbering}
                        language={language}
                    />
                </div>

                {/* Right: Source, Controls, Logs */}
                <div className="w-1/2 flex flex-col space-y-4 min-h-0">

                    {/* 1. Source File */}
                    <div className="flex-1 bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex flex-col justify-center min-h-0">
                        {/* Redundant label removed */}
                        <div {...getRootProps()} className="flex items-center justify-center w-full flex-1 min-h-0">
                            <div className={`flex flex-col items-center justify-center w-full h-full border-2 border-dashed rounded-lg cursor-pointer transition-colors ${isDragActive ? 'border-purple-500 bg-purple-50' : 'border-gray-300 bg-gray-50 hover:bg-gray-100'}`}>
                                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                                    <input {...getInputProps()} className="hidden" />
                                    {file ? (
                                        <div className="text-center">
                                            <p className="text-sm font-medium text-purple-600 truncate max-w-xs">{file.name}</p>
                                            <p className="text-xs text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                                        </div>
                                    ) : (
                                        <>
                                            <p className="mb-2 text-sm text-gray-500 text-center"><span className="font-semibold">{t('click_to_upload', language)}</span> {t('bookmark_drag_drop_desc', language)}</p>
                                            <p className="text-xs text-gray-500">{t('max_file_size', language)}</p>
                                        </>
                                    )}
                                </div>
                            </div>
                        </div>
                        {file && (
                            <div className="mt-2 text-sm text-green-600 font-medium flex items-center bg-green-50 p-2 rounded border border-green-200">
                                <FileText size={16} className="mr-2" />
                                {t('file_selected', language)}: {file.name}
                                {serverFile && <span className="ml-2 text-xs text-gray-500">{t('upload_ready', language)}</span>}
                            </div>
                        )}
                    </div>

                    {/* 2. Controls */}
                    <div className="flex-none bg-white p-4 rounded-lg shadow-sm border border-gray-200 flex flex-col space-y-3">

                        {/* Row 1: Page Offset */}
                        <div className="flex items-center justify-between h-9">
                            <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
                                {t('page_offset_label', language)}
                            </label>
                            <div className="flex items-center space-x-2">
                                <input
                                    type="number"
                                    value={offset}
                                    onChange={(e) => setOffset(parseInt(e.target.value) || 0)}
                                    className="block w-24 h-8 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-1 border text-center"
                                />
                                <span className="text-xs text-gray-400">
                                    {t('page_offset_help', language)}
                                </span>
                            </div>
                        </div>

                        {/* Row 2: Dir OCR (VLM) */}
                        <div className="flex items-center space-x-2 h-9">
                            <span className="text-sm font-medium text-gray-900 whitespace-nowrap w-24">{t('dir_ocr_label', language)}</span>
                            <div className="flex-1 flex items-center space-x-2">
                                <input
                                    placeholder="Start"
                                    value={vlmStart}
                                    onChange={(e) => setVlmStart(e.target.value)}
                                    className="block w-full h-8 rounded border-gray-300 sm:text-xs p-1 border text-center"
                                />
                                <span className="text-gray-400">-</span>
                                <input
                                    placeholder="End"
                                    value={vlmEnd}
                                    onChange={(e) => setVlmEnd(e.target.value)}
                                    className="block w-full h-8 rounded border-gray-300 sm:text-xs p-1 border text-center"
                                />
                            </div>
                            <button
                                onClick={handleVLMRec}
                                disabled={isProcessing}
                                className="px-3 h-8 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition-colors shadow-sm whitespace-nowrap disabled:bg-gray-400 disabled:cursor-not-allowed"
                            >
                                {t('btn_confirm', language)}
                            </button>
                        </div>

                        {/* Row 3: Actions (Clip Rec | Auto-Num) */}
                        <div className="grid grid-cols-2 gap-3 h-9">
                            <button
                                onClick={handleClipboardRec}
                                disabled={isProcessing}
                                className="flex items-center justify-center h-8 px-3 bg-white text-gray-700 text-xs font-medium rounded border border-gray-300 hover:bg-gray-50 transition-colors shadow-sm disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400"
                            >
                                {t('btn_clip_rec', language)}
                            </button>

                            <button
                                onClick={() => setAutoNumbering(!autoNumbering)}
                                className={`flex items-center justify-center h-8 px-3 rounded text-xs font-medium border transition-colors shadow-sm space-x-2 ${autoNumbering
                                    ? 'bg-blue-100 text-blue-700 border-blue-200'
                                    : 'bg-white text-gray-500 border-gray-300 hover:bg-gray-50'
                                    }`}
                                title={t('lbl_auto_numbering', language)}
                            >
                                <span>{t('lbl_auto_numbering', language)}</span>
                                <span>{autoNumbering ? 'ON' : 'OFF'}</span>
                            </button>
                        </div>

                        {/* Row 4: Add Bookmarks */}
                        <button
                            onClick={handleStart}
                            disabled={!file || !serverFile || isProcessing || !tocText.trim()}
                            className={`
                                w-full h-9 rounded-lg shadow-sm text-sm font-medium text-white transition-all
                                ${(!file || !serverFile || isProcessing || !tocText.trim())
                                    ? 'bg-gray-300 cursor-not-allowed'
                                    : 'bg-blue-600 hover:bg-blue-700 hover:shadow-md'
                                }
                            `}
                        >
                            {isProcessing ? t('btn_processing', language) : t('btn_add_bookmarks', language)}
                        </button>

                        {resultUrl && (
                            <a
                                href={downloadUrl(resultUrl) || '#'}
                                className="inline-flex items-center justify-center h-9 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 transition-colors"
                            >
                                <Download size={16} className="mr-2" />
                                {t('download_result', language)}
                            </a>
                        )}
                    </div>

                    {/* 3. Logs */}
                    <div className="flex-1 bg-gray-900 rounded-lg shadow-inner p-4 overflow-y-auto font-mono text-xs text-green-400 min-h-0">
                        {logs.length === 0 ? (
                            <span className="text-gray-600">{t('log_wait', language)}</span>
                        ) : (
                            logs.map((log, i) => (
                                <div key={i} className="mb-1">
                                    <span className="text-gray-500">[{new Date().toLocaleTimeString()}]</span> {log}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default BookmarkWorkspace;

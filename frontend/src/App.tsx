import { useState, useEffect, useCallback } from 'react'
import { t, Language } from './utils/i18n';
import { EngineSelector } from './components/EngineSelector'
import { SettingsPanel, BookmarkAISettingsPanel, Config } from './components/SettingsPanel';
import { ProgressBar } from './components/ProgressBar'
import BookmarkWorkspace from './components/BookmarkWorkspace'
import { apiUrl, downloadUrl, uploadPdf, type UploadedPdf, type TaskStatus } from './utils/api';
import { FileText, Play, Settings, Globe, Bookmark, Download } from 'lucide-react';

function App() {
    const [activeView, setActiveView] = useState<'workspace' | 'settings' | 'bookmark'>('workspace');
    const [selectedEngine, setSelectedEngine] = useState('tesseract');
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [uploadedPdf, setUploadedPdf] = useState<UploadedPdf | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
    const [taskResult, setTaskResult] = useState<TaskStatus | null>(null);
    const [config, setConfig] = useState<Config | null>(null);
    const [docLanguage, setDocLanguage] = useState(''); // Per-task language
    const [ocrMode, setOcrMode] = useState<'normal' | 'force' | 'skip'>('normal');
    const [deskew, setDeskew] = useState(false);
    const [optimize, setOptimize] = useState(true);

    // Load config on mount
    useEffect(() => {
        fetch(apiUrl('/api/config'))
            .then(res => res.json())
            .then(data => {
                setConfig(data);
                setSelectedEngine(data.selected_engine || 'tesseract');
            })
            .catch(err => console.error("Failed to load config:", err));
    }, []);

    const handleSaveConfig = async (configToSave: Config | null = config) => {
        if (!configToSave) return;
        try {
            await fetch(apiUrl('/api/config'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(configToSave)
            });
            // We only alert on explicit saves, not auto-saves
        } catch (error) {
            console.error("Failed to save config:", error);
            alert(t('alert_config_failed', language));
        }
    };

    const handleExplicitSave = () => {
        handleSaveConfig().then(() => alert(t('alert_config_saved', language)));
    };

    // Derived state for language
    const language: Language = (config?.app_settings?.language as Language) || 'en';

    const handleLanguageChange = (lang: Language) => {
        if (!config) return;
        const newConfig = { ...config };
        if (!newConfig.app_settings) newConfig.app_settings = { language: 'en' };
        newConfig.app_settings.language = lang;
        setConfig(newConfig);
        handleSaveConfig(newConfig); // Auto-save global settings
    };

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files.length > 0) {
            const file = event.target.files[0];
            if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
                alert(t('alert_no_path', language));
                return;
            }
            setSelectedFile(file);
            setUploadedPdf(null);
            setTaskResult(null);
            setCurrentTaskId(null);
            setIsUploading(true);

            try {
                const uploaded = await uploadPdf(file);
                setUploadedPdf(uploaded);
            } catch (error) {
                console.error("Failed to upload PDF:", error);
                alert(t('alert_upload_failed', language));
                setSelectedFile(null);
            } finally {
                setIsUploading(false);
            }
        }
    };

    const handleStartOCR = async () => {
        if (!selectedFile) return;

        setIsProcessing(true);
        setCurrentTaskId(null);
        setTaskResult(null);

        try {
            const source = uploadedPdf || await uploadPdf(selectedFile);
            if (!uploadedPdf) setUploadedPdf(source);

            const response = await fetch(apiUrl('/api/ocr'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    input_path: source.path,
                    engine: selectedEngine,
                    language: docLanguage || undefined,
                    ocr_mode: ocrMode,
                    deskew: deskew,
                    optimize: optimize ? 1 : 0
                })
            });

            const data = await response.json();
            console.log("OCR Started:", data);
            if (!response.ok) {
                throw new Error(data.detail || response.statusText);
            }
            setCurrentTaskId(data.task_id);

        } catch (error) {
            console.error("Failed to start OCR:", error);
            alert(t('alert_ocr_failed', language));
            setIsProcessing(false);
        }
    };

    const handleTaskComplete = useCallback((task: TaskStatus) => {
        setTaskResult(task);
        setIsProcessing(false);
    }, []);

    const handleTaskError = useCallback((message: string) => {
        alert(message);
        setIsProcessing(false);
    }, []);

    return (
        <div className="flex h-screen bg-gray-100 text-gray-800 font-sans">
            {/* Sidebar */}
            <div className="w-64 bg-white border-r border-gray-200 flex flex-col justify-between">
                <div>
                    <div className="p-4 border-b border-gray-100 flex items-center space-x-2">
                        <div className="w-8 h-8 bg-blue-600 rounded-md flex items-center justify-center text-white font-bold text-sm">PDF</div>
                        <span className="font-bold text-lg text-gray-700">Toolbox</span>
                    </div>

                    <nav className="flex-1 p-4 space-y-1">
                        <div
                            onClick={() => setActiveView('workspace')}
                            className={`flex items-center space-x-2 px-3 py-2 rounded-md font-medium cursor-pointer transition-colors ${activeView === 'workspace' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}
                        >
                            <FileText size={18} />
                            <span>{t('sidebar_ocr', language)}</span>
                        </div>
                        <div
                            onClick={() => setActiveView('bookmark')}
                            className={`flex items-center space-x-2 px-3 py-2 rounded-md font-medium cursor-pointer transition-colors ${activeView === 'bookmark' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}
                        >
                            <Bookmark size={18} />
                            <span>{t('sidebar_bookmark', language)}</span>
                        </div>
                    </nav>
                </div>

                {/* Bottom Settings */}
                <div className="p-4 border-t border-gray-100">
                    <div
                        onClick={() => setActiveView('settings')}
                        className={`flex items-center space-x-2 px-3 py-2 rounded-md font-medium cursor-pointer transition-colors ${activeView === 'settings' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}
                    >
                        <Settings size={18} />
                        <span>{t('sidebar_settings', language)}</span>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <main className="flex-1 p-8 overflow-y-auto">
                {activeView === 'workspace' && (
                    <>
                        <h1 className="text-2xl font-bold mb-6 text-gray-800">{t('workspace_title', language)}</h1>

                        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 max-w-3xl">
                            {/* File Selection */}
                            <div className="mb-8">
                                <label className="block text-sm font-medium text-gray-700 mb-2">{t('source_pdf', language)}</label>
                                <div className="flex items-center justify-center w-full">
                                    <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100 transition-colors">
                                        <div className="flex flex-col items-center justify-center pt-5 pb-6">
                                            <p className="mb-2 text-sm text-gray-500"><span className="font-semibold">{t('click_to_upload', language)}</span> {t('drag_drop', language)}</p>
                                            <p className="text-xs text-gray-500">{t('max_file_size', language)}</p>
                                        </div>
                                        <input type="file" className="hidden" accept=".pdf" onChange={handleFileChange} />
                                    </label>
                                </div>
                                {selectedFile && (
                                    <div className="mt-2 text-sm text-green-600 font-medium flex items-center bg-green-50 p-2 rounded border border-green-200">
                                        <FileText size={16} className="mr-2" />
                                        {t('file_selected', language)}: {selectedFile.name}
                                        {isUploading && <span className="ml-2 text-xs text-gray-500">{t('uploading', language)}</span>}
                                        {uploadedPdf && <span className="ml-2 text-xs text-gray-500">{t('upload_ready', language)}</span>}
                                    </div>
                                )}
                            </div>

                            {/* Configuration */}
                            <div className="grid grid-cols-1 gap-6 mb-8">
                                <div className="space-y-4">
                                    <EngineSelector selectedEngine={selectedEngine} language={language} onSelect={setSelectedEngine} />

                                    {/* Task-specific language for MinerU Pipeline */}
                                    {selectedEngine === 'mineru' && config?.engines?.mineru?.api?.model === 'pipeline' && (
                                        <div className="bg-blue-50 p-3 rounded-lg border border-blue-100 animate-in fade-in slide-in-from-top-2 duration-300">
                                            <label className="block text-xs font-bold text-blue-700 mb-1 uppercase tracking-wider">
                                                {t('doc_lang_label', language)}
                                            </label>
                                            <input
                                                type="text"
                                                placeholder={t('doc_lang_ph', language)}
                                                value={docLanguage}
                                                onChange={(e) => setDocLanguage(e.target.value)}
                                                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border bg-white"
                                            />
                                        </div>
                                    )}

                                    {/* Global Image Optimization Toggles */}
                                    <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                                        <h3 className="text-xs font-bold text-gray-500 mb-3 uppercase tracking-wider flex items-center">
                                            {t('ocr_mode_label', language)}
                                        </h3>
                                        <div className="grid grid-cols-3 gap-2 mb-4">
                                            {(['normal', 'force', 'skip'] as const).map(mode => (
                                                <button
                                                    key={mode}
                                                    type="button"
                                                    onClick={() => setOcrMode(mode)}
                                                    className={`px-3 py-2 rounded-md border text-xs font-medium transition-colors ${ocrMode === mode
                                                        ? 'bg-blue-600 text-white border-blue-600'
                                                        : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                                                        }`}
                                                    title={t(`ocr_mode_${mode}_tip`, language)}
                                                >
                                                    {t(`ocr_mode_${mode}`, language)}
                                                </button>
                                            ))}
                                        </div>

                                        <h3 className="text-xs font-bold text-gray-500 mb-3 uppercase tracking-wider flex items-center">
                                            {t('global_img_opts', language)}
                                        </h3>
                                        <div className="flex space-x-6">
                                            <label className="flex items-center cursor-pointer group">
                                                <input
                                                    type="checkbox"
                                                    checked={deskew}
                                                    onChange={(e) => setDeskew(e.target.checked)}
                                                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                                />
                                                <span className="ml-2 text-sm text-gray-700 font-medium group-hover:text-blue-600 transition-colors">
                                                    {t('global_deskew', language)}
                                                </span>
                                                <span className="ml-1 cursor-help text-gray-400 group-hover:text-blue-400" title={t('tip_global_deskew', language)}>ⓘ</span>
                                            </label>

                                            <label className="flex items-center cursor-pointer group">
                                                <input
                                                    type="checkbox"
                                                    checked={optimize}
                                                    onChange={(e) => setOptimize(e.target.checked)}
                                                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                                />
                                                <span className="ml-2 text-sm text-gray-700 font-medium group-hover:text-blue-600 transition-colors">
                                                    {t('global_optimize', language)}
                                                </span>
                                                <span className="ml-1 cursor-help text-gray-400 group-hover:text-blue-400" title={t('tip_global_optimize', language)}>ⓘ</span>
                                            </label>
                                        </div>
                                    </div>

                                    <p className="text-xs text-gray-400 mt-2 text-right">
                                        {t('config_engine_desc', language)}
                                    </p>
                                </div>
                            </div>

                            {/* Action */}
                            <div className="flex items-center justify-end border-t pt-6">
                                <button
                                    onClick={handleStartOCR}
                                    disabled={!selectedFile || !uploadedPdf || isUploading || isProcessing}
                                    className={`flex items-center px-6 py-2.5 rounded-lg text-white font-medium transition-colors focus:ring-4 focus:ring-blue-200 ${!selectedFile || !uploadedPdf || isUploading || isProcessing ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
                                        }`}
                                >
                                    <Play size={18} className="mr-2" />
                                    {isUploading ? t('uploading', language) : isProcessing ? t('btn_processing', language) : t('btn_start_ocr', language)}
                                </button>
                            </div>

                            {/* Progress */}
                            {isProcessing && (
                                <ProgressBar
                                    taskId={currentTaskId}
                                    onComplete={handleTaskComplete}
                                    onError={handleTaskError}
                                />
                            )}

                            {taskResult?.download_url && (
                                <div className="mt-4 flex justify-end">
                                    <a
                                        href={downloadUrl(taskResult.download_url) || '#'}
                                        className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium bg-green-600 text-white hover:bg-green-700 transition-colors"
                                    >
                                        <Download size={16} className="mr-2" />
                                        {t('download_result', language)}
                                    </a>
                                </div>
                            )}
                        </div>
                    </>
                )}

                {activeView === 'bookmark' && (
                    <BookmarkWorkspace language={language} config={config} />
                )}

                {activeView === 'settings' && (
                    <div className="max-w-3xl space-y-6">
                        {/* 1. General Settings Card */}
                        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                            <h2 className="text-lg font-medium text-gray-900 flex items-center mb-4">
                                <Globe size={20} className="mr-2 text-blue-500" />
                                {t('general_settings', language)}
                            </h2>
                            <div className="flex items-center space-x-4">
                                <label className="text-sm font-medium text-gray-700">{t('language', language)}</label>
                                <div className="flex space-x-2">
                                    <button
                                        onClick={() => handleLanguageChange('en')}
                                        className={`px-3 py-1.5 rounded text-xs font-medium border transition-colors ${language === 'en' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'}`}
                                    >
                                        English
                                    </button>
                                    <button
                                        onClick={() => handleLanguageChange('zh')}
                                        className={`px-3 py-1.5 rounded text-xs font-medium border transition-colors ${language === 'zh' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'}`}
                                    >
                                        简体中文
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* 2. OCR Engine Config Card (Wrapper) */}
                        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                            <div className="mb-4">
                                <h2 className="text-lg font-medium text-gray-900">{t('engine_config', language)}</h2>
                                <p className="text-sm text-gray-500 mt-1">{t('engine_config_desc', language)}</p>
                            </div>

                            {/* Engine Selectors (Horizontal Tabs) */}
                            <div className="border-b border-gray-200 mb-4 flex space-x-4">
                                {['tesseract', 'paddle', 'deepseek', 'mineru'].map(engine => (
                                    <button
                                        key={engine}
                                        onClick={() => {
                                            if (config) {
                                                const newConfig = { ...config, selected_engine: engine };
                                                setConfig(newConfig);
                                            }
                                        }}
                                        className={`pb-2 text-sm font-medium border-b-2 transition-colors capitalize ${config?.selected_engine === engine ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
                                    >
                                        {engine}
                                    </button>
                                ))}
                            </div>

                            <SettingsPanel
                                selectedEngine={config?.selected_engine || 'tesseract'}
                                config={config}
                                language={language}
                                onConfigChange={setConfig}
                                onSave={handleExplicitSave}
                            />
                        </div>

                        {/* 3. Bookmark AI Settings Card */}
                        <BookmarkAISettingsPanel
                            config={config}
                            language={language}
                            onConfigChange={setConfig}
                            onSave={handleExplicitSave}
                        />
                    </div>
                )}
            </main>
        </div>
    );
};

export default App;

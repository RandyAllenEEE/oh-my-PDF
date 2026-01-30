import { t, Language } from '../utils/i18n';

interface EngineSelectorProps {
    selectedEngine: string;
    language: Language;
    onSelect: (engine: string) => void;
}

const ENGINES = [
    { id: 'tesseract', name: 'Tesseract' },
    { id: 'paddle', name: 'PaddleOCR' },
    { id: 'deepseek', name: 'DeepSeek-OCR' },
    { id: 'mineru', name: 'MinerU' },
];

export const EngineSelector: React.FC<EngineSelectorProps> = ({ selectedEngine, language, onSelect }) => {
    return (
        <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('label_ocr_engine', language)}</label>
            <select
                value={selectedEngine}
                onChange={(e) => onSelect(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
            >
                {ENGINES.map((engine) => (
                    <option key={engine.id} value={engine.id}>
                        {engine.name}
                    </option>
                ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">
                {t('desc_ocr_engine', language)}
            </p>
        </div>
    );
};

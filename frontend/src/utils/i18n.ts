
type Translations = {
    [key: string]: {
        en: string;
        zh: string;
    };
};

const translations: Translations = {
    // Sidebar & Navigation
    // Sidebar & Navigation
    'sidebar_ocr': { en: 'OCR Workspace', zh: 'OCR制作双层PDF' },
    'sidebar_bookmark': { en: 'PDF Directory', zh: 'PDF 目录编辑' },
    'sidebar_settings': { en: 'Settings', zh: '全局设置' },

    // Workspace View
    'workspace_title': { en: 'OCR Workspace', zh: 'OCR制作双层PDF' },
    'source_pdf': { en: 'Source PDF', zh: '源文件 (PDF)' },
    'click_to_upload': { en: 'Click to upload', zh: '点击上传' },
    'drag_drop': { en: 'or drag and drop', zh: '或拖拽文件到此处' },
    'max_file_size': { en: 'Supported format: PDF only', zh: '仅支持 PDF 文件' },
    'file_selected': { en: 'Selected', zh: '已选择' },
    'config_engine_desc': { en: 'Configure engine settings in the Settings tab.', zh: '在“设置”选项卡中配置引擎参数。' },
    'btn_start_ocr': { en: 'Start OCR Task', zh: '开始识别' },
    'btn_processing': { en: 'Processing...', zh: '处理中...' },

    // Bookmark Workspace
    'bookmark_title': { en: 'PDF Directory Editor', zh: 'PDF 目录编辑' },
    'bookmark_drag_drop_desc': { en: 'or drag and drop to extract existing bookmarks', zh: '或拖拽文件以提取现有目录' },
    'dir_text_label': { en: 'Directory Text (TOC)', zh: '目录文本 (TOC)' },
    'dir_text_ph': { en: "Introduction 1\nChapter 1 The Beginning 5\nChapter 2 The Middle 20", zh: "前言 1\n第一章 开始 5\n第二章 经过 20" },
    'dir_text_help': { en: 'Copy text here. Use indentation for hierarchy.', zh: '在此粘贴文本。使用缩进来控制层级。' },
    'page_offset_label': { en: 'Page Offset', zh: '页码偏移' },
    'page_offset_help': { en: '(Final Page = Text Page + Offset)', zh: '(写入页码 = 文本页码 + 偏移量)' },
    'btn_add_bookmarks': { en: 'Add Bookmarks', zh: '添加目录' },
    'log_file_loaded': { en: 'File loaded: ', zh: '文件已加载: ' },
    'log_extracting': { en: 'Extracting existing bookmarks...', zh: '正在提取现有目录...' },
    'log_extract_success': { en: 'Bookmarks extracted successfully.', zh: '现有目录提取成功。' },
    'log_no_bookmarks': { en: 'No existing bookmarks found.', zh: '未发现现有目录。' },
    'log_extract_fail': { en: 'Extraction failed: ', zh: '提取失败: ' },
    'log_task_start': { en: 'Starting Bookmark Task...', zh: '开始添加目录...' },
    'log_task_success': { en: 'Task started successfully! Check source folder for _new.pdf', zh: '任务已启动！查看源文件夹中的 _new.pdf' },
    'log_error': { en: 'Error: ', zh: '错误: ' },
    'log_wait': { en: 'Waiting for actions...', zh: '等待操作...' },

    // Editor Toolbar
    'editor_indent_increase': { en: 'Increase Indent', zh: '增加缩进' },
    'editor_indent_decrease': { en: 'Decrease Indent', zh: '减少缩进' },
    'editor_preview_mode': { en: 'Preview Mode', zh: '预览模式' },
    'editor_edit_mode': { en: 'Edit Mode', zh: '编辑模式' },
    'preview_col_index': { en: 'Index', zh: '序号' },
    'preview_col_title': { en: 'Title', zh: '标题' },
    'preview_col_page': { en: 'Page', zh: '页码' },
    'btn_write_indices': { en: 'Write Indices', zh: '写入序号' },
    'lbl_auto_numbering': { en: 'Auto Numbering', zh: '自动编号' },
    'op_write_indices_success': { en: 'Indices written to text.', zh: '序号已写入文本。' },

    // Bookmark AI
    'bookmark_ai_settings': { en: 'Bookmark AI Settings', zh: '书签 AI 设置' },
    'bookmark_ai_desc': { en: 'Configure VLM for visual TOC extraction and LLM for text cleaning.', zh: '配置用于视觉目录提取的 VLM 和用于文本清洗的 LLM。' },
    'tab_vlm': { en: 'Visual Extraction (PDF)', zh: '视觉提取 (PDF)' },
    'tab_llm': { en: 'Text Cleaning', zh: '文本清洗' },
    'enable_feature': { en: 'Enable Feature', zh: '启用此功能' },
    // 'model_name': reused from below
    'prompt_template': { en: 'Prompt Template', zh: '提示词模板' },
    'prompt_tip': { en: 'Use default if unsure. Ensure output format matches editor requirements.', zh: '不确定请使用默认值。确保输出格式符合编辑器要求。' },
    'dir_ocr_label': { en: 'Directory OCR', zh: '目录 OCR 识别' },
    'btn_confirm': { en: 'Confirm', zh: '识别确认' },
    'btn_clip_rec': { en: 'Clipboard Rec', zh: '识别剪切板目录文字' },

    // Engine Selector
    'label_ocr_engine': { en: 'OCR Engine', zh: 'OCR 引擎' },
    'desc_ocr_engine': { en: 'Select the OCR engine to use for processing.', zh: '选择用于处理的 OCR 引擎。' },

    // General Sections
    'general_settings': { en: 'General Settings', zh: '通用设置' },
    'language': { en: 'Display Language', zh: '显示语言' },
    'engine_config': { en: 'Engine Configuration', zh: 'OCR 引擎配置' },
    'engine_config_desc': { en: 'Configure global settings for each OCR engine.', zh: '配置各个 OCR 引擎的全局参数。' },
    'config_title': { en: 'Configuration', zh: '配置' },
    'save_changes': { en: 'Save Changes', zh: '保存更改' },
    'global_optimize': { en: 'Optimize PDF', zh: '图像压缩' },
    'global_deskew': { en: 'Deskew Pages', zh: '自动纠偏' },
    'global_img_opts': { en: 'Image Optimization', zh: '图像优化' },

    // Provider Strategy
    'provider_strategy': { en: 'Provider Strategy', zh: '服务提供商策略' },
    'prov_paddle_api': { en: 'Paddle Hub / Serving API', zh: 'Paddle Hub / Serving 接口' },
    'prov_ollama': { en: 'Local (Ollama compatible)', zh: '本地 (Ollama 兼容)' },
    'prov_deepseek_ollama': { en: 'Ollama (Local)', zh: 'Ollama (本地)' },
    'prov_mineru_api': { en: 'MinerU Cloud API', zh: 'MinerU 云端接口' },

    // Ollama Fields
    'ollama_settings': { en: 'Ollama Settings', zh: 'Ollama 设置' },
    'localhost_url': { en: 'Localhost URL', zh: '本地服务地址' },
    'localhost_url_desc': { en: 'The address where your local Ollama instance is running.', zh: '本地 Ollama 实例运行的地址。' },
    'model_name': { en: 'Model Name', zh: '模型名称' },

    // API Fields
    'api_endpoint': { en: 'API Endpoint URL', zh: 'API 接口地址' },
    'api_key': { en: 'API Key / Token', zh: 'API 密钥 / Token' },
    'global_token': { en: 'Global Access Token', zh: '全局 Access Token' },
    'model_version': { en: 'Model Version', zh: '模型版本' },
    'active_model': { en: 'Active Model', zh: '当前模型' },
    'model_name_id': { en: 'Model Name / ID', zh: '模型名称 / ID' },
    'api_guide': { en: 'API Guide', zh: 'API 使用指南' },

    // Tesseract
    'tesseract_desc': { en: 'Tesseract is a local binary engine. If installed in a non-standard location, specify it below.', zh: 'Tesseract 是本地二进制引擎。如果安装在非标准位置，请在下方指定。' },
    'tesseract_path': { en: 'Tesseract Binary Path', zh: 'Tesseract 主程序路径' },
    'tesseract_path_desc': { en: 'Use the absolute path to the folder containing tesseract.exe, or the exe itself.', zh: '请使用包含 tesseract.exe 的文件夹绝对路径，或直接指向 exe 文件。' },
    'tesseract_langs_label': { en: 'OCR Languages', zh: '识别语言' },
    'tesseract_langs_ph': { en: 'e.g. eng;chi_sim;equ', zh: '例如 eng;chi_sim;equ' },
    'tesseract_langs_help': { en: 'Supports multiple languages separated by semicolon (;). Typical codes: eng, chi_sim, chi_tra, equ.', zh: '支持多个语言，请使用分号 (;) 分线。常见代码：eng, chi_sim, chi_tra, equ。' },

    // Pipeline Options (MinerU)
    'pipeline_options': { en: 'Pipeline Options', zh: 'Pipeline 选项' },
    'force_ocr': { en: 'Force OCR', zh: '强制 OCR' },
    'formulas': { en: 'Formulas', zh: '公式识别' },
    'tables': { en: 'Tables', zh: '表格解析' },
    'secondary_lang': { en: 'Secondary Language', zh: '次要语言' },

    // Paddle Configs
    'orientation_fix': { en: 'Orientation Fix', zh: '方向矫正' },
    'unwarping': { en: 'Unwarping', zh: '扭曲矫正' },
    'textline_fix': { en: 'Textline Fix', zh: '文本行矫正' },
    'table_rec': { en: 'Table Recognition', zh: '表格识别' },
    'formula_rec': { en: 'Formula Recognition', zh: '公式识别' },
    'seal_det': { en: 'Seal Detection', zh: '印章检测' },
    'chart_rec': { en: 'Chart Recognition', zh: '图表识别' },
    'layout_analysis': { en: 'Layout Analysis', zh: '版面分析' },
    'repetition_penalty': { en: 'Repetition Penalty', zh: '重复抑制' },
    'temperature': { en: 'Temperature', zh: '温度' },

    // Tooltips
    'tip_orientation': { en: 'Correct document rotation angle', zh: '纠正文档旋转角度' },
    'tip_unwarping': { en: 'Correct paper curling or perspective limitation', zh: '纠正纸张弯曲或透视形变' },
    'tip_textline': { en: 'Correct skewed text lines', zh: '修正单行文字倾斜' },
    'tip_table': { en: 'Extract structured table data', zh: '提取表格结构化数据' },
    'tip_formula': { en: 'Recognize math formulas to LaTeX', zh: '识别数学公式并转为 LaTeX' },
    'tip_seal': { en: 'Detect and recognize stamps/seals', zh: '检测并识别公章内容' },
    'tip_chart': { en: 'Recognize charts as table data', zh: '将图表识别为表格数据' },
    'tip_layout': { en: 'Distinguish text, titles, images', zh: '分析版面并区分文字、标题、图片等区域' },
    'tip_rep_penalty': { en: 'Higher value suppresses repetition', zh: '权重越高越能抑制模型复读' },
    'tip_temp': { en: 'Lower value is more deterministic', zh: '控制生成结果的稳健型，数值越低越确定' },
    'tip_force_ocr': { en: 'Force OCR on all pages', zh: '对所有页面强制执行 OCR' },
    'tip_formulas_en': { en: 'Enable formula recognition (LaTeX)', zh: '开启公式识别与 LaTeX 转换' },
    'tip_tables_en': { en: 'Enable high-precision table parsing', zh: '开启表格高精度解析' },
    'tip_sec_lang': { en: 'Primary is Chinese, set secondary here', zh: '主语言默认为中文，在此处设置次要语言' },
    'tip_secure_store': { en: 'Securely stored in config.json', zh: '安全存储在本地 config.json 中' },
    'tip_paddle_token': { en: 'Required for PaddleX cloud models', zh: 'PaddleX/PaddleOCR 云端模型必填项' },
    'tip_global_optimize': { en: 'Compress images to reduce file size (requires pngquant)', zh: '压缩图像以减小文件体积 (需 pngquant)' },
    'tip_global_deskew': { en: 'Straighten crooked scans (requires unpaper)', zh: '自动校正倾斜的扫描页面 (需 unpaper)' },

    // Placeholders & ProTips
    'ph_pipeline': { en: 'Pipeline (Layout analysis + features)', zh: 'Pipeline (版面分析 + 功能开关)' },
    'ph_vlm': { en: 'VLM (High precision model)', zh: 'VLM (高精度视觉语言模型)' },
    'ph_html': { en: 'MinerU-HTML (Specific for HTML files)', zh: 'MinerU-HTML (仅适用于 HTML 源文件)' },
    'ph_sec_lang': { en: 'en (English), etc.', zh: 'en (英语), 等' },
    'ph_model_ollama': { en: 'e.g. deepseek-r1:8b', zh: '例如 deepseek-r1:8b' },
    'ph_model_api': { en: 'e.g. gpt-4o, claude-3', zh: '例如 gpt-4o, claude-3' },
    'protip_vlm': { en: 'ProTip: VLM is recommended for complex documents.', zh: '提示：VLM 推荐用于处理复杂文档。' },
    'protip_pipeline': { en: 'Note: Pipeline supports highest layout accuracy.', zh: '注意：Pipeline 在版面解析精度上表现最好。' },
    'protip_html': { en: 'Important: Use only for .html source files.', zh: '重要：仅适用于 .html 格式的源文件。' },

    // Alerts
    'alert_config_saved': { en: 'Configuration saved successfully!', zh: '设置保存成功！' },
    'alert_config_failed': { en: 'Failed to save configuration.', zh: '保存设置失败。' },
    'alert_no_path': { en: 'Could not get file path. Are you running in browser mode? This app requires Electron.', zh: '无法获取文件路径。请确保在 Electron 环境中运行。' },
    'alert_ocr_failed': { en: 'Failed to start OCR task. Check backend console.', zh: '启动 OCR 任务失败，请检查后端后台。' },

    // MinerU Workplace Specific
    'doc_lang_label': { en: 'Document Language (Pipeline)', zh: '文档语言 (Pipeline)' },
    'doc_lang_ph': { en: 'ch, en, etc.', zh: 'ch, en, 等' },

};

export type Language = 'en' | 'zh';

export const t = (key: string, lang: Language = 'en'): string => {
    const item = translations[key];
    if (!item) return key; // Fallback to key if not found
    return item[lang] || item['en'];
};

# Oh-My-PDF Toolbox

A powerful, modern, and extensible PDF toolbox designed for heavy document workflows. Featuring AI-powered OCR, intelligent bookmark management with grounding, and advanced PDF optimization.

## 🚀 Features

-   **Intelligent OCR**: Powered by `OCRmyPDF`, supporting Tesseract and custom API engines (like PaddleOCR).
    -   Multiple modes: `Normal`, `Force OCR`, and `Skip OCR`.
    -   Support for sidecar HOCR/JSON generation.
-   **AI Bookmark Management**:
    -   **LLM Enrichment**: Use models like `glm-4-flash` to clean and structure table of contents.
    -   **VLM Grounding**: Leverage Vision Language Models (e.g., `deepseek-v3` via Ollama) to recognize text and coordinates directly from PDF pages.
    -   **Fill-back Editor**: Integrated TOC editor with the ability to "fill back" AI-generated bookmarks.
-   **Advanced Optimization**:
    -   Lossy compression using `pngquant`.
    -   Document cleaning and deskewing with `unpaper`.
-   **Modern UI**: Built with React and Tailwind CSS, featuring a responsive layout and dark mode.
-   **Process Management**: Seamlessly manages the local Python worker process within the Electron container.

## 🛠 Technology Stack

-   **Frontend**: Electron, Vite, React, TypeScript, Tailwind CSS.
-   **Backend**: Python 3.10+, FastAPI, PyMuPDF (fitz), OCRmyPDF.
-   **Packaging**:
    -   **Backend**: PyInstaller (Bundled as `pdf-toolbox-server.exe`).
    -   **Frontend**: `electron-builder`.

## 📦 Prerequisites

Before running or building the project, ensure you have the following installed:

1.  **[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)**: Required for the local OCR engine.
2.  **[Ghostscript](https://ghostscript.com/releases/gsdnld.html)**: Required for PDF processing.
3.  **[Ollama](https://ollama.com/)** (Optional): For local AI features (LLM/VLM).
4.  **Python 3.10+** & **Node.js**: For development.

## 🛠 Development Setup

### 1. Backend Setup
```bash
cd backend
poetry install
# Copy and configure your config.json if needed
```

### 2. Frontend Setup
```bash
cd frontend
npm install
```

### 3. Running in Development
-   Start backend: `cd backend && poetry run python src/main.py`
-   Start frontend: `cd frontend && npm run dev`

## 🏗 Build & Packaging

We provide a master build script to automate the entire process:

```bash
python build_all.py
```

The resulting standalone executable will be available in the `release/win-unpacked` directory.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

-   **[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF)** - The engine behind our OCR.
-   **[pdfdir](https://github.com/pdfdir/pdfdir)** - Inspiration for bookmark management.
-   **[Lucide React](https://lucide.dev/)** - For the beautiful icons.

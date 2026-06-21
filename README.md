# Oh-My-PDF Toolbox

A powerful, modern, and extensible PDF toolbox designed for heavy document workflows. Featuring AI-powered OCR, intelligent bookmark management with grounding, and advanced PDF optimization.

Current version: `0.2.0`

## 🚀 Features

-   **Intelligent OCR**: Powered by `OCRmyPDF`, supporting Tesseract and custom API engines such as PaddleOCR, DeepSeek OCR, and MinerU.
    -   Multiple modes: `Normal`, `Force OCR`, and `Skip Text`.
    -   Custom engines are bridged through generated hOCR/JSON so the final PDF keeps searchable text aligned with the original page image.
-   **AI Bookmark Management**:
    -   **LLM Enrichment**: Use models like `glm-4-flash` to clean and structure table of contents.
    -   **VLM Grounding**: Leverage Vision Language Models (e.g., `deepseek-v3` via Ollama) to recognize text and coordinates directly from PDF pages.
    -   **Fill-back Editor**: Integrated TOC editor with the ability to "fill back" AI-generated bookmarks.
-   **Advanced Optimization**:
    -   Lossy compression using `pngquant`.
    -   Document cleaning and deskewing with `unpaper`.
-   **Lightweight Web UI**: Built with Vite, React, TypeScript, and Tailwind CSS. The FastAPI backend can serve the built frontend directly, so Electron is no longer required.
-   **Browser-safe File Flow**: PDFs are uploaded into a local backend workspace and processed outputs are returned through download links.

## 🛠 Technology Stack

-   **Frontend**: Vite, React, TypeScript, Tailwind CSS.
-   **Backend**: Python 3.10+, FastAPI, PyMuPDF (fitz), OCRmyPDF.
-   **Packaging**:
    -   **Backend**: PyInstaller standalone server (`pdf-toolbox-server.exe`).
    -   **Frontend**: Static assets bundled into the backend server.

## 📦 Prerequisites

Before running or building the project, ensure you have the following installed:

1.  **[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)**: Required for the local OCR engine.
2.  **[Ghostscript](https://ghostscript.com/releases/gsdnld.html)**: Required for PDF processing.
3.  **[Ollama](https://ollama.com/)** (Optional): For local AI features (LLM/VLM).
4.  **Python 3.10-3.14 recommended** & **Node.js 20.19+ or 22.12+**: For development and packaging.

Optional API keys/tokens are only needed for cloud features:

-   PaddleOCR API mode: AI Studio access token and model endpoint URL.
-   MinerU API mode: MinerU API key.
-   Bookmark AI with OpenAI-compatible providers: API key and base URL.

## 🛠 Development Setup

### 1. Backend Setup
```bash
cd backend
poetry install
poetry run uvicorn src.main:app --host 127.0.0.1 --port 17654 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

During development, open `http://127.0.0.1:17655`. The Vite dev server
proxies `/api` and `/ws` to the backend at `http://127.0.0.1:17654`.

### 3. Local Web Mode
```bash
cd frontend
npm run build

cd ../backend
poetry run python src/main.py
```

The backend serves the built frontend, opens `http://127.0.0.1:17654`
automatically by default, and stores uploaded PDFs/results in
`backend/workspace/`. If the preferred port is already in use, the packaged
server automatically selects a free local port and opens that actual URL.

Useful environment variables:

- `PDF_TOOLBOX_PORT=18123`: prefer a specific backend port.
- `PDF_TOOLBOX_FRONTEND_PORT=18124`: prefer a specific Vite dev-server port.
- `PDF_TOOLBOX_HOST=127.0.0.1`: bind to a specific local host.
- `PDF_TOOLBOX_NO_BROWSER=1`: disable automatic browser opening during automation.

## ✅ Tests

```powershell
py tests/run_tests.py quick
py tests/run_tests.py local
$env:OH_MY_PDF_RUN_EXTERNAL='1'; py tests/run_tests.py external
```

`quick` runs deterministic backend/frontend tests. `local` adds local
Tesseract/Ghostscript OCR and PDF text-layer alignment checks. `external` uses
the ignored runtime config copied from `release/win-unpacked/config.json` and
calls every configured Paddle model endpoint, the configured DeepSeek/Ollama
model, MinerU API, and bookmark AI modes.

## 🏗 Build & Packaging

The master build script builds the frontend first, then bundles it into the standalone backend server:

```bash
python build_all.py
```

The packaged server is first built at `backend/dist_py/pdf-toolbox-server.exe`,
then synchronized into `release/win-unpacked/pdf-toolbox-server.exe`.
`backend/dependencies` is copied to both `backend/dist_py/dependencies` and the
release folder so bundled `pngquant` and `unpaper` are discoverable next to the
executable. The sync step preserves `release/win-unpacked/config.json`.

See [CHANGELOG.md](CHANGELOG.md) for version history.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

-   **[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF)** - The engine behind our OCR.
-   **[pdfdir](https://github.com/pdfdir/pdfdir)** - Inspiration for bookmark management.
-   **[Lucide React](https://lucide.dev/)** - For the beautiful icons.

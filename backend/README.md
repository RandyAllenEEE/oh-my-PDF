# Oh-My-PDF Backend

The local FastAPI service for Oh-My-PDF Toolbox. It runs OCR/bookmark jobs, stores browser uploads in a local workspace, exposes result downloads, and can serve the built Vite frontend directly.

Current version: `0.2.0`

## Prerequisites (CRITICAL)

This application relies on external OCR engines. You **MUST** install the following dependencies manually before running the application:

### 1. Ghostscript (Required for PDF processing)
- **Windows**: [Download Ghostscript](https://ghostscript.com/releases/gsdnld.html)
- **Linux**: `sudo apt install ghostscript`
- **macOS**: `brew install ghostscript`

### 2. Tesseract OCR (Required for default OCR)
- **Windows**: [Download Tesseract via UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
- **Linux**: `sudo apt install tesseract-ocr`
- **macOS**: `brew install tesseract`

> [!IMPORTANT]
> Ensure that both `gs` (Ghostscript) and `tesseract` are available in your system's `PATH`.

---

## Installation

```bash
# Install dependencies using Poetry
poetry install
```

## Running

```bash
# Start the API server
poetry run uvicorn src.main:app --host 127.0.0.1 --port 17654 --reload
```

After running `npm run build` in `../frontend`, you can also start:

```bash
poetry run python src/main.py
```

This serves the built frontend and opens `http://127.0.0.1:17654`
automatically by default. If the preferred port is occupied, the packaged
server selects a free local port and opens the actual URL.

Useful environment variables:

- `PDF_TOOLBOX_PORT=18123`: prefer a specific backend port.
- `PDF_TOOLBOX_FRONTEND_PORT=18124`: prefer a specific Vite dev-server port.
- `PDF_TOOLBOX_HOST=127.0.0.1`: bind to a specific local host.
- `PDF_TOOLBOX_NO_BROWSER=1`: suppress browser opening in scripts or tests.

Uploaded PDFs and generated outputs are stored in `backend/workspace/`.

The repository-level `py build_all.py` command builds the latest backend
executable and synchronizes it into `../release/win-unpacked` while preserving
the local `config.json`.

## Tests

```bash
poetry run pytest
```

The tests mock OCR execution and do not require Tesseract, Ghostscript, cloud API keys, or Ollama.
The repository-level runner also provides broader suites:

```powershell
py tests/run_tests.py quick
py tests/run_tests.py local
$env:OH_MY_PDF_RUN_EXTERNAL='1'; py tests/run_tests.py external
```

`external` reads the ignored runtime config copied from
`release/win-unpacked/config.json` and validates configured Paddle, DeepSeek,
MinerU, and bookmark AI modes.

## Acknowledgments

This project stands on the shoulders of giants. We express our deepest gratitude to:

*   **@[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF)**: The core engine that powers our PDF processing. Its robust plugin system allowed us to extend functionality seamlessly.
*   **@[pdfdir](https://github.com/pdfdir/pdfdir)**: Inspiring our directory and bookmark management features.

---

## License
See the repository root `LICENSE`.

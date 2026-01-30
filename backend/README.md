# Oh-My-PDF Backend

The backend service for the Oh-My-PDF Toolbox, built with FastAPI and OCRmyPDF.

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
poetry run uvicorn src.main:app --reload
```

## Acknowledgments

This project stands on the shoulders of giants. We express our deepest gratitude to:

*   **@[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF)**: The core engine that powers our PDF processing. Its robust plugin system allowed us to extend functionality seamlessly.
*   **@[pdfdir](https://github.com/pdfdir/pdfdir)**: Inspiring our directory and bookmark management features.

---

## License
[Your License Here]

# Changelog

## 0.2.0 - 2026-06-21

- Migrated the application release path from Electron to a lightweight FastAPI + Vite web UI served by the backend executable.
- Added browser-safe upload/download workspace flow for OCR and bookmark workflows.
- Added OCR modes for Normal, Force OCR, and Skip Text across the backend API and frontend UI.
- Added automatic local browser opening for packaged runs, with `PDF_TOOLBOX_NO_BROWSER=1` for automation.
- Changed default local ports to avoid common development ports: backend `17654`, Vite dev server `17655`, with environment overrides and backend port fallback.
- Added release artifact synchronization into `release/win-unpacked` while preserving local `config.json`.
- Expanded tests for local OCR, custom OCR plugins, PDF text-layer alignment, real configured external OCR/AI modes, release packaging helpers, and frontend API utilities.
- Improved Paddle, DeepSeek OCR, and MinerU hOCR parsing/alignment handling, including MinerU root-level block JSON output.

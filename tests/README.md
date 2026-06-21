# Test Framework

This directory contains the project-level test framework. Test code is tracked;
private configs, PDFs, API responses, OCR outputs, and run reports are not.

## Local Private Files

Ignored paths:

- `tests/local/`
- `tests/results/`
- `tests/artifacts/`
- `tests/fixtures/private/`

The test runner copies `release/win-unpacked/config.json` to
`tests/local/config.runtime.json` when available. Do not commit either file.

## Commands

```powershell
py tests/run_tests.py quick
py tests/run_tests.py local
$env:OH_MY_PDF_RUN_EXTERNAL='1'; py tests/run_tests.py external
$env:OH_MY_PDF_RUN_EXTERNAL='1'; py tests/run_tests.py all
```

`quick` runs deterministic unit/API tests and frontend Vitest tests. `local`
adds local Tesseract/Ghostscript OCR. `external` uses the configured Paddle,
MinerU, Ollama/DeepSeek, and bookmark AI modes from the runtime config.

The local suite also validates double-layer PDF alignment. It generates
deterministic image PDFs, runs each OCR mode path, and checks that the output PDF
keeps the image layer, exposes searchable text, and places each text-layer
rectangle inside the expected page region. Unit tests separately assert the hOCR
bbox conversion for Paddle, DeepSeek, and MinerU inputs.

The external suite repeats the alignment check against real configured OCR
models: every Paddle model endpoint in the config, the configured DeepSeek/Ollama
model, and MinerU API output are each used to create a double-layer PDF whose
searchable text rectangles must land near the source text regions.

External failures should be treated as real diagnostics, not ignored. Common
cases:

- MinerU `401 Unauthorized`: refresh the API key in the release UI/config.
- Bookmark LLM returns empty text: Ollama `thinking` is disabled by default for
  tool calls; if it still happens, verify the configured model is loaded and can
  answer a short prompt outside the app.
- Ollama timeouts: increase `OH_MY_PDF_OLLAMA_TIMEOUT_SEC` and
  `OH_MY_PDF_LLM_TIMEOUT_SEC`.
- MinerU result zip download fails behind a proxy: direct download fallback is
  enabled by default; set `OH_MY_PDF_MINERU_DOWNLOAD_DIRECT_FALLBACK=0` to
  disable it.

Useful overrides:

- `OH_MY_PDF_TEST_CONFIG`: explicit config path.
- `OH_MY_PDF_RUN_EXTERNAL=1`: enable external tests.
- `OH_MY_PDF_OLLAMA_TIMEOUT_SEC=900`: allow slow local VLM/OCR model calls.
- `OH_MY_PDF_LLM_TIMEOUT_SEC=900`: allow slow bookmark AI calls.
- `OH_MY_PDF_MINERU_POLL_TIMEOUT_SEC=1200`: cap MinerU polling time.
- `OH_MY_PDF_MINERU_DOWNLOAD_RETRIES=3`: retry MinerU result zip downloads.
- `OH_MY_PDF_MINERU_DOWNLOAD_TIMEOUT_SEC=180`: per-attempt MinerU zip timeout.

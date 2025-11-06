# BillsOCR

A simple web app to upload bill images, extract key details with OCR, and append results to an Excel file you can download.

## Prerequisites

- Python 3.10+
- Tesseract OCR installed on your machine
  - macOS (Homebrew): `brew install tesseract`
  - Linux (Debian/Ubuntu): `sudo apt-get install tesseract-ocr`
  - Windows: Install from `https://github.com/UB-Mannheim/tesseract/wiki` and add to PATH

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Run the server

```bash
uvicorn app.main:app --reload
```

- Open `http://localhost:8000` in your browser for the UI.
- The Excel file is stored at `data/bills.xlsx` (auto-created when first result is saved).

## Features

- Upload one or more images (`.png`, `.jpg`, `.jpeg`, `.webp`)
- OCR performed locally using Tesseract via `pytesseract`
- Heuristic parsing of `vendor`, `date`, and `total amount`
- Append rows to Excel with `openpyxl`
- Download the latest Excel from `/api/download`

## Notes

- Parsing is heuristic; adjust patterns in `app/ocr.py` to fit your bills.
- If Tesseract is installed in a non-standard path, set the environment variable `TESSERACT_CMD` to the tesseract binary path.

## Project Structure

```
app/
  main.py        # FastAPI app and endpoints
  ocr.py         # OCR and parsing utilities
  excel.py       # Excel writer utilities
static/
  index.html     # Web UI
  app.js         # UI logic
  style.css      # Basic styles
requirements.txt
README.md
```


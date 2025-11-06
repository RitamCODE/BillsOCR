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

## Deploy to Render (free tier)

1. Push this repository to GitHub (private or public).
2. Create a free account at [Render](https://render.com) and choose **New > Web Service**.
3. Connect the GitHub repo, pick the branch you want to deploy, and set **Runtime** to *Docker*. Render will auto-detect the `Dockerfile` in the repo root.
4. Leave the build command empty (Render will run `docker build`) and the start command blank so the `CMD` in the `Dockerfile` (`uvicorn app.main:app --host 0.0.0.0 --port 8000`) is used.
5. (Optional but recommended) Add a Persistent Disk with mount path `/app/data` to keep the generated `data/bills.xlsx` between restarts. Without the disk the file resets whenever the service rebuilds.
6. Click **Create Web Service**. The free plan sleeps after periods of inactivity; the app will wake up automatically on the next request.

The `Dockerfile` installs Tesseract and all Python dependencies so nothing else is required on the Render side. If you customize dependencies, rebuild the service to apply the changes.

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

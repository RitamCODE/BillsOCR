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

### Option A: One-click blueprint

1. Push the repo to GitHub/GitLab and note the repo URL.
2. In Render, go to **Dashboard ▸ New ▸ Blueprint** and paste the repo URL.
3. Render reads `render.yaml` and proposes a *Web Service* named `bills-ocr` on the free plan using the included `Dockerfile`. Accept the defaults.
4. (Optional) Keep the `bills-data` disk from the blueprint if you want OCR results to persist across restarts. Disks incur a small charge (~$0.15/GB/mo). Delete the disk before deploying if you prefer ephemeral storage.
5. Click **Apply** to trigger the initial deploy.

### Option B: Manual web service

1. Push this repository to GitHub (private or public).
2. Create a free account at [Render](https://render.com) and choose **New > Web Service**.
3. Connect the GitHub repo, pick the branch you want to deploy, and set **Runtime** to *Docker*. Render auto-detects the `Dockerfile`.
4. Leave the build command empty (Render runs `docker build`) and the start command blank so the `CMD` in the `Dockerfile` (`uvicorn app.main:app --host 0.0.0.0 --port 8000`) is used.
5. (Optional) Add a Persistent Disk with mount path `/app/data` to keep the generated `data/bills.xlsx` between restarts. Without the disk the file resets whenever the service rebuilds.
6. Click **Create Web Service**. The free plan sleeps after periods of inactivity; the app wakes on the next request.

The `Dockerfile` installs Tesseract and all Python dependencies so nothing else is required on the Render side. Rebuild the service whenever you change dependencies.

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

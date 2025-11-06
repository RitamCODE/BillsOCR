from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from typing import List
import os
import traceback
import logging
from datetime import datetime
from .ocr import extract_bill_info_from_image
from .excel import ExcelWriter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
EXCEL_PATH = os.path.join(DATA_DIR, "bills.xlsx")

os.makedirs(DATA_DIR, exist_ok=True)

app = FastAPI(title="BillsOCR")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}", "traceback": traceback.format_exc()}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "errors": exc.errors()}
    )


@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=500, detail="UI not found")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/extract")
async def extract(files: List[UploadFile] = File(...)):
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")

        logger.info(f"Processing {len(files)} file(s)")
        excel_writer = ExcelWriter(EXCEL_PATH)
        results = []

        for file in files:
            try:
                filename = file.filename or "unknown"
                logger.info(f"Processing file: {filename}")
                
                # Check file type more flexibly
                content_type = file.content_type or ""
                if not any(ct in content_type.lower() for ct in ["image/png", "image/jpeg", "image/jpg", "image/webp"]):
                    # Also check filename extension as fallback
                    if not any(ext in filename.lower() for ext in [".png", ".jpg", ".jpeg", ".webp"]):
                        error_msg = f"Unsupported file type: {content_type or 'unknown'}"
                        logger.warning(f"{filename}: {error_msg}")
                        results.append({
                            "filename": filename,
                            "vendor": "",
                            "date": "",
                            "total": "",
                            "raw_text": "",
                            "processed_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                            "error": error_msg
                        })
                        continue

                image_bytes = await file.read()
                if not image_bytes:
                    error_msg = "Empty file"
                    logger.warning(f"{filename}: {error_msg}")
                    results.append({
                        "filename": filename,
                        "vendor": "",
                        "date": "",
                        "total": "",
                        "raw_text": "",
                        "processed_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                        "error": error_msg
                    })
                    continue

                logger.info(f"{filename}: Running OCR...")
                info = extract_bill_info_from_image(image_bytes, filename=filename)
                logger.info(f"{filename}: OCR completed successfully")
                results.append(info)
                excel_writer.append_row(info)
            except Exception as e:
                # Log the error and continue with other files
                error_msg = str(e)
                logger.error(f"{filename}: Error - {error_msg}", exc_info=True)
                results.append({
                    "filename": filename,
                    "vendor": "",
                    "date": "",
                    "total": "",
                    "raw_text": "",
                    "processed_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    "error": error_msg
                })

        try:
            excel_writer.save()
        except Exception as e:
            logger.error(f"Excel save error: {e}", exc_info=True)
            # Excel save error shouldn't fail the whole request

        logger.info(f"Completed processing. Success: {len([r for r in results if not r.get('error')])}, Errors: {len([r for r in results if r.get('error')])}")
        return {"results": results, "excel_path": "/api/download"}
    except Exception as e:
        logger.error(f"Fatal error in extract endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/api/download")
async def download_excel():
    if not os.path.exists(EXCEL_PATH):
        raise HTTPException(status_code=404, detail="Excel not found yet")
    return FileResponse(EXCEL_PATH, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="bills.xlsx")



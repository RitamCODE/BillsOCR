import os
import re
import shutil
from datetime import datetime
from typing import Dict, Any
from io import BytesIO
from PIL import Image
import pytesseract


def _find_tesseract():
    """Auto-detect Tesseract binary in common locations."""
    # Check environment variable first
    tesseract_cmd = os.environ.get("TESSERACT_CMD")
    if tesseract_cmd and os.path.exists(tesseract_cmd):
        return tesseract_cmd
    
    # Check if tesseract is in PATH
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        return tesseract_path
    
    # Check conda environment paths
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        conda_paths = [
            os.path.join(conda_prefix, "bin", "tesseract"),
            os.path.join(conda_prefix, "Library", "bin", "tesseract.exe"),  # Windows
        ]
        for path in conda_paths:
            if os.path.exists(path):
                return path
    
    # Check common macOS Homebrew locations
    common_paths = [
        "/opt/homebrew/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/opt/local/bin/tesseract",  # MacPorts
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    # Try to find in common conda installation locations
    home = os.path.expanduser("~")
    conda_base_paths = [
        os.path.join(home, "miniconda3", "envs", "billsocr", "bin", "tesseract"),
        os.path.join(home, "anaconda3", "envs", "billsocr", "bin", "tesseract"),
        "/opt/homebrew/Caskroom/miniconda/base/envs/billsocr/bin/tesseract",
        "/usr/local/miniconda3/envs/billsocr/bin/tesseract",
    ]
    for path in conda_base_paths:
        if os.path.exists(path):
            return path
    
    return None


TESSERACT_CMD = _find_tesseract()
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
else:
    # Set a placeholder so we can provide a helpful error message
    pytesseract.pytesseract.tesseract_cmd = None


DATE_PATTERNS = [
    r"(?:DATE|INVOICE DATE|BILL DATE)[\s:]*(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})",  # Date: MM/DD/YY
    r"(\d{1,2}[\-/]\d{1,2}[\-/]\d{4})",  # MM/DD/YYYY or DD/MM/YYYY
    r"(\d{4}[\-/]\d{1,2}[\-/]\d{1,2})",  # YYYY-MM-DD or YYYY/MM/DD
    r"(\d{1,2}[\-/]\d{1,2}[\-/]\d{2})",  # MM/DD/YY or DD/MM/YY (but not timestamps)
    r"([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})",  # Month DD, YYYY
]

AMOUNT_PATTERNS = [
    r"(?:TOTAL|AMOUNT DUE|GRAND TOTAL|BALANCE DUE|TOTAL DUE)[\s:]*\$?\s*(\d{1,3}(?:[\,\s]?\d{3})*(?:\.\d{2})?)",
    r"(?:TOTAL|AMOUNT DUE|GRAND TOTAL|BALANCE DUE)[^\d]*(\d+\.\d{2})",
    r"\$?\s*(\d{1,3}(?:[\,\s]?\d{3})*(?:\.\d{2}))\s*(?:TOTAL|AMOUNT|DUE)",
]


def _clean_amount(value: str) -> str:
    value = value.replace(",", "").strip()
    return value


def _parse_date(text: str, lines: list[str]) -> str:
    # First, try to find date near "DATE" label
    for i, line in enumerate(lines):
        date_match = re.search(r"(?:DATE|INVOICE DATE|BILL DATE)[\s:]*(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})", line, re.IGNORECASE)
        if date_match:
            raw = date_match.group(1)
            # Try to parse it
            for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%y", "%d/%m/%y"):
                try:
                    dt = datetime.strptime(raw, fmt)
                    return dt.strftime("%Y-%m-%d")
                except Exception:
                    continue
            return raw
    
    # Look for dates in the first half of the document (avoid timestamps at the end)
    text_half = "\n".join(lines[:max(1, len(lines)//2)])
    
    # Avoid timestamps (dates followed by time like "11/04/25 22:06")
    for pattern in DATE_PATTERNS[1:]:  # Skip the labeled pattern, already tried
        matches = list(re.finditer(pattern, text_half, re.IGNORECASE))
        for m in matches:
            raw = m.group(1)
            # Skip if it looks like a timestamp (has time after it)
            if m.end() < len(text_half) and re.search(r'\d{1,2}:\d{2}', text_half[m.end():m.end()+10]):
                continue
            # Try to parse
            for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%y", "%d/%m/%y", "%b %d, %Y", "%B %d, %Y"):
                try:
                    dt = datetime.strptime(raw, fmt)
                    return dt.strftime("%Y-%m-%d")
                except Exception:
                    continue
            return raw
    return ""


def _parse_amount(text: str, lines: list[str]) -> str:
    # Look for "Total" label with amount on same or next line
    for i, line in enumerate(lines):
        # Check if line contains "Total" keyword
        if re.search(r'\b(?:TOTAL|AMOUNT DUE|GRAND TOTAL|BALANCE DUE|TOTAL DUE)\b', line, re.IGNORECASE):
            # Try to find amount on same line
            amount_match = re.search(r'\$?\s*(\d{1,3}(?:[\,\s]?\d{3})*(?:\.\d{2})?)', line, re.IGNORECASE)
            if amount_match:
                return _clean_amount(amount_match.group(1))
            # Try next line
            if i + 1 < len(lines):
                amount_match = re.search(r'\$?\s*(\d{1,3}(?:[\,\s]?\d{3})*(?:\.\d{2})?)', lines[i+1], re.IGNORECASE)
                if amount_match:
                    return _clean_amount(amount_match.group(1))
    
    # Fallback: look for labeled totals in full text
    for pattern in AMOUNT_PATTERNS:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return _clean_amount(m.group(1))
    
    # Last resort: find last amount that looks like a total (has cents)
    candidates = re.findall(r'\$?\s*(\d+\.\d{2})\b', text)
    if candidates:
        return _clean_amount(candidates[-1])
    
    return ""


def _guess_vendor(lines: list[str]) -> str:
    # Look for vendor name in first few lines (usually at top of receipt)
    for i, line in enumerate(lines[:10]):  # Check first 10 lines
        s = line.strip()
        # Skip empty lines, lines with mostly numbers, or garbage
        if not s or len(s) < 3:
            continue
        # Skip lines that are mostly numbers or special chars
        if len(re.sub(r'[^A-Za-z\s]', '', s)) < len(s) * 0.5:
            continue
        # Skip common receipt header words
        if re.search(r'\b(?:RECEIPT|INVOICE|BILL|DATE|TOTAL|AMOUNT|ITEM|QTY|PRICE)\b', s, re.IGNORECASE):
            continue
        # Skip lines that look like addresses or phone numbers
        if re.search(r'\d{3}[-.]?\d{3}[-.]?\d{4}|\(\d{3}\)', s):
            continue
        # Prefer lines with capital letters (store names often capitalized)
        if re.search(r'[A-Z]{2,}', s):
            # Clean up common OCR errors
            s = re.sub(r'^[^A-Za-z]+', '', s)  # Remove leading non-letters
            s = re.sub(r'[^A-Za-z0-9\s&\-\.]+', '', s)  # Keep only letters, numbers, spaces, &, -, .
            if len(s) >= 3:
                return s[:128]
        # Fallback: any line with reasonable text
        elif len(re.sub(r'[^A-Za-z]', '', s)) >= 3:
            s = re.sub(r'^[^A-Za-z]+', '', s)
            s = re.sub(r'[^A-Za-z0-9\s&\-\.]+', '', s)
            if len(s) >= 3:
                return s[:128]
    
    # Last resort: return first non-empty line, cleaned up
    for line in lines[:5]:
        s = line.strip()
        if len(s) >= 3:
            s = re.sub(r'^[^A-Za-z0-9]+', '', s)
            return s[:128]
    
    return ""


def extract_bill_info_from_image(image_bytes: bytes, filename: str | None = None) -> Dict[str, Any]:
    if not TESSERACT_CMD:
        raise RuntimeError(
            "Tesseract OCR is not installed or not found in PATH.\n"
            "Please install it using one of these methods:\n"
            "  - Homebrew: brew install tesseract\n"
            "  - Conda: conda install -c conda-forge tesseract\n"
            "  - Or set TESSERACT_CMD environment variable to the tesseract binary path"
        )
    
    try:
        image = Image.open(BytesIO(image_bytes))
        # Handle different image modes
        if image.mode not in ('RGB', 'L'):
            image = image.convert("RGB")
        else:
            image = image.convert("RGB")
    except Exception as e:
        raise RuntimeError(f"Failed to open image: {str(e)}")

    try:
        # Use better OCR config for receipts
        ocr_text = pytesseract.image_to_string(image, config='--psm 6')
    except Exception as e:
        raise RuntimeError(f"OCR processing failed: {str(e)}")
    
    lines = [ln.strip() for ln in ocr_text.splitlines() if ln.strip()]
    normalized_text = "\n".join(lines)

    vendor = _guess_vendor(lines)
    date_str = _parse_date(normalized_text, lines)
    amount_str = _parse_amount(normalized_text, lines)

    return {
        "filename": filename or "",
        "vendor": vendor,
        "date": date_str,
        "total": amount_str,
        "raw_text": ocr_text,
        "processed_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }



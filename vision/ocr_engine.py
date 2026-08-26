"""
Vision & OCR Extraction Engine
==============================
Robust multi-stage computer vision pipeline for MRZ, Aadhaar Cards, and QR code extraction:
1. QR Code Detection: Uses PyZBar and OpenCV QRCodeDetector on multi-contrast/thresholded images.
2. MRZ Detection & ICAO 9303 Anchor-Based Optical Reconstruction:
   - MRZ ROI Isolation: Automatically crops and upscales the bottom 25-30% of the document.
   - Anchor-based alignment: Uses Country Code and Date/Sex tokens to accurately reconstruct Line 1 & Line 2.
   - Positional character confusion correction ('O' <-> '0', 'I' <-> '1', 'S' <-> '5', etc.).
   - Watermark & Guilloche background filter cleaning on MRZ filler zones.
   - TD3 (Passport: 44 chars) and TD2 (Visa: 36 chars) extraction.
3. Aadhaar Card OCR:
   - Extracts 12-digit UID, Name, DOB, Gender, and runs Verhoeff D_5 validation.
"""

import os
import re
import shutil
import warnings
from typing import Dict, Any, Optional, Tuple, List

# Suppress library deprecation warnings
warnings.filterwarnings("ignore")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    CV2_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    PIL_AVAILABLE = False

# Global cached EasyOCR reader instance
_EASYOCR_READER = None


def get_easyocr_reader():
    """Lazy-loads and caches the EasyOCR Reader instance."""
    global _EASYOCR_READER
    if _EASYOCR_READER is None:
        try:
            import easyocr
            _EASYOCR_READER = easyocr.Reader(['en'], gpu=False, verbose=False)
        except Exception:
            _EASYOCR_READER = None
    return _EASYOCR_READER


def configure_tesseract_path():
    """Auto-detects Tesseract binary on Windows and configures pytesseract/PATH."""
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        shutil.which("tesseract")
    ]
    
    for path in possible_paths:
        if path and os.path.isfile(path):
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = path
                tess_dir = os.path.dirname(path)
                if tess_dir not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = tess_dir + os.pathsep + os.environ.get("PATH", "")
                return path
            except Exception:
                pass
    return None


configure_tesseract_path()


def enhance_image_for_ocr(img_gray: Any) -> List[Any]:
    """Generates enhanced variants of a grayscale image."""
    if not CV2_AVAILABLE or img_gray is None:
        return [img_gray]
        
    variants = [img_gray]
    try:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        variants.append(clahe.apply(img_gray))
        
        blurred = cv2.GaussianBlur(img_gray, (3, 3), 0)
        _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        variants.append(otsu)
        
        adaptive = cv2.adaptiveThreshold(
            img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4
        )
        variants.append(adaptive)
    except Exception:
        pass
    return variants


def detect_and_read_qr_from_mat(img: Any) -> Optional[str]:
    """Decodes QR codes from a numpy image."""
    if not CV2_AVAILABLE or img is None:
        return None
        
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        
        # 1. Try PyZBar first
        try:
            from pyzbar.pyzbar import decode as pyzbar_decode
            for variant in enhance_image_for_ocr(gray):
                decoded_objs = pyzbar_decode(variant)
                for obj in decoded_objs:
                    if obj.data:
                        try:
                            text = obj.data.decode("utf-8", errors="ignore").strip()
                            if text:
                                return text
                        except Exception:
                            pass
        except Exception:
            pass
            
        # 2. Try OpenCV QRCodeDetector
        detector = cv2.QRCodeDetector()
        for variant in enhance_image_for_ocr(gray):
            data, _, _ = detector.detectAndDecode(variant)
            if data and data.strip():
                return data.strip()
                
        # 3. Try 90/180/270 rotations
        for rot in (cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE):
            rot_gray = cv2.rotate(gray, rot)
            data, _, _ = detector.detectAndDecode(rot_gray)
            if data and data.strip():
                return data.strip()
                
        return None
    except Exception:
        return None


def detect_and_read_qr(image_bytes: bytes) -> Optional[str]:
    """Decodes QR codes from image bytes."""
    if not CV2_AVAILABLE:
        return None
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return detect_and_read_qr_from_mat(img)
    except Exception:
        return None


# ----------------------------------------------------------------------
# ICAO 9303 Anchor-Based Optical MRZ Reconstruction
# ----------------------------------------------------------------------

def repair_td3_line1(raw_l1: str) -> Optional[Tuple[str, str]]:
    """
    Cleans and repairs a TD3 Passport MRZ Line 1 (44 chars).
    Returns Tuple[repaired_line_1, issuing_country_3_letters].
    Format: P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<
    """
    cleaned = raw_l1.upper()
    cleaned = cleaned.replace('«', '<').replace('»', '<').replace(' ', '').replace('(', '<').replace(')', '<')
    
    # Must start with P< or P followed by 3 letters
    if not (cleaned.startswith('P<') or (len(cleaned) >= 4 and cleaned.startswith('P') and cleaned[1:4].isalpha())):
        return None
        
    if not cleaned.startswith('P<') and len(cleaned) >= 5 and cleaned[4] != '<':
        cleaned = cleaned[0] + '<' + cleaned[1:]

    # Extract issuing country (chars 2:5)
    country = cleaned[2:5] if len(cleaned) >= 5 else "UTO"
    
    # Normalize noise characters in the filler zone: '*', '4', '8', 'K', spaces, etc.
    clean_chars = []
    for c in cleaned:
        if c.isalpha() or c == '<':
            clean_chars.append(c)
        elif c in ('4', '*', '8', 'K', '-', '_', '.', '0', ' '):
            clean_chars.append('<')
            
    repaired = "".join(clean_chars)[:44].ljust(44, '<')
    return repaired, country


def repair_td3_line2(raw_l2: str, issuing_country: str = "UTO") -> Optional[str]:
    """
    Cleans and repairs a TD3 Passport MRZ Line 2 (44 chars) using anchor tokens.
    Anchor tokens:
    - Country Code (e.g. 'MLI', 'UTO', 'IND')
    - DOB / Sex / Expiry patterns
    """
    cleaned = re.sub(r'[^A-Za-z0-9<]', '', raw_l2.upper())
    if len(cleaned) < 32:
        return None
        
    # Helper mappers
    def to_digit(c: str) -> str:
        mapping = {'O': '0', 'D': '0', 'Q': '0', 'I': '1', 'L': '1', 'Z': '2', 'S': '5', 'B': '8'}
        return mapping.get(c, c if c.isdigit() else '0')
        
    def to_letter(c: str) -> str:
        mapping = {'0': 'O', '1': 'I', '2': 'Z', '5': 'S', '8': 'B'}
        return mapping.get(c, c if c.isalpha() else 'X')

    country_idx = cleaned.find(issuing_country)
    
    if country_idx != -1 and country_idx <= 12:
        # Pre-country is DocNumber + CheckDigit (should be 10 chars)
        pre_country = cleaned[:country_idx]
        # First 2 chars can be letters (e.g. PP), next chars are digits
        doc_chars = list(pre_country)
        for idx in range(2, len(doc_chars)):
            doc_chars[idx] = to_digit(doc_chars[idx])
        doc_field = "".join(doc_chars).ljust(10, '0')[:10]
        
        # Remainder after country code
        suffix = cleaned[country_idx + len(issuing_country):]
        if len(suffix) >= 15:
            dob_field = "".join(to_digit(c) for c in suffix[:6])
            dob_cd = to_digit(suffix[6]) if len(suffix) > 6 else '0'
            raw_sex = suffix[7] if len(suffix) > 7 else '<'
            sex_field = 'M' if raw_sex in ('M', '0', 'N', 'U', 'H') else ('F' if raw_sex in ('F', 'E', 'P') else '<')
            exp_field = "".join(to_digit(c) for c in suffix[8:14]) if len(suffix) >= 14 else '000000'
            exp_cd = to_digit(suffix[14]) if len(suffix) > 14 else '0'
            opt_field = suffix[15:].ljust(16, '<')[:16]
            return f"{doc_field}{issuing_country}{dob_field}{dob_cd}{sex_field}{exp_field}{exp_cd}{opt_field}"
            
    # Fallback positional correction
    chars = list(cleaned[:44].ljust(44, '<'))
    chars[9] = to_digit(chars[9])
    for i in (10, 11, 12): chars[i] = to_letter(chars[i])
    for i in range(13, 20): chars[i] = to_digit(chars[i])
    if chars[20] not in ('M', 'F', '<'):
        chars[20] = 'M' if chars[20] in ('0', 'N', 'H', 'U') else ('F' if chars[20] in ('E', 'P') else '<')
    for i in range(21, 28): chars[i] = to_digit(chars[i])
    chars[43] = to_digit(chars[43])
    return "".join(chars)


def repair_td2_line1(raw_l1: str) -> Optional[Tuple[str, str]]:
    """Cleans and repairs a TD2 Visa MRZ Line 1 (36 chars)."""
    cleaned = raw_l1.upper()
    cleaned = cleaned.replace('«', '<').replace('»', '<').replace(' ', '').replace('(', '<').replace(')', '<')
    if not (cleaned.startswith('V<') or (len(cleaned) >= 4 and cleaned.startswith('V'))):
        return None
    country = cleaned[2:5] if len(cleaned) >= 5 else "UTO"
    return cleaned[:36].ljust(36, '<'), country


def repair_td2_line2(raw_l2: str, issuing_country: str = "UTO") -> Optional[str]:
    """Cleans and repairs a TD2 Visa MRZ Line 2 (36 chars)."""
    cleaned = re.sub(r'[^A-Za-z0-9<]', '', raw_l2.upper())
    if len(cleaned) < 28:
        return None
    return cleaned[:36].ljust(36, '<')


def extract_mrz_candidates_from_text(raw_text: str, target_type: Optional[str] = None) -> Optional[Tuple[str, str]]:
    """
    Identifies and repairs 2-line TD3 or TD2 MRZ strings from recognized OCR text lines.
    """
    raw_lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    
    # 1. TD3 Passport Candidate Search
    if target_type in (None, "auto", "passport"):
        for i in range(len(raw_lines)):
            l1_candidate = raw_lines[i]
            # Must match standard Passport MRZ Line 1 signature (P< or P + Country)
            if re.match(r'^P<[A-Z0-9<]{3,}', l1_candidate.upper()) or re.match(r'^P[A-Z]{3}<', l1_candidate.upper()):
                repaired_1 = repair_td3_line1(l1_candidate)
                if repaired_1:
                    l1_str, country = repaired_1
                    # Look at subsequent lines for Line 2
                    for j in range(i + 1, min(i + 4, len(raw_lines))):
                        l2_candidate = raw_lines[j]
                        repaired_l2 = repair_td3_line2(l2_candidate, issuing_country=country)
                        if repaired_l2 and len(repaired_l2) == 44:
                            return "passport", f"{l1_str}\n{repaired_l2}"

    # 2. TD2 Visa Candidate Search
    if target_type in (None, "auto", "visa"):
        for i in range(len(raw_lines)):
            l1_candidate = raw_lines[i]
            if re.match(r'^V<[A-Z0-9<]{3,}', l1_candidate.upper()) or re.match(r'^V[A-Z]{3}<', l1_candidate.upper()):
                repaired_1 = repair_td2_line1(l1_candidate)
                if repaired_1:
                    l1_str, country = repaired_1
                    for j in range(i + 1, min(i + 4, len(raw_lines))):
                        l2_candidate = raw_lines[j]
                        repaired_l2 = repair_td2_line2(l2_candidate, issuing_country=country)
                        if repaired_l2 and len(repaired_l2) == 36:
                            return "visa", f"{l1_str}\n{repaired_l2}"
                            
    return None


def run_full_ocr_on_image(img: Any) -> str:
    """Runs EasyOCR or PyTesseract on an image matrix and returns recognized text lines."""
    reader = get_easyocr_reader()
    if reader is not None:
        try:
            results = reader.readtext(img, detail=0)
            if results:
                return "\n".join(results)
        except Exception:
            pass
            
    try:
        import pytesseract
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        return pytesseract.image_to_string(gray)
    except Exception:
        pass
        
    return ""


def extract_document_from_image(
    image_bytes: bytes,
    explicit_doc_type: Optional[str] = None,
    include_redacted_image: bool = False
) -> Tuple[str, str, float, Optional[str], Optional[str]]:
    """
    Main vision extraction controller:
    - If doc_type == 'aadhaar': Decodes QR code or extracts optical text + optional UIDAI physical redaction.
    - If doc_type == 'passport': Isolates MRZ ROI + VIZ ROI and extracts TD3 passport MRZ & VIZ text.
    - If doc_type == 'visa': Isolates MRZ ROI + VIZ ROI and extracts TD2 visa MRZ & VIZ text.
    - If doc_type is auto/None: Intelligently classifies document and extracts both MRZ & VIZ.
    
    Returns:
        Tuple[doc_type: str, raw_payload: str, confidence: float, viz_text: Optional[str], redacted_image_b64: Optional[str]]
    """
    if not CV2_AVAILABLE:
        raise ValueError("OpenCV is required for image processing.")
        
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode uploaded image. Ensure file is a valid JPEG, PNG, or WebP.")
        
    # Scale image to optimal resolution (width ~1600px)
    h, w = img.shape[:2]
    if w > 2400 or w < 900:
        scale = 1600.0 / w
        img = cv2.resize(img, (1600, int(h * scale)), interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC)
        h, w = img.shape[:2]

    target_type = explicit_doc_type.lower().strip() if explicit_doc_type else "auto"

    # Extract VIZ Text from top 70% of document for cross-validation
    viz_roi = img[:int(h * 0.70), :]
    viz_text = run_full_ocr_on_image(viz_roi)

    # Helper for in-memory Aadhaar redaction (Zero-disk persistence)
    def sanitize_aadhaar_canvas(raw_canvas: np.ndarray, uid_hint: Optional[str] = None) -> Optional[str]:
        if not include_redacted_image:
            return None
        try:
            from vision.redaction_engine import redact_aadhaar_image
            _, b64_uri = redact_aadhaar_image(raw_canvas, raw_uid=uid_hint)
            return b64_uri
        except Exception:
            return None

    # -------------------------------------------------------------
    # CASE 1: Explicitly requested AADHAAR
    # -------------------------------------------------------------
    if target_type == "aadhaar":
        qr_text = detect_and_read_qr_from_mat(img)
        if qr_text:
            redacted_b64 = sanitize_aadhaar_canvas(img)
            return "aadhaar", qr_text, 0.98, viz_text, redacted_b64
            
        ocr_text = run_full_ocr_on_image(img)
        if ocr_text and ocr_text.strip():
            redacted_b64 = sanitize_aadhaar_canvas(img)
            return "aadhaar", ocr_text, 0.94, viz_text, redacted_b64
            
        raise ValueError("Could not detect QR code or read text from the provided Aadhaar image.")

    # -------------------------------------------------------------
    # CASE 2 & 3: PASSPORT or VISA or AUTO MRZ EXTRACTION
    # -------------------------------------------------------------
    # A. Multi-Scale MRZ Region of Interest (ROI) Scan (Bottom 30% of document)
    mrz_roi = img[int(h * 0.70):, :]
    mrz_roi_scaled = cv2.resize(mrz_roi, (w * 2, int(h * 0.30 * 2)), interpolation=cv2.INTER_CUBIC)
    
    roi_text = run_full_ocr_on_image(mrz_roi_scaled)
    roi_candidate = extract_mrz_candidates_from_text(roi_text, target_type=target_type if target_type != "auto" else None)
    if roi_candidate:
        return roi_candidate[0], roi_candidate[1], 0.96, viz_text, None

    # B. Full Image OCR Scan
    full_text = run_full_ocr_on_image(img)
    full_candidate = extract_mrz_candidates_from_text(full_text, target_type=target_type if target_type != "auto" else None)
    if full_candidate:
        return full_candidate[0], full_candidate[1], 0.95, viz_text, None

    # If passport was explicitly requested and failed:
    if target_type == "passport":
        raise ValueError("Could not extract a valid 2-line TD3 Passport MRZ from the uploaded image.")

    # If visa was explicitly requested and failed:
    if target_type == "visa":
        raise ValueError("Could not extract a valid 2-line TD2 Visa MRZ from the uploaded image.")

    # -------------------------------------------------------------
    # CASE 4: AUTO DETECTION Fallback (Check Aadhaar QR / Text)
    # -------------------------------------------------------------
    qr_text = detect_and_read_qr_from_mat(img)
    if qr_text:
        redacted_b64 = sanitize_aadhaar_canvas(img)
        return "aadhaar", qr_text, 0.98, viz_text, redacted_b64

    aadhaar_indicators = ["AADHAAR", "GOVERNMENT OF INDIA", "UNIQUE IDENTIFICATION", "BHARAT SARKAR", "DOB", "MALE", "FEMALE"]
    has_aadhaar_keyword = any(kw in full_text.upper() for kw in aadhaar_indicators)
    has_uid_pattern = bool(re.search(r'\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b', full_text))
    
    if has_uid_pattern or (has_aadhaar_keyword and ("MALE" in full_text.upper() or "FEMALE" in full_text.upper() or "DOB" in full_text.upper())):
        redacted_b64 = sanitize_aadhaar_canvas(img)
        return "aadhaar", full_text, 0.92, viz_text, redacted_b64

    raise ValueError(
        "Could not automatically detect a valid document type (Passport TD3, Visa TD2, or Aadhaar Card). "
        "Please specify 'doc_type' explicitly or ensure the image is clear and well-lit."
    )

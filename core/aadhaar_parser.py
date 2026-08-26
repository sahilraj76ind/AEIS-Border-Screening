"""
Aadhaar Parser & Verhoeff Checksum Engine
=========================================
Implements the Verhoeff checksum algorithm from first principles and parses:
1. Aadhaar XML QR / Secure QR payloads.
2. Optical Character Recognition (OCR) text extracted from physical/e-Aadhaar cards
   (extracting Name, Date of Birth, Gender, 12-digit UID, and Address).

Verhoeff Algorithm Background:
------------------------------
Invented by Jacobus Verhoeff in 1969, this algorithm utilizes the dihedral group D_5
(order 10) to compute and verify error-detecting check digits.

Properties:
- Detects 100% of single-digit transcription errors.
- Detects 100% of adjacent transposition errors.
- Used for the 12th digit of every valid Indian Aadhaar number.
"""

import xml.etree.ElementTree as ET
import re
from typing import Dict, Any, Optional, List, Tuple


# ----------------------------------------------------------------------
# Verhoeff Dihedral Group D_5 Matrices
# ----------------------------------------------------------------------

VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0)
)

VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8)
)

VERHOEFF_INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)


def validate_verhoeff(number_str: str) -> bool:
    """
    Validates a number string (including its check digit) using the Verhoeff algorithm.
    """
    clean_digits = [int(c) for c in str(number_str) if c.isdigit()]
    if not clean_digits:
        return False
        
    c = 0
    for idx, digit in enumerate(reversed(clean_digits)):
        c = VERHOEFF_D[c][VERHOEFF_P[idx % 8][digit]]
        
    return c == 0


def generate_verhoeff_check_digit(number_without_check: str) -> str:
    """
    Calculates the Verhoeff check digit for an input sequence of digits.
    """
    clean_digits = [int(c) for c in str(number_without_check) if c.isdigit()]
    c = 0
    for idx, digit in enumerate(reversed(clean_digits), start=1):
        c = VERHOEFF_D[c][VERHOEFF_P[idx % 8][digit]]
        
    return str(VERHOEFF_INV[c])


def mask_aadhaar_uid(uid_str: Optional[str], formatted: bool = True) -> str:
    """
    UIDAI Compliant Masking Transformer:
    Masks the first 8 digits of a 12-digit Indian Aadhaar UID.
    - If formatted=True: 'XXXX XXXX 9019'
    - If formatted=False: 'XXXXXXXX9019'
    
    Complies with:
    - Aadhaar (Targeted Delivery of Financial and Other Subsidies, Benefits and Services) Act, 2016 (Section 29)
    - UIDAI Circular Comp/01/2018
    - RBI Master Direction on KYC (Masked Aadhaar Mandate)
    """
    if not uid_str:
        return "XXXX XXXX XXXX"
        
    digits_only = re.sub(r'\D', '', str(uid_str))
    if len(digits_only) == 12:
        last4 = digits_only[8:]
        return f"XXXX XXXX {last4}" if formatted else f"XXXXXXXX{last4}"
    elif len(digits_only) >= 4:
        last4 = digits_only[-4:]
        return f"XXXX XXXX {last4}" if formatted else f"XXXXXXXX{last4}"
    return "XXXX XXXX XXXX"


# ----------------------------------------------------------------------
# Aadhaar Card OCR Text Extractor
# ----------------------------------------------------------------------

AADHAAR_HEADER_KEYWORDS = [
    "GOVERNMENT OF INDIA", "UNIQUE IDENTIFICATION", "AUTHORITY OF INDIA",
    "BHARAT SARKAR", "MERA AADHAAR", "MERI PEHCHAN", "ENROLMENT", "VID"
]

def extract_aadhaar_from_ocr_text(ocr_text: str) -> Dict[str, Any]:
    """
    Parses optical text recognized from an Aadhaar card image when QR code is not present.
    Extracts:
    - 12-digit UID
    - Name
    - Date of Birth / Year of Birth
    - Gender
    - Address & Pincode (if back side)
    """
    raw_lines = [l.strip() for l in ocr_text.splitlines() if l.strip()]
    full_text = "\n".join(raw_lines)
    
    # 1. Extract 12-Digit Aadhaar UID (Format: 'XXXX XXXX XXXX' or 'XXXXXXXXXXXX')
    uid = None
    verhoeff_valid = None
    
    # Match standard 4-4-4 digit spacing or continuous 12 digits
    uid_matches = re.findall(r'\b([2-9]\d{3}\s?\d{4}\s?\d{4})\b', full_text)
    if uid_matches:
        # Prefer the last match (typically at bottom of card)
        raw_uid = uid_matches[-1]
        clean_uid = re.sub(r'\s', '', raw_uid)
        if len(clean_uid) == 12:
            uid = clean_uid
            verhoeff_valid = validate_verhoeff(clean_uid)
            
    # If no 12-digit match, check for masked Aadhaar (e.g. XXXX XXXX 1234)
    if not uid:
        masked_match = re.search(r'\b([X\d]{4}\s?[X\d]{4}\s?\d{4})\b', full_text, re.IGNORECASE)
        if masked_match:
            uid = masked_match.group(1).upper()
            verhoeff_valid = None

    # 2. Extract Date of Birth / Year of Birth
    dob = None
    dob_match = re.search(
        r'(?:DOB|D\.O\.B|Date of Birth|Birth|Year of Birth|जन्म तिथि|जन्म वर्ष)[:\s]*([0-3]?[0-9][/\-.][0-1]?[0-9][/\-.][12][90]\d{2})',
        full_text,
        re.IGNORECASE
    )
    if dob_match:
        raw_dob = dob_match.group(1).replace('-', '/').replace('.', '/')
        # Normalize to YYYY-MM-DD if in DD/MM/YYYY format
        parts = raw_dob.split('/')
        if len(parts) == 3 and len(parts[2]) == 4:
            dob = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        else:
            dob = raw_dob
    else:
        # Try finding 4-digit Year of Birth
        yob_match = re.search(r'(?:Year of Birth|YOB|जन्म वर्ष)[:\s]*([12][90]\d{2})', full_text, re.IGNORECASE)
        if yob_match:
            dob = yob_match.group(1)

    # 3. Extract Gender (Standardized to ICAO M/F/X)
    gender = None
    if re.search(r'\b(FEMALE|महिला)\b', full_text, re.IGNORECASE):
        gender = "F"
    elif re.search(r'\b(MALE|पुरुष)\b', full_text, re.IGNORECASE):
        gender = "M"
    elif re.search(r'\b(TRANSGENDER)\b', full_text, re.IGNORECASE):
        gender = "X"

    # 4. Extract Name
    # Heuristic: Name line usually precedes the DOB line, contains only alphabetic characters,
    # and is not a header like "Government of India".
    name = None
    for idx, line in enumerate(raw_lines):
        upper_l = line.upper()
        if any(kw in upper_l for kw in AADHAAR_HEADER_KEYWORDS):
            continue
        if re.search(r'(DOB|Date of Birth|जन्म|MALE|FEMALE|\d{4})', upper_l, re.IGNORECASE):
            continue
        # Clean line of non-alpha characters
        clean_candidate = re.sub(r'[^A-Za-z\s]', '', line).strip()
        clean_candidate = re.sub(r'^(?:Name|NAME|Nom)[:\s]*', '', clean_candidate).strip()
        words = clean_candidate.split()
        if len(words) >= 2 and len(clean_candidate) >= 4 and len(clean_candidate) <= 40:
            name = clean_candidate
            break

    # 5. Extract Pincode (if back side)
    pincode = None
    pin_match = re.search(r'\b([1-9]\d{5})\b', full_text)
    if pin_match:
        pincode = pin_match.group(1)

    overall_valid = bool(verhoeff_valid) if verhoeff_valid is not None else (uid is not None)

    return {
        "document_type": "aadhaar",
        "format": "AADHAAR_CARD",
        "_raw_uid_in_memory": uid,
        "extracted_fields": {
            "name": name,
            "document_number": mask_aadhaar_uid(uid),
            "nationality": "IND",
            "date_of_birth": dob,
            "sex": gender,
            "date_of_expiry": None,  # Aadhaar cards have lifetime validity
            "pincode": pincode,
            "state": None,
            "address": None
        },
        "checksum_validation": {
            "verhoeff_check": verhoeff_valid,
            "overall_valid": overall_valid
        }
    }


# ----------------------------------------------------------------------
# Aadhaar QR Parsing
# ----------------------------------------------------------------------

def parse_aadhaar_xml_qr(xml_text: str) -> Dict[str, Any]:
    """Parses standard Aadhaar XML barcode/QR data (`PrintLetterBarcodeData`)."""
    try:
        xml_clean = xml_text.strip()
        root = ET.fromstring(xml_clean)
        attribs = root.attrib
        
        uid = attribs.get("uid", "").strip()
        name = attribs.get("name", "").strip()
        raw_gender = attribs.get("gender", "").strip().upper()
        gender = "M" if raw_gender in ("M", "MALE") else ("F" if raw_gender in ("F", "FEMALE") else ("X" if raw_gender else None))
        dob = attribs.get("dob", attribs.get("yob", "")).strip()
        
        addr_parts = [
            attribs.get(k, "").strip() 
            for k in ("house", "street", "lm", "loc", "vtc", "po", "dist", "state", "pc")
            if attribs.get(k, "").strip()
        ]
        address = ", ".join(addr_parts)
        
        verhoeff_valid = validate_verhoeff(uid) if len(uid) == 12 and uid.isdigit() else None
        
        return {
            "uid": uid,
            "name": name,
            "gender": gender,
            "date_of_birth": dob,
            "year_of_birth": attribs.get("yob", ""),
            "care_of": attribs.get("co", ""),
            "pincode": attribs.get("pc", ""),
            "district": attribs.get("dist", ""),
            "state": attribs.get("state", ""),
            "address": address,
            "verhoeff_valid": verhoeff_valid,
            "raw_attributes": attribs
        }
    except Exception as e:
        raise ValueError(f"Failed to parse Aadhaar XML QR: {e}")


def parse_aadhaar_data(data_payload: str) -> Dict[str, Any]:
    """
    Unified entry point for parsing Aadhaar data from either:
    1. Direct 12-digit Aadhaar UID string.
    2. XML QR text.
    3. Full OCR text of an Aadhaar card.
    """
    cleaned = data_payload.strip()
    
    # 1. XML QR payload
    if "<PrintLetterBarcodeData" in cleaned or "<xml" in cleaned:
        parsed_xml = parse_aadhaar_xml_qr(cleaned)
        uid = parsed_xml.get("uid", "")
        uid_digits = re.sub(r'\D', '', uid)
        
        verhoeff_result = parsed_xml.get("verhoeff_valid")
        if verhoeff_result is None and len(uid_digits) == 12:
            verhoeff_result = validate_verhoeff(uid_digits)
            
        overall_valid = bool(verhoeff_result) if verhoeff_result is not None else True
        
        return {
            "document_type": "aadhaar",
            "format": "AADHAAR_QR",
            "_raw_uid_in_memory": uid_digits,
            "extracted_fields": {
                "name": parsed_xml.get("name"),
                "document_number": mask_aadhaar_uid(uid),
                "nationality": "IND",
                "date_of_birth": parsed_xml.get("date_of_birth"),
                "sex": parsed_xml.get("gender"),
                "date_of_expiry": None,
                "pincode": parsed_xml.get("pincode"),
                "state": parsed_xml.get("state"),
                "address": parsed_xml.get("address")
            },
            "checksum_validation": {
                "verhoeff_check": verhoeff_result,
                "overall_valid": overall_valid
            }
        }
        
    # 2. Raw 12-digit number
    digits_only = re.sub(r'\D', '', cleaned)
    if len(digits_only) == 12 and ("<" not in cleaned and "{" not in cleaned and "\n" not in cleaned):
        is_valid = validate_verhoeff(digits_only)
        return {
            "document_type": "aadhaar",
            "format": "AADHAAR_UID",
            "_raw_uid_in_memory": digits_only,
            "extracted_fields": {
                "document_number": mask_aadhaar_uid(digits_only),
                "name": None,
                "nationality": "IND",
                "date_of_birth": None,
                "sex": None,
                "date_of_expiry": None
            },
            "checksum_validation": {
                "verhoeff_check": is_valid,
                "overall_valid": is_valid
            }
        }
        
    # 3. Full OCR text of an Aadhaar card
    return extract_aadhaar_from_ocr_text(cleaned)


if __name__ == "__main__":
    print("=" * 70)
    print("Aadhaar & Verhoeff Checksum Engine - Self Test")
    print("=" * 70)
    
    # Test 1: Verhoeff algorithm verification on standard test vectors
    test_num = "236"
    expected_cd = generate_verhoeff_check_digit(test_num)
    assert expected_cd == "3"
    assert validate_verhoeff("2363") is True
    
    # Test 2: Valid 12-digit Aadhaar sample UID
    base_aadhaar = "99998888777"
    cd = generate_verhoeff_check_digit(base_aadhaar)
    valid_aadhaar = base_aadhaar + cd
    assert validate_verhoeff(valid_aadhaar) is True
    
    # Test 3: Aadhaar OCR Text Parsing (Front of physical card)
    sample_ocr = (
        "Government of India\n"
        "Unique Identification Authority of India\n"
        "Akshay Singh\n"
        "DOB: 12/08/1998\n"
        "Male\n"
        f"{valid_aadhaar[:4]} {valid_aadhaar[4:8]} {valid_aadhaar[8:]}\n"
    )
    parsed_ocr = parse_aadhaar_data(sample_ocr)
    print("\n--- Parsed Physical Aadhaar OCR Card ---")
    print(f"Name: {parsed_ocr['extracted_fields']['name']}")
    print(f"UID: {parsed_ocr['extracted_fields']['document_number']}")
    print(f"DOB: {parsed_ocr['extracted_fields']['date_of_birth']}")
    print(f"Gender: {parsed_ocr['extracted_fields']['sex']}")
    print(f"Verhoeff Valid: {parsed_ocr['checksum_validation']['verhoeff_check']}")
    assert parsed_ocr['extracted_fields']['name'] == "Akshay Singh"
    assert parsed_ocr['extracted_fields']['document_number'] == valid_aadhaar
    assert parsed_ocr['checksum_validation']['verhoeff_check'] is True
    print("\n[OK] Aadhaar OCR text parser & Verhoeff algorithm verified successfully!")

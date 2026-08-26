"""
TD3 (Passport) MRZ Parser
=========================
Implements the parser and validator for Machine Readable Passports adhering to
ICAO Doc 9303 Part 4 (Specifications for Machine Readable Passports).

MRZ Format: TD3 (2 lines x 44 characters = 88 characters total)

Structure Definition:
---------------------
Line 1 (44 chars):
  Pos [0:2]   ( 2 chars): Document code (e.g., 'P<', 'PO', 'PS', 'PA')
  Pos [2:5]   ( 3 chars): Issuing State or Organization (ISO 3166-1 alpha-3 code)
  Pos [5:44]  (39 chars): Primary & Secondary Identifier (Surname << Given Names)

Line 2 (44 chars):
  Pos [0:9]   ( 9 chars): Document Number
  Pos [9]     ( 1 char ): Document Number Check Digit (ICAO 9303 weights 7,3,1)
  Pos [10:13] ( 3 chars): Nationality (ISO 3166-1 alpha-3 code)
  Pos [13:19] ( 6 chars): Date of Birth (YYMMDD)
  Pos [19]    ( 1 char ): Date of Birth Check Digit (ICAO 9303)
  Pos [20]    ( 1 char ): Sex ('M', 'F', 'X', or '<' for unspecified)
  Pos [21:27] ( 6 chars): Date of Expiry (YYMMDD)
  Pos [27]    ( 1 char ): Date of Expiry Check Digit (ICAO 9303)
  Pos [28:42] (14 chars): Optional Data (Personal Number / National ID)
  Pos [42]    ( 1 char ): Optional Data Check Digit (or '<' if not used)
  Pos [43]    ( 1 char ): Composite Check Digit

Composite Check Digit Calculation (ICAO Doc 9303 Part 4, Section 4.2.2):
  Evaluated over:
    Line2[0:10]  (Document Number + its check digit)
    + Line2[13:20] (Date of Birth + its check digit)
    + Line2[21:43] (Date of Expiry + its check digit + Optional Data + its check digit)
"""

from typing import Dict, Any, List, Optional
from .mrz_utils import verify_mrz_check_digit, compute_mrz_check_digit, clean_mrz_string


def parse_name(name_raw: str) -> Dict[str, str]:
    """
    Parses MRZ name field formatted as: SURNAME<<GIVEN<NAMES<<<...
    
    Returns:
        Dict with 'surname', 'given_names', and formatted 'full_name'.
    """
    name_clean = name_raw.strip().rstrip('<')
    parts = name_clean.split('<<')
    surname = parts[0].replace('<', ' ').strip() if len(parts) > 0 else ""
    given_names = parts[1].replace('<', ' ').strip() if len(parts) > 1 else ""
    
    full_name = f"{given_names} {surname}".strip() if given_names else surname
    return {
        "surname": surname,
        "given_names": given_names,
        "full_name": full_name,
        "raw_name": name_raw
    }


def parse_td3_mrz(mrz_text: str) -> Dict[str, Any]:
    """
    Parses and validates a 2-line TD3 Passport Machine Readable Zone (MRZ).
    
    Args:
        mrz_text: 2 lines of 44 characters each, separated by newline.
        
    Returns:
        Dict containing extracted_fields and checksum_validation results.
        
    Raises:
        ValueError: If MRZ text is not 2 lines of 44 characters.
    """
    cleaned = clean_mrz_string(mrz_text)
    lines = cleaned.split('\n')
    
    if len(lines) != 2:
        raise ValueError(f"TD3 MRZ requires exactly 2 lines, found {len(lines)} lines.")
    
    line1, line2 = lines[0], lines[1]
    
    if len(line1) != 44 or len(line2) != 44:
        raise ValueError(
            f"TD3 lines must be 44 characters each. Got line 1: {len(line1)}, line 2: {len(line2)}"
        )
    
    # -------------------------------------------------------------
    # Line 1 Extraction
    # -------------------------------------------------------------
    doc_code = line1[0:2].replace('<', '')
    issuing_country = line1[2:5].replace('<', '')
    name_data = parse_name(line1[5:44])
    
    # -------------------------------------------------------------
    # Line 2 Extraction
    # -------------------------------------------------------------
    doc_number_raw = line2[0:9]
    doc_number_check = line2[9]
    nationality = line2[10:13].replace('<', '')
    dob_raw = line2[13:19]
    dob_check = line2[19]
    sex = line2[20]
    expiry_raw = line2[21:27]
    expiry_check = line2[27]
    optional_data_raw = line2[28:42]
    optional_data_check = line2[42]
    composite_check = line2[43]
    
    clean_doc_number = doc_number_raw.replace('<', '')
    clean_optional_data = optional_data_raw.replace('<', '')
    
    # -------------------------------------------------------------
    # Check Digit Validations (ICAO Doc 9303 Part 4)
    # -------------------------------------------------------------
    # 1. Document Number Check
    valid_doc_num = verify_mrz_check_digit(doc_number_raw, doc_number_check)
    
    # 2. Date of Birth Check
    valid_dob = verify_mrz_check_digit(dob_raw, dob_check)
    
    # 3. Date of Expiry Check
    valid_expiry = verify_mrz_check_digit(expiry_raw, expiry_check)
    
    # 4. Optional Data Check (if used, else check digit '<' is accepted)
    valid_optional = verify_mrz_check_digit(optional_data_raw, optional_data_check)
    
    # 5. Composite Check Digit
    # Composite string spans: Line2[0:10] + Line2[13:20] + Line2[21:43]
    composite_data = line2[0:10] + line2[13:20] + line2[21:43]
    valid_composite = verify_mrz_check_digit(composite_data, composite_check)
    
    overall_valid = valid_doc_num and valid_dob and valid_expiry and valid_composite
    
    return {
        "document_type": "passport",
        "format": "TD3",
        "extracted_fields": {
            "name": name_data["full_name"],
            "surname": name_data["surname"],
            "given_names": name_data["given_names"],
            "document_type_code": doc_code,
            "issuing_country": issuing_country,
            "document_number": clean_doc_number,
            "nationality": nationality,
            "date_of_birth_raw": dob_raw,
            "sex": sex if sex in ('M', 'F', 'X') else 'UNSPECIFIED',
            "date_of_expiry_raw": expiry_raw,
            "optional_data": clean_optional_data,
        },
        "checksum_validation": {
            "document_number_check": valid_doc_num,
            "dob_check": valid_dob,
            "expiry_check": valid_expiry,
            "optional_data_check": valid_optional,
            "composite_check": valid_composite,
            "overall_valid": overall_valid
        },
        "raw_mrz": {
            "line1": line1,
            "line2": line2
        }
    }


if __name__ == "__main__":
    print("=" * 70)
    print("TD3 (Passport) MRZ Parser - Self Test")
    print("=" * 70)
    
    # Specimen TD3 Passport MRZ (ICAO Doc 9303 Standard Sample / MIDV-500 test vector)
    # Line 1: P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<
    # Line 2: L898902C36UTO7408122F1204159ZE184226B<<<<<10
    valid_td3 = (
        "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
        "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
    )
    
    res = parse_td3_mrz(valid_td3)
    print("\n--- Valid TD3 Passport Extraction ---")
    print(f"Name: {res['extracted_fields']['name']}")
    print(f"Doc Number: {res['extracted_fields']['document_number']}")
    print(f"DOB Raw: {res['extracted_fields']['date_of_birth_raw']}")
    print(f"Expiry Raw: {res['extracted_fields']['date_of_expiry_raw']}")
    print(f"Nationality: {res['extracted_fields']['nationality']}")
    print(f"Checksums: {res['checksum_validation']}")
    assert res['checksum_validation']['overall_valid'] is True, "Valid sample should pass all checks"
    
    # Deliberately Tampered TD3 Sample: alter expiry year 120415 -> 130415
    tampered_td3 = (
        "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
        "L898902C36UTO7408122F1304159ZE184226B<<<<<10"
    )
    res_tampered = parse_td3_mrz(tampered_td3)
    print("\n--- Tampered TD3 Passport (Altered Expiry Year) ---")
    print(f"Checksums: {res_tampered['checksum_validation']}")
    assert res_tampered['checksum_validation']['expiry_check'] is False
    assert res_tampered['checksum_validation']['composite_check'] is False
    assert res_tampered['checksum_validation']['overall_valid'] is False
    print("[OK] Deliberate tampering correctly flagged by check digit engine!")

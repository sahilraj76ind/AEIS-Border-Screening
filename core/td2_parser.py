"""
TD2 (Visa) MRZ Parser
=====================
Implements the parser and validator for Machine Readable Visas adhering to
ICAO Doc 9303 Part 7 (Machine Readable Visas - Format B / TD2).

MRZ Format: TD2 (2 lines x 36 characters = 72 characters total)

Structure Definition:
---------------------
Line 1 (36 chars):
  Pos [0:2]   ( 2 chars): Document code (e.g., 'V<', 'VI', 'VB')
  Pos [2:5]   ( 3 chars): Issuing State or Organization (ISO 3166-1 alpha-3 code)
  Pos [5:36]  (31 chars): Primary & Secondary Identifier (Surname << Given Names)

Line 2 (36 chars):
  Pos [0:9]   ( 9 chars): Document Number
  Pos [9]     ( 1 char ): Document Number Check Digit (ICAO 9303 weights 7,3,1)
  Pos [10:13] ( 3 chars): Nationality (ISO 3166-1 alpha-3 code)
  Pos [13:19] ( 6 chars): Date of Birth (YYMMDD)
  Pos [19]    ( 1 char ): Date of Birth Check Digit (ICAO 9303)
  Pos [20]    ( 1 char ): Sex ('M', 'F', 'X', or '<')
  Pos [21:27] ( 6 chars): Date of Expiry (YYMMDD)
  Pos [27]    ( 1 char ): Date of Expiry Check Digit (ICAO 9303)
  Pos [28:35] ( 7 chars): Optional Data
  Pos [35]    ( 1 char ): Composite Check Digit

Composite Check Digit Calculation (ICAO Doc 9303 Part 7, Section 4.2.2):
  Evaluated over:
    Line2[0:10]  (Document Number + its check digit)
    + Line2[13:20] (Date of Birth + its check digit)
    + Line2[21:35] (Date of Expiry + its check digit + Optional Data)
"""

from typing import Dict, Any
from .mrz_utils import verify_mrz_check_digit, clean_mrz_string
from .td3_parser import parse_name


def parse_td2_mrz(mrz_text: str) -> Dict[str, Any]:
    """
    Parses and validates a 2-line TD2 Visa Machine Readable Zone (MRZ).
    
    Args:
        mrz_text: 2 lines of 36 characters each, separated by newline.
        
    Returns:
        Dict containing extracted_fields and checksum_validation results.
        
    Raises:
        ValueError: If MRZ text is not 2 lines of 36 characters.
    """
    cleaned = clean_mrz_string(mrz_text)
    lines = cleaned.split('\n')
    
    if len(lines) != 2:
        raise ValueError(f"TD2 MRZ requires exactly 2 lines, found {len(lines)} lines.")
    
    line1, line2 = lines[0], lines[1]
    
    if len(line1) != 36 or len(line2) != 36:
        raise ValueError(
            f"TD2 lines must be 36 characters each. Got line 1: {len(line1)}, line 2: {len(line2)}"
        )
    
    # -------------------------------------------------------------
    # Line 1 Extraction
    # -------------------------------------------------------------
    doc_code = line1[0:2].replace('<', '')
    issuing_country = line1[2:5].replace('<', '')
    name_data = parse_name(line1[5:36])
    
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
    optional_data_raw = line2[28:35]
    composite_check = line2[35]
    
    clean_doc_number = doc_number_raw.replace('<', '')
    clean_optional_data = optional_data_raw.replace('<', '')
    
    # -------------------------------------------------------------
    # Check Digit Validations (ICAO Doc 9303 Part 7)
    # -------------------------------------------------------------
    valid_doc_num = verify_mrz_check_digit(doc_number_raw, doc_number_check)
    valid_dob = verify_mrz_check_digit(dob_raw, dob_check)
    valid_expiry = verify_mrz_check_digit(expiry_raw, expiry_check)
    
    # Composite check digit spans Line2[0:10] + Line2[13:20] + Line2[21:35]
    composite_data = line2[0:10] + line2[13:20] + line2[21:35]
    valid_composite = verify_mrz_check_digit(composite_data, composite_check)
    
    overall_valid = valid_doc_num and valid_dob and valid_expiry and valid_composite
    
    return {
        "document_type": "visa",
        "format": "TD2",
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
    print("TD2 (Visa) MRZ Parser - Self Test")
    print("=" * 70)
    
    # Specimen TD2 Visa MRZ (ICAO Doc 9303 Part 7 / MIDV-500 sample vector)
    # Line 1 (36 chars): V<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<
    # Line 2 (36 chars): L8988901C4XXX4009078F9612109<<<<<<<6
    valid_td2 = (
        "V<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<\n"
        "L8988901C4XXX4009078F9612109<<<<<<<6"
    )
    
    res = parse_td2_mrz(valid_td2)
    print("\n--- Valid TD2 Visa Extraction ---")
    print(f"Name: {res['extracted_fields']['name']}")
    print(f"Doc Number: {res['extracted_fields']['document_number']}")
    print(f"DOB Raw: {res['extracted_fields']['date_of_birth_raw']}")
    print(f"Expiry Raw: {res['extracted_fields']['date_of_expiry_raw']}")
    print(f"Nationality: {res['extracted_fields']['nationality']}")
    print(f"Checksums: {res['checksum_validation']}")
    assert res['checksum_validation']['overall_valid'] is True, "Valid TD2 sample should pass all checks"
    
    # Deliberately Tampered TD2 Sample: alter document number check digit 4 -> 5
    tampered_td2 = (
        "V<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<\n"
        "L8988901C5XXX4009078F9612109<<<<<<<6"
    )
    res_tampered = parse_td2_mrz(tampered_td2)
    print("\n--- Tampered TD2 Visa (Altered Check Digit) ---")
    print(f"Checksums: {res_tampered['checksum_validation']}")
    assert res_tampered['checksum_validation']['document_number_check'] is False
    assert res_tampered['checksum_validation']['overall_valid'] is False
    print("[OK] Deliberate TD2 tampering caught successfully!")

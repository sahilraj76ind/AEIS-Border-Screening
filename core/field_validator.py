"""
Field-Level Semantic Validator
==============================
Performs contextual integrity checks on parsed identity fields:
1. Expiry Date: Flags 'EXPIRED' if document expiry date < today.
2. Date of Birth: Flags 'INVALID_DOB' if in the future or > 120 years ago.
3. Nationality: Flags 'INVALID_NATIONALITY' against ISO 3166-1 alpha-3 and ICAO 9303 codes.
4. Sex: Flags 'INVALID_SEX' if outside permitted ICAO codes (M, F, X, <).
5. Checksum Status: Flags 'CHECKSUM_FAILED' if check digit validations failed.
"""

from datetime import date, datetime
from typing import Dict, Any, List, Optional, Tuple, Set


# Comprehensive ISO 3166-1 alpha-3 country codes
ISO_3166_1_ALPHA_3: Set[str] = {
    "AFG", "ALB", "DZA", "AND", "AGO", "ATG", "ARG", "ARM", "AUS", "AUT",
    "AZE", "BHS", "BHR", "BGD", "BRB", "BLR", "BEL", "BLZ", "BEN", "BTN",
    "BOL", "BIH", "BWA", "BRA", "BRN", "BGR", "BFA", "BDI", "CPV", "KHM",
    "CMR", "CAN", "CAF", "TCD", "CHL", "CHN", "COL", "COM", "COG", "COD",
    "CRI", "CIV", "HRV", "CUB", "CYP", "CZE", "DNK", "DJI", "DMA", "DOM",
    "ECU", "EGY", "SLV", "GNQ", "ERI", "EST", "SWZ", "ETH", "FJI", "FIN",
    "FRA", "GAB", "GMB", "GEO", "DEU", "GHA", "GRC", "GRD", "GTM", "GIN",
    "GNB", "GUY", "HTI", "HND", "HUN", "ISL", "IND", "IDN", "IRN", "IRQ",
    "IRL", "ISR", "ITA", "JAM", "JPN", "JOR", "KAZ", "KEN", "KIR", "PRK",
    "KOR", "KWT", "KGZ", "LAO", "LVA", "LBN", "LSO", "LBR", "LBY", "LIE",
    "LTU", "LUX", "MDG", "MWI", "MYS", "MDV", "MLI", "MLT", "MHL", "MRT",
    "MUS", "MEX", "FSM", "MDA", "MCO", "MNG", "MNE", "MAR", "MOZ", "MMR",
    "NAM", "NRU", "NPL", "NLD", "NZL", "NIC", "NER", "NGA", "MKD", "NOR",
    "OMN", "PAK", "PLW", "PAN", "PNG", "PRY", "PER", "PHL", "POL", "PRT",
    "QAT", "ROU", "RUS", "RWA", "KNA", "LCA", "VCT", "WSM", "SMR", "STP",
    "SAU", "SEN", "SRB", "SYC", "SLE", "SGP", "SVK", "SVN", "SLB", "SOM",
    "ZAF", "SSD", "ESP", "LKA", "SDN", "SUR", "SWE", "CHE", "SYR", "TWN",
    "TJK", "TZA", "THA", "TLS", "TGO", "TON", "TTO", "TUN", "TUR", "TKM",
    "TUV", "UGA", "UKR", "ARE", "GBR", "USA", "URY", "UZB", "VUT", "VEN",
    "VNM", "YEM", "ZMB", "ZWE", "HKG", "MAC", "PRI", "GUM", "VIR", "ASM"
}

# ICAO Doc 9303 Part 3 Section 4.3 Reserved & Special Codes
ICAO_SPECIAL_CODES: Set[str] = {
    "UTO",  # Utopia (Standard ICAO specimen / test country)
    "D<<",  # Germany (historical / special MRTD code)
    "GBD",  # British Overseas Territories Citizen
    "GBN",  # British National (Overseas)
    "GBO",  # British Overseas Citizen
    "GBP",  # British Protected Person
    "GBS",  # British Subject
    "XXA",  # Stateless Person (1954 Convention)
    "XXB",  # Refugee (1951 Convention)
    "XXC",  # Person of Undetermined Nationality
    "XXX",  # Unspecified Nationality
    "UNA",  # United Nations Agency / Official
    "UNK",  # Unknown
    "XOM",  # Sovereign Military Order of Malta
    "XPO"   # Interpol
}

VALID_COUNTRY_CODES: Set[str] = ISO_3166_1_ALPHA_3 | ICAO_SPECIAL_CODES


def parse_mrz_date(raw_date: Optional[str], is_birth_date: bool = False, reference_date: Optional[date] = None) -> Tuple[Optional[date], Optional[str]]:
    """
    Parses a 6-character YYMMDD MRZ date string into a Python `date` object
    using ICAO century windowing / pivot heuristics.
    
    Century Pivot Logic:
    - Current Year = ref_date.year (e.g. 2026)
    - For DOB:
        A human age is bounded between 0 and 120 years.
        If (2000 + YY) > current_year:
            year = 1900 + YY
        Else:
            year = 2000 + YY
    - For Expiry:
        Documents have standard validity periods (typically 5 to 10 years).
        If (2000 + YY) < (current_year - 40):
            year = 1900 + YY
        Else:
            year = 2000 + YY
            
    Returns:
        Tuple[Optional[date], Optional[str]]: (parsed_date_obj, iso_formatted_string "YYYY-MM-DD")
    """
    if not raw_date or len(raw_date) != 6 or not raw_date.isdigit():
        return None, None
        
    ref_date = reference_date or date.today()
    current_year = ref_date.year
    current_century = (current_year // 100) * 100  # 2000
    
    yy = int(raw_date[0:2])
    mm = int(raw_date[2:4])
    dd = int(raw_date[4:6])
    
    # Basic calendar boundary check
    if mm < 1 or mm > 12 or dd < 1 or dd > 31:
        return None, None
        
    if is_birth_date:
        # If 2000+yy is in future relative to current year, person was born in 1900s
        if (current_century + yy) > current_year:
            year = (current_century - 100) + yy
        else:
            year = current_century + yy
    else:
        # Expiry date: if 2000+yy is more than 40 years in past, assume 1900s
        if (current_century + yy) < (current_year - 40):
            year = (current_century - 100) + yy
        else:
            year = current_century + yy
            
    try:
        dt = date(year, mm, dd)
        return dt, dt.isoformat()
    except ValueError:
        # Invalid date like Feb 30th
        return None, None


def validate_document_fields(parsed_doc: Dict[str, Any], reference_date: Optional[date] = None) -> List[str]:
    """
    Runs semantic integrity checks on parsed document fields and returns
    a list of warning/error flags.
    
    Flags:
    - 'EXPIRED': Document expiry date is in the past.
    - 'INVALID_DOB': Date of birth is impossible (future date or age > 120).
    - 'INVALID_NATIONALITY': Nationality code not recognized in ISO 3166-1 / ICAO.
    - 'INVALID_SEX': Sex code is not recognized.
    - 'CHECKSUM_FAILED': One or more check digit validations failed.
    
    Args:
        parsed_doc: Parsed document dict containing 'extracted_fields' and 'checksum_validation'.
        reference_date: Optional date for evaluation (defaults to today).
        
    Returns:
        List[str]: List of identified flag strings.
    """
    flags: List[str] = []
    ref_date = reference_date or date.today()
    fields = parsed_doc.get("extracted_fields", {})
    checksums = parsed_doc.get("checksum_validation", {})
    
    # 1. Checksum Validation Status
    if checksums and not checksums.get("overall_valid", True):
        flags.append("CHECKSUM_FAILED")
        
    # 2. Expiry Date Validation
    raw_expiry = fields.get("date_of_expiry_raw")
    if raw_expiry:
        exp_date, exp_iso = parse_mrz_date(raw_expiry, is_birth_date=False, reference_date=ref_date)
        if exp_date:
            fields["date_of_expiry"] = exp_iso
            if exp_date < ref_date:
                flags.append("EXPIRED")
        else:
            flags.append("INVALID_EXPIRY_DATE")
            
    # 3. Date of Birth Validation
    raw_dob = fields.get("date_of_birth_raw")
    if raw_dob:
        dob_date, dob_iso = parse_mrz_date(raw_dob, is_birth_date=True, reference_date=ref_date)
        if dob_date:
            fields["date_of_birth"] = dob_iso
            age_years = (ref_date - dob_date).days / 365.25
            if dob_date > ref_date or age_years > 120:
                flags.append("INVALID_DOB")
        else:
            flags.append("INVALID_DOB")
            
    # 4. Nationality / Issuing Country Validation
    nationality = fields.get("nationality")
    if nationality:
        clean_nat = nationality.upper().replace("<", "")
        if clean_nat and clean_nat not in VALID_COUNTRY_CODES:
            flags.append("INVALID_NATIONALITY")
            
    # 5. Sex Validation
    sex = fields.get("sex")
    if sex and sex not in ("M", "F", "X", "<", "UNSPECIFIED"):
        flags.append("INVALID_SEX")
        
    return flags


if __name__ == "__main__":
    print("=" * 70)
    print("Field-Level Semantic Validator - Self Test")
    print("=" * 70)
    
    test_today = date(2026, 8, 25)
    
    # Test 1: Valid sample
    doc_sample = {
        "extracted_fields": {
            "nationality": "IND",
            "date_of_birth_raw": "950812",  # 1995-08-12
            "date_of_expiry_raw": "280812", # 2028-08-12
            "sex": "M"
        },
        "checksum_validation": {"overall_valid": True}
    }
    flags1 = validate_document_fields(doc_sample, reference_date=test_today)
    print(f"Sample 1 Flags: {flags1}")
    assert flags1 == [], f"Expected no flags, got {flags1}"
    
    # Test 2: Expired sample (Expiry: 2020-04-15)
    doc_expired = {
        "extracted_fields": {
            "nationality": "USA",
            "date_of_birth_raw": "800101",
            "date_of_expiry_raw": "200415", # Expired in 2020
            "sex": "F"
        },
        "checksum_validation": {"overall_valid": True}
    }
    flags2 = validate_document_fields(doc_expired, reference_date=test_today)
    print(f"Expired Sample Flags: {flags2}")
    assert "EXPIRED" in flags2
    
    # Test 3: Invalid Nationality & Checksum failure
    doc_tampered = {
        "extracted_fields": {
            "nationality": "ZZZ", # Non-existent country code
            "date_of_birth_raw": "900505",
            "date_of_expiry_raw": "300505",
            "sex": "M"
        },
        "checksum_validation": {"overall_valid": False}
    }
    flags3 = validate_document_fields(doc_tampered, reference_date=test_today)
    print(f"Tampered Sample Flags: {flags3}")
    assert "INVALID_NATIONALITY" in flags3
    assert "CHECKSUM_FAILED" in flags3
    
    print("\n[OK] Field-level validator verified successfully!")

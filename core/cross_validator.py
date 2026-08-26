"""
Cross-Zone Consistency Engine (VIZ vs. MRZ / QR)
================================================
ICAO Doc 9303 Part 3 / Part 4 Cross-Verification Architecture:
Compares human-readable Visual Inspection Zone (VIZ) data against
Machine Readable Zone (MRZ) and QR payloads to detect Photoshop tampering,
digital font injection, and selective physical page alterations.
"""

import re
import difflib
from typing import Dict, Any, Optional, List, Tuple


# ----------------------------------------------------------------------
# Multilingual Month Mapping (EN, FR, ES, DE, IT)
# ----------------------------------------------------------------------
MONTH_MAP = {
    # English
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06",
    "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
    "JANUARY": "01", "FEBRUARY": "02", "MARCH": "03", "APRIL": "04", "JUNE": "06",
    "JULY": "07", "AUGUST": "08", "SEPTEMBER": "09", "OCTOBER": "10", "NOVEMBER": "11", "DECEMBER": "12",
    # French
    "JANV": "01", "FEVR": "02", "FÉVR": "02", "AVR": "04", "MAI": "05", "JUIN": "06",
    "JUIL": "07", "AOUT": "08", "AOÛT": "08", "DÉC": "12",
    # Spanish
    "ENE": "01", "ENERO": "01", "FEBRERO": "02", "MARZO": "03", "ABR": "04", "ABRIL": "04",
    "MAYO": "05", "JUNIO": "06", "JULIO": "07", "AGO": "08", "AGOSTO": "08", "SEPTIEMBRE": "09",
    "OCTUBRE": "10", "NOVIEMBRE": "11", "DICIEMBRE": "12",
    # German
    "JANUAR": "01", "FEBRUAR": "02", "MÄRZ": "03", "OKT": "10", "OKTOBER": "10", "DEZ": "12", "DEZEMBER": "12"
}


def normalize_viz_date(raw_date_str: str) -> Optional[str]:
    """
    Normalizes diverse international date formats into ISO YYYY-MM-DD format.
    Examples:
    - '01 JANI JAN 98' -> '1998-01-01'
    - '30 JUINI JUN 25' -> '2025-06-30'
    - '29 JUINI JUN 30' -> '2030-06-29'
    - '12/08/1998' -> '1998-08-12'
    - '1998-01-01' -> '1998-01-01'
    """
    if not raw_date_str:
        return None
        
    cleaned = raw_date_str.strip().upper()
    
    # 1. Direct ISO format YYYY-MM-DD
    iso_match = re.search(r'\b(19\d{2}|20\d{2})[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])\b', cleaned)
    if iso_match:
        return f"{iso_match.group(1)}-{iso_match.group(2)}-{iso_match.group(3)}"
        
    # 2. Format DD/MM/YYYY or DD-MM-YYYY
    dmy_match = re.search(r'\b(0[1-9]|[12]\d|3[01])[-/.](0[1-9]|1[0-2])[-/.](19\d{2}|20\d{2})\b', cleaned)
    if dmy_match:
        return f"{dmy_match.group(3)}-{dmy_match.group(2)}-{dmy_match.group(1)}"
        
    # 3. Clean OCR noise on month tokens
    clean_text = re.sub(r'[/|:]', ' ', cleaned)
    clean_text = re.sub(r'\b(JANI|JANV|JAN)\b', 'JAN', clean_text)
    clean_text = re.sub(r'\b(JUINI|JUIN|JUN)\b', 'JUN', clean_text)
    clean_text = re.sub(r'\b(FEVRI|FEVR|FEB)\b', 'FEB', clean_text)
    clean_text = re.sub(r'\b(AOÛTI|AOUT|AUG)\b', 'AUG', clean_text)
    
    # Text format: '01 JAN 98' or '30 JUN 2025' or '12 AUG 1974'
    text_date_match = re.search(
        r'\b(0?[1-9]|[12]\d|3[01])\s+([A-ZÀ-Ÿ]{3,})(?:[\s]+[A-ZÀ-Ÿ]{3,})*[\s]+(\d{2}|\d{4})\b',
        clean_text
    )
    if text_date_match:
        day = text_date_match.group(1).zfill(2)
        month_raw = text_date_match.group(2)
        year_raw = text_date_match.group(3)
        
        month_num = "01"
        for m_key, m_val in MONTH_MAP.items():
            if m_key in month_raw:
                month_num = m_val
                break
            
        # Century pivot for 2-digit years
        if len(year_raw) == 2:
            y_int = int(year_raw)
            year_full = f"20{year_raw}" if y_int <= 40 else f"19{year_raw}"
        else:
            year_full = year_raw
            
        return f"{year_full}-{month_num}-{day}"
        
    return None


def extract_viz_fields(viz_text: str) -> Dict[str, Any]:
    """
    Extracts structured demographic fields from the Visual Inspection Zone (VIZ) text.
    Handles English, French, Spanish, and standard international passport labels with fuzzy tolerance.
    """
    raw_lines = [l.strip() for l in viz_text.splitlines() if l.strip()]
    full_text = "\n".join(raw_lines)
    
    extracted: Dict[str, Any] = {
        "surname": None,
        "given_names": None,
        "name": None,
        "document_number": None,
        "date_of_birth": None,
        "date_of_expiry": None,
        "sex": None,
        "nationality": None,
        "issuing_country": None
    }
    
    # -------------------------------------------------------------
    # 1. Document Number / Passport Number
    # -------------------------------------------------------------
    for line in raw_lines:
        line_up = line.upper()
        m = re.search(r'\b([A-Z]{1,3}[0-9O]{6,9})\b', line_up)
        if m:
            val = m.group(1).upper()
            if not any(kw in val for kw in ('PASSPORT', 'PASSEPORT', 'REPUBLIQUE', 'MALIENNE', 'CONFIDENTIAL')):
                extracted["document_number"] = val.replace('O', '0')
                break

    if not extracted["document_number"]:
        doc_num_match = re.search(
            r'(?:Passport\s*N[°o/]|N[°o]\s*de\s*passeport|Document\s*N[°o/]|Passport\s*No)[:\s/]*([A-Z0-9]{6,12})',
            full_text,
            re.IGNORECASE
        )
        if doc_num_match:
            extracted["document_number"] = doc_num_match.group(1).strip().upper().replace('O', '0')

    # -------------------------------------------------------------
    # 2. Names (Given Names & Surname)
    # -------------------------------------------------------------
    HEADER_NOISE = ('SURNAME', 'SUMAMEL', 'SOURNAM', 'NAME', 'NOM', 'GIVEN', 'PRENOM', 'NOMBRES', 'VORNAME', 'APELLIDO')
    
    given_name = None
    surname = None
    
    # Pass 1: Direct same-line match e.g. "Nom / Surname: SMITH" or "Surname: SMITH"
    for l in raw_lines:
        if not surname:
            m = re.search(r'(?:Nom\s*/\s*Surname|Surname|Nom|Apellidos|Nachname)[:\s]+([A-ZÀ-Ÿ\s\-]{2,30})$', l, re.IGNORECASE)
            if m:
                cand = m.group(1).strip().upper()
                if cand.replace(' ', '').isalpha() and not any(kw in cand for kw in ('PASSPORT', 'PASSEPORT', 'REPUBLIQUE', 'MALIENNE') + HEADER_NOISE):
                    surname = cand
        if not given_name:
            m = re.search(r'(?:Prénoms\s*/\s*Given\s*names|Given\s*names|Prénoms|Prénom|Nombres|Vornamen)[:\s]+([A-ZÀ-Ÿ\s\-]{2,35})$', l, re.IGNORECASE)
            if m:
                cand = m.group(1).strip().upper()
                if cand.replace(' ', '').isalpha() and not any(kw in cand for kw in HEADER_NOISE):
                    given_name = cand

    # Pass 2: Next-line and multi-line anchor matching
    if not given_name:
        for idx, l in enumerate(raw_lines):
            if re.search(r'given|renom|prenom|vornam|nombr', l, re.IGNORECASE):
                if idx + 1 < len(raw_lines):
                    cand = raw_lines[idx + 1].strip().upper()
                    if cand.replace(' ', '').isalpha() and len(cand) >= 2 and not any(kw in cand for kw in HEADER_NOISE):
                        given_name = cand
                        break

    if not surname:
        for idx, l in enumerate(raw_lines):
            if re.search(r'given|renom|prenom|vornam|nombr', l, re.IGNORECASE):
                for back_idx in range(idx - 1, max(-1, idx - 5), -1):
                    cand = raw_lines[back_idx].strip().upper()
                    if cand.replace(' ', '').isalpha() and len(cand) >= 2 and not any(kw in cand for kw in ('MLI', 'PASSPORT', 'PASSEPORT', 'CONFIDENTIAL') + HEADER_NOISE):
                        surname = cand
                        break
            elif re.search(r'^(?:Nom/Surname|Surname|Nom|Apellidos|Nachname|Nom\s*Sumamel)[:\s/]*$', l, re.IGNORECASE):
                if idx + 1 < len(raw_lines):
                    cand = raw_lines[idx + 1].strip().upper()
                    if cand.replace(' ', '').isalpha() and len(cand) >= 2 and not any(kw in cand for kw in HEADER_NOISE):
                        surname = cand
                        break

    extracted["surname"] = surname
    extracted["given_names"] = given_name
    
    if given_name and surname:
        extracted["name"] = f"{given_name} {surname}"
    elif surname:
        extracted["name"] = surname
    elif given_name:
        extracted["name"] = given_name

    # -------------------------------------------------------------
    # 3. Dates (DOB & Expiry)
    # -------------------------------------------------------------
    all_dates: List[str] = []
    for line in raw_lines:
        d = normalize_viz_date(line)
        if d and d not in all_dates:
            all_dates.append(d)
            
    # Chronological sort: earlier date is DOB, later is Expiry
    if len(all_dates) == 1:
        extracted["date_of_birth"] = all_dates[0]
    elif len(all_dates) >= 2:
        extracted["date_of_birth"] = all_dates[0]
        extracted["date_of_expiry"] = all_dates[-1]

    # -------------------------------------------------------------
    # 4. Sex / Gender
    # -------------------------------------------------------------
    for idx, line in enumerate(raw_lines):
        m = re.search(r'\b(Sexe|Sex|Geschlecht|Sexo)[:\s/]*\n?([MFX]|MALE|FEMALE|HOMME|FEMME)\b', line, re.IGNORECASE)
        if m:
            val = m.group(2).upper()
            extracted["sex"] = "M" if val in ('M', 'MALE', 'HOMME') else ("F" if val in ('F', 'FEMALE', 'FEMME') else "X")
            break
        elif re.search(r'\b(Sexe|Sex)\b', line, re.IGNORECASE):
            # Check current line or next 2 lines for standalone M/F/X
            found_sex = None
            for offset in range(0, 3):
                if idx + offset < len(raw_lines):
                    tok = raw_lines[idx + offset].strip().upper()
                    if tok in ('M', 'F', 'X'):
                        found_sex = tok
                        break
            if found_sex:
                extracted["sex"] = found_sex
                break

    # -------------------------------------------------------------
    # 5. Nationality
    # -------------------------------------------------------------
    for line in raw_lines:
        if re.search(r'MALIENNE|INDIAN|FRENCH|AMERICAN|BRITISH|GERMAN|UTOPIAN|CANADIAN', line, re.IGNORECASE):
            m = re.search(r'(MALIENNE|INDIAN|FRENCH|AMERICAN|BRITISH|GERMAN|UTOPIAN|CANADIAN)', line, re.IGNORECASE)
            if m:
                extracted["nationality"] = m.group(1).upper()
                break

    return extracted


def compute_string_similarity(str1: Optional[str], str2: Optional[str]) -> float:
    """Computes normalized Levenshtein sequence similarity ratio (0.0 to 1.0)."""
    if not str1 or not str2:
        return 0.0
    s1 = re.sub(r'[^A-Z0-9]', '', str1.upper())
    s2 = re.sub(r'[^A-Z0-9]', '', str2.upper())
    if s1 == s2:
        return 1.0
    return difflib.SequenceMatcher(None, s1, s2).ratio()


def cross_validate_viz_and_mrz(viz_data: Dict[str, Any], mrz_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Forensic Cross-Check Engine:
    Compares VIZ extracted fields against parsed MRZ fields.
    Returns:
    - is_consistent: bool
    - overall_match_score: float (0.0 - 1.0)
    - field_matches: detailed per-field match dictionary
    - mismatch_flags: list of raised discrepancy flags
    """
    mrz_fields = mrz_data.get("extracted_fields", {})
    
    mismatch_flags: List[str] = []
    field_matches: Dict[str, Any] = {}
    
    scores: List[float] = []
    
    # 1. Document Number Check
    viz_doc = viz_data.get("document_number")
    mrz_doc = mrz_fields.get("document_number")
    if viz_doc and mrz_doc:
        doc_sim = compute_string_similarity(viz_doc, mrz_doc)
        matched = (doc_sim >= 0.85) or (viz_doc in mrz_doc) or (mrz_doc in viz_doc)
        field_matches["document_number"] = {
            "viz_value": viz_doc,
            "mrz_value": mrz_doc,
            "matched": matched,
            "similarity": round(doc_sim, 3)
        }
        scores.append(1.0 if matched else doc_sim)
        if not matched:
            mismatch_flags.append("VIZ_MRZ_DOC_NUM_MISMATCH")

    # 2. Name Matching
    viz_name = viz_data.get("name")
    mrz_name = mrz_fields.get("name")
    if viz_name and mrz_name:
        name_sim = compute_string_similarity(viz_name, mrz_name)
        
        # Token set match (handles order differences like "DRAMANE MAMMADOU" vs "MAMMADOU DRAMANE")
        viz_tokens = set(re.findall(r'\w+', viz_name.upper()))
        mrz_tokens = set(re.findall(r'\w+', mrz_name.upper()))
        token_overlap = len(viz_tokens.intersection(mrz_tokens)) / max(len(viz_tokens), len(mrz_tokens), 1)
        
        matched = (name_sim >= 0.80) or (token_overlap >= 0.80)
        final_sim = max(name_sim, token_overlap)
        
        field_matches["name"] = {
            "viz_value": viz_name,
            "mrz_value": mrz_name,
            "matched": matched,
            "similarity": round(final_sim, 3)
        }
        scores.append(1.0 if matched else final_sim)
        if not matched:
            mismatch_flags.append("VIZ_MRZ_NAME_MISMATCH")

    # 3. Date of Birth Check
    viz_dob = viz_data.get("date_of_birth")
    mrz_dob = mrz_fields.get("date_of_birth") # YYYY-MM-DD format from parser
    if viz_dob and mrz_dob:
        dob_matched = (viz_dob == mrz_dob)
        field_matches["date_of_birth"] = {
            "viz_value": viz_dob,
            "mrz_value": mrz_dob,
            "matched": dob_matched,
            "similarity": 1.0 if dob_matched else 0.0
        }
        scores.append(1.0 if dob_matched else 0.0)
        if not dob_matched:
            mismatch_flags.append("VIZ_MRZ_DOB_MISMATCH")

    # 4. Date of Expiry Check
    viz_exp = viz_data.get("date_of_expiry")
    mrz_exp = mrz_fields.get("date_of_expiry")
    if viz_exp and mrz_exp:
        exp_matched = (viz_exp == mrz_exp)
        field_matches["date_of_expiry"] = {
            "viz_value": viz_exp,
            "mrz_value": mrz_exp,
            "matched": exp_matched,
            "similarity": 1.0 if exp_matched else 0.0
        }
        scores.append(1.0 if exp_matched else 0.0)
        if not exp_matched:
            mismatch_flags.append("VIZ_MRZ_EXPIRY_MISMATCH")

    # 5. Sex Check
    viz_sex = viz_data.get("sex")
    mrz_sex = mrz_fields.get("sex")
    if viz_sex and mrz_sex:
        sex_matched = (viz_sex.upper() == mrz_sex.upper())
        field_matches["sex"] = {
            "viz_value": viz_sex,
            "mrz_value": mrz_sex,
            "matched": sex_matched,
            "similarity": 1.0 if sex_matched else 0.0
        }
        scores.append(1.0 if sex_matched else 0.0)
        if not sex_matched:
            mismatch_flags.append("VIZ_MRZ_SEX_MISMATCH")

    overall_score = round(sum(scores) / len(scores), 3) if scores else 1.0
    is_consistent = (len(mismatch_flags) == 0) and (overall_score >= 0.85)

    return {
        "is_consistent": is_consistent,
        "overall_match_score": overall_score,
        "viz_extracted": viz_data,
        "field_matches": field_matches,
        "mismatch_flags": mismatch_flags
    }


if __name__ == "__main__":
    print("=" * 70)
    print("Cross-Zone Consistency Engine (VIZ vs. MRZ) - Self Test")
    print("=" * 70)
    
    sample_mali_viz = (
        "PASSEPORT\n"
        "REPUBLIQUE DU MALI\n"
        "PASSPORT\n"
        "Type: P  Code: MLI  Passport No: PP0000000\n"
        "Nom / Surname:\n"
        "DRAMANE\n"
        "Prénoms / Given names:\n"
        "MAMMADOU\n"
        "Nationalité / Nationality:\n"
        "MALIENNE\n"
        "Date de naissance / Date of birth: 01 JANI JAN 98\n"
        "Sexe / Sex: M\n"
        "Date d'expiration / Date of expiry: 29 JUINI JUN 30\n"
    )
    
    viz_fields = extract_viz_fields(sample_mali_viz)
    print("\n[1] Extracted VIZ Fields:")
    for k, v in viz_fields.items():
        print(f"  {k}: {v}")
        
    assert viz_fields["document_number"] == "PP0000000"
    assert viz_fields["surname"] == "DRAMANE"
    assert viz_fields["given_names"] == "MAMMADOU"
    assert viz_fields["date_of_birth"] == "1998-01-01"
    assert viz_fields["date_of_expiry"] == "2030-06-29"

    mrz_fields = {
        "extracted_fields": {
            "name": "MAMMADOU DRAMANE",
            "document_number": "PP0000000",
            "date_of_birth": "1998-01-01",
            "date_of_expiry": "2030-06-29",
            "sex": "M"
        }
    }
    res_consistent = cross_validate_viz_and_mrz(viz_fields, mrz_fields)
    print("\n[2] Consistency Validation Result (Authentic Document):")
    print(f"  Is Consistent: {res_consistent['is_consistent']}")
    print(f"  Overall Match Score: {res_consistent['overall_match_score']}")
    assert res_consistent["is_consistent"] is True
    assert len(res_consistent["mismatch_flags"]) == 0

    # Photoshop Tampered Document
    tampered_viz = dict(viz_fields)
    tampered_viz["name"] = "JOHN DOE"
    tampered_viz["document_number"] = "K9999999"
    res_tampered = cross_validate_viz_and_mrz(tampered_viz, mrz_fields)
    print("\n[3] Consistency Validation Result (Photoshop Tampered Document):")
    print(f"  Is Consistent: {res_tampered['is_consistent']}")
    print(f"  Mismatch Flags: {res_tampered['mismatch_flags']}")
    assert res_tampered["is_consistent"] is False
    assert "VIZ_MRZ_NAME_MISMATCH" in res_tampered["mismatch_flags"]
    assert "VIZ_MRZ_DOC_NUM_MISMATCH" in res_tampered["mismatch_flags"]
    
    print("\n[OK] Cross-Zone Consistency Engine self-test passed 100%!")

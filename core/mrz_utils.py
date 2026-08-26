"""
MRZ Utilities - ICAO Doc 9303 Check Digit Engine
=================================================
This module provides a pure-Python implementation of the check-digit calculation
and verification algorithms specified in ICAO Doc 9303 (Part 3: Specifications 
Common to all MRTDs - Section 4.9: Machine Readable Zone Check Digits).

Background & Mathematical Principles:
-------------------------------------
1. Why Check Digits?
   Optical Character Recognition (OCR) at border checkpoints can suffer from
   substitution errors (e.g. 'O' vs '0', 'B' vs '8', 'I' vs '1'). Check digits
   ensure data integrity by introducing mathematical redundancy.
   The ICAO 9303 weighting algorithm detects 100% of single-character substitution
   errors and most transposition errors of adjacent characters.

2. Weighting Factor:
   A cyclic repeating sequence of weights: 7, 3, 1, 7, 3, 1, ...
   Applied positionally from left to right across the data string.

3. Character Mapping:
   - Filler character '<' = 0
   - Digits '0' through '9' = 0 through 9
   - Letters 'A' through 'Z' = 10 through 35 (where A=10, B=11, ..., Z=35)

4. Checksum Formula:
   CheckDigit = ( sum( char_value(c_i) * weight[i % 3] for i, c_i in enumerate(data) ) ) % 10
"""

from typing import Union


# ICAO 9303 standard cyclic weights
ICAO_WEIGHTS = (7, 3, 1)


def char_to_mrz_value(char: str) -> int:
    """
    Maps an individual MRZ character to its integer value according to ICAO Doc 9303 Part 3.
    
    Mapping rules:
    - '<' (Filler character) -> 0
    - '0' - '9'             -> 0 - 9
    - 'A' - 'Z'             -> 10 - 35
    
    Args:
        char: Single MRZ character (uppercase string of length 1).
        
    Returns:
        int: Numerical value [0-35].
        
    Raises:
        ValueError: If character is outside [A-Z0-9<].
    """
    if len(char) != 1:
        raise ValueError(f"Expected single character, got: {char!r}")
    
    char_upper = char.upper()
    if char_upper == '<':
        return 0
    elif '0' <= char_upper <= '9':
        return int(char_upper)
    elif 'A' <= char_upper <= 'Z':
        # 'A' has ASCII 65 -> 65 - 55 = 10; 'Z' has ASCII 90 -> 90 - 55 = 35
        return ord(char_upper) - 55
    else:
        raise ValueError(f"Invalid MRZ character: {char!r}. Allowed: [A-Z0-9<]")


def compute_mrz_check_digit(data: str) -> str:
    """
    Computes the ICAO Doc 9303 modulo-10 check digit for a given alphanumeric MRZ string.
    
    Formula:
        Sum = sum(char_to_mrz_value(data[i]) * ICAO_WEIGHTS[i % 3] for i in range(len(data)))
        CheckDigit = Sum % 10
        
    Args:
        data: The input MRZ string (e.g. document number, date of birth, expiry date).
        
    Returns:
        str: Single character check digit ('0'-'9').
    """
    total = 0
    for idx, char in enumerate(data):
        val = char_to_mrz_value(char)
        weight = ICAO_WEIGHTS[idx % 3]
        total += val * weight
        
    return str(total % 10)


def verify_mrz_check_digit(data: str, expected_check_digit: Union[str, int]) -> bool:
    """
    Verifies that the provided check digit matches the calculated ICAO Doc 9303 check digit.
    
    Special Case:
    - If the check digit character is '<' and all characters in data are '<',
      the field is unused and considered valid (sum=0 % 10 = 0, but '<' represents omitted).
      
    Args:
        data: The payload string.
        expected_check_digit: The check digit extracted from the MRZ line (single char).
        
    Returns:
        bool: True if check digit is valid, False otherwise.
    """
    expected_str = str(expected_check_digit).strip()
    
    # Handle unused/filler fields (e.g. optional data filled with '<' and check digit '<')
    if expected_str == '<' and all(c == '<' for c in data):
        return True
        
    try:
        calculated = compute_mrz_check_digit(data)
        return calculated == expected_str
    except ValueError:
        return False


def clean_mrz_string(text: str) -> str:
    """
    Sanitizes raw MRZ text by standardizing linebreaks, stripping whitespace,
    and converting to uppercase.
    """
    lines = [line.strip().upper() for line in text.strip().splitlines() if line.strip()]
    return "\n".join(lines)


if __name__ == "__main__":
    # Educational test block demonstrating ICAO 9303 calculation
    print("=" * 60)
    print("ICAO Doc 9303 Check Digit Engine - Self Test")
    print("=" * 60)
    
    # Official ICAO Doc 9303 Part 3 Example:
    # Document number: "L898902C3" -> Check digit should be "6"
    # Calculation:
    # L(21)*7 + 8*3 + 9*1 + 8*7 + 9*3 + 0*1 + 2*7 + C(12)*3 + 3*1
    # = 147 + 24 + 9 + 56 + 27 + 0 + 14 + 36 + 3 = 316
    # 316 % 10 = 6
    sample_doc = "L898902C3"
    computed = compute_mrz_check_digit(sample_doc)
    is_valid = verify_mrz_check_digit(sample_doc, "6")
    print(f"Sample Document: {sample_doc}")
    print(f"Computed Check Digit: {computed} (Expected: '6') -> Valid: {is_valid}")
    assert computed == "6", f"Expected 6, got {computed}"
    assert is_valid is True
    
    # Test mutation (deliberate tampering: L898902C3 -> L898902C4)
    tampered_doc = "L898902C4"
    tampered_valid = verify_mrz_check_digit(tampered_doc, "6")
    print(f"Tampered Document: {tampered_doc} with check digit '6' -> Valid: {tampered_valid}")
    assert tampered_valid is False, "Tampered doc should fail check digit validation"
    
    print("\n[OK] ICAO Doc 9303 check digit engine verified successfully!")

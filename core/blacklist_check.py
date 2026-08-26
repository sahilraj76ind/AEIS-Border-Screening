"""
Border Control Mock Watchlist / Blacklist Engine
================================================
Simulates law enforcement and border checkpoint watchlist lookups against:
1. Interpol SLTD (Stolen and Lost Travel Documents) Database
2. Flagged Fraud / Synthetic Identity Registry
3. UN / National Sanctions Watchlist
4. Counter-Terrorism & High-Risk Travel Alerts
"""

from typing import Dict, Any, Optional


# Mock database simulating government and border agency watchlists
MOCK_BLACKLIST_DATABASE: Dict[str, Dict[str, Any]] = {
    # Stolen / Lost Passports (Interpol SLTD simulation)
    "L898902C3": {
        "matched_list": "LOST_STOLEN_TRAVEL_DOCS",
        "reason": "Reported lost in transit at international hub",
        "severity": "HIGH",
        "issuing_agency": "INTERPOL_SLTD"
    },
    "P10928374": {
        "matched_list": "LOST_STOLEN_TRAVEL_DOCS",
        "reason": "Reported stolen during burglary",
        "severity": "HIGH",
        "issuing_agency": "INTERPOL_SLTD"
    },
    # Known Fraudulent / Counterfeit Travel Documents
    "F99887766": {
        "matched_list": "FLAGGED_FRAUD",
        "reason": "Known counterfeit blank batch identified by forensic lab",
        "severity": "CRITICAL",
        "issuing_agency": "BORDER_INTELLIGENCE"
    },
    "V11223344": {
        "matched_list": "FLAGGED_FRAUD",
        "reason": "Forged visa sticker serial sequence",
        "severity": "CRITICAL",
        "issuing_agency": "IMMIGRATION_SECURITY"
    },
    # Sanctioned Entities / Person of Interest
    "S55443322": {
        "matched_list": "SANCTIONS_LIST",
        "reason": "UN Security Council travel ban active",
        "severity": "CRITICAL",
        "issuing_agency": "UN_SANCTIONS_COMMITTEE"
    },
    # High-Risk Watchlist (Aadhaar mock)
    "999988887777": {
        "matched_list": "TERROR_FINANCING_WATCHLIST",
        "reason": "Flagged financial intelligence alert",
        "severity": "CRITICAL",
        "issuing_agency": "FINANCIAL_INTEL_UNIT"
    },
    "123456789012": {
        "matched_list": "FLAGGED_FRAUD",
        "reason": "Test sample flagged as revoked identity credential",
        "severity": "MEDIUM",
        "issuing_agency": "UIDAI_REVOCATION_REGISTRY"
    }
}


def check_document_blacklist(document_number: Optional[str]) -> Dict[str, Any]:
    """
    Checks if a document number is flagged on any border control watchlist.
    
    Args:
        document_number: Document serial number, passport number, visa number, or Aadhaar UID.
        
    Returns:
        Dict:
            is_blacklisted: bool
            matched_list: Optional[str]
            reason: Optional[str]
            severity: Optional[str]
    """
    if not document_number:
        return {
            "is_blacklisted": False,
            "matched_list": None,
            "reason": None,
            "severity": None
        }
        
    clean_number = document_number.strip().upper().replace("<", "").replace(" ", "")
    
    if clean_number in MOCK_BLACKLIST_DATABASE:
        hit = MOCK_BLACKLIST_DATABASE[clean_number]
        return {
            "is_blacklisted": True,
            "matched_list": hit["matched_list"],
            "reason": hit["reason"],
            "severity": hit["severity"],
            "issuing_agency": hit["issuing_agency"]
        }
        
    return {
        "is_blacklisted": False,
        "matched_list": None,
        "reason": None,
        "severity": None
    }


def get_all_blacklisted_records() -> Dict[str, Dict[str, Any]]:
    """Returns the full blacklist registry for testing or administrative review."""
    return MOCK_BLACKLIST_DATABASE


if __name__ == "__main__":
    print("=" * 70)
    print("Border Control Mock Watchlist - Self Test")
    print("=" * 70)
    
    # Test Clean Document
    clean_res = check_document_blacklist("A98765432")
    print(f"Clean Doc (A98765432): {clean_res}")
    assert clean_res["is_blacklisted"] is False
    
    # Test Stolen Passport
    stolen_res = check_document_blacklist("L898902C3")
    print(f"Stolen Doc (L898902C3): {stolen_res}")
    assert stolen_res["is_blacklisted"] is True
    assert stolen_res["matched_list"] == "LOST_STOLEN_TRAVEL_DOCS"
    
    # Test Aadhaar Watchlist
    aadhaar_res = check_document_blacklist("9999 8888 7777")
    print(f"Aadhaar Watchlist (999988887777): {aadhaar_res}")
    assert aadhaar_res["is_blacklisted"] is True
    assert aadhaar_res["matched_list"] == "TERROR_FINANCING_WATCHLIST"
    
    print("\n[OK] Blacklist check engine verified successfully!")

"""
Backward-compatibility forwarder for reports package.
"""
from orchestration_platform.reports.forensic_generator import (
    generate_forensic_pdf,
    compute_report_hash,
    make_numbered_canvas
)

"""
Synthetic Test Asset Suite Generator
====================================
Generates programmatic image fixtures for the 4 core verification scenarios:
1. Clean/Valid Case: Matched passport, visa, and selfie images.
2. Traditional Tamper Case: Document image with altered/spliced text triggering ELA.
3. GenAI/Deepfake Case: Synthetic portrait image with artificial diffusion texture.
4. Cross-Document Inconsistency Case: Documents with mismatched names / inverted date sequences.
"""

import os
import sys
import io
from typing import Dict, Any, List, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from pathlib import Path

# Dynamic Root & Package Path Resolution
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PLATFORM_DIR = Path(__file__).resolve().parent.parent
TESTS_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORM_DIR))

sample_dir = str(TESTS_DIR / "sample_data")
os.makedirs(sample_dir, exist_ok=True)


def draw_simple_face(draw_obj, center_x, center_y, radius=60):
    """Draws a clean synthetic face graphic on image canvas."""
    # Head
    draw_obj.ellipse(
        [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
        fill=(225, 195, 175), outline=(50, 50, 50), width=3
    )
    # Eyes
    draw_obj.ellipse([center_x - 25, center_y - 20, center_x - 10, center_y - 5], fill=(40, 40, 40))
    draw_obj.ellipse([center_x + 10, center_y - 20, center_x + 25, center_y - 5], fill=(40, 40, 40))
    # Nose
    draw_obj.line([center_x, center_y - 5, center_x, center_y + 15], fill=(100, 100, 100), width=2)
    # Smile
    draw_obj.arc([center_x - 30, center_y + 5, center_x + 30, center_y + 35], start=0, end=180, fill=(150, 30, 30), width=3)


def generate_valid_passport() -> str:
    """Creates clean TD3 Passport image with valid MRZ and VIZ text."""
    img = Image.new('RGB', (1200, 800), color=(250, 248, 240))
    draw = ImageDraw.Draw(img)

    try:
        font_hdr = ImageFont.load_default(size=36)
        font_txt = ImageFont.load_default(size=28)
        font_mrz = ImageFont.load_default(size=32)
    except Exception:
        font_hdr = font_txt = font_mrz = None

    # Header
    draw.rectangle([0, 0, 1200, 100], fill=(20, 40, 80))
    draw.text((400, 30), "PASSPORT / PASSEPORT", fill=(255, 255, 255), font=font_hdr)

    # Face photo box
    draw.rectangle([60, 150, 360, 540], fill=(210, 210, 210), outline=(0, 0, 0), width=3)
    draw_simple_face(draw, 210, 330, radius=75)

    # VIZ Data
    draw.text((410, 150), "Type: P  Code: UTO  Passport No: A98765432", fill=(0, 0, 0), font=font_txt)
    draw.text((410, 210), "Surname / Nom: ERIKSSON", fill=(0, 0, 0), font=font_txt)
    draw.text((410, 270), "Given Names / Prénoms: ANNA MARIA", fill=(0, 0, 0), font=font_txt)
    draw.text((410, 330), "Nationality: UTOPIAN", fill=(0, 0, 0), font=font_txt)
    draw.text((410, 390), "Date of Birth: 12 AUG 1974", fill=(0, 0, 0), font=font_txt)
    draw.text((410, 450), "Sex: F", fill=(0, 0, 0), font=font_txt)
    draw.text((410, 510), "Date of Expiry: 01 JAN 2034", fill=(0, 0, 0), font=font_txt)

    # MRZ Zone (Bottom 30%)
    draw.rectangle([0, 580, 1200, 800], fill=(255, 255, 255))
    line1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
    line2 = "A987654326UTO7408122F3401011ZE184226B<<<<<16"

    draw.text((30, 620), line1, fill=(0, 0, 0), font=font_mrz)
    draw.text((30, 700), line2, fill=(0, 0, 0), font=font_mrz)

    path = os.path.join(sample_dir, "valid_passport.jpg")
    img.save(path, "JPEG", quality=95)
    return path


def generate_valid_visa() -> str:
    """Creates clean TD2 Visa image with matching name & MRZ."""
    img = Image.new('RGB', (1000, 650), color=(245, 250, 245))
    draw = ImageDraw.Draw(img)

    try:
        font_hdr = ImageFont.load_default(size=32)
        font_txt = ImageFont.load_default(size=26)
        font_mrz = ImageFont.load_default(size=28)
    except Exception:
        font_hdr = font_txt = font_mrz = None

    # Header
    draw.rectangle([0, 0, 1000, 80], fill=(40, 90, 50))
    draw.text((340, 24), "VISA - ENTRY PERMIT", fill=(255, 255, 255), font=font_hdr)

    # VIZ Data
    draw.text((50, 110), "Visa No: L8988901C4", fill=(0, 0, 0), font=font_txt)
    draw.text((50, 160), "Name: ERIKSSON, ANNA MARIA", fill=(0, 0, 0), font=font_txt)
    draw.text((50, 210), "Nationality: UTO", fill=(0, 0, 0), font=font_txt)
    draw.text((50, 260), "Date of Birth: 12 AUG 1974", fill=(0, 0, 0), font=font_txt)
    draw.text((50, 310), "Expiry Date: 10 SEP 2029", fill=(0, 0, 0), font=font_txt)

    # MRZ Zone (Bottom 30%)
    draw.rectangle([0, 450, 1000, 650], fill=(255, 255, 255))
    line1 = "V<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<"
    line2 = "L8988901C4XXX7408128F9612109<<<<<<<6"

    draw.text((30, 480), line1, fill=(0, 0, 0), font=font_mrz)
    draw.text((30, 550), line2, fill=(0, 0, 0), font=font_mrz)

    path = os.path.join(sample_dir, "valid_visa.jpg")
    img.save(path, "JPEG", quality=95)
    return path


def generate_valid_selfie() -> str:
    """Creates clean traveler live selfie image."""
    img = Image.new('RGB', (600, 800), color=(235, 235, 240))
    draw = ImageDraw.Draw(img)
    draw_simple_face(draw, 300, 380, radius=140)

    path = os.path.join(sample_dir, "valid_selfie.jpg")
    img.save(path, "JPEG", quality=95)
    return path


def generate_tampered_ela_document() -> str:
    """
    Creates a document image with multi-compression digital splicing/editing:
    a) Save baseline document at high quality (quality=95).
    b) Paste a modified text box patch saved at uncompressed high contrast.
    c) Save composite at quality=100 to produce high ELA recompression noise variance (mean_diff > 8.0).
    """
    base_path = generate_valid_passport()
    base_img = Image.open(base_path).convert('RGB')

    # Create a spliced patch with high-contrast altered text & border
    patch = Image.new('RGB', (600, 250), color=(255, 200, 200))
    p_draw = ImageDraw.Draw(patch)
    try:
        font = ImageFont.load_default(size=28)
    except Exception:
        font = None

    p_draw.text((20, 20), "ALTERED EXPIRY: 99 DEC 2099", fill=(255, 0, 0), font=font)
    p_draw.text((20, 80), "TAMPERED NAME: FAKE JOHN SMITH", fill=(0, 0, 255), font=font)
    p_draw.rectangle([0, 0, 599, 249], outline=(255, 0, 0), width=8)

    # Paste uncompressed spliced patch over original document canvas
    base_img.paste(patch, (410, 200))

    path = os.path.join(sample_dir, "tampered_ela_document.jpg")
    base_img.save(path, "JPEG", quality=100, comment=b"ALTERED_ELA_TAMPERED_FIXTURE")
    return path


def generate_genai_synthetic_face() -> str:
    """
    Creates a synthetic portrait image with ultra-smooth artificial texture
    and uniform gradients designed to yield a high AI probability score (> 75%).
    """
    img = Image.new('L', (600, 800), color=220)
    draw = ImageDraw.Draw(img)

    # Draw synthetic face features
    draw.ellipse([200, 250, 400, 510], fill=180)
    draw.ellipse([240, 320, 280, 360], fill=120)
    draw.ellipse([320, 320, 360, 360], fill=120)
    draw.polygon([(300, 350), (280, 410), (320, 410)], fill=150)
    draw.arc([250, 420, 350, 460], start=0, end=180, fill=100, width=5)

    # Apply Gaussian blur to create smooth diffusion texture without camera sensor noise
    img = img.filter(ImageFilter.GaussianBlur(radius=8)).convert('RGB')

    path = os.path.join(sample_dir, "genai_synthetic_face.jpg")
    img.save(path, "JPEG", quality=95)
    return path


def generate_inconsistent_visa() -> str:
    """Creates a visa document with mismatched name (JOHN SMITH vs ANNA ERIKSSON) and doc number (V12345678)."""
    img = Image.new('RGB', (1000, 650), color=(245, 250, 245))
    draw = ImageDraw.Draw(img)

    try:
        font_hdr = ImageFont.load_default(size=32)
        font_txt = ImageFont.load_default(size=26)
        font_mrz = ImageFont.load_default(size=28)
    except Exception:
        font_hdr = font_txt = font_mrz = None

    draw.rectangle([0, 0, 1000, 80], fill=(40, 90, 50))
    draw.text((340, 24), "VISA - ENTRY PERMIT", fill=(255, 255, 255), font=font_hdr)

    draw.text((50, 110), "Visa No: V12345678", fill=(0, 0, 0), font=font_txt)
    draw.text((50, 160), "Name: SMITH, JOHN", fill=(0, 0, 0), font=font_txt)
    draw.text((50, 210), "Nationality: USA", fill=(0, 0, 0), font=font_txt)
    draw.text((50, 260), "Date of Birth: 01 JAN 1990", fill=(0, 0, 0), font=font_txt)

    # MRZ Zone
    draw.rectangle([0, 450, 1000, 650], fill=(255, 255, 255))
    line1 = "V<UTOSMITH<<JOHN<<<<<<<<<<<<<<<<<<<<"
    line2 = "V123456784USA9001018M2812319<<<<<<<6"

    draw.text((30, 480), line1, fill=(0, 0, 0), font=font_mrz)
    draw.text((30, 550), line2, fill=(0, 0, 0), font=font_mrz)

    path = os.path.join(sample_dir, "inconsistent_visa.jpg")
    img.save(path, "JPEG", quality=95)
    return path


def build_all_test_assets() -> Dict[str, str]:
    """Generates all synthetic test assets and returns path mapping."""
    print("Generating Synthetic Test Asset Suite in tests/sample_data/...")
    assets = {
        "valid_passport": generate_valid_passport(),
        "valid_visa": generate_valid_visa(),
        "valid_selfie": generate_valid_selfie(),
        "tampered_ela_doc": generate_tampered_ela_document(),
        "genai_synthetic_face": generate_genai_synthetic_face(),
        "inconsistent_visa": generate_inconsistent_visa()
    }
    for k, v in assets.items():
        print(f"  [CREATED] {k} -> {os.path.basename(v)}")
    return assets


if __name__ == "__main__":
    build_all_test_assets()

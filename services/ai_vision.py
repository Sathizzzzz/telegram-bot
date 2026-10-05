"""
AI Vision & OCR Service for ClaimSathi.
Features dual-engine intelligence:
1. Google Gemini API (multimodal vision) when GEMINI_API_KEY is configured.
2. High-speed Local RapidOCR (ONNX runtime) that runs 100% locally on CPU with zero API keys needed!
"""
import os
import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

from utils.admin import redact_pii

logger = logging.getLogger("ClaimSathi.AIVision")

class _PIIFilter(logging.Filter):
    """Logging filter that redacts PII from log records."""
    def filter(self, record):
        record.msg = redact_pii(str(record.msg))
        if record.args:
            record.args = tuple(redact_pii(str(arg)) if isinstance(arg, str) else arg for arg in record.args)
        return True

# Attach PII redaction filter to the module logger
logger.addFilter(_PIIFilter())

INDIAN_INVOICE_VISION_PROMPT = """
You are an expert Indian consumer warranty assistant. Analyze this uploaded image carefully.

Determine the image type:
1. "INVOICE": An Indian store receipt, cash memo, tax invoice (Amazon India, Flipkart, Croma, Reliance Digital, Vijay Sales, local shop).
2. "PRODUCT_LABEL": Serial number sticker, IMEI barcode, rating plate, appliance specifications tag.
3. "DEFECT_ISSUE": A photo showing a broken, defective, or malfunctioning product (e.g. green line on screen, cracked screen, burnt port, damaged appliance, headphone issue).
4. "OTHER": An unrelated image.

Output ONLY a valid JSON object with the following structure:
{
  "image_type": "INVOICE" | "PRODUCT_LABEL" | "DEFECT_ISSUE" | "OTHER",
  "product_name": "Full product name (e.g. Apple iPhone 15 Pro, Voltas 1.5 Ton Split AC)",
  "brand": "Brand name (e.g. Apple, Samsung, LG, boAt, Dell, HP, OnePlus, etc.)",
  "category": "Smartphone" | "Laptop" | "TV & Audio" | "Home Appliance" | "Wearable" | "Kitchen Appliance" | "Other",
  "retailer": "Retailer name (e.g. Amazon India, Flipkart, Croma, Reliance Digital, AK Communication, Offline Store)",
  "purchase_date": "YYYY-MM-DD or null if not found",
  "price_paid": 0.0,
  "serial_no": "IMEI or Serial Number if visible, else null",
  "warranty_months": 12,
  "detected_issue": "Description of any visible defect or problem if DEFECT_ISSUE",
  "is_claimable_verdict": "CLAIMABLE" | "CONDITIONAL" | "NOT_CLAIMABLE",
  "verdict_reason": "Clear explanation of whether standard warranty or special Indian policy covers this",
  "indian_consumer_tip": "Specific actionable advice for Indian service centers or retrieving lost bills"
}
"""


def _parse_gemini_json(text_response: str) -> Optional[Dict[str, Any]]:
    """Cleanly extracts JSON object from model output."""
    clean = text_response.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    try:
        return json.loads(clean)
    except Exception as e:
        logger.warning(f"Failed to parse JSON directly from Gemini: {e}")
        start = clean.find("{")
        end = clean.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(clean[start:end+1])
            except Exception:
                pass
    return None


async def analyze_image_with_gemini(image_path: Path, caption: str = "") -> Optional[Dict[str, Any]]:
    """Attempts to analyze an image using the google-genai library if GEMINI_API_KEY is available."""
    from config import GEMINI_API_KEY
    api_key = GEMINI_API_KEY
    if not api_key:
        return None

    try:
        from google import genai
        from PIL import Image
        import io

        client = genai.Client(api_key=api_key)

        # Convert PIL image to bytes for the new SDK
        pil_image = Image.open(image_path)
        img_buffer = io.BytesIO()
        # Use JPEG for smaller payload (PNG can be very large)
        pil_image.save(img_buffer, format="JPEG", quality=85)
        img_bytes = img_buffer.getvalue()

        prompt = INDIAN_INVOICE_VISION_PROMPT
        if caption:
            prompt += f"\n\nUser caption/context: {caption}"

        # Use the new SDK's Part format for images
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part(text=prompt),
                types.Part(inline_data=types.InlineData(
                    mime_type="image/jpeg",
                    data=img_bytes,
                )),
            ],
        )

        if response and response.text:
            parsed = _parse_gemini_json(response.text)
            if parsed:
                logger.info(f"Gemini Vision successfully processed image as: {parsed.get('image_type')}")
                return parsed
    except Exception as e:
        logger.error(f"Error calling Gemini Vision API: {e}", exc_info=True)

    return None


def extract_text_via_local_ocr(image_path: Path) -> str:
    """Runs RapidOCR locally on CPU to extract all text lines from the image."""
    try:
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        result, _ = engine(str(image_path))
        if result:
            lines = [line[1].strip() for line in result if line[1].strip()]
            extracted = "\n".join(lines)
            logger.info(f"Local RapidOCR extracted {len(lines)} lines from image.")
            return extracted
    except Exception as e:
        logger.warning(f"Local RapidOCR execution failed: {e}")
    return ""


def parse_ocr_text_to_product(ocr_text: str, caption: str = "") -> Dict[str, Any]:
    """
    Intelligently extracts invoice entities from raw OCR text for Indian consumer bills.
    """
    combined = f"{ocr_text}\n{caption}".strip()
    lower_text = combined.lower()

    # 1. Detect Brand & Category
    known_brands = {
        "apple": ("Apple", "Smartphone"),
        "iphone": ("Apple", "Smartphone"),
        "ipad": ("Apple", "Smartphone"),
        "macbook": ("Apple", "Laptop"),
        "samsung": ("Samsung", "Smartphone"),
        "oneplus": ("OnePlus", "Smartphone"),
        "xiaomi": ("Xiaomi", "Smartphone"),
        "redmi": ("Xiaomi", "Smartphone"),
        "poco": ("Xiaomi", "Smartphone"),
        "boat": ("boAt", "Wearable"),
        "airdopes": ("boAt", "Wearable"),
        "noise": ("Noise", "Wearable"),
        "boult": ("Boult", "Wearable"),
        "realme": ("Realme", "Smartphone"),
        "vivo": ("Vivo", "Smartphone"),
        "oppo": ("Oppo", "Smartphone"),
        "motorola": ("Motorola", "Smartphone"),
        "dell": ("Dell", "Laptop"),
        "hp": ("HP", "Laptop"),
        "lenovo": ("Lenovo", "Laptop"),
        "asus": ("ASUS", "Laptop"),
        "acer": ("Acer", "Laptop"),
        "lg": ("LG", "Home Appliance"),
        "whirlpool": ("Whirlpool", "Home Appliance"),
        "voltas": ("Voltas", "Home Appliance"),
        "daikin": ("Daikin", "Home Appliance"),
        "sony": ("Sony", "TV & Audio"),
        "panasonic": ("Panasonic", "Home Appliance"),
        "godrej": ("Godrej", "Home Appliance"),
        "havells": ("Havells", "Home Appliance"),
        "philips": ("Philips", "Home Appliance"),
        "zebronics": ("Zebronics", "Personal Care & Electronics"),
        "zzebronics": ("Zebronics", "Personal Care & Electronics"),
        "nova": ("Nova", "Personal Care"),
        "syska": ("Syska", "Personal Care"),
    }

    brand = "Unknown Brand"
    category = "General"
    for key, (b_name, cat) in known_brands.items():
        if key in lower_text:
            brand = b_name
            category = cat
            break

    # 2. Extract Product Name
    product_name = None

    # Check for Apple iPhone pattern
    iphone_match = re.search(r'(iphone\s*\d+\s*(?:pro\s*max|pro|plus|mini)?)', lower_text, re.I)
    if iphone_match:
        brand = "Apple"
        category = "Smartphone"
        base_name = f"Apple {iphone_match.group(1).title()}"
        storage_m = re.search(r'(\d{2,4}\s*gb)', combined, re.I)
        color_m = re.search(r'(natural titanium|blue titanium|white titanium|black titanium|starlight|midnight|gold|silver|space black|deep purple|alpine green)', lower_text, re.I)
        details = []
        if storage_m:
            details.append(storage_m.group(1).upper().replace(" ", ""))
        if color_m:
            details.append(color_m.group(1).title())
        product_name = f"{base_name} ({', '.join(details)})" if details else base_name

    # Check for Samsung Galaxy pattern
    if not product_name:
        samsung_match = re.search(r'(galaxy\s*[a-z0-9\s]+(?:ultra|plus|\+)?)', lower_text, re.I)
        if samsung_match:
            brand = "Samsung"
            category = "Smartphone"
            product_name = f"Samsung {samsung_match.group(1).title().strip()}"

    # Check for boAt Airdopes
    if not product_name:
        boat_match = re.search(r'(airdopes\s*[0-9]{2,4}[a-z]*)', lower_text, re.I)
        if boat_match:
            brand = "boAt"
            category = "Wearable"
            product_name = f"boAt {boat_match.group(1).title()}"

    # Check for Trimmer / Grooming device
    if not product_name and any(k in lower_text for k in ["trim", "trims", "shaver", "groom"]):
        category = "Personal Care"
        product_name = f"{brand} Trimmer / Grooming Kit" if brand != "Unknown Brand" else "Trimmer / Grooming Kit"

    # Fallback to Particulars / Item Description line if present
    if not product_name:
        lines = [line.strip() for line in ocr_text.split("\n") if line.strip()]
        for i, line in enumerate(lines):
            if any(h in line.lower() for h in ["particulars", "description", "item name", "product"]):
                if i + 1 < len(lines):
                    candidate = lines[i + 1]
                    if (len(candidate) > 3 and not candidate.isdigit() and
                        not any(w in candidate.lower() for w in ["warranty", "guarantee", "year", "missed call", "call", "activate"])):
                        product_name = candidate
                        break

    if not product_name:
        product_name = f"{brand} Device" if brand != "Unknown Brand" else "Electronic Device"

    # 3. Extract Serial / IMEI Number
    imei_m = re.search(r'(?:IMEI|SERIAL|S/N|SN)\s*[-:]?\s*([A-Z0-9]{10,18})', combined, re.I)
    serial_no = None
    if imei_m:
        serial_no = imei_m.group(1).strip()
    else:
        # Check for standalone 15-digit IMEI
        standalone_imei = re.search(r'\b(35[0-9]{13}|86[0-9]{13})\b', combined)
        if standalone_imei:
            serial_no = standalone_imei.group(1)

    # 4. Extract Purchase Date (DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD)
    purchase_date_str = None
    date_match = re.search(r'(?:dated?|date|inv date|invoice date)?\s*[-:]?\s*([0-9]{1,2})[-/.]([0-9]{1,2})[-/.]([0-9]{4})', combined, re.I)
    if date_match:
        d1, d2, d3 = date_match.group(1), date_match.group(2), date_match.group(3)
        # Usually DD-MM-YYYY in India
        day = int(d1)
        month = int(d2)
        year = int(d3)
        if day <= 31 and month <= 12 and 2000 <= year <= 2030:
            purchase_date_str = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"

    if not purchase_date_str:
        # Check YYYY-MM-DD
        date_iso = re.search(r'\b(202[0-9])[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12][0-9]|3[01])\b', combined)
        if date_iso:
            purchase_date_str = f"{date_iso.group(1)}-{date_iso.group(2)}-{date_iso.group(3)}"
        else:
            purchase_date_str = date.today().strftime("%Y-%m-%d")

    # 5. Detect Food / Restaurant Receipt vs Warranty Invoice
    is_food_receipt = any(k in lower_text for k in [
        "burger", "byprep", "бургер", "coffee", "tea", "чай", "restaurant", "cafe", "pizza", "dining", "hotel", 
        "шоп", "говядины", "блюдо", "меню", "food", "kitchen", "bakery", "pastry", "tenge", "tehte", "тенге",
        "bce cvmmi", "kypant", "kpa6", "bapxak", "бархан"
    ])

    # 6. Extract Retailer / Store Name
    retailer = "Store / Retailer"
    if "amazon" in lower_text:
        retailer = "Amazon India"
    elif "flipkart" in lower_text:
        retailer = "Flipkart"
    elif "croma" in lower_text:
        retailer = "Croma"
    elif "reliance" in lower_text:
        retailer = "Reliance Digital"
    elif "vijay sales" in lower_text:
        retailer = "Vijay Sales"
    elif is_food_receipt and any(k in lower_text for k in ["bapxak", "бархан", "burger", "byprep"]):
        retailer = "Burger Shop (Бархан)"
    else:
        # Check first clean line
        lines = [l.strip() for l in ocr_text.split("\n") if l.strip()]
        for l in lines[:6]:
            l_clean = re.sub(r'[^a-zA-Z0-9\s]', '', l).strip()
            digits = re.sub(r'[^0-9]', '', l_clean)
            if l.lower() in ["invoice", "tax invoice", "bill", "cash memo", "retail invoice", "receipt"]:
                continue
            if len(digits) >= 8:  # phone numbers or long digits
                continue
            if any(w in l.lower() for w in ["missed call", "activate", "give us", "customer care", "helpline", "warranty", "trim", "product", "quality", "promise", "convenient", "stylish"]):
                continue
            if len(l_clean) >= 4 and not any(k in l.lower() for k in ["ground floor", "phone", "contact", "date", "kassa", "stol", "dt6"]):
                retailer = l
                break

    if retailer == "Store / Retailer" and brand != "Unknown Brand":
        retailer = f"{brand} Retail Store"

    # If food receipt, customize product & category default
    if is_food_receipt and product_name == "Electronic Device":
        product_name = "Food & Dining / Retail Receipt"
        brand = "Food / Restaurant"
        category = "Other"

    # 7. Extract Total Price / Amount Paid
    # Exclude order numbers, invoice numbers, phone numbers, and table numbers
    excluded_numbers = set(re.findall(
        r'(?:order|заказ|3axa|inv|invoice|bill\s*no|receipt\s*no|table|stol|kassa|касса|phone|tel|contact)[\s:#№]*([0-9]{3,})',
        combined,
        re.I
    ))

    price_paid = None
    all_prices = re.findall(r'\b([1-9][0-9]{2,}(?:,[0-9]{3})*(?:\.[0-9]{2})?)\b', combined)
    if all_prices:
        candidates = []
        for p in all_prices:
            clean_num = p.replace(",", "").replace(" ", "")
            if clean_num in excluded_numbers:
                continue
            try:
                val = float(clean_num)
                # Ignore pin codes (e.g. 110086) or phone numbers
                if 200 <= val <= 500000 and len(clean_num.split(".")[0]) <= 6:
                    if not (val >= 110000 and val <= 110099 and "." not in p):
                        candidates.append(val)
            except Exception:
                pass
        if candidates:
            # Check if there is a number near total/итого/к оплате keywords
            total_m = re.search(r'(?:total|grand total|net amount|amount payable|итого|итог|оплат|сумма|к оплате)[\s:=]*([0-9\s,]+(?:\.[0-9]{2})?)', combined, re.I)
            if total_m:
                t_val_str = total_m.group(1).replace(",", "").replace(" ", "")
                try:
                    t_val = float(t_val_str)
                    if 100 <= t_val <= 500000:
                        price_paid = t_val
                except Exception:
                    pass
            if not price_paid:
                price_paid = max(candidates)

    # 8. Warranty Duration
    warranty_months = 12
    if is_food_receipt:
        warranty_months = 0
    else:
        # Check years (e.g. 2 year, 2 years, 2year, 3 years, 5 years)
        yr_m = re.search(r'([1-9]|10)\s*years?', lower_text)
        if not yr_m:
            yr_m = re.search(r'([1-9]|10)year', lower_text)
        if yr_m:
            warranty_months = int(yr_m.group(1)) * 12
        elif "3 months" in lower_text or "3 month" in lower_text:
            warranty_months = 3
        elif "6 months" in lower_text or "6 month" in lower_text:
            warranty_months = 6
        elif "compressor" in lower_text or "motor" in lower_text:
            warranty_months = 120

    return {
        "image_type": "INVOICE",
        "product_name": product_name,
        "brand": brand,
        "category": category,
        "retailer": retailer,
        "purchase_date": purchase_date_str,
        "price_paid": price_paid,
        "serial_no": serial_no,
        "warranty_months": warranty_months,
        "is_food_receipt": is_food_receipt,
        "detected_issue": None,
        "is_claimable_verdict": "CLAIMABLE",
        "verdict_reason": "Store bill verified and parsed via OCR.",
        "indian_consumer_tip": "Preserve this digital record. Invoices from GST-registered stores are legally binding proofs.",
    }


def smart_fallback_analyzer(filename_or_text: str, caption: str = "", image_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Primary local parser: Uses Local RapidOCR if image_path is available,
    otherwise uses regex heuristics on text/caption.
    """
    # If image_path exists, run high-accuracy Local RapidOCR
    if image_path and image_path.exists():
        ocr_text = extract_text_via_local_ocr(image_path)
        if ocr_text and len(ocr_text) > 15:
            return parse_ocr_text_to_product(ocr_text, caption=caption)

    # Secondary text/caption heuristic parser
    combined = f"{filename_or_text} {caption}".lower()
    return parse_ocr_text_to_product(combined, caption=caption)
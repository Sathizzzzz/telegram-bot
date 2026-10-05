"""
Warranty Intelligence & Claim Diagnostics for the Indian Consumer Mindset.
Tailored for common Indian scenarios: lost bills, service center rejections,
brand-specific warranty clauses, and claim eligibility.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import re

@dataclass
class ClaimDiagnosis:
    verdict: str  # "CLAIMABLE", "CONDITIONAL", "NOT_CLAIMABLE", "LOST_BILL_WORKAROUND"
    verdict_emoji: str
    verdict_title: str
    confidence: str
    explanation: str
    service_center_advice: str
    lost_bill_tip: str
    brand_policy_note: Optional[str] = None
    action_steps: List[str] = None

# Known Indian manufacturer policies & special warranty recall programs
INDIAN_BRAND_SPECIAL_POLICIES = {
    "oneplus": (
        "🟢 *OnePlus Lifetime Screen Warranty*: In India, OnePlus offers a Lifetime Free Screen Replacement "
        "for OnePlus 8, 9, 10, and 11 series affected by the green line issue after software updates, "
        "provided there is no visible external physical crack or liquid damage."
    ),
    "samsung": (
        "🟢 *Samsung Green Line / Display Policy*: Samsung India provides a one-time free screen replacement "
        "for select Galaxy S20, S21, and S22 series devices experiencing green line display lines, even slightly "
        "out of warranty, subject to physical inspection."
    ),
    "xiaomi": (
        "🟢 *Xiaomi / Poco Extended Motherboard Warranty*: Poco X3 Pro and select Mi series phones have an "
        "officially extended 2-year warranty for motherboard/reboot loop issues in India."
    ),
    "boat": (
        "🟢 *boAt Doorstep Replacement*: For Airdopes & headsets, boAt does not usually repair units. "
        "If you register a complaint online at support.boat-lifestyle.com, a courier picks up the faulty unit "
        "and delivers a brand new sealed replacement within 5-7 days."
    ),
    "apple": (
        "🍏 *Apple No-Bill Policy*: Apple Authorised Service Providers (AASPs like Aptronix, Imagine, Unicorn) "
        "verify warranty purely via the device Serial Number / IMEI on Apple's GSX database. A physical bill is rarely needed."
    ),
    "dell": (
        "💻 *Dell Service Tag Onsite*: Dell tracks warranty via the 7-character Service Tag sticker on the laptop base. "
        "Most consumer laptops have Next Business Day Onsite warranty where a technician visits your home with parts."
    ),
    "hp": (
        "💻 *HP Serial Lookup*: HP verifies warranty via serial number online. Bill is only needed if purchase date "
        "in HP system differs from your actual invoice date."
    ),
    "lg": (
        "❄️ *LG Appliance Motor/Compressor*: While the overall appliance warranty is 1 year, LG gives 10 years warranty "
        "on Smart Inverter compressors (Refrigerators) and Direct Drive motors (Washing Machines)."
    ),
    "whirlpool": (
        "❄️ *Whirlpool 10-Year Warranty*: 10-year warranty applies to the compressor and motor on most refrigerators and washers."
    ),
}

# Standard Indian appliance warranty periods (in months)
INDIAN_CATEGORY_WARRANTY_DEFAULTS = {
    "smartphone": {"standard": 12, "battery": 12, "charger": 6, "screen": 12},
    "laptop": {"standard": 12, "battery": 12, "adapter": 12},
    "tablet": {"standard": 12, "battery": 12},
    "tv": {"standard": 12, "panel": 24},
    "air_conditioner": {"standard": 12, "pcb": 60, "compressor": 120},
    "refrigerator": {"standard": 12, "compressor": 120},
    "washing_machine": {"standard": 24, "motor": 120},
    "microwave": {"standard": 12, "magnetron": 36},
    "water_purifier": {"standard": 12, "membrane": 12},
    "earbuds": {"standard": 12, "replacement_type": "swap"},
    "smartwatch": {"standard": 12},
    "mixer_grinder": {"standard": 24, "motor": 60},
    "geyser": {"standard": 24, "tank": 84, "heating_element": 48},
}

LOST_BILL_RETRIEVAL_GUIDE = {
    "amazon": (
        "📦 *How to get Amazon India Bill in 1 Minute:*\n"
        "1. Open Amazon App -> Tap Profile icon -> *'Your Orders'*\n"
        "2. Search for the product -> Tap *'Download Invoice'*\n"
        "3. Select *'Tax Invoice'* and save the PDF. Service centers accept this without question!"
    ),
    "flipkart": (
        "🛍️ *How to get Flipkart Bill in 1 Minute:*\n"
        "1. Open Flipkart App -> Tap *'Account'* -> *'Orders'*\n"
        "2. Tap the item -> Scroll down to *'Download Invoice'*\n"
        "3. Valid legal GST invoice is saved directly to your phone."
    ),
    "croma": (
        "🏬 *How to get Croma Duplicate Bill:*\n"
        "• Visit any Croma store or call 1800-572-7662 with your registered phone number used during checkout.\n"
        "• Croma will instantly WhatsApp / email you the duplicate tax invoice."
    ),
    "reliance_digital": (
        "⚡ *How to get Reliance Digital Bill:*\n"
        "• Walk into any Reliance Digital showroom or message their official WhatsApp bot (1800 889 1055).\n"
        "• Provide your mobile number; they can retrieve bills up to 5 years old from their POS system."
    ),
    "offline_store": (
        "🏪 *Local Offline Electronic Shop:*\n"
        "• All GST-registered shops are legally mandated to retain sales ledgers for 6 years.\n"
        "• If you know the approximate month and payment mode (UPI, card, or phone number), the shopkeeper can reprint a duplicate GST invoice."
    ),
}

def analyze_claim_eligibility(
    issue_description: str,
    brand: Optional[str] = None,
    product_category: Optional[str] = None,
    days_since_purchase: Optional[int] = None
) -> ClaimDiagnosis:
    """
    Evaluates whether an issue is claimable under warranty in India,
    taking into account Indian service center behaviors and loopholes.
    """
    text = (issue_description or "").lower()
    brand_clean = (brand or "").lower().strip()
    cat_clean = (product_category or "").lower().strip()

    # Match brand policy note if any
    brand_note = None
    for b_key, note in INDIAN_BRAND_SPECIAL_POLICIES.items():
        if b_key in brand_clean or b_key in text:
            brand_note = note
            break

    # 1. Clear Non-Claimable cases: Physical cracks, water/liquid damage (unless ADLD)
    has_physical_crack = any(k in text for k in ["cracked", "shattered", "broken screen", "tuta", "phoot gaya", "gir gaya", "dropped"])
    has_water_damage = any(k in text for k in ["water", "liquid", "pani", "soaked", "rain", "spill", "swimming"])
    has_burn_damage = any(k in text for k in ["burned", "jal gaya", "burnt", "fire", "spark"])

    # 2. Definite Claimable cases: Green line, motherboard dead, audio failure, AC cooling, mic failure
    has_green_line = any(k in text for k in ["green line", "pink line", "vertical line", "display line", "hari line"])
    has_motherboard = any(k in text for k in ["motherboard", "dead", "won't turn on", "not turning on", "bootloop", "reboot loop", "chalu nahi"])
    has_audio_issue = any(k in text for k in ["one side", "left side", "right side", "sound low", "mic", "awaz", "speaker", "charging case"])
    has_appliance_issue = any(k in text for k in ["cooling", "compressor", "thanda nahi", "motor", "drum", "gas leak", "pcb error"])

    # Lost bill specific query
    has_lost_bill_query = any(k in text for k in ["lost bill", "no bill", "bill kho gaya", "bill nahi hai", "without bill", "bina bill"])

    # Evaluation logic
    if has_green_line and any(b in (brand_clean + " " + text) for b in ["oneplus", "samsung", "vivo", "realme", "motorola"]):
        return ClaimDiagnosis(
            verdict="CLAIMABLE",
            verdict_emoji="🟢",
            verdict_title="Likely 100% Free Claimable (Special Screen Recall Policy)",
            confidence="High",
            explanation=(
                "Green/Pink display lines appearing after software updates on AMOLED screens are widely recognized "
                "manufacturing defects in India. OnePlus and Samsung provide FREE screen replacement even if the standard "
                "1-year warranty has lapsed, as long as there is no dent or glass crack on the frame."
            ),
            service_center_advice=(
                "⚠️ *Important Tip*: When visiting the service center, clearly state: "
                "'This line appeared suddenly after a regular software OTA update. The phone has never been dropped or exposed to water.' "
                "Inspect your screen in front of the technician to ensure they note 'Zero external physical damage' on the job sheet."
            ),
            lost_bill_tip="Bill is usually NOT required for OnePlus/Samsung screen replacement if your IMEI is clean and device is Indian variant.",
            brand_policy_note=brand_note,
            action_steps=[
                "Take a photo of your screen displaying the IMEI number (*#06#) as proof.",
                "Back up your phone data before handing it over.",
                "Visit an official brand Authorized Service Center (avoid third-party repair shops)."
            ]
        )

    if has_physical_crack and not has_green_line:
        return ClaimDiagnosis(
            verdict="NOT_CLAIMABLE",
            verdict_emoji="🔴",
            verdict_title="Standard Warranty Rejection (Physical Damage)",
            confidence="High",
            explanation=(
                "Manufacturer standard warranties in India strictly exclude accidental physical damage, cracked glass, or dents. "
                "Service centers will classify this as 'Customer Induced Damage' (CID)."
            ),
            service_center_advice=(
                "• Official brand repair will charge for a complete display/housing assembly replacement.\n"
                "• Did you buy this with an ICICI/HDFC/Axis credit card or on Amazon/Flipkart? Check if you had complimentary "
                "Accidental Damage Protection (ADLD) or purchase protection insurance.\n"
                "• Alternatively, check Cashify trade-in to exchange the damaged device for instant cash."
            ),
            lost_bill_tip="Even with a bill, standard warranty does not cover shattered screens unless you purchased an insurance plan like OneAssist or Onsitego.",
            brand_policy_note=brand_note,
            action_steps=[
                "Check your bank/credit card purchase benefits or credit card travel insurance.",
                "Check OneAssist / Onsitego active coverage.",
                "Tap 'Resale Value (Cashify)' to see what your device is worth as-is."
            ]
        )

    if has_water_damage:
        return ClaimDiagnosis(
            verdict="NOT_CLAIMABLE",
            verdict_emoji="🔴",
            verdict_title="Liquid Ingress Not Covered under Standard Warranty",
            confidence="High",
            explanation=(
                "All modern electronics have internal Liquid Contact Indicators (LCI stickers) that turn red or pink on moisture contact. "
                "Even IP68 water-resistant phones explicitly void warranty for liquid ingress in India."
            ),
            service_center_advice=(
                "Technicians open the back cover and inspect LCI stickers. If the sticker is white, liquid has not reached the motherboard "
                "and you can claim for internal component failure. Do NOT turn on or plug the device into a charger!"
            ),
            lost_bill_tip="Check if you had an active extended warranty with accidental liquid damage (ADLD) coverage.",
            brand_policy_note=brand_note,
            action_steps=[
                "Do NOT charge the device (prevents short circuits).",
                "Keep in a dry environment with silica gel packets.",
                "If covered by OneAssist or device insurance, file an ADLD insurance claim."
            ]
        )

    if has_audio_issue or "earbud" in cat_clean or "earbud" in text or "boat" in brand_clean or "noise" in brand_clean:
        return ClaimDiagnosis(
            verdict="CLAIMABLE",
            verdict_emoji="🟢",
            verdict_title="100% Eligible for Free Brand Replacement",
            confidence="High",
            explanation=(
                "TWS Earbuds with one side not charging, low sound output, or mic failure are the #1 claimed issue in India. "
                "Brands like boAt, Noise, Boult, Realme, and OnePlus do not repair earbuds — they provide a complete NEW replacement unit!"
            ),
            service_center_advice=(
                "• For boAt & Noise: You do not need to stand in line at a service center! Go to their official support portal, "
                "enter your serial number, and book a free doorstep pickup.\n"
                "• Keep the charging case and both earbuds in the original box (or safely wrapped)."
            ),
            lost_bill_tip="If bought on Amazon/Flipkart, download your Tax Invoice in 30 seconds from your order history. That invoice is 100% valid!",
            brand_policy_note=brand_note,
            action_steps=[
                "Clean the brass charging pins on the earbud with a dry cotton swab (sometimes resolves connection issues).",
                "Download your Amazon/Flipkart invoice or enter serial number on the brand support site.",
                "Book free courier pickup."
            ]
        )

    if has_appliance_issue or any(c in cat_clean for c in ["ac", "refrigerator", "washing", "appliance"]):
        return ClaimDiagnosis(
            verdict="CLAIMABLE",
            verdict_emoji="🟢",
            verdict_title="Claimable (Check Component Warranty)",
            confidence="High",
            explanation=(
                "In India, major home appliances have dual-tier warranties:\n"
                "1. Comprehensive Product Warranty: 1 or 2 Years (Covers all internal parts & visits)\n"
                "2. Extended Component Warranty: 5 to 10 Years on Compressors (AC/Fridge), Motors (Washing Machines), and Inverter PCBs!"
            ),
            service_center_advice=(
                "Even if your 1-year general warranty expired, if the compressor or inverter motor failed, the BRAND MUST REPLACE THE PART FOR FREE! "
                "You only pay a nominal technician visit fee (~₹350-₹500) and gas charging if applicable."
            ),
            lost_bill_tip=(
                "Appliances have a metal rating plate sticker on the side/back showing the Model Number, Serial Number, and Manufacturing Month. "
                "Technicians can verify brand warranty from this sticker even if the paper bill is missing!"
            ),
            brand_policy_note=brand_note,
            action_steps=[
                "Take a clear photo of the silver/metal serial plate on the appliance body.",
                "Call the brand toll-free number from our Brand Support Directory to book a home visit.",
                "Insist on original spare parts under the 10-year motor/compressor warranty."
            ]
        )

    # General / Default Diagnosis
    return ClaimDiagnosis(
        verdict="CLAIMABLE" if (days_since_purchase is None or days_since_purchase <= 365) else "CONDITIONAL",
        verdict_emoji="🟢" if (days_since_purchase is None or days_since_purchase <= 365) else "🟡",
        verdict_title="Likely Covered under Manufacturer Warranty",
        confidence="Medium",
        explanation=(
            "Internal manufacturing defects, sudden hardware failures, sensor malfunction, charging port issues, "
            "and software corruption without external physical abuse are fully covered under standard brand warranty in India."
        ),
        service_center_advice=(
            "• Service centers in India are legally obligated under the Consumer Protection Act 2019 to rectify manufacturing defects.\n"
            "• Request an official Job Sheet with detailed defect remarks when leaving the item.\n"
            "• Never admit to dropping or opening the device if it failed spontaneously."
        ),
        lost_bill_tip=(
            "• If purchased online: Download the Tax Invoice from Amazon / Flipkart / Croma.\n"
            "• If purchased offline: Visit the store or call their billing desk with the mobile number you provided at purchase.\n"
            "• Brands like Apple, Dell, Lenovo, HP check warranty purely via Serial Number online!"
        ),
        brand_policy_note=brand_note,
        action_steps=[
            "Backup personal data if it is a phone or laptop.",
            "Locate the serial number on the device body or settings.",
            "Check our Brand Support Directory for official toll-free & WhatsApp support."
        ]
    )
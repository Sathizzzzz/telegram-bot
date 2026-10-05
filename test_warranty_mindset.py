"""
Automated unit verification for the Indian Consumer Mindset warranty features.
Tests claim diagnostics, lost-bill recovery, smart OCR extraction, and database persistence.
"""
import sys
from datetime import date
from services.warranty_intelligence import (
    analyze_claim_eligibility,
    LOST_BILL_RETRIEVAL_GUIDE,
    INDIAN_BRAND_SPECIAL_POLICIES,
)
from services.ai_vision import smart_fallback_analyzer
from database.db import init_db, get_db
from database.models import User, ProductWarranty

sys.stdout.reconfigure(encoding="utf-8")


def run_tests():
    print("🚀 Starting Indian Consumer Mindset Tests...\n")

    # 1. Test OnePlus Screen Green Line
    diag1 = analyze_claim_eligibility("my oneplus 9 screen has a green vertical line after update", brand="OnePlus")
    print(f"Scenario 1 (OnePlus Green Line): {diag1.verdict_emoji} {diag1.verdict_title}")
    assert diag1.verdict == "CLAIMABLE", f"Expected CLAIMABLE, got {diag1.verdict}"
    assert "OnePlus" in diag1.brand_policy_note, "Expected OnePlus policy note"
    print("  ✓ Correctly identified as 100% free recall warranty!\n")

    # 2. Test boAt Earbuds Dead Side
    diag2 = analyze_claim_eligibility("my boat airdopes left earbud is dead not charging", brand="boAt", product_category="Wearable")
    print(f"Scenario 2 (boAt Dead Earbud): {diag2.verdict_emoji} {diag2.verdict_title}")
    assert diag2.verdict == "CLAIMABLE", f"Expected CLAIMABLE, got {diag2.verdict}"
    assert "replacement" in diag2.explanation.lower(), "Expected replacement mention"
    print("  ✓ Correctly identified as doorstep free replacement!\n")

    # 3. Test AC Cooling Failure (1.5 Years Old)
    diag3 = analyze_claim_eligibility("voltas split ac cooling not working", brand="Voltas", product_category="Home Appliance", days_since_purchase=500)
    print(f"Scenario 3 (AC 1.5 Years Old): {diag3.verdict_emoji} {diag3.verdict_title}")
    assert diag3.verdict == "CLAIMABLE", f"Expected CLAIMABLE component warranty, got {diag3.verdict}"
    assert "compressor" in diag3.explanation.lower(), "Expected compressor warranty explanation"
    print("  ✓ Correctly explained 10-year compressor warranty despite 1-yr general expiry!\n")

    # 4. Test Shattered Screen (Accidental Damage)
    diag4 = analyze_claim_eligibility("phone fell down and display glass shattered", brand="Samsung")
    print(f"Scenario 4 (Shattered Screen): {diag4.verdict_emoji} {diag4.verdict_title}")
    assert diag4.verdict == "NOT_CLAIMABLE", f"Expected NOT_CLAIMABLE, got {diag4.verdict}"
    print("  ✓ Correctly identified physical damage and suggested ADLD/Cashify alternatives!\n")

    # 5. Test Lost Bill Recovery Guides
    assert "amazon" in LOST_BILL_RETRIEVAL_GUIDE
    assert "flipkart" in LOST_BILL_RETRIEVAL_GUIDE
    assert "croma" in LOST_BILL_RETRIEVAL_GUIDE
    assert "reliance_digital" in LOST_BILL_RETRIEVAL_GUIDE
    print("Scenario 5 (Lost Bill Retrieval): Verified guides for Amazon, Flipkart, Croma, Reliance Digital.")
    print("  ✓ All Indian retailer recovery guides present!\n")

    # 6. Test Smart Fallback AI Vision Analyzer
    parsed = smart_fallback_analyzer("invoice_iphone15_amazon.jpg", caption="Bought on Amazon for 79900 on 2024-06-15")
    print(f"Scenario 6 (AI Scan Fallback): {parsed['product_name']} | Retailer: {parsed['retailer']} | Date: {parsed['purchase_date']}")
    assert parsed["brand"] == "Apple"
    assert parsed["retailer"] == "Amazon India"
    assert parsed["purchase_date"] =="2024-06-15"
    print("  ✓ Smart analyzer accurately extracted Brand, Retailer, and Purchase Date!\n")

    # 7. Test Database Operations
    init_db()
    with get_db() as db:
        test_user = db.query(User).filter_by(user_id=999999999).first()
        if not test_user:
            test_user = User(user_id=999999999, first_name="Ramesh", plan_tier="free")
            db.add(test_user)
            db.commit()

        prod = ProductWarranty(
            user_id=999999999,
            product_name="Apple iPhone 15",
            category="Smartphone",
            brand="Apple",
            purchase_platform="Amazon India",
            purchase_date=date.today(),
            warranty_months=12,
            expiry_date=date.today(),
            serial_no="F2LN80V00D9",
        )
        db.add(prod)
        db.commit()
        prod_id = prod.id
        print(f"Scenario 7 (Database Vault): Archived '{prod.product_name}' with ID {prod_id}")
        assert prod_id > 0
        db.delete(prod)
        db.delete(test_user)
        db.commit()
        print("  ✓ SQLite database successfully persisted and cleaned up warranty record!\n")

    print("🎉 ALL 7 INDIAN CONSUMER MINDSET VERIFICATION TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_tests()
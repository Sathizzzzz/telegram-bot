"""
Quick syntax and module integrity check for WarrantyBot India.
"""
import py_compile
from pathlib import Path

files = [
    "config.py",
    "database/models.py",
    "database/db.py",
    "services/brand_directory.py",
    "services/warranty_intelligence.py",
    "services/ai_vision.py",
    "services/pdf_service.py",
    "services/supabase_storage.py",
    "utils/keyboards.py",
    "utils/admin.py",
    "handlers/start.py",
    "handlers/add_product.py",
    "handlers/claim_checker.py",
    "handlers/vault.py",
    "handlers/monetization.py",
    "handlers/claim.py",
    "handlers/reminders.py",
    "main.py",
]

import sys
sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent
all_good = True
for f in files:
    target = base / f
    try:
        py_compile.compile(str(target), doraise=True)
        print(f"[OK] Syntax OK: {f}")
    except Exception as e:
        print(f"[ERROR] Error in {f}: {e}")
        all_good = False

if all_good:
    print(f"\nAll {len(files)} Python modules compiled with ZERO syntax errors!")
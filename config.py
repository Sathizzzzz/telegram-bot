import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the bot directory
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Token
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Optional Google Gemini API Key for Vision & OCR
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# OpenRouter API Key for AI Vision (Free tier available at openrouter.ai)
# Supports: google/gemini-flash-1.5-8b, meta-llama/llama-3.2-11b-vision-instruct, etc.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-flash-1.5-8b")

# Database URL (Supports SQLite locally, and Supabase / PostgreSQL in Cloud)
raw_db_url = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'warranty_vault.db'}")
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
DATABASE_URL = raw_db_url

# Supabase Storage Configuration (Optional for Cloud Bill Storage)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "invoices")

# Admins
ADMIN_IDS = [
    int(uid.strip())
    for uid in os.getenv("ADMIN_IDS", "").split(",")
    if uid.strip().isdigit()
]

# Monetization & Affiliate Links
ONEASSIST_CODE = os.getenv("ONEASSIST_AFFILIATE_CODE", "WB_INDIA")
ONSITEGO_CODE = os.getenv("ONSITEGO_AFFILIATE_CODE", "WB_INDIA")
CASHIFY_CODE = os.getenv("CASHIFY_PARTNER_CODE", "WB_INDIA")
URBAN_COMPANY_REF = os.getenv("URBAN_COMPANY_REF", "WB_INDIA")

# Invoice Storage Directory (Local Cache)
INVOICE_STORAGE_DIR = BASE_DIR / os.getenv("INVOICE_STORAGE_DIR", "data/invoices")
INVOICE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
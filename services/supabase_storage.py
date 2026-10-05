"""
Supabase Storage Client for ClaimSathi.
Provides permanent cloud storage for store receipts, bills, and PDFs.
Uses lightweight asynchronous httpx requests with zero heavy SDK dependencies.
Gracefully falls back to local disk storage when Supabase is not configured.
"""
import logging
from pathlib import Path
from typing import Optional
import httpx
from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET

logger = logging.getLogger("ClaimSathi.SupabaseStorage")


def is_supabase_configured() -> bool:
    """Checks if Supabase credentials are provided."""
    return bool(SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL.startswith("http"))


async def upload_invoice_to_supabase(local_file_path: Path, filename: str) -> Optional[str]:
    """
    Uploads a bill/invoice file to Supabase Storage bucket.
    Returns the public/accessible URL of the stored file if successful, otherwise None.
    """
    if not is_supabase_configured():
        logger.debug("Supabase not configured. Using local disk storage.")
        return None

    if not local_file_path.exists():
        logger.error(f"Cannot upload: local file does not exist: {local_file_path}")
        return None

    clean_url = SUPABASE_URL.rstrip("/")
    endpoint = f"{clean_url}/storage/v1/object/{SUPABASE_BUCKET}/{filename}"

    # Determine MIME type
    ext = local_file_path.suffix.lower()
    content_type = "image/jpeg"
    if ext == ".png":
        content_type = "image/png"
    elif ext == ".pdf":
        content_type = "application/pdf"
    elif ext == ".webp":
        content_type = "image/webp"

    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apiKey": SUPABASE_KEY,
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    try:
        with open(local_file_path, "rb") as f:
            file_bytes = f.read()

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(endpoint, headers=headers, content=file_bytes)
            if resp.status_code in (200, 201):
                public_url = f"{clean_url}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"
                logger.info(f"Successfully uploaded {filename} to Supabase Storage: {public_url}")
                return public_url
            else:
                logger.warning(f"Supabase Storage upload returned status {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.error(f"Failed to upload {filename} to Supabase Storage: {e}")

    return None


async def download_invoice_from_supabase(filename_or_url: str) -> Optional[bytes]:
    """Downloads invoice bytes from Supabase Storage."""
    if not is_supabase_configured():
        return None

    clean_url = SUPABASE_URL.rstrip("/")
    if filename_or_url.startswith("http"):
        url = filename_or_url
    else:
        url = f"{clean_url}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename_or_url}"

    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apiKey": SUPABASE_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.content
    except Exception as e:
        logger.error(f"Failed to download from Supabase Storage: {e}")

    return None
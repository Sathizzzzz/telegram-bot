"""
OpenRouter Vision Service for ClaimSathi.
Uses OpenRouter's OpenAI-compatible API to analyze bill/invoice images
with top-tier vision models (Gemini Flash, LLaMA Vision, etc.).

OpenRouter provides free-tier access to powerful vision models:
- google/gemini-flash-1.5-8b (Free, fast, great for Indian invoices)
- meta-llama/llama-3.2-11b-vision-instruct (Free, open-source)
- google/gemini-2.0-flash-exp:free (Free experimental)

Docs: https://openrouter.ai/docs
Get free API key: https://openrouter.ai/keys
"""
import base64
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from config import OPENROUTER_API_KEY
from utils.admin import redact_pii

logger = logging.getLogger("ClaimSathi.OpenRouter")


class _PIIFilter(logging.Filter):
    """Logging filter that redacts PII from log records."""
    def filter(self, record):
        record.msg = redact_pii(str(record.msg))
        if record.args:
            record.args = tuple(
                redact_pii(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True


logger.addFilter(_PIIFilter())

# OpenRouter endpoint — 100% OpenAI-compatible
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Default model: Free Gemini Flash — best for Indian invoice OCR
# Override with OPENROUTER_MODEL env var if needed
DEFAULT_MODEL = "google/gemini-flash-1.5-8b"

# Fallback free models (tried in order if default fails)
FALLBACK_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.2-11b-vision-instruct:free",
]

VISION_PROMPT = """You are an expert Indian consumer warranty assistant. Analyze this uploaded bill/invoice image carefully.

Output ONLY a valid JSON object with this structure (no markdown, no explanation):
{
  "image_type": "INVOICE" | "PRODUCT_LABEL" | "DEFECT_ISSUE" | "OTHER",
  "product_name": "Full product name (e.g. Apple iPhone 15 Pro, Voltas 1.5 Ton Split AC)",
  "brand": "Brand name (e.g. Apple, Samsung, LG, boAt, Dell, HP, OnePlus)",
  "category": "Smartphone" | "Laptop" | "TV & Audio" | "Home Appliance" | "Wearable" | "Kitchen Appliance" | "Personal Care" | "Other",
  "retailer": "Store name (e.g. Amazon India, Flipkart, Croma, Reliance Digital, local shop name)",
  "purchase_date": "YYYY-MM-DD or null",
  "price_paid": 0.0,
  "serial_no": "IMEI or Serial Number if visible, else null",
  "warranty_months": 12,
  "detected_issue": "Description of defect if DEFECT_ISSUE, else null",
  "is_claimable_verdict": "CLAIMABLE" | "CONDITIONAL" | "NOT_CLAIMABLE",
  "verdict_reason": "Why this is or is not claimable under Indian consumer law",
  "indian_consumer_tip": "Specific tip for Indian consumers (service center, GST bill importance, etc.)"
}"""


def _encode_image_to_base64(image_path: Path) -> Optional[str]:
    """Encodes an image file to base64 string for the API."""
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to encode image to base64: {e}")
        return None


def _get_mime_type(image_path: Path) -> str:
    """Determines MIME type from file extension."""
    ext = image_path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }
    return mime_map.get(ext, "image/jpeg")


def _parse_json_response(text: str) -> Optional[Dict[str, Any]]:
    """Safely extracts JSON from model output, handling markdown fences."""
    clean = text.strip()
    # Strip markdown code fences if present
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean.strip())
    try:
        return json.loads(clean)
    except Exception:
        # Try extracting just the JSON object
        start = clean.find("{")
        end = clean.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(clean[start:end + 1])
            except Exception:
                pass
    logger.warning("Could not parse JSON from OpenRouter response.")
    return None


async def analyze_image_with_openrouter(
    image_path: Path,
    caption: str = "",
    model: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Sends an image to OpenRouter's vision API and returns structured invoice data.

    Args:
        image_path: Local path to the image file.
        caption: Optional user-provided context/caption.
        model: Override the default model (optional).

    Returns:
        Parsed dict with invoice fields, or None if all attempts fail.
    """
    if not OPENROUTER_API_KEY:
        logger.info("OPENROUTER_API_KEY not configured — skipping OpenRouter vision.")
        return None

    if not image_path or not image_path.exists():
        logger.warning(f"Image not found at path: {image_path}")
        return None

    # Encode image
    image_b64 = _encode_image_to_base64(image_path)
    if not image_b64:
        return None

    mime_type = _get_mime_type(image_path)

    # Build prompt with optional caption context
    prompt = VISION_PROMPT
    if caption:
        prompt += f"\n\nUser note about this image: {caption}"

    # Build OpenAI-compatible message payload
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{image_b64}",
                    },
                },
            ],
        }
    ]

    # Determine model order to try
    selected_model = model or DEFAULT_MODEL
    models_to_try = [selected_model] + [m for m in FALLBACK_MODELS if m != selected_model]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # OpenRouter recommends these headers for app attribution
        "HTTP-Referer": "https://t.me/ClaimSathiBot",
        "X-Title": "ClaimSathi - Indian Warranty Manager",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt_model in models_to_try:
            payload = {
                "model": attempt_model,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.1,  # Low temperature = more deterministic JSON
            }

            try:
                logger.info(f"Calling OpenRouter with model: {attempt_model}")
                response = await client.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    if content:
                        parsed = _parse_json_response(content)
                        if parsed:
                            logger.info(
                                f"✅ OpenRouter ({attempt_model}) successfully analyzed image "
                                f"as: {parsed.get('image_type', 'UNKNOWN')}"
                            )
                            # Tag which model was used (useful for debugging)
                            parsed["_analyzed_by"] = f"openrouter/{attempt_model}"
                            return parsed

                elif response.status_code == 402:
                    logger.warning(f"OpenRouter model {attempt_model} requires credits — trying next.")
                elif response.status_code == 429:
                    logger.warning(f"OpenRouter rate limit hit for {attempt_model} — trying next.")
                else:
                    logger.warning(
                        f"OpenRouter returned {response.status_code} for {attempt_model}: "
                        f"{response.text[:200]}"
                    )

            except httpx.TimeoutException:
                logger.warning(f"OpenRouter timed out for model: {attempt_model}")
            except Exception as e:
                logger.error(f"OpenRouter error with {attempt_model}: {e}")

    logger.error("All OpenRouter models failed — falling back to next engine.")
    return None

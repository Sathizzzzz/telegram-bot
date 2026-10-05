"""
Admin Authorization & Security Utilities for ClaimSathi.
Provides admin checks, rate limiting, and input sanitization helpers.
"""
import functools
import html
import logging
import re
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_IDS

logger = logging.getLogger("ClaimSathi.Admin")


def is_admin(user_id: int) -> bool:
    """Checks if a Telegram user ID is in the configured admin list."""
    return user_id in ADMIN_IDS


def admin_required(func: Callable):
    """
    Decorator that gates a handler behind admin authorization.
    Returns a no-op response if the user is not an admin.
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_user = update.effective_user
        if not tg_user or not is_admin(tg_user.id):
            logger.warning(f"Unauthorized admin access attempt by user {tg_user.id if tg_user else 'unknown'}")
            if update.message:
                await update.message.reply_text("🚫 *Access Denied.* Admin privileges required.")
            elif update.callback_query:
                await update.callback_query.answer("🚫 Admins only.", show_alert=True)
            return None
        return await func(update, context)
    return wrapper


def sanitize_text(text: str, max_length: int = 200) -> str:
    """
    Strips HTML, trims whitespace, and truncates user-supplied text
    before storing it in the database. Prevents stored XSS if ever
    rendered in a web admin panel or exported.
    """
    if not text:
        return ""
    cleaned = html.escape(str(text).strip())
    return cleaned[:max_length]


def sanitize_serial(text: str) -> str:
    """
    Sanitizes serial numbers / IMEIs: keeps only alphanumeric
    characters, dashes, and spaces, then truncates to 30 chars.
    """
    if not text:
        return ""
    cleaned = re.sub(r'[^A-Za-z0-9\- ]', '', str(text).strip())
    return cleaned[:30]


def redact_pii(text: str) -> str:
    """
    Redacts potential PII from log messages: masks serial numbers,
    phone numbers, and prices.
    """
    if not text:
        return ""
    # Mask 10+ digit numbers (IMEI, serial, phone)
    text = re.sub(r'\b\d{10,16}\b', '[REDACTED]', text)
    # Mask email-like patterns
    text = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL_REDACTED]', text)
    return text


class RateLimiter:
    """
    Simple in-memory rate limiter for Telegram handlers.
    Prevents bot flood / spam attacks.
    """
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._user_timestamps: dict[int, list[float]] = {}

    def check(self, user_id: int) -> bool:
        """Returns True if the user is within rate limits, False otherwise."""
        import time
        now = time.time()
        if user_id not in self._user_timestamps:
            self._user_timestamps[user_id] = []
        timestamps = self._user_timestamps[user_id]
        # Remove timestamps outside the window
        cutoff = now - self.window_seconds
        timestamps = [t for t in timestamps if t > cutoff]
        self._user_timestamps[user_id] = timestamps
        if len(timestamps) >= self.max_requests:
            return False
        timestamps.append(now)
        return True


# Global rate limiter instance: 10 requests per 60 seconds per user
rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
"""
WarrantyBot India — Main Application Entrypoint.
Automated Warranty Vault & Monetization Engine for India (Free on Telegram).
"""
import sys
import logging
from datetime import time
from telegram import Update, BotCommand
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from config import BOT_TOKEN, ADMIN_IDS
from database.db import init_db
from handlers.start import (
    start_command,
    help_command,
    show_language_selector,
    handle_set_language_callback,
)
from handlers.add_product import get_add_product_conversation_handler
from handlers.vault import show_vault_catalog, handle_vault_callback
from handlers.monetization import (
    show_monetization_hub,
    handle_monetization_callbacks,
    show_pro_membership,
)
from handlers.claim import show_brand_directory, handle_brand_directory_callback
from handlers.claim_checker import (
    get_claim_checker_conversation_handler,
    show_lost_bill_guide_callback,
    start_claim_checker,
)
from handlers.reminders import simulate_30_day_alert, check_expiring_warranties_job
from utils.admin import admin_required, rate_limiter, redact_pii

# Configure Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ClaimSathi")


def main():
    """Starts the ClaimSathi application."""
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        print("\n" + "=" * 70)
        print("⚠️  MISSING TELEGRAM BOT TOKEN!")
        print("=" * 70)
        print("To run ClaimSathi (क्लेम साथी) for FREE on Telegram:")
        print("1. Open Telegram and search for @BotFather")
        print("2. Send: /newbot and choose a name (e.g. ClaimSathi)")
        print("3. Copy the HTTP API token provided by @BotFather")
        print("4. Paste it into the .env file:")
        print("   TELEGRAM_BOT_TOKEN=your_token_from_botfather")
        print("5. Run this script again: python main.py")
        print("=" * 70 + "\n")
        sys.exit(1)

    # 1. Initialize local SQLite tables
    logger.info("Initializing database...")
    init_db()

    # 2. Build Telegram Application with resilient timeouts and auto-registered commands
    async def post_init(application):
        commands = [
            BotCommand("start", "🚀 Start ClaimSathi & View Dashboard"),
            BotCommand("add", "📸 Upload Bill / Register Device"),
            BotCommand("vault", "📂 My Vault / View Saved Bills"),
            BotCommand("claim", "🔍 Is It Claimable? (Check Defects)"),
            BotCommand("lostbill", "🧾 Claim Warranty Without a Bill"),
            BotCommand("brands", "🎧 Official Brand Helpline & WhatsApp"),
            BotCommand("language", "🌐 Switch Language (English / हिंदी)"),
            BotCommand("alert30", "🔔 Simulate 30-Day Expiry Reminder"),
            BotCommand("help", "💡 How to Use ClaimSathi"),
        ]
        await application.bot.set_my_commands(commands)
        logger.info("Bot commands successfully registered with Telegram Bot API!")

    logger.info("Building Telegram bot application...")
    request_cfg = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0)
    app = ApplicationBuilder().token(BOT_TOKEN).request(request_cfg).post_init(post_init).build()

    # 3. Register Conversation Handlers
    app.add_handler(get_claim_checker_conversation_handler())
    app.add_handler(get_add_product_conversation_handler())

    # 4. Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("language", show_language_selector))
    app.add_handler(CommandHandler("lang", show_language_selector))
    app.add_handler(CommandHandler("claim", start_claim_checker))
    app.add_handler(CommandHandler("lostbill", show_lost_bill_guide_callback))
    app.add_handler(CommandHandler("vault", show_vault_catalog))
    app.add_handler(CommandHandler("catalog", show_vault_catalog))
    app.add_handler(CommandHandler("monetize", admin_required(show_monetization_hub)))
    app.add_handler(CommandHandler("brands", show_brand_directory))
    app.add_handler(CommandHandler("alert30", admin_required(simulate_30_day_alert)))

    # 5. Reply Keyboard Handlers
    app.add_handler(MessageHandler(filters.Regex(r"^(🔍 Is It Claimable\?|🔍 क्या यह क्लेम होगा\?)$"), start_claim_checker))
    app.add_handler(MessageHandler(filters.Regex(r"^(🧾 Lost Bill Recovery Guide|🧾 खोए बिल की गाइड)$"), show_lost_bill_guide_callback))
    app.add_handler(MessageHandler(filters.Regex(r"^(📂 My Vault / Catalog|📂 मेरा वॉल्ट / कैटलॉग)$"), show_vault_catalog))
    app.add_handler(MessageHandler(filters.Regex(r"^(🛡️ Extended Warranty & AMC|🛡️ एक्सटेंडेड वारंटी)$"), show_monetization_hub))
    app.add_handler(MessageHandler(filters.Regex(r"^(🔔 Simulate 30-Day Alert|🔔 30-दिन एक्सपायरी अलर्ट)$"), simulate_30_day_alert))
    app.add_handler(MessageHandler(filters.Regex(r"^(🎧 Brand Support Directory|🎧 ब्रांड सपोर्ट डायरेक्टरी)$"), show_brand_directory))
    app.add_handler(MessageHandler(filters.Regex(r"^(🌐 Language / भाषा|🌐 Language \(English/हिंदी\))$"), show_language_selector))
    app.add_handler(MessageHandler(filters.Regex("^💎 Pro Vault Membership$"), show_pro_membership))

    # 6. Callback Query Handlers
    app.add_handler(
        CallbackQueryHandler(
            handle_set_language_callback,
            pattern="^set_lang:",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            show_lost_bill_guide_callback,
            pattern="^lost_bill_guide$",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            show_brand_directory,
            pattern="^open_directory$",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            handle_vault_callback,
            pattern="^(list_vault|view_prod:|view_bill:|gen_pdf:|brand_help:|del_item:)",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            handle_monetization_callbacks,
            pattern="^(extend_warn:|cashify:|lead:|pro_upgrade_)",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            handle_brand_directory_callback,
            pattern="^dir_brand:",
        )
    )

    # 7. Scheduled Daily Job for Expiry Alerts
    if app.job_queue:
        app.job_queue.run_daily(
            check_expiring_warranties_job,
            time=time(hour=9, minute=0, second=0),
            name="daily_warranty_expiry_scan",
        )
        logger.info("Daily warranty scan scheduled at 09:00 AM.")

    # 8. Error Handler
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Unhandled error: {redact_pii(str(context.error))}")
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ An unexpected error occurred. Our team has been notified. Please try again later."
                )
            except Exception:
                pass

    app.add_error_handler(error_handler)

    logger.info("ClaimSathi is online! Listening for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
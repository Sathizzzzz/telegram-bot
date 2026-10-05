"""
Automated Reminders & Simulation Engine for WarrantyBot India.
Handles scheduled daily warranty scans and the instant 'Simulate 30-Day Alert' event.
"""
from datetime import date
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.db import get_db
from database.models import ProductWarranty, ReminderLog, User
from config import CASHIFY_CODE, ONEASSIST_CODE


async def simulate_30_day_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Simulates the exact 30-Day Alert incoming event shown in the PRD simulator screenshot.
    """
    tg_user = update.effective_user
    if not tg_user:
        return

    # Check if user has an actual product in vault, otherwise simulate with sample iPhone 15 Pro
    with get_db() as db:
        prod = (
            db.query(ProductWarranty)
            .filter_by(user_id=tg_user.id)
            .order_by(ProductWarranty.expiry_date.asc())
            .first()
        )

    device_name = prod.product_name if prod else "Apple iPhone 15 Pro (256 GB)"
    retailer = prod.purchase_platform if prod else "Apple Store / Amazon"
    serial = prod.serial_no if prod else "DNQW98XXPL91"

    alert_text = (
        f"🚨 *AUTOMATED WARRANTY EXPIRY ALERT: 30 DAYS LEFT* 🚨\n\n"
        f"📱 *Device:* {device_name}\n"
        f"🏪 *Retailer:* {retailer}\n"
        f"🔢 *Serial/IMEI:* `{serial}`\n"
        f"⏳ *Time Remaining:* Exactly *30 Days* until manufacturer warranty expires!\n\n"
        f"💡 *Action Checklist Before Warranty Lapses:*\n"
        f"1️⃣ *Final Free Checkup*: Visit authorized center for any minor screen, battery, or microphone issues before repairs become chargeable.\n"
        f"2️⃣ *Extend Your Warranty*: Buy an additional 1-year coverage pack starting at ₹1,499.\n"
        f"3️⃣ *Upgrade via Cashify*: Trade-in your device now for *up to 35% higher buyback* while warranty is still active!\n\n"
        f"👇 *Choose your action:* "
    )

    pid = prod.id if prod else 0
    keyboard = [
        [
            InlineKeyboardButton("🛡️ Extend Warranty with OneAssist", callback_data=f"lead:OneAssist:{pid}"),
        ],
        [
            InlineKeyboardButton("💰 Check Cashify Trade-in Price", callback_data=f"lead:Cashify:{pid}"),
        ],
        [
            InlineKeyboardButton("📑 Download Claim Dossier PDF", callback_data=f"gen_pdf:{pid}" if prod else "no_prod_pdf"),
        ],
    ]

    await update.message.reply_text(
        alert_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def check_expiring_warranties_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Background automated job that scans the database daily and notifies users of approaching warranty expirations.
    """
    today = date.today()
    milestones = [30, 15, 7, 1, 0]

    with get_db() as db:
        products = db.query(ProductWarranty).all()

        for prod in products:
            days_left = (prod.expiry_date - today).days

            if days_left in milestones:
                log_tag = f"{days_left}_day" if days_left > 0 else "expired"

                # Check if already notified for this milestone
                already_sent = (
                    db.query(ReminderLog)
                    .filter_by(product_id=prod.id, reminder_type=log_tag)
                    .first()
                )
                if already_sent:
                    continue

                # Prepare alert
                urgency = "🚨 *URGENT EXCLUSION WARNING*" if days_left <= 7 else "🔔 *Warranty Alert*"
                days_msg = f"in *{days_left} days*" if days_left > 0 else "*TODAY*"

                msg = (
                    f"{urgency}\n\n"
                    f"Your *{prod.product_name}* warranty expires {days_msg} ({prod.expiry_date.strftime('%d %b %Y')})!\n\n"
                    f"Take action now to prevent high out-of-warranty repair costs."
                )

                keyboard = [
                    [InlineKeyboardButton("🛡️ Extend Warranty", callback_data=f"extend_warn:{prod.id}")],
                    [InlineKeyboardButton("💰 Cashify Resale", callback_data=f"cashify:{prod.id}")],
                    [InlineKeyboardButton("📑 Claim Dossier", callback_data=f"gen_pdf:{prod.id}")],
                ]

                try:
                    await context.bot.send_message(
                        chat_id=prod.user_id,
                        text=msg,
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )
                    # Log notification
                    db.add(ReminderLog(product_id=prod.id, reminder_type=log_tag))
                    db.commit()
                except Exception as e:
                    print(f"Failed to send reminder to user {prod.user_id}: {e}")
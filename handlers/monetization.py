"""
Monetization Engine Handlers for WarrantyBot India.
Implements:
1. Extended Warranty / AMC Leads (OneAssist, Onsitego)
2. Cashify Resale & Upgrade Engine
3. Urban Company Doorstep Service Checks
4. Pro Vault Subscription
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.db import get_db
from database.models import LeadRequest, ProductWarranty, User
from config import ONEASSIST_CODE, CASHIFY_CODE, ONSITEGO_CODE


async def show_monetization_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the Warranty Protection & Monetization hub."""
    text = (
        "🛡️ *WarrantyBot India — Protection & Monetization Engine* 🇮🇳\n\n"
        "Maximize device lifespan or unlock cash before warranty expires:\n\n"
        "1️⃣ *Extended Warranty & AMC (OneAssist / Onsitego)*\n"
        "Extend coverage by 1–2 years for smartphones, laptops, TVs & ACs against accidental damage & hardware failure.\n\n"
        "2️⃣ *Sell & Upgrade on Cashify*\n"
        "Devices sold while warranty is active fetch up to *35% higher resale value*!\n\n"
        "3️⃣ *Doorstep Maintenance (Urban Company)*\n"
        "Pre-expiry health checkup & servicing for ACs, RO water purifiers, washing machines.\n\n"
        "👇 *Choose an option below:*"
    )
    keyboard = [
        [
            InlineKeyboardButton("🛡️ Get Extended Warranty Quote", callback_data="lead:OneAssist:0"),
        ],
        [
            InlineKeyboardButton("💰 Estimate Resale Price (Cashify)", callback_data="lead:Cashify:0"),
        ],
        [
            InlineKeyboardButton("🔧 Book Doorstep Appliance Check", callback_data="lead:UrbanCompany:0"),
        ],
    ]
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_monetization_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes lead generation requests and affiliate referrals."""
    query = update.callback_query
    await query.answer()
    data = query.data
    tg_user = update.effective_user

    # Handle extend warranty from product card
    if data.startswith("extend_warn:"):
        prod_id = int(data.split(":")[1])
        with get_db() as db:
            prod = db.query(ProductWarranty).filter_by(id=prod_id).first()
            p_name = prod.product_name if prod else "your device"

        text = (
            f"🛡️ *Extended Warranty Protection for {p_name}*\n\n"
            f"Protect against high repair costs once the manufacturer warranty ends:\n\n"
            f"• *OneAssist Care Pack*: Covers screen damage, liquid spills, and motherboard faults.\n"
            f"• *Onsitego Protection*: 100% cashless repairs at authorized service centers.\n\n"
            f"Select your preferred warranty provider:"
        )
        keyboard = [
            [InlineKeyboardButton("🛡️ OneAssist (Best for Mobiles & Laptops)", callback_data=f"lead:OneAssist:{prod_id}")],
            [InlineKeyboardButton("🛡️ Onsitego (Best for AC, TV & Fridge)", callback_data=f"lead:Onsitego:{prod_id}")],
            [InlineKeyboardButton("⬅️ Back", callback_data=f"view_prod:{prod_id}")],
        ]
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    # Handle Cashify resale from product card
    elif data.startswith("cashify:"):
        prod_id = int(data.split(":")[1])
        with get_db() as db:
            prod = db.query(ProductWarranty).filter_by(id=prod_id).first()
            p_name = prod.product_name if prod else "your device"
            days = prod.days_remaining if prod else 0

        text = (
            f"💰 *Sell {p_name} on Cashify India*\n\n"
            f"⏰ *Warranty Status:* {days} days left.\n\n"
            f"💡 *Pro Tip:* Selling your phone or laptop while 10–30 days of warranty remain "
            f"gives you the *highest possible buyback quote* before depreciation hits!\n\n"
            f"• Free Doorstep Pickup\n"
            f"• Instant UPI / Cash Bank Transfer\n\n"
            f"Tap below to claim an exclusive bonus ₹500 trade-in voucher:"
        )
        keyboard = [
            [
                InlineKeyboardButton(
                    "🚀 Get Instant Cashify Quote",
                    url=f"https://www.cashify.in/?referral={CASHIFY_CODE}",
                )
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data=f"view_prod:{prod_id}")],
        ]
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    # Lead submission handler
    elif data.startswith("lead:"):
        parts = data.split(":")
        provider = parts[1]
        prod_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None

        # Save lead to database
        with get_db() as db:
            lead = LeadRequest(
                user_id=tg_user.id,
                product_id=prod_id if prod_id and prod_id > 0 else None,
                service_type="extended_warranty" if provider in ["OneAssist", "Onsitego"] else provider.lower(),
                provider=provider,
                status="lead_created",
            )
            db.add(lead)
            db.commit()

        if provider == "OneAssist":
            referral_url = f"https://www.oneassist.in/?code={ONEASSIST_CODE}"
            msg = (
                f"✅ *OneAssist Extended Warranty Lead Registered!* 🛡️\n\n"
                f"Our partner OneAssist offers seamless doorstep repairs with 100% cashless claims.\n\n"
                f"👉 [Click here to complete plan activation]({referral_url})"
            )
        elif provider == "Onsitego":
            referral_url = f"https://www.onsitego.com/?ref={ONSITEGO_CODE}"
            msg = (
                f"✅ *Onsitego Protection Plan Selected!* 🛡️\n\n"
                f"Get certified brand repairs with genuine spare parts.\n\n"
                f"👉 [Click here to review Onsitego plans]({referral_url})"
            )
        elif provider == "Cashify":
            referral_url = f"https://www.cashify.in/?ref={CASHIFY_CODE}"
            msg = (
                f"✅ *Cashify Trade-in Request Initiated!* 💰\n\n"
                f"👉 [Click here to lock in your maximum buyback quote]({referral_url})"
            )
        else:
            msg = (
                f"✅ *Service Request Logged!* 🔧\n\n"
                f"A certified technician referral link has been created for your location."
            )

        await query.message.reply_text(msg, parse_mode="Markdown")


async def show_pro_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays VIP / Pro Vault membership tier."""
    text = (
        "💎 *WarrantyBot Pro Vault Membership*\n\n"
        "Upgrade your warranty management experience:\n\n"
        "✨ *Pro Benefits:*\n"
        "• ♾️ *Unlimited Devices* (Free tier: 5 items)\n"
        "• ☁️ *Encrypted Cloud Invoice Backup* (High-res PDFs & receipts)\n"
        "• 👨‍👩‍👧 *Family Sharing* (Track all household electronics in one place)\n"
        "• 📑 *Automated Brand Claim Manager* (Direct claim filing assistance)\n"
        "• 🔔 *WhatsApp + Telegram Dual Notifications*\n\n"
        "💰 *Introductory Indian Pricing:*\n"
        "• Monthly: *₹49 / month*\n"
        "• Annual Pass: *₹399 / year* (Save 32%)\n\n"
        "🔒 Zero hidden charges. Cancel anytime."
    )
    keyboard = [
        [InlineKeyboardButton("💳 Upgrade to Pro (₹399/yr)", callback_data="pro_upgrade_annual")],
        [InlineKeyboardButton("💳 Monthly Pass (₹49/mo)", callback_data="pro_upgrade_monthly")],
    ]
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
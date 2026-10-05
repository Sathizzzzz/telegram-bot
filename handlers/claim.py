"""
Brand Directory & Support Center Handler for WarrantyBot India.
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from services.brand_directory import BRAND_SUPPORT_DATA


async def show_brand_directory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays popular consumer brands for instant verified support."""
    buttons = []
    # Create 2 columns of brands
    brand_keys = list(BRAND_SUPPORT_DATA.keys())
    for i in range(0, len(brand_keys), 2):
        row = []
        b1_key = brand_keys[i]
        b1 = BRAND_SUPPORT_DATA[b1_key]
        row.append(InlineKeyboardButton(b1["name"], callback_data=f"dir_brand:{b1_key}"))
        if i + 1 < len(brand_keys):
            b2_key = brand_keys[i + 1]
            b2 = BRAND_SUPPORT_DATA[b2_key]
            row.append(InlineKeyboardButton(b2["name"], callback_data=f"dir_brand:{b2_key}"))
        buttons.append(row)

    text = (
        "🎧 *Official Brand Support Directory (India)* 🇮🇳\n\n"
        "Avoid scam customer care numbers! Select a brand below to get verified toll-free numbers, "
        "official WhatsApp service bots, and warranty registration links:"
    )

    if update.message:
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )


async def handle_brand_directory_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows detailed verified support card for selected brand."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("dir_brand:"):
        brand_key = data.split(":")[1]
        b_info = BRAND_SUPPORT_DATA.get(brand_key)
        if not b_info:
            await query.message.reply_text("Brand information not found.")
            return

    text = (
        f"🏢 *{b_info['name']} — Verified Support*\n\n"
        f"📞 *Toll-Free Helpline:*\n`{b_info['toll_free']}`\n\n"
        f"💬 *WhatsApp Support:*\n{b_info['whatsapp'] or 'Available via Toll-Free'}\n\n"
        f"🌐 *Support Portal:*\n{b_info['support_url']}\n\n"
        f"🔍 *Official Warranty Check:*\n{b_info['warranty_check_url']}\n\n"
        f"💡 _Tip: Have your serial / IMEI number and store bill ready when contacting support._"
    )

    buttons = []
    if b_info.get("whatsapp"):
        buttons.append([InlineKeyboardButton("💬 Chat on WhatsApp", url=b_info["whatsapp"])])
    if b_info.get("warranty_check_url"):
        buttons.append([InlineKeyboardButton("🔍 Check Official Warranty Online", url=b_info["warranty_check_url"])])

    await query.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
    )
"""
Product Registration Flow for ClaimSathi.
Uses AI Vision & OCR to scan invoices, bills, and device nameplates instantly.
Solves the Indian consumer problem: lost bills, forgotten warranty periods,
and hesitation over claim eligibility.
Includes an interactive 1-click field editor to easily fix or add missing details.
"""
from datetime import datetime, date, timedelta
from pathlib import Path
import logging
import re

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config import INVOICE_STORAGE_DIR
from database.db import get_db
from database.models import User, ProductWarranty
from services.ai_vision import analyze_image_with_gemini, smart_fallback_analyzer
from services.warranty_intelligence import analyze_claim_eligibility
from services.supabase_storage import upload_invoice_to_supabase
from handlers.claim_checker import render_claim_diagnosis_response
from utils.keyboards import (
    get_category_keyboard,
    get_platform_keyboard,
    get_warranty_period_keyboard,
    get_main_reply_keyboard,
    get_product_actions_keyboard,
    get_smart_confirm_keyboard,
    get_edit_fields_keyboard,
)
from utils.admin import sanitize_text, sanitize_serial

logger = logging.getLogger("ClaimSathi.AddProduct")

# Max file size for uploads: 10MB
MAX_UPLOAD_SIZE = 10 * 1024 * 1024

# Conversation States
WAITING_FOR_PHOTO = 1
WAITING_FOR_NAME = 2
WAITING_FOR_CATEGORY = 3
WAITING_FOR_PLATFORM = 4
WAITING_FOR_DATE = 5
WAITING_FOR_WARRANTY = 6
WAITING_FOR_SERIAL = 7
WAITING_FOR_SMART_CONFIRM = 8
WAITING_FOR_EDIT_CHOICE = 9
WAITING_FOR_SINGLE_FIELD_INPUT = 10


def format_smart_scan_card(user_data: dict, user_lang: str = "en") -> str:
    """Formats the rich verification card summarizing scanned or updated details."""
    product_name = user_data.get("product_name") or "Electronic Device"
    brand = user_data.get("brand") or "Unknown Brand"
    category = user_data.get("category") or "General"
    retailer = user_data.get("purchase_platform") or "Store / Retailer"
    p_date = user_data.get("purchase_date") or date.today()
    warranty_months = user_data.get("warranty_months", 12)
    expiry_date = user_data.get("expiry_date") or (p_date + timedelta(days=int(warranty_months * 30.4375)))
    days_left = (expiry_date - date.today()).days
    serial_no = user_data.get("serial_no")
    price_paid = user_data.get("price_paid")
    is_food = user_data.get("is_food_receipt", False)

    if warranty_months == 0:
        status_icon = "⚪"
        status_str = "No Standard Warranty (Retail / Dining Receipt)"
    elif days_left > 0:
        status_icon = "🟢"
        status_str = f"*{days_left} Days Remaining*"
    else:
        status_icon = "🟣"
        status_str = f"*Expired ({abs(days_left)} days ago)*"

    price_str = f"₹{price_paid:,.2f}" if price_paid else "Recorded"

    food_notice = ""
    if is_food:
        if user_lang == "hi":
            food_notice = "ℹ️ *सूचना:* यह बिल रेस्टोरेंट या सामान्य खरीद का प्रतीत होता है। आप इसे खर्च के लिए सेव कर सकते हैं या नीचे 'विवरण बदलें' से डिवाइस नाम व वारंटी सेट कर सकते हैं।\n\n"
        else:
            food_notice = "ℹ️ *Notice:* This looks like a restaurant or general retail receipt rather than an appliance or gadget warranty bill. You can still save it to your cloud vault or tap ✏️ Edit Details to adjust info.\n\n"

    if user_lang == "hi":
        return (
            f"⚡ *स्टोर बिल स्कैन और वेरीफाई हो गया!* 🛡️\n\n"
            f"{food_notice}"
            f"*{product_name}*\n"
            f"• ब्रांड: {brand}\n"
            f"• कैटेगरी: {category}\n"
            f"• विक्रेता / स्टोर: {retailer}\n"
            f"• खरीद की तारीख: *{p_date.strftime('%d %b %Y')}*\n"
            f"• वारंटी अवधि: *{warranty_months} महीने* (समाप्ति: *{expiry_date.strftime('%d %b %Y')}*)\n"
            f"• वारंटी स्टेटस: {status_icon} {status_str}\n"
            f"• सीरियल / IMEI: `{serial_no or 'फोटो द्वारा सुरक्षित'}`\n"
            f"• कुल राशि: `{price_str}`\n"
            f"• क्लाउड वॉल्ट: 🔒 *सुरक्षित आर्काइव*\n\n"
            f"💡 _क्या यह जानकारी सही है? यदि कोई जानकारी गलत या अधूरी है, तो ✏️ विवरण बदलें पर टैप करें:_"
        )
    else:
        return (
            f"⚡ *Store Bill Scanned & Verified!* 🛡️\n\n"
            f"{food_notice}"
            f"*{product_name}*\n"
            f"• Brand: {brand}\n"
            f"• Category: {category}\n"
            f"• Retailer: {retailer}\n"
            f"• Purchase Date: *{p_date.strftime('%d %b %Y')}*\n"
            f"• Warranty Duration: *{warranty_months} Months* (Expires: *{expiry_date.strftime('%d %b %Y')}*)\n"
            f"• Warranty Status: {status_icon} {status_str}\n"
            f"• Serial / IMEI: `{serial_no or 'Archived via Photo'}`\n"
            f"• Price Paid: `{price_str}`\n"
            f"• Cloud Vault: 🔒 *Bill Permanently Preserved*\n\n"
            f"💡 _Does this look accurate? If any info is wrong or missing, tap ✏️ Edit Details to update it instantly:_"
        )


async def start_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiates product registration, prompting user for invoice photo or bill."""
    context.user_data.clear()
    prompt = (
        "📸 *Step 1: Upload Store Bill, Product Photo, or Defect*\n\n"
        "Please send a *photo* or *PDF* of your invoice/receipt (Amazon, Flipkart, Croma, Reliance Digital, or offline shop).\n\n"
        "💡 *ClaimSathi Superpowers:*\n"
        "• *Instant Bill Scanning*: AI extracts the brand, date, and warranty duration automatically.\n"
        "• *Cloud Vault*: Never worry about lost or faded paper bills ever again!\n"
        "• *Claim Checker*: If your device is broken, send a photo of the defect to check if it's covered.\n\n"
        "⏩ _You can also tap /skip_photo to enter details manually._"
    )
    if update.message:
        await update.message.reply_text(prompt, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(prompt, parse_mode="Markdown")
    return WAITING_FOR_PHOTO


async def handle_direct_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered directly when user uploads a photo outside the menu."""
    return await handle_invoice_photo(update, context)


async def handle_invoice_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes uploaded photo with AI vision and smart OCR extraction."""
    message = update.message
    caption = (message.caption or "").strip()
    status_msg = await message.reply_text("🔍 *Scanning Photo & Analyzing Warranty Terms...* ⚡", parse_mode="Markdown")

    local_path = None
    file_id = None
    file_type = "photo"

    try:
        if message.photo:
            photo = message.photo[-1]
            file_id = photo.file_id
            file_type = "photo"
            tg_file = await photo.get_file()
            local_filename = f"{tg_file.file_unique_id}.jpg"
            local_path = INVOICE_STORAGE_DIR / local_filename
            await tg_file.download_to_drive(local_path)
        elif message.document:
            doc = message.document
            # Validate file size before downloading
            if doc.file_size and doc.file_size > MAX_UPLOAD_SIZE:
                await status_msg.delete()
                await message.reply_text(
                    "⚠️ *File too large.* Maximum size is 10MB. Please send a smaller file.",
                    parse_mode="Markdown",
                )
                return WAITING_FOR_PHOTO
            file_id = doc.file_id
            file_type = "document"
            tg_file = await doc.get_file()
            ext = Path(doc.file_name or "invoice.pdf").suffix or ".pdf"
            local_filename = f"{tg_file.file_unique_id}{ext}"
            local_path = INVOICE_STORAGE_DIR / local_filename
            await tg_file.download_to_drive(local_path)
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        await status_msg.delete()
        await message.reply_text(
            "❌ Error downloading file. Please try again.",
            parse_mode="Markdown",
        )
        return WAITING_FOR_PHOTO

    # Check if Gemini Vision is available
    ai_data = None
    cloud_url = None
    if local_path and local_path.exists():
        try:
            cloud_url = await upload_invoice_to_supabase(local_path, local_filename)
        except Exception as e:
            logger.warning(f"Supabase upload attempt failed: {e}")

    if local_path and local_path.exists() and local_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
        ai_data = await analyze_image_with_gemini(local_path, caption=caption)

    # Use high-accuracy Local RapidOCR if Gemini is not configured or offline
    if not ai_data:
        filename_hint = message.document.file_name if message.document else "invoice.jpg"
        ai_data = smart_fallback_analyzer(filename_hint, caption=caption, image_path=local_path)

    # Detect if user uploaded a photo of a defect/broken item or asked a claim question
    if ai_data.get("image_type") == "DEFECT_ISSUE" or any(k in caption.lower() for k in ["claim", "broken", "crack", "green line", "water", "pani"]):
        try:
            await status_msg.delete()
        except Exception:
            pass
        return await render_claim_diagnosis_response(update, caption or ai_data.get("detected_issue") or "Defective product")

    # It's an invoice or product tag! Extract smart parameters
    product_name = ai_data.get("product_name") or "Electronic Device"
    brand = ai_data.get("brand") or "Brand"
    category = ai_data.get("category") or "General"
    retailer = ai_data.get("retailer") or "Store / Retailer"
    warranty_months = ai_data.get("warranty_months") if ai_data.get("warranty_months") is not None else 12
    serial_no = ai_data.get("serial_no")
    price_paid = ai_data.get("price_paid")
    is_food = ai_data.get("is_food_receipt", False)

    # Parse purchase date
    p_date_raw = ai_data.get("purchase_date")
    p_date = date.today()
    if p_date_raw:
        try:
            p_date = datetime.strptime(str(p_date_raw)[:10], "%Y-%m-%d").date()
        except Exception:
            p_date = date.today()

    expiry_date = p_date + timedelta(days=int(warranty_months * 30.4375))

    # Fetch user language preference
    user_lang = "en"
    tg_user = update.effective_user
    if tg_user:
        with get_db() as db:
            user = db.query(User).filter_by(user_id=tg_user.id).first()
            if user:
                user_lang = getattr(user, "language", "en") or "en"

    # Store in context
    context.user_data["product_name"] = product_name
    context.user_data["brand"] = brand
    context.user_data["category"] = category
    context.user_data["purchase_platform"] = retailer
    context.user_data["purchase_date"] = p_date
    context.user_data["warranty_months"] = warranty_months
    context.user_data["expiry_date"] = expiry_date
    context.user_data["serial_no"] = serial_no
    context.user_data["price_paid"] = price_paid
    context.user_data["invoice_file_id"] = file_id
    context.user_data["invoice_file_type"] = file_type
    context.user_data["local_invoice_path"] = cloud_url or (str(local_path) if local_path else None)
    context.user_data["cloud_invoice_url"] = cloud_url
    context.user_data["is_food_receipt"] = is_food
    context.user_data["user_lang"] = user_lang

    try:
        await status_msg.delete()
    except Exception:
        pass

    card = format_smart_scan_card(context.user_data, user_lang)
    await message.reply_text(
        card,
        parse_mode="Markdown",
        reply_markup=get_smart_confirm_keyboard(user_lang),
    )
    return WAITING_FOR_SMART_CONFIRM


async def handle_smart_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles 1-click confirmation or editing from the smart scan card."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_lang = context.user_data.get("user_lang", "en")

    if data == "smart_confirm_save":
        return await save_product_to_vault(query, context)
    elif data == "smart_edit_details":
        p_name = context.user_data.get("product_name", "Unknown")
        ret = context.user_data.get("purchase_platform", "Unknown")
        dt_val = context.user_data.get("purchase_date", date.today())
        dt_str = dt_val.strftime("%d %b %Y") if isinstance(dt_val, (date, datetime)) else str(dt_val)
        w_m = context.user_data.get("warranty_months", 12)
        s_no = context.user_data.get("serial_no") or "None"
        pr = context.user_data.get("price_paid")
        pr_str = f"₹{pr:,.2f}" if pr else "Not specified"

        if user_lang == "hi":
            picker_text = (
                "✏️ *आप कौन सा विवरण बदलना या जोड़ना चाहते हैं?*\n\n"
                f"• *डिवाइस का नाम*: `{p_name}`\n"
                f"• *दुकान / स्टोर*: `{ret}`\n"
                f"• *खरीद की तारीख*: `{dt_str}`\n"
                f"• *वारंटी*: `{w_m} महीने`\n"
                f"• *सीरियल / IMEI*: `{s_no}`\n"
                f"• *कुल कीमत*: `{pr_str}`\n\n"
                f"👉 _नीचे किसी भी फील्ड पर टैप करें जिसे आप सही करना चाहते हैं:_"
            )
        else:
            picker_text = (
                "✏️ *Select which detail you would like to edit or add:*\n\n"
                f"• *Device Name*: `{p_name}`\n"
                f"• *Store / Retailer*: `{ret}`\n"
                f"• *Purchase Date*: `{dt_str}`\n"
                f"• *Warranty Period*: `{w_m} Months`\n"
                f"• *Serial / IMEI*: `{s_no}`\n"
                f"• *Price Paid*: `{pr_str}`\n\n"
                f"👉 _Tap any field below to update it directly:_"
            )

        await query.message.reply_text(
            picker_text,
            parse_mode="Markdown",
            reply_markup=get_edit_fields_keyboard(user_lang),
        )
        return WAITING_FOR_EDIT_CHOICE
    elif data == "cancel_action":
        context.user_data.clear()
        await query.message.reply_text("❌ Registration cancelled.", reply_markup=get_main_reply_keyboard(user_lang))
        return ConversationHandler.END


async def handle_edit_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispatches the chosen field for interactive single-step editing."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_lang = context.user_data.get("user_lang", "en")

    if data == "smart_confirm_save":
        return await save_product_to_vault(query, context)
    elif data == "cancel_action":
        context.user_data.clear()
        await query.message.reply_text("❌ Registration cancelled.", reply_markup=get_main_reply_keyboard(user_lang))
        return ConversationHandler.END

    field = data.replace("edit_field:", "")
    context.user_data["editing_field"] = field

    if field == "name":
        await query.message.reply_text(
            "✏️ *Please reply with the correct Product Name & Brand:*\n_(e.g. Apple iPhone 15 Pro, Samsung 55\" Smart TV, or boAt Airdopes)_",
            parse_mode="Markdown",
        )
        return WAITING_FOR_SINGLE_FIELD_INPUT
    elif field == "retailer":
        await query.message.reply_text(
            "🏬 *Please reply with the Store / Retailer name:*\n_(e.g. Amazon India, Flipkart, Croma, Reliance Digital, or Burger Shop)_",
            parse_mode="Markdown",
        )
        return WAITING_FOR_SINGLE_FIELD_INPUT
    elif field == "date":
        await query.message.reply_text(
            "📅 *Please reply with the Purchase Date:*\n_(e.g. `2024-12-29`, `29-12-2024`, or `today`)_",
            parse_mode="Markdown",
        )
        return WAITING_FOR_SINGLE_FIELD_INPUT
    elif field == "warranty":
        await query.message.reply_text(
            "🛡️ *Select or enter the Warranty Duration (months):*",
            reply_markup=get_warranty_period_keyboard(),
        )
        return WAITING_FOR_WARRANTY
    elif field == "serial":
        await query.message.reply_text(
            "🔢 *Please reply with the Serial Number or IMEI:*\n_(Reply with the number, or send /skip to leave blank)_",
            parse_mode="Markdown",
        )
        return WAITING_FOR_SINGLE_FIELD_INPUT
    elif field == "price":
        await query.message.reply_text(
            "💰 *Please reply with the Total Price Paid:*\n_(e.g. `10350` or `92000`)_",
            parse_mode="Markdown",
        )
        return WAITING_FOR_SINGLE_FIELD_INPUT
    elif field == "category":
        await query.message.reply_text(
            "🏷️ *Select the Category:*",
            reply_markup=get_category_keyboard(),
        )
        return WAITING_FOR_CATEGORY


async def handle_single_field_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Updates the selected single field and returns to the smart scan card."""
    field = context.user_data.get("editing_field")
    text = update.message.text.strip()
    user_lang = context.user_data.get("user_lang", "en")

    if field == "name":
        context.user_data["product_name"] = sanitize_text(text, max_length=200)
        words = text.split()
        if words:
            context.user_data["brand"] = sanitize_text(words[0], max_length=100)
    elif field == "retailer":
        context.user_data["purchase_platform"] = sanitize_text(text, max_length=100)
    elif field == "date":
        p_date = None
        if text.lower() in ["today", "now"]:
            p_date = date.today()
        elif text.lower() in ["yesterday"]:
            p_date = date.today() - timedelta(days=1)
        else:
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
                try:
                    p_date = datetime.strptime(text, fmt).date()
                    break
                except ValueError:
                    pass
        if p_date:
            context.user_data["purchase_date"] = p_date
            warranty_m = context.user_data.get("warranty_months", 12)
            context.user_data["expiry_date"] = p_date + timedelta(days=int(warranty_m * 30.4375))
        else:
            await update.message.reply_text("⚠️ Could not recognize date format. Please reply like `2024-12-29` (YYYY-MM-DD):")
            return WAITING_FOR_SINGLE_FIELD_INPUT
    elif field == "serial":
        context.user_data["serial_no"] = sanitize_serial(text)
    elif field == "price":
        clean_p = re.sub(r'[^0-9.]', '', text.replace(",", ""))
        try:
            context.user_data["price_paid"] = float(clean_p)
        except Exception:
            pass

    context.user_data["editing_field"] = None

    await update.message.reply_text("✅ *Updated successfully!*", parse_mode="Markdown")
    card = format_smart_scan_card(context.user_data, user_lang)
    await update.message.reply_text(
        card,
        parse_mode="Markdown",
        reply_markup=get_smart_confirm_keyboard(user_lang),
    )
    return WAITING_FOR_SMART_CONFIRM


async def skip_single_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows skipping optional single field inputs like serial or price."""
    field = context.user_data.get("editing_field")
    user_lang = context.user_data.get("user_lang", "en")
    if field == "serial":
        context.user_data["serial_no"] = None
    elif field == "price":
        context.user_data["price_paid"] = None
    context.user_data["editing_field"] = None

    await update.message.reply_text("⏩ Skipped.")
    card = format_smart_scan_card(context.user_data, user_lang)
    await update.message.reply_text(
        card,
        parse_mode="Markdown",
        reply_markup=get_smart_confirm_keyboard(user_lang),
    )
    return WAITING_FOR_SMART_CONFIRM


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows skipping the photo upload step."""
    context.user_data["invoice_file_id"] = None
    context.user_data["invoice_file_type"] = None
    await update.message.reply_text(
        "⏩ Photo skipped.\n\n"
        "What is the *Brand & Product Name*?\n"
        "_(Example: Apple iPhone 15 Pro, LG 1.5 Ton AC, boAt Nirvana)_",
        parse_mode="Markdown",
    )
    return WAITING_FOR_NAME


async def handle_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Captures product name and brand."""
    text = update.message.text.strip()
    if len(text) < 2:
        await update.message.reply_text("Please enter a valid product name.")
        return WAITING_FOR_NAME

    context.user_data["product_name"] = sanitize_text(text, max_length=200)
    words = text.split()
    context.user_data["brand"] = sanitize_text(words[0] if words else "Unknown", max_length=100)

    await update.message.reply_text(
        f"Great: *{context.user_data['product_name']}*\n\nSelect the device *Category*:",
        parse_mode="Markdown",
        reply_markup=get_category_keyboard(),
    )
    return WAITING_FOR_CATEGORY


async def handle_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles category selection."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_lang = context.user_data.get("user_lang", "en")
    if data == "cancel_action":
        await query.message.reply_text("❌ Registration cancelled.", reply_markup=get_main_reply_keyboard(user_lang))
        return ConversationHandler.END

    category = data.replace("cat:", "")
    context.user_data["category"] = category

    # If this was called from the quick-edit picker, return to the smart scan card
    if context.user_data.get("editing_field") == "category":
        context.user_data["editing_field"] = None
        await query.message.reply_text(f"✅ Category updated to *{category}*!", parse_mode="Markdown")
        card = format_smart_scan_card(context.user_data, user_lang)
        await query.message.reply_text(
            card,
            parse_mode="Markdown",
            reply_markup=get_smart_confirm_keyboard(user_lang),
        )
        return WAITING_FOR_SMART_CONFIRM

    await query.message.edit_text(
        f"Category: *{category}*\n\nWhere was it purchased?",
        parse_mode="Markdown",
        reply_markup=get_platform_keyboard(),
    )
    return WAITING_FOR_PLATFORM


async def handle_platform_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles retailer platform selection."""
    query = update.callback_query
    await query.answer()

    platform = query.data.replace("plat:", "")
    context.user_data["purchase_platform"] = platform

    today_str = date.today().strftime("%Y-%m-%d")
    await query.message.edit_text(
        f"Retailer: *{platform}*\n\n"
        f"📅 What was the *Purchase Date*?\n\n"
        f"• Reply with *today* (for today, `{today_str}`)\n"
        f"• Or enter in *YYYY-MM-DD* format (e.g. `2024-06-15`)",
        parse_mode="Markdown",
    )
    return WAITING_FOR_DATE


async def handle_purchase_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validates and stores purchase date."""
    text = update.message.text.strip().lower()

    if text in ["today", "now"]:
        p_date = date.today()
    elif text in ["yesterday"]:
        p_date = date.today() - timedelta(days=1)
    else:
        try:
            p_date = datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            try:
                p_date = datetime.strptime(text, "%d-%m-%Y").date()
            except ValueError:
                await update.message.reply_text(
                    "⚠️ Invalid date format. Please reply with *today* or format like `2024-05-20` (YYYY-MM-DD):",
                    parse_mode="Markdown",
                )
                return WAITING_FOR_DATE

    context.user_data["purchase_date"] = p_date

    await update.message.reply_text(
        f"Purchase Date recorded: *{p_date.strftime('%d %B %Y')}*\n\n"
        f"Select the *Warranty Duration*:",
        parse_mode="Markdown",
    )
    return WAITING_FOR_WARRANTY


async def handle_warranty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles warranty duration choice."""
    query = update.callback_query
    await query.answer()

    val = query.data.replace("warn:", "")
    if val == "custom":
        await query.message.reply_text("Please type the warranty period in number of months (e.g. `18` or `36`):")
        return WAITING_FOR_WARRANTY

    try:
        months = int(val)
    except ValueError:
        months = 12

    if context.user_data.get("editing_field") == "warranty":
        context.user_data["warranty_months"] = months
        p_date = context.user_data.get("purchase_date") or date.today()
        context.user_data["expiry_date"] = p_date + timedelta(days=int(months * 30.4375))
        context.user_data["editing_field"] = None
        user_lang = context.user_data.get("user_lang", "en")
        await query.message.reply_text(f"✅ Warranty period updated to *{months} Months*!", parse_mode="Markdown")
        card = format_smart_scan_card(context.user_data, user_lang)
        await query.message.reply_text(
            card,
            parse_mode="Markdown",
            reply_markup=get_smart_confirm_keyboard(user_lang),
        )
        return WAITING_FOR_SMART_CONFIRM

    return await finalize_warranty_and_prompt_serial(query.message, context, months)


async def handle_custom_warranty_months(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles custom months text input."""
    text = update.message.text.strip()
    if not text.isdigit() or int(text) < 0:
        await update.message.reply_text("Please enter a valid number of months (e.g. `18`):")
        return WAITING_FOR_WARRANTY
    months = int(text)

    if context.user_data.get("editing_field") == "warranty":
        context.user_data["warranty_months"] = months
        p_date = context.user_data.get("purchase_date") or date.today()
        context.user_data["expiry_date"] = p_date + timedelta(days=int(months * 30.4375))
        context.user_data["editing_field"] = None
        user_lang = context.user_data.get("user_lang", "en")
        await update.message.reply_text(f"✅ Warranty period updated to *{months} Months*!", parse_mode="Markdown")
        card = format_smart_scan_card(context.user_data, user_lang)
        await update.message.reply_text(
            card,
            parse_mode="Markdown",
            reply_markup=get_smart_confirm_keyboard(user_lang),
        )
        return WAITING_FOR_SMART_CONFIRM

    return await finalize_warranty_and_prompt_serial(update.message, context, months)


async def finalize_warranty_and_prompt_serial(message, context: ContextTypes.DEFAULT_TYPE, months: int):
    """Stores months, calculates expiry, and asks for serial/IMEI."""
    context.user_data["warranty_months"] = months
    p_date: date = context.user_data.get("purchase_date", date.today())

    approx_days = int(months * 30.4375)
    expiry_date = p_date + timedelta(days=approx_days)
    context.user_data["expiry_date"] = expiry_date

    await message.reply_text(
        f"🛡️ Warranty: *{months} Months* (Expires: *{expiry_date.strftime('%d %B %Y')}*)\n\n"
        f"Enter the *Serial Number* or *IMEI* (Optional for official claim):\n\n"
        f"💡 _Reply with the serial number, or type /skip_serial to finish._",
        parse_mode="Markdown",
    )
    return WAITING_FOR_SERIAL


async def handle_serial_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Captures serial/IMEI number."""
    text = update.message.text.strip()
    context.user_data["serial_no"] = sanitize_serial(text)
    return await save_product_to_vault(update, context)


async def skip_serial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skips serial number input."""
    context.user_data["serial_no"] = None
    return await save_product_to_vault(update, context)


async def save_product_to_vault(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    """Saves the completed warranty record into SQLite and shows confirmation card."""
    tg_user = update_or_query.effective_user if hasattr(update_or_query, "effective_user") else update_or_query.from_user
    data = context.user_data
    user_lang = data.get("user_lang", "en")

    with get_db() as db:
        user = db.query(User).filter_by(user_id=tg_user.id).first()
        if not user:
            user = User(user_id=tg_user.id, first_name=tg_user.first_name, plan_tier="free")
            db.add(user)
            db.commit()

        p_date = data.get("purchase_date") or date.today()
        w_months = data.get("warranty_months", 12)
        exp_date = data.get("expiry_date") or (p_date + timedelta(days=int(w_months * 30.4375)))

        product = ProductWarranty(
            user_id=tg_user.id,
            product_name=data.get("product_name") or "Electronic Appliance",
            category=data.get("category", "General"),
            brand=data.get("brand", "Unknown"),
            purchase_platform=data.get("purchase_platform") or "Local Store",
            purchase_date=p_date,
            warranty_months=w_months,
            expiry_date=exp_date,
            serial_no=data.get("serial_no"),
            invoice_file_id=data.get("invoice_file_id"),
            invoice_file_type=data.get("invoice_file_type"),
            local_invoice_path=data.get("local_invoice_path"),
        )
        db.add(product)
        db.commit()
        product_id = product.id
        days_left = product.days_remaining

    status_icon = "🟢" if days_left > 0 else "🟣"
    status_str = f"*{days_left} Days Remaining*" if days_left > 0 else f"*Expired ({abs(days_left)} days ago)*"

    if user_lang == "hi":
        card = (
            f"🎉 *बिल सफलतापूर्वक वॉल्ट में सुरक्षित हो गया!* 🛡️\n\n"
            f"*{data.get('product_name')}*\n"
            f"• कैटेगरी: {data.get('category')}\n"
            f"• विक्रेता: {data.get('purchase_platform')}\n"
            f"• खरीद की तारीख: {p_date.strftime('%d %b %Y')}\n"
            f"• समाप्ति तिथि: *{exp_date.strftime('%d %b %Y')}*\n"
            f"• स्टेटस: {status_icon} {status_str}\n"
            f"• सीरियल / IMEI: `{data.get('serial_no') or 'सुरक्षित'}`\n"
            f"• स्टोर बिल: {'✅ क्लाउड वॉल्ट में हमेशा के लिए सुरक्षित' if data.get('invoice_file_id') else '⚠️ अपलोड नहीं किया गया'}\n\n"
            f"🔔 *समाप्ति से 30, 15, 7 और 1 दिन पहले स्वचालित अलर्ट शेड्यूल कर दिए गए हैं।*"
        )
    else:
        card = (
            f"🎉 *Product Successfully Archived in Warranty Vault!* 🛡️\n\n"
            f"*{data.get('product_name')}*\n"
            f"• Category: {data.get('category')}\n"
            f"• Retailer: {data.get('purchase_platform')}\n"
            f"• Purchased: {p_date.strftime('%d %b %Y')}\n"
            f"• Expiry Date: *{exp_date.strftime('%d %b %Y')}*\n"
            f"• Status: {status_icon} {status_str}\n"
            f"• Serial / IMEI: `{data.get('serial_no') or 'Archived via Photo'}`\n"
            f"• Store Bill: {'✅ Stored Permanently in Cloud Vault' if data.get('invoice_file_id') else '⚠️ Not uploaded'}\n\n"
            f"🔔 *Automated alerts scheduled for 30, 15, 7, and 1 day before expiry.*"
        )

    if hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.message.reply_text(
            card,
            parse_mode="Markdown",
            reply_markup=get_product_actions_keyboard(product_id),
        )
    elif hasattr(update_or_query, "reply_text"):
        await update_or_query.reply_text(
            card,
            parse_mode="Markdown",
            reply_markup=get_product_actions_keyboard(product_id),
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels registration flow."""
    user_lang = context.user_data.get("user_lang", "en")
    context.user_data.clear()
    await update.message.reply_text("Registration cancelled.", reply_markup=get_main_reply_keyboard(user_lang))
    return ConversationHandler.END


def get_add_product_conversation_handler():
    """Builds and returns the complete ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("add", start_add_product),
            MessageHandler(filters.Regex(r"^(📸 Upload Store Bill|📸 बिल अपलोड करें)$"), start_add_product),
            MessageHandler(filters.PHOTO | filters.Document.ALL, handle_direct_photo),
        ],
        states={
            WAITING_FOR_PHOTO: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, handle_invoice_photo),
                CommandHandler("skip_photo", skip_photo),
            ],
            WAITING_FOR_SMART_CONFIRM: [
                CallbackQueryHandler(handle_smart_confirm_callback, pattern="^(smart_confirm_save|smart_edit_details|cancel_action)"),
            ],
            WAITING_FOR_EDIT_CHOICE: [
                CallbackQueryHandler(handle_edit_choice_callback, pattern="^(edit_field:|smart_confirm_save|cancel_action)"),
            ],
            WAITING_FOR_SINGLE_FIELD_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_single_field_input),
                CommandHandler("skip", skip_single_field),
            ],
            WAITING_FOR_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_name),
            ],
            WAITING_FOR_CATEGORY: [
                CallbackQueryHandler(handle_category_callback, pattern="^cat:|^cancel_action"),
            ],
            WAITING_FOR_PLATFORM: [
                CallbackQueryHandler(handle_platform_callback, pattern="^plat:"),
            ],
            WAITING_FOR_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_purchase_date),
            ],
            WAITING_FOR_WARRANTY: [
                CallbackQueryHandler(handle_warranty_callback, pattern="^warn:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_warranty_months),
            ],
            WAITING_FOR_SERIAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_serial_input),
                CommandHandler("skip_serial", skip_serial),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_registration)],
        allow_reentry=True,
    )
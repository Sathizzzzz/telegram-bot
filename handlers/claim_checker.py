"""
Interactive Claim Eligibility Checker & Indian Service Center Guide Handler.
Answers: "Is this claimable under warranty?", "I lost my bill, what do I do?",
and diagnoses photos of defects or issues.
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from services.warranty_intelligence import (
    analyze_claim_eligibility,
    LOST_BILL_RETRIEVAL_GUIDE,
    INDIAN_BRAND_SPECIAL_POLICIES,
)
from services.brand_directory import BRAND_SUPPORT_DATA, find_brand_support
from utils.keyboards import get_main_reply_keyboard

WAITING_FOR_CLAIM_QUERY = 1


async def start_claim_checker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for checking warranty claim eligibility."""
    text = (
        "🔍 *Warranty Claim & Lost Bill Diagnosis (India)* 🇮🇳\n\n"
        "Unsure if your device issue will be covered for free, or lost your store receipt?\n\n"
        "💬 *Send me your question or a photo of the defect:*\n"
        "• _'My phone screen has a green line after update'_\n"
        "• _'boAt earbud left side has low volume'_\n"
        "• _'AC is not cooling, 1 year is over'_\n"
        "• _'I lost my bill, how do I claim warranty?'_\n"
        "• _Or send a photo of the defective screen/appliance._\n\n"
        "💡 _Type your query below or tap /cancel to return._"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown")
    return WAITING_FOR_CLAIM_QUERY


async def handle_claim_query_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes user text query about warranty claims."""
    user_query = update.message.text.strip()
    return await render_claim_diagnosis_response(update, user_query)


async def handle_claim_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes uploaded defect photo in the claim checker."""
    caption = update.message.caption or "Defective product / issue photo"
    await update.message.reply_text("🔍 *Analyzing defect photo & warranty policies...* ⏳", parse_mode="Markdown")
    return await render_claim_diagnosis_response(update, caption)


async def render_claim_diagnosis_response(update: Update, query_text: str):
    """Builds and delivers rich Indian warranty diagnosis."""
    diagnosis = analyze_claim_eligibility(query_text)

    # Check if a specific brand was mentioned
    brand_support = None
    for b_key in BRAND_SUPPORT_DATA.keys():
        if b_key in query_text.lower():
            brand_support = BRAND_SUPPORT_DATA[b_key]
            break

    # Build response message
    steps_text = ""
    if diagnosis.action_steps:
        steps_text = "\n".join([f"• {step}" for step in diagnosis.action_steps])

    response = (
        f"{diagnosis.verdict_emoji} *Warranty Verdict: {diagnosis.verdict_title}*\n\n"
        f"📋 *Analysis:*\n{diagnosis.explanation}\n\n"
        f"🗣️ *Service Center Battle Guide (What to say):*\n{diagnosis.service_center_advice}\n\n"
        f"🧾 *Lost Bill Solution:*\n{diagnosis.lost_bill_tip}\n\n"
    )

    if diagnosis.brand_policy_note:
        response += f"ℹ️ *Special Policy Alert:*\n{diagnosis.brand_policy_note}\n\n"

    if steps_text:
        response += f"✅ *Action Steps:*\n{steps_text}\n\n"

    response += "⚖️ _Consumer Right: Under Consumer Protection Act 2019, if a brand rejects a genuine claim without valid technical proof, you can lodge a free complaint at National Consumer Helpline (NCH 1915)._"

    buttons = []
    if brand_support:
        b_name = brand_support["name"]
        if brand_support.get("whatsapp"):
            buttons.append([InlineKeyboardButton(f"💬 Chat with {b_name} on WhatsApp", url=brand_support["whatsapp"])])
        if brand_support.get("warranty_check_url"):
            buttons.append([InlineKeyboardButton("🔍 Check Official Warranty Online", url=brand_support["warranty_check_url"])])

    buttons.append([
        InlineKeyboardButton("📄 Lost Bill Recovery Guide", callback_data="lost_bill_guide"),
        InlineKeyboardButton("🎧 Brand Directory", callback_data="open_directory"),
    ])

    await update.effective_message.reply_text(
        response,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return ConversationHandler.END


async def show_lost_bill_guide_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays detailed instructions for recovering missing bills in India."""
    if update.callback_query:
        await update.callback_query.answer()

    text = (
        "🧾 *Indian Lost Bill Recovery Guide* 🇮🇳\n\n"
        "Never give up on a warranty claim just because you misplaced the paper receipt!\n\n"
        f"{LOST_BILL_RETRIEVAL_GUIDE['amazon']}\n\n"
        f"{LOST_BILL_RETRIEVAL_GUIDE['flipkart']}\n\n"
        f"{LOST_BILL_RETRIEVAL_GUIDE['croma']}\n\n"
        f"{LOST_BILL_RETRIEVAL_GUIDE['reliance_digital']}\n\n"
        f"{LOST_BILL_RETRIEVAL_GUIDE['offline_store']}\n\n"
        "💡 *Pro-Tip*: Brands like Apple, Dell, Lenovo, and HP verify active warranty purely using the Serial Number or Service Tag. You often do NOT need a bill at all!"
    )

    buttons = [
        [InlineKeyboardButton("🔍 Check Another Issue", callback_data="start_claim_check")],
        [InlineKeyboardButton("📂 View My Vault", callback_data="list_vault")],
    ]

    await update.effective_message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


def get_claim_checker_conversation_handler():
    """Builds conversation handler for claim checking."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("claim", start_claim_checker),
            MessageHandler(filters.Regex(r"^(🔍 Is It Claimable\?|🔍 क्या यह क्लेम होगा\?)$"), start_claim_checker),
            CallbackQueryHandler(start_claim_checker, pattern="^start_claim_check$"),
        ],
        states={
            WAITING_FOR_CLAIM_QUERY: [
                MessageHandler(filters.PHOTO, handle_claim_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_claim_query_text),
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: u.message.reply_text("Check cancelled.", reply_markup=get_main_reply_keyboard()))],
        allow_reentry=True,
    )
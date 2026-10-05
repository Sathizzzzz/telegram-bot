"""
Start, Help, and Language Handlers for ClaimSathi.
Clean, professional English by default with optional Hindi localization.
"""
from telegram import Update
from telegram.ext import ContextTypes
from database.db import get_db
from database.models import User, ProductWarranty
from utils.keyboards import get_main_reply_keyboard, get_language_keyboard


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command and welcomes the user in their preferred language."""
    tg_user = update.effective_user
    if not tg_user:
        return

    with get_db() as db:
        user = db.query(User).filter_by(user_id=tg_user.id).first()
        if not user:
            user = User(
                user_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                language="en",
                plan_tier="free",
                vault_limit=5,
            )
            db.add(user)
            db.commit()

        user_lang = getattr(user, "language", "en") or "en"
        products = db.query(ProductWarranty).filter_by(user_id=tg_user.id).all()
        total_count = len(products)
        active_count = sum(1 for p in products if not p.is_expired)

    if user_lang == "hi":
        welcome_text = (
            f"🇮🇳 *ClaimSathi (क्लेम साथी) में आपका स्वागत है!* 🛡️\n\n"
            f"*आपका पर्सनल वारंटी पार्टनर और डिजिटल बिल लॉकर*\n"
            f"अब कभी स्टोर बिल नहीं खोएगा और न ही क्लेम का मौका छूटेगा!\n\n"
            f"📊 *आपके वॉल्ट का स्टेटस:*\n"
            f"• सुरक्षित गैजेट्स और अप्लायंसेज: *{total_count}*\n"
            f"• एक्टिव वारंटी: *{active_count}*\n"
            f"• मेंबरशिप: *फ्री प्लान* (टेलीग्राम पर हमेशा मुफ्त)\n\n"
            f"⚡ *ClaimSathi आपकी कैसे मदद करता है:*\n"
            f"1️⃣ *बिल फोटो अपलोड करें*: दुकान की रसीद या Amazon/Flipkart का बिल भेजें — AI अपने आप स्कैन करके सुरक्षित कर लेगा।\n"
            f"2️⃣ *क्या यह क्लेम होगा?*: स्क्रीन में ग्रीन लाइन, ईयरबड की आवाज बंद या AC की कूलिंग खराब? पूछें और जानें कि क्या फ्री में बनेगा!\n"
            f"3️⃣ *खोए बिल की गाइड*: बिना बिल के IMEI या सीरियल नंबर से वारंटी क्लेम करने का तरीका जानें।\n"
            f"4️⃣ *मेरा वॉल्ट*: सभी गैजेट्स की लिस्ट देखें और 1-क्लिक में आधिकारिक क्लेम PDF डाउनलोड करें।\n"
            f"5️⃣ *ब्रांड डायरेक्टरी*: 20+ प्रमुख ब्रांड्स के ऑफिशियल टोल-फ्री और WhatsApp सपोर्ट लिंक्स।\n\n"
            f"👇 *शुरू करने के लिए नीचे दिए गए बटन पर टैप करें या बिल की फोटो भेजें:*"
        )
    else:
        # Professional English default
        welcome_text = (
            f"🛡️ *Welcome to ClaimSathi!* 🇮🇳\n\n"
            f"*Your AI-Powered Warranty Vault & Claim Protection Assistant*\n"
            f"Never misplace a store invoice again or lose money on claimable repairs.\n\n"
            f"📊 *Your Vault Overview:*\n"
            f"• Registered Devices & Appliances: *{total_count}*\n"
            f"• Active Warranties: *{active_count}*\n"
            f"• Plan Tier: *Free Plan* (Unlimited Cloud Document Storage)\n\n"
            f"⚡ *What ClaimSathi does for you:*\n"
            f"1️⃣ *Upload Bill Photo*: Instantly scan and archive store receipts or PDF invoices.\n"
            f"2️⃣ *Is It Claimable?*: Diagnose hardware faults, verify brand recall policies, and get official claim advice.\n"
            f"3️⃣ *Lost Bill Recovery*: Complete guidelines to retrieve legal duplicate tax invoices or claim via serial number.\n"
            f"4️⃣ *My Vault*: Track warranty countdowns and generate official 1-Click Claim Dossiers.\n"
            f"5️⃣ *Brand Directory*: Verified support helplines and WhatsApp portals for 20+ top brands.\n\n"
            f"👇 *Select an option below or send a photo of your receipt to begin:*"
        )

    await update.effective_message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_reply_keyboard(user_lang),
    )


async def show_language_selector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays language preference options."""
    prompt = (
        "🌐 *Language Settings / भाषा चयन*\n\n"
        "Please select your preferred language:\n"
        "कृपया अपनी पसंदीदा भाषा चुनें:"
    )
    await update.effective_message.reply_text(
        prompt,
        parse_mode="Markdown",
        reply_markup=get_language_keyboard(),
    )


async def handle_set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves user language preference and updates the interface."""
    query = update.callback_query
    await query.answer()

    lang = query.data.split(":")[1]
    tg_user = update.effective_user

    with get_db() as db:
        user = db.query(User).filter_by(user_id=tg_user.id).first()
        if user:
            user.language = lang
            db.commit()

    if lang == "hi":
        msg = "✅ *भाषा बदलकर 'हिंदी' कर दी गई है।*\n\nअब आप सभी संदेश और मेनू हिंदी में देख सकते हैं।"
    else:
        msg = "✅ *Language updated to 'English (Default)'.*\n\nAll menus and claim intelligence are now displayed in professional English."

    await query.message.reply_text(
        msg,
        parse_mode="Markdown",
        reply_markup=get_main_reply_keyboard(lang),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides usage guidance."""
    tg_user = update.effective_user
    user_lang = "en"
    if tg_user:
        with get_db() as db:
            user = db.query(User).filter_by(user_id=tg_user.id).first()
            if user:
                user_lang = getattr(user, "language", "en") or "en"

    if user_lang == "hi":
        help_text = (
            "💡 *ClaimSathi गाइड:*\n\n"
            "• *📸 बिल अपलोड करें*: रसीद या इनवॉइस की फोटो भेजें। AI इसे तुरंत वॉल्ट में सुरक्षित कर देगा।\n"
            "• *🔍 क्या यह क्लेम होगा?*: अपनी समस्या पूछें (जैसे स्क्रीन लाइन, ईयरबड साउंड) और क्लेम की पात्रता जानें।\n"
            "• *🧾 खोए बिल की गाइड*: Amazon, Flipkart, Croma से डुप्लिकेट बिल निकालने की पूरी विधि।\n"
            "• *📂 मेरा वॉल्ट*: अपने सभी पंजीकृत इलेक्ट्रॉनिक्स और बिल देखें।\n"
            "• *🎧 ब्रांड डायरेक्टरी*: आधिकारिक हेल्पलाइन और WhatsApp चैट लिंक।\n"
            "• *🌐 Language / भाषा*: भाषा बदलने के लिए इस बटन पर टैप करें।"
        )
    else:
        help_text = (
            "💡 *ClaimSathi Quick Guide:*\n\n"
            "• *📸 Upload Store Bill*: Send any photo of an invoice, receipt, or appliance rating plate to archive it.\n"
            "• *🔍 Is It Claimable?*: Ask any warranty question (e.g. 'green line on screen', 'boat earbud not charging') for an instant verdict and service center advice.\n"
            "• *🧾 Lost Bill Guide*: Step-by-step instructions for recovering duplicate invoices from Amazon, Flipkart, Croma, Reliance Digital, and offline stores.\n"
            "• *📂 My Vault*: Access all your registered electronics, models, serial numbers, and stored bills.\n"
            "• *🔔 Simulate 30-Day Alert*: Preview automated expiry warnings before warranty lapses.\n"
            "• *🎧 Brand Support Directory*: Verified WhatsApp & toll-free customer care contacts for 20+ brands.\n"
            "• *🌐 Language*: Tap to switch between English and Hindi anytime."
        )

    await update.effective_message.reply_text(help_text, parse_mode="Markdown")
"""
Telegram Keyboard builders for WarrantyBot India.
"""
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_reply_keyboard(lang: str = "en"):
    """Main persistent reply keyboard with clean professional English default."""
    if lang == "hi":
        keyboard = [
            ["📸 बिल अपलोड करें", "🔍 क्या यह क्लेम होगा?"],
            ["📂 मेरा वॉल्ट / कैटलॉग", "🎧 ब्रांड सपोर्ट डायरेक्टरी"],
            ["🛡️ एक्सटेंडेड वारंटी", "🔔 30-दिन एक्सपायरी अलर्ट"],
            ["🧾 खोए बिल की गाइड", "🌐 Language / भाषा"],
        ]
    else:
        keyboard = [
            ["📸 Upload Store Bill", "🔍 Is It Claimable?"],
            ["📂 My Vault / Catalog", "🎧 Brand Support Directory"],
            ["🛡️ Extended Warranty & AMC", "🔔 Simulate 30-Day Alert"],
            ["🧾 Lost Bill Recovery Guide", "🌐 Language / भाषा"],
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_language_keyboard():
    """Language selection keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English (Default)", callback_data="set_lang:en"),
            InlineKeyboardButton("🇮🇳 हिंदी (Hindi)", callback_data="set_lang:hi"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_smart_confirm_keyboard(lang: str = "en"):
    """1-click confirmation keyboard for AI-scanned bills."""
    if lang == "hi":
        keyboard = [
            [
                InlineKeyboardButton("✅ कन्फर्म करें और वॉल्ट में सेव करें", callback_data="smart_confirm_save"),
            ],
            [
                InlineKeyboardButton("✏️ विवरण बदलें", callback_data="smart_edit_details"),
                InlineKeyboardButton("🔍 क्लेम चेक करें", callback_data="start_claim_check"),
            ],
            [InlineKeyboardButton("❌ रद्द करें", callback_data="cancel_action")],
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm & Save to Vault", callback_data="smart_confirm_save"),
            ],
            [
                InlineKeyboardButton("✏️ Edit Details", callback_data="smart_edit_details"),
                InlineKeyboardButton("🔍 Check Claimability", callback_data="start_claim_check"),
            ],
            [InlineKeyboardButton("❌ Discard", callback_data="cancel_action")],
        ]
    return InlineKeyboardMarkup(keyboard)


def get_edit_fields_keyboard(lang: str = "en"):
    """Interactive field picker to edit individual scanned attributes."""
    if lang == "hi":
        keyboard = [
            [
                InlineKeyboardButton("✏️ डिवाइस का नाम", callback_data="edit_field:name"),
                InlineKeyboardButton("🏷️ कैटेगरी", callback_data="edit_field:category"),
            ],
            [
                InlineKeyboardButton("🏬 स्टोर / विक्रेता", callback_data="edit_field:retailer"),
                InlineKeyboardButton("📅 खरीद की तारीख", callback_data="edit_field:date"),
            ],
            [
                InlineKeyboardButton("🛡️ वारंटी अवधि", callback_data="edit_field:warranty"),
                InlineKeyboardButton("🔢 सीरियल / IMEI", callback_data="edit_field:serial"),
            ],
            [
                InlineKeyboardButton("💰 कीमत / Amount", callback_data="edit_field:price"),
                InlineKeyboardButton("✅ पूरा हुआ — सेव करें", callback_data="smart_confirm_save"),
            ],
            [InlineKeyboardButton("❌ रद्द करें", callback_data="cancel_action")],
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("✏️ Device Name", callback_data="edit_field:name"),
                InlineKeyboardButton("🏷️ Category", callback_data="edit_field:category"),
            ],
            [
                InlineKeyboardButton("🏬 Store / Retailer", callback_data="edit_field:retailer"),
                InlineKeyboardButton("�5 Purchase Date", callback_data="edit_field:date"),
            ],
            [
                InlineKeyboardButton("🛡️ Warranty Period", callback_data="edit_field:warranty"),
                InlineKeyboardButton("🔢 Serial / IMEI", callback_data="edit_field:serial"),
            ],
            [
                InlineKeyboardButton("💰 Price / Amount", callback_data="edit_field:price"),
                InlineKeyboardButton("✅ Done — Save to Vault", callback_data="smart_confirm_save"),
            ],
            [InlineKeyboardButton("❌ Discard", callback_data="cancel_action")],
        ]
    return InlineKeyboardMarkup(keyboard)


def get_category_keyboard():
    """Category picker for registered products."""
    keyboard = [
        [
            InlineKeyboardButton("📱 Smartphone / Tablet", callback_data="cat:Smartphone"),
            InlineKeyboardButton("💻 Laptop / PC", callback_data="cat:Laptop"),
        ],
        [
            InlineKeyboardButton("📺 TV & Audio", callback_data="cat:TV & Audio"),
            InlineKeyboardButton("❄️ AC & Refrigerator", callback_data="cat:Home Appliance"),
        ],
        [
            InlineKeyboardButton("⌚ Smartwatch & Wearables", callback_data="cat:Wearable"),
            InlineKeyboardButton("🔌 Kitchen & Small Appliances", callback_data="cat:Kitchen Appliance"),
        ],
        [
            InlineKeyboardButton("🚗 Vehicle / EV Gadget", callback_data="cat:Vehicle/EV"),
            InlineKeyboardButton("📦 Other Gadgets", callback_data="cat:Other"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_platform_keyboard():
    """Platform / retailer where device was purchased."""
    keyboard = [
        [
            InlineKeyboardButton("📦 Amazon India", callback_data="plat:Amazon"),
            InlineKeyboardButton("🛍️ Flipkart", callback_data="plat:Flipkart"),
        ],
        [
            InlineKeyboardButton("🏬 Croma", callback_data="plat:Croma"),
            InlineKeyboardButton("⚡ Reliance Digital", callback_data="plat:Reliance Digital"),
        ],
        [
            InlineKeyboardButton("🍎 Apple Store / Brand", callback_data="plat:Official Store"),
            InlineKeyboardButton("🏪 Local Offline Store", callback_data="plat:Offline Store"),
        ],
        [InlineKeyboardButton("⏩ Skip", callback_data="plat:Unknown")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_warranty_period_keyboard():
    """Warranty duration presets common in India."""
    keyboard = [
        [
            InlineKeyboardButton("6 Months", callback_data="warn:6"),
            InlineKeyboardButton("1 Year (Standard)", callback_data="warn:12"),
        ],
        [
            InlineKeyboardButton("2 Years", callback_data="warn:24"),
            InlineKeyboardButton("3 Years", callback_data="warn:36"),
        ],
        [
            InlineKeyboardButton("5 Years (Compressor/Motor)", callback_data="warn:60"),
        ],
        [InlineKeyboardButton("✏️ Enter Custom Months", callback_data="warn:custom")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_product_actions_keyboard(product_id: int):
    """Actions available when viewing a specific product in the vault."""
    keyboard = [
        [
            InlineKeyboardButton("🧾 View Stored Bill", callback_data=f"view_bill:{product_id}"),
            InlineKeyboardButton("📑 Claim Dossier PDF", callback_data=f"gen_pdf:{product_id}"),
        ],
        [
            InlineKeyboardButton("🛡️ Extend Warranty", callback_data=f"extend_warn:{product_id}"),
            InlineKeyboardButton("💰 Resale Value (Cashify)", callback_data=f"cashify:{product_id}"),
        ],
        [
            InlineKeyboardButton("🎧 Brand Helpline", callback_data=f"brand_help:{product_id}"),
            InlineKeyboardButton("🗑️ Remove Item", callback_data=f"del_item:{product_id}"),
        ],
        [InlineKeyboardButton("⬅️ Back to Catalog", callback_data="list_vault")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_monetization_keyboard(product_id: int = None):
    """Monetization options for warranties & maintenance."""
    pid = product_id or 0
    keyboard = [
        [
            InlineKeyboardButton("🛡️ OneAssist Extended Care", callback_data=f"lead:OneAssist:{pid}"),
            InlineKeyboardButton("🛡️ Onsitego Protection", callback_data=f"lead:Onsitego:{pid}"),
        ],
        [
            InlineKeyboardButton("💰 Check Cashify Trade-in", callback_data=f"lead:Cashify:{pid}"),
            InlineKeyboardButton("🔧 Urban Company Doorstep Check", callback_data=f"lead:UrbanCompany:{pid}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
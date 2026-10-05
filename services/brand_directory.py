"""
Brand Directory & Support Engine for India.
Provides verified toll-free numbers, WhatsApp support lines, and claim portals.
"""

BRAND_SUPPORT_DATA = {
    "apple": {
        "name": "Apple India",
        "toll_free": "000800 1009009",
        "whatsapp": None,
        "support_url": "https://support.apple.com/en-in",
        "warranty_check_url": "https://checkcoverage.apple.com/in/en/",
    },
    "samsung": {
        "name": "Samsung India",
        "toll_free": "1800 572 67864 / 1800 40 7267864",
        "whatsapp": "https://wa.me/91180057267864",
        "support_url": "https://www.samsung.com/in/support/",
        "warranty_check_url": "https://www.samsung.com/in/support/your-service/warranty-check",
    },
    "lg": {
        "name": "LG Electronics India",
        "toll_free": "1800 315 9999 / 1800 180 9999",
        "whatsapp": "https://wa.me/919711709999",
        "support_url": "https://www.lg.com/in/support",
        "warranty_check_url": "https://www.lg.com/in/support/warranty",
    },
    "sony": {
        "name": "Sony India",
        "toll_free": "1800 103 7799",
        "whatsapp": "https://wa.me/918595997669",
        "support_url": "https://www.sony.co.in/electronics/support",
        "warranty_check_url": "https://www.sony.co.in/microsite/warranty/",
    },
    "xiaomi": {
        "name": "Xiaomi / Redmi India",
        "toll_free": "1800 103 6286",
        "whatsapp": "https://wa.me/918861826286",
        "support_url": "https://www.mi.com/in/service/repair/",
        "warranty_check_url": "https://www.mi.com/in/verify/#/en/tab/imei",
    },
    "oneplus": {
        "name": "OnePlus India",
        "toll_free": "1800 102 8411",
        "whatsapp": "https://wa.me/919289606888",
        "support_url": "https://www.oneplus.in/support",
        "warranty_check_url": "https://www.oneplus.in/support/repair-pricing",
    },
    "dell": {
        "name": "Dell India",
        "toll_free": "1800 425 0088 / 1800 425 2067",
        "whatsapp": "https://wa.me/918045688555",
        "support_url": "https://www.dell.com/support/home/en-in",
        "warranty_check_url": "https://www.dell.com/support/home/en-in?app=warranty",
    },
    "hp": {
        "name": "HP India",
        "toll_free": "1800 258 7170",
        "whatsapp": "https://wa.me/912261014560",
        "support_url": "https://support.hp.com/in-en",
        "warranty_check_url": "https://support.hp.com/in-en/check-warranty",
    },
    "lenovo": {
        "name": "Lenovo India",
        "toll_free": "1800 419 7555",
        "whatsapp": "https://wa.me/918067916666",
        "support_url": "https://pcsupport.lenovo.com/in/en",
        "warranty_check_url": "https://pcsupport.lenovo.com/in/en/warranty-lookup",
    },
    "boat": {
        "name": "boAt Lifestyle",
        "toll_free": "022 6918 1920",
        "whatsapp": "https://wa.me/919930776788",
        "support_url": "https://support.boat-lifestyle.com/",
        "warranty_check_url": "https://support.boat-lifestyle.com/register-complaint",
    },
    "noise": {
        "name": "Noise (GoNoise)",
        "toll_free": "+91 88821 32132",
        "whatsapp": "https://wa.me/918882132132",
        "support_url": "https://help.gonoise.com/",
        "warranty_check_url": "https://help.gonoise.com/support/tickets/new",
    },
    "whirlpool": {
        "name": "Whirlpool India",
        "toll_free": "1800 208 1800",
        "whatsapp": "https://wa.me/919667427788",
        "support_url": "https://www.whirlpoolindia.com/services",
        "warranty_check_url": "https://www.whirlpoolindia.com/request-service",
    },
    "godrej": {
        "name": "Godrej Appliances",
        "toll_free": "1800 209 5511",
        "whatsapp": "https://wa.me/919321665511",
        "support_url": "https://www.godrej.com/appliances/support",
        "warranty_check_url": "https://www.godrej.com/appliances/book-a-service",
    },
    "havells": {
        "name": "Havells India",
        "toll_free": "08045 77 1313",
        "whatsapp": "https://wa.me/919711773333",
        "support_url": "https://www.havells.com/en/consumer/support.html",
        "warranty_check_url": "https://www.havells.com/en/consumer/support/register-complaint.html",
    },
    "philips": {
        "name": "Philips India",
        "toll_free": "1800 102 2929",
        "whatsapp": "https://wa.me/919311827299",
        "support_url": "https://www.philips.co.in/c-w/support-home.html",
        "warranty_check_url": "https://www.philips.co.in/c-w/support-home/warranty.html",
    },
    "asus": {
        "name": "ASUS India",
        "toll_free": "1800 209 0365",
        "whatsapp": "https://wa.me/912261567300",
        "support_url": "https://www.asus.com/in/support/",
        "warranty_check_url": "https://www.asus.com/in/support/warranty-status-inquiry/",
    },
    "realme": {
        "name": "Realme India",
        "toll_free": "1800 102 2777",
        "whatsapp": "https://wa.me/919319692222",
        "support_url": "https://www.realme.com/in/support",
        "warranty_check_url": "https://www.realme.com/in/support/phonecheck",
    },
}


def find_brand_support(brand_query: str):
    clean_q = brand_query.lower().strip()
    for key, data in BRAND_SUPPORT_DATA.items():
        if key in clean_q or clean_q in key:
            return data
    return None
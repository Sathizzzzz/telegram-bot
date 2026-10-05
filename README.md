# ClaimSathi (क्लेम साथी)
### Aapka Personal Warranty Partner — AI Bill Locker & Free Claim Assistant (Free Telegram Edition)

> **Solving the Real Indian Consumer Pain Points:**
> * **Lost & Faded Bills**: Paper receipts fade within 3-6 months. We permanently archive the bill in the cloud with automatic brand, purchase date, and warranty extraction.
> * **"Is It Claimable?" Mystery**: When a screen shows a green line, earbud goes dead, or AC stops cooling, ClaimSathi diagnoses whether the brand will repair/replace it for free.
> * **Lost Bill Recovery**: Step-by-step guides to retrieve legal duplicate tax invoices from Amazon, Flipkart, Croma, Reliance Digital, or claim via IMEI/Serial number without paper bills.
> * **100% FREE on Telegram**: Zero hosting/WhatsApp API fees, unlimited cloud document storage, no credit card required.

---

## 📱 Feature Mapping (Tailored for India)

| Feature | How ClaimSathi Solves the Indian Problem |
| :--- | :--- |
| **⚡ AI Bill Scan & 1-Click Vault** | Take a photo of any receipt (paper bill, Amazon/Flipkart PDF, appliance plate). AI extracts Brand, Date, Retailer, and Expiry date for 1-click archiving. |
| **🔍 Is It Claimable? (क्लेम चेकर)** | Send a photo of the defect (green line, cracked back, loose hinge) or type your problem. Get an instant **Claimability Verdict**, Indian service center battle tips, and brand WhatsApp support. |
| **🧾 Lost Bill Recovery Guide** | Complete actionable instructions for recovering duplicate invoices from Amazon, Flipkart, Croma, Reliance Digital, and local GST dealers. |
| **📂 My Vault / Catalog** | View all registered appliances, remaining days countdown, and view saved bills anytime. |
| **📑 1-Click Claim Dossier PDF** | Official service center claim PDF with purchase date, retailer, IMEI/serial number ready for authorized center visits. |
| **🎧 Brand Support Directory** | Verified toll-free numbers and official WhatsApp support bots for Samsung, Apple, LG, Sony, Xiaomi, boAt, Dell, HP, Whirlpool, etc. |
| **🔔 Automated Expiry Reminders** | Timely alerts at 30, 15, 7, and 1 day before warranty expires. |
| **💰 Monetization Hub** | Extended warranty (OneAssist / Onsitego), Cashify resale trade-in, and Urban Company doorstep appliance check. |

---

## 🚀 Quick Setup (Takes 2 Minutes)

### Step 1: Get your FREE Bot Token from Telegram
1. Open the **Telegram** app on your phone or PC.
2. In the search bar, search for **`@BotFather`** (the official verified bot with a blue checkmark).
3. Send the command:
   ```
   /newbot
   ```
4. Follow the prompts:
   - Enter a display name: `ClaimSathi`
   - Enter a username ending in `bot`: (e.g., `ClaimSathiBot` or `ClaimSathi_bot`)
5. BotFather will give you a token like:
   `7123456789:AAFlm3x4Yz...`
6. Copy that token!

---

### Step 2: Configure the Token
Open the file [`telegram-bot/.env`](file:///c:/Users/Welcome/Documents/telegram-bot/.env) and paste your token:
```env
TELEGRAM_BOT_TOKEN=paste_your_token_here
```

---

### Step 3: Run the Bot!

#### On Windows:
Just double-click:
[`run_bot.bat`](file:///c:/Users/Welcome/Documents/telegram-bot/run_bot.bat)

*Or in your terminal / PowerShell:*
```bash
cd telegram-bot
pip install -r requirements.txt
python main.py
```

---

## 🛠️ Project Structure

```
telegram-bot/
├── .env                  # Bot token & configuration
├── .env.example          # Sample environment variables
├── requirements.txt      # Python dependencies (python-telegram-bot, reportlab, etc.)
├── main.py               # Bot entrypoint & scheduler
├── config.py             # Config settings loader
├── run_bot.bat           # 1-click Windows runner
│
├── database/
│   ├── models.py         # Users, ProductWarranty, ReminderLog, LeadRequest models
│   └── db.py             # SQLite database session manager
│
├── handlers/
│   ├── start.py          # /start welcome message & main menu
│   ├── add_product.py    # Multi-step bill upload & product registration conversation
│   ├── vault.py          # Catalog, view bills, download PDF claim sheets
│   ├── monetization.py   # OneAssist, Onsitego, Cashify trade-in & Pro tiers
│   ├── claim.py          # Verified Indian brand customer care directory
│   └── reminders.py      # Automated daily expiry checks & 30-day alert simulator
│
├── services/
│   ├── brand_directory.py # Curated support numbers for 20+ top Indian brands
│   └── pdf_service.py    # ReportLab Claim Dossier generator
│
└── utils/
    └── keyboards.py      # Interactive inline & reply keyboards
```

---

## 💡 How the Monetization Engine Works (Zero Hosting Costs)
1. **Affiliate Links (OneAssist & Onsitego)**: When users register a gadget and approach the warranty expiry date, the bot presents them with extended warranty options. Each click logs a lead and redirects through your partner link.
2. **Cashify Trade-in Integration**: Prompting users at the 30-day mark allows them to sell their old device at peak valuation before it becomes out-of-warranty.
3. **Pro Subscription**: Tiered plan model (₹49/month or ₹399/year) stored directly in SQLite for VIP users who want unlimited vault capacity and priority claim assistance.
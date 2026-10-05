"""
Vault / Catalog Handler for WarrantyBot India.
Allows users to browse archived items, view stored invoices, and generate official claim PDFs.
"""
from pathlib import Path
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.db import get_db
from database.models import ProductWarranty, User
from utils.keyboards import get_product_actions_keyboard
from services.pdf_service import generate_claim_dossier
from services.brand_directory import find_brand_support

logger = logging.getLogger("ClaimSathi.Vault")


async def show_vault_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the user's complete catalog/vault of products."""
    tg_user = update.effective_user
    if not tg_user:
        return

    with get_db() as db:
        products = (
            db.query(ProductWarranty)
            .filter_by(user_id=tg_user.id)
            .order_by(ProductWarranty.expiry_date.asc())
            .all()
        )

        if not products:
            msg = (
                "📭 *Your Warranty Vault is Empty!*\n\n"
                "You haven't archived any appliances or gadgets yet.\n\n"
                "Tap *📸 Upload Store Bill* to save your first receipt and activate automated alerts!"
            )
            if update.message:
                await update.message.reply_text(msg, parse_mode="Markdown")
            elif update.callback_query:
                await update.callback_query.message.reply_text(msg, parse_mode="Markdown")
            return

        buttons = []
        catalog_lines = ["📂 *Your Warranty Vault Catalog:*\n"]

        for idx, prod in enumerate(products, 1):
            days = prod.days_remaining
            if days > 15:
                status_icon = "🟢"
                status_note = f"{days}d left"
            elif days >= 0:
                status_icon = "🟡"
                status_note = f"{days}d left (Expiring soon!)"
            else:
                status_icon = "🔴"
                status_note = f"Expired {abs(days)}d ago"

            catalog_lines.append(f"{idx}. {status_icon} *{prod.product_name}* — {status_note}")
            buttons.append([
                InlineKeyboardButton(
                    f"{status_icon} {prod.product_name} ({prod.brand})",
                    callback_data=f"view_prod:{prod.id}",
                )
            ])

        catalog_lines.append("\n👇 *Tap any item below to view bill, claim dossier, or extend warranty:*")
        text = "\n".join(catalog_lines)
        markup = InlineKeyboardMarkup(buttons)

        if update.message:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
        elif update.callback_query:
            await update.callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=markup)


async def handle_vault_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles item selection, invoice retrieval, PDF generation, and deletion."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "list_vault":
        return await show_vault_catalog(update, context)

    # View individual product card
    if data.startswith("view_prod:"):
        prod_id = int(data.split(":")[1])
        with get_db() as db:
            prod = db.query(ProductWarranty).filter_by(id=prod_id).first()
            if not prod:
                await query.message.reply_text("Product not found.")
                return

            days = prod.days_remaining
            status_icon = "🟢" if days > 15 else ("🟡" if days >= 0 else "🔴")

            card = (
                f"🛡️ *Vault Item: {prod.product_name}*\n\n"
                f"• Brand: *{prod.brand}*\n"
                f"• Category: {prod.category}\n"
                f"• Retailer: {prod.purchase_platform or 'N/A'}\n"
                f"• Purchased: {prod.purchase_date.strftime('%d %b %Y')}\n"
                f"• Warranty Expiry: *{prod.expiry_date.strftime('%d %b %Y')}*\n"
                f"• Status: {status_icon} *{days} Days Remaining*\n"
                f"• Serial / IMEI: `{prod.serial_no or 'Not set'}`\n"
                f"• Bill Stored: {'✅ Yes (Available below)' if prod.invoice_file_id else '⚠️ No'}\n"
            )

            await query.message.edit_text(
                card,
                parse_mode="Markdown",
                reply_markup=get_product_actions_keyboard(prod.id),
            )

    # Retrieve and view stored bill
    elif data.startswith("view_bill:"):
        prod_id = int(data.split(":")[1])
        with get_db() as db:
            prod = db.query(ProductWarranty).filter_by(id=prod_id).first()
            if not prod or (not prod.invoice_file_id and not prod.local_invoice_path):
                await query.message.reply_text("⚠️ No bill photo was uploaded for this item.")
                return

            caption = (
                f"🧾 *Stored Bill / Invoice*\n\n"
                f"• Item: *{prod.product_name}*\n"
                f"• Store: *{prod.purchase_platform or 'Store'}*\n"
                f"• Date: *{prod.purchase_date.strftime('%d %b %Y')}*\n"
                f"• Expiry: *{prod.expiry_date.strftime('%d %b %Y')}*\n"
                f"• Serial/IMEI: `{prod.serial_no or 'Not set'}`"
            )
            sent = False
            if prod.invoice_file_id:
                try:
                    if prod.invoice_file_type == "photo":
                        await query.message.reply_photo(photo=prod.invoice_file_id, caption=caption, parse_mode="Markdown")
                    else:
                        await query.message.reply_document(document=prod.invoice_file_id, caption=caption, parse_mode="Markdown")
                    sent = True
                except Exception as e:
                    logger.warning(f"Could not send by file_id, falling back to local file: {e}")

            if not sent and prod.local_invoice_path:
                if prod.local_invoice_path.startswith("http"):
                    try:
                        await query.message.reply_photo(photo=prod.local_invoice_path, caption=caption, parse_mode="Markdown")
                        sent = True
                    except Exception as e:
                        logger.warning(f"Could not send via cloud URL: {e}")

                if not sent:
                    p = Path(prod.local_invoice_path)
                    if p.exists():
                        with open(p, "rb") as f:
                            if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                                await query.message.reply_photo(photo=f, caption=caption, parse_mode="Markdown")
                            else:
                                await query.message.reply_document(document=f, filename=p.name, caption=caption, parse_mode="Markdown")
                        sent = True

            if not sent:
                await query.message.reply_text("⚠️ Bill file could not be retrieved from the cloud vault.")

    # Generate Official Claim Dossier PDF
    elif data.startswith("gen_pdf:"):
        prod_id = int(data.split(":")[1])
        with get_db() as db:
            prod = db.query(ProductWarranty).filter_by(id=prod_id).first()
            user = db.query(User).filter_by(user_id=prod.user_id).first()
            if not prod:
                await query.message.reply_text("Product not found.")
                return

            await query.message.reply_text("⏳ Generating official Warranty Claim Dossier PDF...")
            pdf_bytes = generate_claim_dossier(prod, user)
            filename = f"WarrantyClaim_{prod.brand}_{prod.id}.pdf"
            await query.message.reply_document(
                document=pdf_bytes,
                filename=filename,
                caption=f"📑 Official Claim Dossier for *{prod.product_name}*\nTake this PDF to the service center or mail it to brand support.",
                parse_mode="Markdown",
            )

    # Show Brand Support Help
    elif data.startswith("brand_help:"):
        prod_id = int(data.split(":")[1])
        with get_db() as db:
            prod = db.query(ProductWarranty).filter_by(id=prod_id).first()
            if not prod:
                return
            support = find_brand_support(prod.brand)
            if support:
                msg = (
                    f"🎧 *Official Support for {support['name']}*\n\n"
                    f"📞 Toll-Free: `{support['toll_free']}`\n"
                    f"💬 WhatsApp: {support['whatsapp'] or 'Available via Toll-Free'}\n"
                    f"🌐 Portal: {support['support_url']}\n"
                    f"🔍 Official Warranty Check: {support['warranty_check_url']}"
                )
            else:
                msg = (
                    f"🎧 Brand Support for *{prod.brand}*:\n\n"
                    f"Please visit the official brand website or check the customer care number on your original store bill."
                )
            await query.message.reply_text(msg, parse_mode="Markdown")

    # Delete product
    elif data.startswith("del_item:"):
        prod_id = int(data.split(":")[1])
        with get_db() as db:
            prod = db.query(ProductWarranty).filter_by(id=prod_id).first()
            if prod:
                db.delete(prod)
                db.commit()
                await query.message.reply_text(f"🗑️ *{prod.product_name}* removed from your vault.", parse_mode="Markdown")
                await show_vault_catalog(update, context)
"""
PDF Generation Service for WarrantyBot India.
Generates an official-looking Warranty Claim Dossier ready for service centers.
"""
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_claim_dossier(product, user) -> BytesIO:
    """Generates an official PDF claim summary sheet for brand service centers."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#0f766e"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "SubTitleStyle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14,
    )
    label_style = ParagraphStyle(
        "LabelStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=colors.HexColor("#1e293b"),
    )
    val_style = ParagraphStyle(
        "ValStyle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#334155"),
    )

    # Header
    story.append(Paragraph("🛡️ ClaimSathi (क्लेम साथी) — Official Warranty Claim Dossier", title_style))
    story.append(
        Paragraph(
            f"Generated on {datetime.now().strftime('%d %B %Y, %I:%M %p')} | Verified Vault Record",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 10))

    # Warranty Status Badge calculation
    days_left = product.days_remaining
    if days_left > 0:
        status_text = f"ACTIVE ({days_left} days remaining)"
        status_color = colors.HexColor("#16a34a")
    elif days_left == 0:
        status_text = "EXPIRES TODAY"
        status_color = colors.HexColor("#ca8a04")
    else:
        status_text = f"EXPIRED ({abs(days_left)} days ago)"
        status_color = colors.HexColor("#dc2626")

    # Table of Details
    data = [
        [Paragraph("Product Name:", label_style), Paragraph(str(product.product_name), val_style)],
        [Paragraph("Brand & Category:", label_style), Paragraph(f"{product.brand} ({product.category})", val_style)],
        [Paragraph("Model Number:", label_style), Paragraph(product.model_no or "Not specified", val_style)],
        [Paragraph("Serial / IMEI No:", label_style), Paragraph(product.serial_no or "Not specified", val_style)],
        [Paragraph("Purchase Platform:", label_style), Paragraph(product.purchase_platform or "Direct Retailer", val_style)],
        [Paragraph("Purchase Date:", label_style), Paragraph(product.purchase_date.strftime("%d %b %Y"), val_style)],
        [Paragraph("Warranty Coverage:", label_style), Paragraph(f"{product.warranty_months} Months", val_style)],
        [Paragraph("Warranty Expiry Date:", label_style), Paragraph(product.expiry_date.strftime("%d %b %Y"), val_style)],
        [Paragraph("Current Status:", label_style), Paragraph(f"<b>{status_text}</b>", val_style)],
        [Paragraph("Customer Name:", label_style), Paragraph(f"{user.first_name or ''} {user.last_name or ''}".strip() or "Registered Customer", val_style)],
        [Paragraph("User Telegram ID:", label_style), Paragraph(str(user.user_id), val_style)],
    ]

    t = Table(data, colWidths=[150, 390])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 20))

    # Notes section
    if product.notes:
        story.append(Paragraph("<b>Additional Notes / Invoice Reference:</b>", label_style))
        story.append(Paragraph(product.notes, val_style))
        story.append(Spacer(1, 15))

    # Instructions for Service Center
    notice_style = ParagraphStyle(
        "NoticeStyle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#475569"),
        backColor=colors.HexColor("#f1f5f9"),
        borderColor=colors.HexColor("#cbd5e1"),
        borderWidth=1,
        borderPadding=10,
        spaceBefore=10,
    )
    instructions = (
        "<b>Important Notice for Authorized Service Centers:</b><br/>"
        "This dossier has been digitally generated via ClaimSathi (क्लेम साथी) Vault. "
        "Original purchase invoices and registration proofs are archived digitally. "
        "For immediate assistance, please reference the serial/IMEI number above."
    )
    story.append(Paragraph(instructions, notice_style))

    doc.build(story)
    buffer.seek(0)
    return buffer
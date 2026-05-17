# # # account/id_card_utils.py
# # import qrcode
# # import base64
# # from io import BytesIO
# # from datetime import datetime
# # from PIL import Image, ImageDraw, ImageFont
# # from reportlab.lib.pagesizes import letter, landscape
# # from reportlab.pdfgen import canvas
# # from reportlab.lib.utils import ImageReader
# # from django.core.files.base import ContentFile
# # from django.core.files.storage import default_storage
# # import os
# # from django.conf import settings

# # class IDCardGenerator:
    
# #     # @staticmethod
# #     # def generate_qr_code(visitor_id, visitor_data):
# #     #     """
# #     #     Generate QR code containing visitor information
# #     #     """
# #     #     # Create QR code data
# #     #     qr_data = {
# #     #         'visitor_id': visitor_id,
# #     #         'full_name': visitor_data.get('full_name'),
# #     #         'email': visitor_data.get('email'),
# #     #         'phone': visitor_data.get('phone_number'),
# #     #         'company': visitor_data.get('company_name', ''),
# #     #         'check_in': str(visitor_data.get('designated_check_in')),
# #     #         'check_out': str(visitor_data.get('designated_check_out')),
# #     #         'site': visitor_data.get('site', {}).get('name') if visitor_data.get('site') else None,
# #     #         'sections': [s.get('name') for s in visitor_data.get('accessible_sections', [])]
# #     #     }
        
# #     #     # Convert to string
# #     #     qr_text = str(qr_data)
        
# #     #     # Generate QR code
# #     #     qr = qrcode.QRCode(
# #     #         version=1,
# #     #         error_correction=qrcode.constants.ERROR_CORRECT_L,
# #     #         box_size=10,
# #     #         border=4,
# #     #     )
# #     #     qr.add_data(qr_text)
# #     #     qr.make(fit=True)
        
# #     #     # Create QR code image
# #     #     qr_image = qr.make_image(fill_color="black", back_color="white")
        
# #     #     # Save to bytes
# #     #     buffer = BytesIO()
# #     #     qr_image.save(buffer, format='PNG')
# #     #     buffer.seek(0)
        
# #     #     return buffer
    
# #     # @staticmethod
# #     # def generate_qr_code(visitor_id, visitor_data):
# #     #     """
# #     #     Generate QR code containing visitor information
# #     #     visitor_data should be a DICTIONARY
# #     #     """
# #     #     # Ensure visitor_data is a dictionary
# #     #     if not isinstance(visitor_data, dict):
# #     #         raise ValueError(f"visitor_data must be a dictionary, got {type(visitor_data)}")
        
# #     #     # Create QR code data as a JSON string
# #     #     import json
# #     #     qr_text = json.dumps(visitor_data, default=str)
        
# #     #     # Generate QR code
# #     #     qr = qrcode.QRCode(
# #     #         version=1,
# #     #         error_correction=qrcode.constants.ERROR_CORRECT_L,
# #     #         box_size=10,
# #     #         border=4,
# #     #     )
# #     #     qr.add_data(qr_text)
# #     #     qr.make(fit=True)
        
# #     #     # Create QR code image
# #     #     qr_image = qr.make_image(fill_color="black", back_color="white")
        
# #     #     # Save to bytes
# #     #     buffer = BytesIO()
# #     #     qr_image.save(buffer, format='PNG')
# #     #     buffer.seek(0)
        
# #     #     return buffer

    
# #     # account/card_utils.py

# #     # @staticmethod
# #     # def generate_qr_code(visitor_id, visitor_data):
# #     #     """
# #     #     Generate QR code containing visitor information
# #     #     visitor_data should be a DICTIONARY with redirect_url
# #     #     """
# #     #     import json
        
# #     #     # Ensure visitor_data is a dictionary
# #     #     if not isinstance(visitor_data, dict):
# #     #         raise ValueError(f"visitor_data must be a dictionary, got {type(visitor_data)}")
        
# #     #     # Make sure redirect_url is included
# #     #     if 'redirect_url' not in visitor_data:
# #     #         # Add redirect URL if missing
# #     #         from django.conf import settings
# #     #         frontend_url = getattr(settings, 'FRONTEND_URL', 'https://vmsfrontend2026.z29.web.core.windows.net')
# #     #         visitor_data['redirect_url'] = f"{frontend_url}/#/visitor/{visitor_data.get('visitor_id')}"
        
# #     #     # Convert to JSON string
# #     #     qr_text = json.dumps(visitor_data, default=str)
        
# #     #     print(f"📱 Encoding QR code with data: {qr_text[:200]}...")  # Debug log
        
# #     #     # Generate QR code with larger size for more data
# #     #     qr = qrcode.QRCode(
# #     #         version=5,  # Increased version for more data (was 1)
# #     #         error_correction=qrcode.constants.ERROR_CORRECT_Q,
# #     #         box_size=10,
# #     #         border=4,
# #     #     )
# #     #     qr.add_data(qr_text)
# #     #     qr.make(fit=True)
        
# #     #     # Create QR code image
# #     #     qr_image = qr.make_image(fill_color="black", back_color="white")
        
# #     #     # Save to bytes
# #     #     buffer = BytesIO()
# #     #     qr_image.save(buffer, format='PNG')
# #     #     buffer.seek(0)
        
# #     #     return buffer
    

# #     @staticmethod
# #     def generate_qr_code(visitor_id, visitor_data):
# #         """
# #         Generate QR code containing a URL that redirects to the visitor page
# #         IMPORTANT: QR code must contain a URL, not just JSON data
# #         """
# #         import json
        
# #         # Get frontend URL from settings
# #         from django.conf import settings
# #         frontend_url = getattr(settings, 'FRONTEND_URL', 'https://vmsfrontend2026.z29.web.core.windows.net')
        
# #         # Create the redirect URL (this is what the QR code should contain)
# #         # Phone cameras recognize "https://" as a URL to open
# #         redirect_url = f"{frontend_url}/#/visitor/{visitor_id}"
        
# #         print(f"📱 Generating QR code with URL: {redirect_url}")
        
# #         # Generate QR code with URL (not JSON)
# #         # This ensures the phone's camera opens the browser instead of showing text
# #         qr = qrcode.QRCode(
# #             version=1,
# #             error_correction=qrcode.constants.ERROR_CORRECT_L,
# #             box_size=10,
# #             border=4,
# #         )
# #         qr.add_data(redirect_url)  # ← USE URL STRING, NOT JSON
# #         qr.make(fit=True)
        
# #         # Create QR code image
# #         qr_image = qr.make_image(fill_color="black", back_color="white")
        
# #         # Save to bytes
# #         buffer = BytesIO()
# #         qr_image.save(buffer, format='PNG')
# #         buffer.seek(0)
        
# #         return buffer
    
# #     @staticmethod
# #     def generate_id_card(visitor, qr_code_buffer, with_photo=False):
# #         """
# #         Generate ID card PDF for visitor
# #         """
# #         buffer = BytesIO()
        
# #         # Create PDF canvas (landscape mode for ID card)
# #         c = canvas.Canvas(buffer, pagesize=landscape(letter))
# #         width, height = landscape(letter)
        
# #         # Card dimensions (standard ID card size)
# #         card_width = width * 0.8
# #         card_height = height * 0.6
# #         card_x = (width - card_width) / 2
# #         card_y = (height - card_height) / 2
        
# #         # Draw card background
# #         c.setFillColorRGB(0.95, 0.95, 0.95)
# #         c.rect(card_x, card_y, card_width, card_height, fill=1, stroke=0)
        
# #         # Draw border
# #         c.setStrokeColorRGB(0.2, 0.4, 0.8)
# #         c.setLineWidth(3)
# #         c.rect(card_x, card_y, card_width, card_height, fill=0, stroke=1)
        
# #         # Header background
# #         c.setFillColorRGB(0.2, 0.4, 0.8)
# #         c.rect(card_x, card_y + card_height - 50, card_width, 50, fill=1, stroke=0)
        
# #         # Title
# #         c.setFillColorRGB(1, 1, 1)
# #         c.setFont("Helvetica-Bold", 16)
# #         c.drawString(card_x + card_width/2 - 50, card_y + card_height - 35, "VISITOR ID CARD")
        
# #         # Visitor Photo (if available)
# #         photo_x = card_x + 20
# #         photo_y = card_y + card_height - 220
# #         photo_size = 100
        
# #         if with_photo and visitor.photo:
# #             try:
# #                 # Download or get photo from URL
# #                 import requests
# #                 response = requests.get(visitor.photo)
# #                 photo_image = Image.open(BytesIO(response.content))
# #                 photo_image = photo_image.resize((photo_size, photo_size))
# #                 photo_buffer = BytesIO()
# #                 photo_image.save(photo_buffer, format='PNG')
# #                 photo_buffer.seek(0)
                
# #                 photo_reader = ImageReader(photo_buffer)
# #                 c.drawImage(photo_reader, photo_x, photo_y, width=photo_size, height=photo_size)
# #             except Exception as e:
# #                 # Draw placeholder if photo fails
# #                 c.setFillColorRGB(0.8, 0.8, 0.8)
# #                 c.rect(photo_x, photo_y, photo_size, photo_size, fill=1, stroke=0)
# #                 c.setFillColorRGB(0, 0, 0)
# #                 c.setFont("Helvetica", 10)
# #                 c.drawString(photo_x + 35, photo_y + 50, "No Photo")
# #         else:
# #             # Draw placeholder
# #             c.setFillColorRGB(0.8, 0.8, 0.8)
# #             c.rect(photo_x, photo_y, photo_size, photo_size, fill=1, stroke=0)
# #             c.setFillColorRGB(0, 0, 0)
# #             c.setFont("Helvetica", 10)
# #             c.drawString(photo_x + 35, photo_y + 50, "No Photo")
        
# #         # Visitor Information
# #         info_x = photo_x + photo_size + 20
# #         info_y = photo_y + photo_size - 20
        
# #         c.setFont("Helvetica-Bold", 12)
# #         c.setFillColorRGB(0, 0, 0)
# #         c.drawString(info_x, info_y, "Visitor Information")
        
# #         c.setFont("Helvetica", 10)
# #         c.setFillColorRGB(0.3, 0.3, 0.3)
        
# #         y_offset = info_y - 20
# #         info_items = [
# #             (f"Name: {visitor.full_name}"),
# #             (f"Email: {visitor.email}"),
# #             (f"Phone: {visitor.phone_number}"),
# #             (f"Company: {visitor.company_name or 'N/A'}"),
# #             (f"Purpose: {visitor.purpose_of_visit[:50] if visitor.purpose_of_visit else 'N/A'}"),
# #         ]
        
# #         for item in info_items:
# #             c.drawString(info_x, y_offset, item)
# #             y_offset -= 15
        
# #         # QR Code
# #         qr_x = card_x + card_width - 130
# #         qr_y = card_y + 20
# #         qr_size = 100
        
# #         qr_reader = ImageReader(qr_code_buffer)
# #         c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)
        
# #         # Check-in/out dates
# #         c.setFont("Helvetica", 8)
# #         c.setFillColorRGB(0.5, 0.5, 0.5)
# #         checkin_str = f"Check-in: {visitor.designated_check_in.strftime('%Y-%m-%d %H:%M') if visitor.designated_check_in else 'N/A'}"
# #         checkout_str = f"Check-out: {visitor.designated_check_out.strftime('%Y-%m-%d %H:%M') if visitor.designated_check_out else 'N/A'}"
# #         c.drawString(card_x + 20, card_y + 15, checkin_str)
# #         c.drawString(card_x + 20, card_y + 5, checkout_str)
        
# #         # Footer
# #         c.setFont("Helvetica", 8)
# #         c.setFillColorRGB(0.5, 0.5, 0.5)
# #         footer_text = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
# #         c.drawString(card_x + card_width - 150, card_y + 5, footer_text)
        
# #         c.save()
# #         buffer.seek(0)
        
# #         return buffer

# #     @staticmethod
# #     def generate_simple_id_card(visitor, qr_code_buffer):
# #         """
# #         Generate simple ID card without photo (fallback)
# #         """
# #         buffer = BytesIO()
        
# #         c = canvas.Canvas(buffer, pagesize=landscape(letter))
# #         width, height = landscape(letter)
        
# #         card_width = width * 0.7
# #         card_height = height * 0.5
# #         card_x = (width - card_width) / 2
# #         card_y = (height - card_height) / 2
        
# #         # Card background
# #         c.setFillColorRGB(0.98, 0.98, 0.98)
# #         c.rect(card_x, card_y, card_width, card_height, fill=1, stroke=0)
        
# #         # Border
# #         c.setStrokeColorRGB(0.2, 0.4, 0.8)
# #         c.setLineWidth(2)
# #         c.rect(card_x, card_y, card_width, card_height, fill=0, stroke=1)
        
# #         # Header
# #         c.setFillColorRGB(0.2, 0.4, 0.8)
# #         c.rect(card_x, card_y + card_height - 40, card_width, 40, fill=1, stroke=0)
# #         c.setFillColorRGB(1, 1, 1)
# #         c.setFont("Helvetica-Bold", 14)
# #         c.drawString(card_x + card_width/2 - 45, card_y + card_height - 28, "VISITOR PASS")
        
# #         # Visitor name (large)
# #         c.setFillColorRGB(0, 0, 0)
# #         c.setFont("Helvetica-Bold", 16)
# #         c.drawString(card_x + 20, card_y + card_height - 80, visitor.full_name)
        
# #         # Other info
# #         c.setFont("Helvetica", 10)
# #         info_y = card_y + card_height - 110
# #         info_items = [
# #             f"Company: {visitor.company_name or 'N/A'}",
# #             f"Purpose: {visitor.purpose_of_visit[:40] if visitor.purpose_of_visit else 'N/A'}",
# #             f"Check-in: {visitor.designated_check_in.strftime('%Y-%m-%d %H:%M') if visitor.designated_check_in else 'N/A'}",
# #         ]
        
# #         for item in info_items:
# #             c.drawString(card_x + 20, info_y, item)
# #             info_y -= 15
        
# #         # QR Code
# #         qr_size = 80
# #         qr_reader = ImageReader(qr_code_buffer)
# #         c.drawImage(qr_reader, card_x + card_width - qr_size - 20, card_y + 20, width=qr_size, height=qr_size)
        
# #         c.save()
# #         buffer.seek(0)
        
# #         return buffer



# # account/id_card_utils.py
# """
# ID Card generator — CR80 plastic card format (85.6 × 54 mm, landscape).
 
# Print at 100 % scale (no page-fit / shrink-to-fit) on any CR80 card printer
# for a perfect-cut result.  The page size in the PDF *is* the card size.
 
# Layout zones (bottom-up, ReportLab coordinate system)
# ──────────────────────────────────────────────────────
#   HEADER   10.5 mm  navy bar — org name + card type label
#   GOLD BAR  1.2 mm  gold rule separating header from body
#   BODY     33.8 mm  photo | info fields | QR code
#   FOOTER    8.5 mm  navy bar — check-in / check-out / timestamp
 
# Body columns (left → right)
# ────────────────────────────
#   Gold accent tab  1.5 mm
#   Photo box       18 mm   vertically centred in body
#   Gutter           3 mm
#   Info column     ~41 mm  name (large) + 4 labelled fields
#   Gutter           2 mm
#   QR column       16 mm   square QR + "Scan to verify" + visitor ID
#   Padding          3 mm
# """
 
# import qrcode
# from io import BytesIO
# from datetime import datetime
# from PIL import Image
# from reportlab.pdfgen import canvas
# from reportlab.lib.utils import ImageReader
# from reportlab.lib.units import mm
# from reportlab.lib.colors import HexColor
# from django.conf import settings
 
 
# # ── Design tokens ──────────────────────────────────────────────────────────
# NAVY        = HexColor("#0D2257")
# GOLD        = HexColor("#D4A017")
# BG          = HexColor("#F7F9FC")
# STRIPE      = HexColor("#E8EDF5")
# TEXT_DARK   = HexColor("#0D1B3E")
# TEXT_MID    = HexColor("#4A5568")
# TEXT_LIGHT  = HexColor("#FFFFFF")
# TEXT_MUTED  = HexColor("#8AAFD8")
# PHOTO_FILL  = HexColor("#DDE3F0")
# PHOTO_STROKE= HexColor("#9AAAC8")
# SEP_LINE    = HexColor("#D0D8EC")
 
# # ── Card geometry (CR80, landscape) ────────────────────────────────────────
# CW = 85.6 * mm
# CH = 54.0 * mm
 
# HEADER_H = 10.5 * mm
# GOLD_H   =  1.2 * mm
# FOOTER_H =  8.5 * mm
# PAD      =  3.0 * mm
 
# BODY_Y   = FOOTER_H
# BODY_H   = CH - HEADER_H - GOLD_H - FOOTER_H
# BODY_TOP = BODY_Y + BODY_H
 
# PHOTO_W  = 18 * mm
# PHOTO_H  = 22 * mm
# PHOTO_X  = PAD
# PHOTO_Y  = BODY_Y + (BODY_H - PHOTO_H) / 2
 
# QR_SIZE  = 16 * mm
# QR_X     = CW - PAD - QR_SIZE
# QR_Y     = BODY_Y + (BODY_H - QR_SIZE) / 2
 
# INFO_X   = PHOTO_X + PHOTO_W + 3 * mm
# INFO_W   = QR_X - INFO_X - 2 * mm
 
# NAME_Y        = BODY_TOP - 3.5 * mm
# FIELD_START_Y = NAME_Y  - 5.0 * mm
# ROW_GAP       = 5.3 * mm
 
 
# # ── Internal helpers ───────────────────────────────────────────────────────
 
# def _truncate(c, text, font, size, max_width):
#     if c.stringWidth(text, font, size) <= max_width:
#         return text
#     while len(text) > 1 and c.stringWidth(text + "...", font, size) > max_width:
#         text = text[:-1]
#     return text + "..."
 
 
# def _draw_background(c):
#     c.setFillColor(BG)
#     c.rect(0, 0, CW, CH, fill=1, stroke=0)
#     c.setFillColor(STRIPE)
#     y = BODY_Y + 1.5 * mm
#     while y < BODY_TOP - 1 * mm:
#         c.rect(PAD, y, CW - 2 * PAD, 0.4, fill=1, stroke=0)
#         y += 1.5 * mm
 
 
# def _draw_header(c, org_name):
#     hdr_y = CH - HEADER_H
#     c.setFillColor(NAVY)
#     c.rect(0, hdr_y, CW, HEADER_H, fill=1, stroke=0)
#     c.setFillColor(GOLD)
#     c.rect(0, hdr_y - GOLD_H, CW, GOLD_H, fill=1, stroke=0)
#     c.setFont("Helvetica-Bold", 8.5)
#     c.setFillColor(TEXT_LIGHT)
#     c.drawCentredString(CW / 2, hdr_y + HEADER_H * 0.57, org_name.upper())
#     c.setFont("Helvetica", 5)
#     c.setFillColor(TEXT_MUTED)
#     c.drawCentredString(CW / 2, hdr_y + HEADER_H * 0.20, "VISITOR ID CARD")
 
 
# def _draw_footer(c, visitor):
#     c.setFillColor(NAVY)
#     c.rect(0, 0, CW, FOOTER_H, fill=1, stroke=0)
#     c.setFillColor(GOLD)
#     c.rect(0, FOOTER_H, CW, 0.7, fill=1, stroke=0)
 
#     checkin  = (visitor.designated_check_in.strftime("%d %b %Y  %H:%M")
#                 if visitor.designated_check_in  else "--")
#     checkout = (visitor.designated_check_out.strftime("%d %b %Y  %H:%M")
#                 if visitor.designated_check_out else "--")
 
#     row1 = FOOTER_H * 0.72
#     row2 = FOOTER_H * 0.26
 
#     c.setFont("Helvetica-Bold", 4.5)
#     c.setFillColor(TEXT_MUTED)
#     c.drawString(PAD, row1, "CHECK-IN")
#     c.drawString(PAD, row2, "CHECK-OUT")
 
#     c.setFont("Helvetica", 4.5)
#     c.setFillColor(TEXT_LIGHT)
#     c.drawString(PAD + 13 * mm, row1, checkin)
#     c.drawString(PAD + 13 * mm, row2, checkout)
 
#     ts = datetime.now().strftime("%Y-%m-%d %H:%M")
#     c.setFont("Helvetica", 3.8)
#     c.setFillColor(HexColor("#5A7FAA"))
#     c.drawRightString(CW - PAD, row2 + 1, "Generated " + ts)
 
 
# def _draw_accent_tab(c):
#     tab_h = BODY_H * 0.45
#     c.setFillColor(GOLD)
#     c.rect(0, BODY_Y + (BODY_H - tab_h) / 2, 1.5 * mm, tab_h, fill=1, stroke=0)
 
 
# def _draw_photo(c, visitor, with_photo):
#     loaded = False
#     if with_photo and getattr(visitor, "photo", None):
#         try:
#             import requests
#             resp = requests.get(str(visitor.photo), timeout=5)
#             resp.raise_for_status()
#             img  = Image.open(BytesIO(resp.content)).convert("RGB")
#             side = min(img.size)
#             img  = img.crop((
#                 (img.width  - side) // 2,
#                 (img.height - side) // 2,
#                 (img.width  + side) // 2,
#                 (img.height + side) // 2,
#             ))
#             img  = img.resize((int(PHOTO_W * 3), int(PHOTO_H * 3)), Image.LANCZOS)
#             buf2 = BytesIO()
#             img.save(buf2, format="PNG")
#             buf2.seek(0)
#             c.drawImage(ImageReader(buf2), PHOTO_X, PHOTO_Y,
#                         width=PHOTO_W, height=PHOTO_H,
#                         preserveAspectRatio=True, mask="auto")
#             loaded = True
#         except Exception:
#             pass
 
#     if not loaded:
#         c.setFillColor(PHOTO_FILL)
#         c.rect(PHOTO_X, PHOTO_Y, PHOTO_W, PHOTO_H, fill=1, stroke=0)
#         c.setStrokeColor(PHOTO_STROKE)
#         c.setLineWidth(0.5)
#         c.rect(PHOTO_X, PHOTO_Y, PHOTO_W, PHOTO_H, fill=0, stroke=1)
#         c.setFont("Helvetica", 5)
#         c.setFillColor(TEXT_MUTED)
#         c.drawCentredString(PHOTO_X + PHOTO_W / 2,
#                             PHOTO_Y + PHOTO_H / 2 - 1.5,
#                             "PHOTO")
 
 
# def _draw_info(c, visitor):
#     # Name
#     c.setFont("Helvetica-Bold", 8.5)
#     c.setFillColor(TEXT_DARK)
#     name = _truncate(c, visitor.full_name or "--", "Helvetica-Bold", 8.5, INFO_W)
#     c.drawString(INFO_X, NAME_Y, name)
 
#     # Gold underline
#     name_w = min(c.stringWidth(visitor.full_name or "", "Helvetica-Bold", 8.5), INFO_W)
#     c.setFillColor(GOLD)
#     c.rect(INFO_X, NAME_Y - 1.5, name_w, 0.9, fill=1, stroke=0)
 
#     # Four detail fields
#     fields = [
#         ("Email",   visitor.email or "--"),
#         ("Phone",   visitor.phone_number or "--"),
#         ("Company", visitor.company_name or "--"),
#         ("Purpose", (visitor.purpose_of_visit or "--")[:45]),
#     ]
 
#     fy = FIELD_START_Y
#     for label, raw_value in fields:
#         c.setFont("Helvetica-Bold", 4.2)
#         c.setFillColor(TEXT_MUTED)
#         c.drawString(INFO_X, fy + 3.8, label.upper())
 
#         value = _truncate(c, raw_value, "Helvetica", 5.2, INFO_W)
#         c.setFont("Helvetica", 5.2)
#         c.setFillColor(TEXT_DARK)
#         c.drawString(INFO_X, fy, value)
 
#         c.setStrokeColor(SEP_LINE)
#         c.setLineWidth(0.3)
#         c.line(INFO_X, fy - 1.0, INFO_X + INFO_W, fy - 1.0)
 
#         fy -= ROW_GAP
 
 
# def _draw_qr(c, qr_buffer, visitor_id):
#     qr_buffer.seek(0)
#     c.drawImage(ImageReader(qr_buffer), QR_X, QR_Y,
#                 width=QR_SIZE, height=QR_SIZE,
#                 preserveAspectRatio=True, mask="auto")
#     c.setFont("Helvetica", 3.8)
#     c.setFillColor(TEXT_MID)
#     c.drawCentredString(QR_X + QR_SIZE / 2, QR_Y - 2.5 * mm, "SCAN TO VERIFY")
#     c.setFont("Helvetica-Bold", 4)
#     c.setFillColor(TEXT_DARK)
#     c.drawCentredString(QR_X + QR_SIZE / 2, QR_Y - 4.3 * mm, str(visitor_id))
 
 
# def _draw_border(c):
#     c.setStrokeColor(NAVY)
#     c.setLineWidth(0.8)
#     c.rect(0.4, 0.4, CW - 0.8, CH - 0.8, fill=0, stroke=1)
 
 
# # ── Public API ─────────────────────────────────────────────────────────────
 
# class IDCardGenerator:
 
#     @staticmethod
#     def generate_qr_code(visitor_id, visitor_data):
#         """
#         Generate a QR code whose payload is the visitor profile URL.
#         Phones open https:// URLs directly in the browser.
#         """
#         frontend_url = getattr(
#             settings, "FRONTEND_URL",
#             "https://vmsfrontend2026.z29.web.core.windows.net",
#         )
#         url = "{0}/#/visitor/{1}".format(frontend_url, visitor_id)
#         print("QR code -> " + url)
 
#         qr = qrcode.QRCode(
#             version=1,
#             error_correction=qrcode.constants.ERROR_CORRECT_M,
#             box_size=10,
#             border=2,
#         )
#         qr.add_data(url)
#         qr.make(fit=True)
 
#         img = qr.make_image(fill_color="#0D2257", back_color="white")
#         buf = BytesIO()
#         img.save(buf, format="PNG")
#         buf.seek(0)
#         return buf
 
#     @staticmethod
#     def generate_id_card(visitor, qr_code_buffer, visitor_id=None, with_photo=True):
#         """
#         Generate a CR80-sized (85.6 x 54 mm) visitor ID card PDF.
 
#         Parameters
#         ----------
#         visitor         Django model instance with fields:
#                           full_name, email, phone_number, company_name,
#                           purpose_of_visit, designated_check_in,
#                           designated_check_out, photo (URL, optional).
#         qr_code_buffer  BytesIO returned by generate_qr_code().
#         visitor_id      String shown under the QR. Defaults to visitor.pk.
#         with_photo      Attempt to fetch and embed visitor.photo.
 
#         Returns
#         -------
#         BytesIO  — PDF buffer, ready to serve or save.
#         """
#         vid      = visitor_id if visitor_id is not None else getattr(visitor, "pk", "--")
#         org_name = getattr(settings, "ORGANISATION_NAME", "VISITOR MANAGEMENT SYSTEM")
 
#         buf = BytesIO()
#         c   = canvas.Canvas(buf, pagesize=(CW, CH))
 
#         _draw_background(c)
#         _draw_header(c, org_name)
#         _draw_footer(c, visitor)
#         _draw_accent_tab(c)
#         _draw_photo(c, visitor, with_photo)
#         _draw_info(c, visitor)
#         _draw_qr(c, qr_code_buffer, vid)
#         _draw_border(c)
 
#         c.showPage()
#         c.save()
#         buf.seek(0)
#         return buf
 
#     @staticmethod
#     def generate_simple_id_card(visitor, qr_code_buffer, visitor_id=None):
#         """Backwards-compatible wrapper — same card without photo fetch."""
#         return IDCardGenerator.generate_id_card(
#             visitor,
#             qr_code_buffer,
#             visitor_id=visitor_id,
#             with_photo=False,
#         )
 



# account/id_card_utils.py
"""
ID Card generator — CR80 plastic card format (85.6 × 54 mm, landscape).
Minimalist, clean design with subtle spacing and hierarchy.
"""

import qrcode
from io import BytesIO
from datetime import datetime
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from django.conf import settings


# ── Design tokens (subtle, minimal) ────────────────────────────────────────
NAVY        = HexColor("#0D2257")
GOLD        = HexColor("#D4A017")
BG          = HexColor("#FAFBFC")
TEXT_DARK   = HexColor("#1A2C3E")
TEXT_MID    = HexColor("#5B6E8C")
TEXT_LIGHT  = HexColor("#FFFFFF")
TEXT_MUTED  = HexColor("#8DA0BC")
PHOTO_FILL  = HexColor("#E8EDF5")
PHOTO_STROKE= HexColor("#B8C4D8")
DIVIDER     = HexColor("#E2E8F0")

# ── Card geometry (CR80, landscape) ────────────────────────────────────────
CW = 85.6 * mm
CH = 54.0 * mm

HEADER_H = 10.5 * mm
HEADER_TOP = CH - HEADER_H

GOLD_BAR_H = 1.0 * mm
GOLD_BAR_Y = HEADER_TOP - GOLD_BAR_H

FOOTER_H = 8.5 * mm
FOOTER_TOP = FOOTER_H

PAD = 3.0 * mm

BODY_H = CH - HEADER_H - GOLD_BAR_H - FOOTER_H
BODY_TOP = FOOTER_H + BODY_H

# Photo dimensions
PHOTO_W = 18 * mm
PHOTO_H = 22 * mm
PHOTO_X = PAD
PHOTO_Y = FOOTER_H + (BODY_H - PHOTO_H) / 2

# QR code dimensions
QR_SIZE = 16 * mm
QR_X = CW - PAD - QR_SIZE
QR_Y = FOOTER_H + (BODY_H - QR_SIZE) / 2

# Info column dimensions
INFO_X = PHOTO_X + PHOTO_W + 3 * mm
INFO_W = QR_X - INFO_X - 2 * mm

# Typography - subtle sizes
FONT_LABEL = 3.8
FONT_VALUE = 5.2
FONT_NAME = 8.5
FONT_SMALL = 3.5
FONT_TINY = 3.2

# Spacing (minimal, consistent)
LINE_HEIGHT = 5.5 * mm
LABEL_VALUE_GAP = 1.8 * mm
FIELD_GAP = 1.2 * mm
ROW_GAP = 6.0 * mm


# ── Internal helpers ───────────────────────────────────────────────────────

def _truncate(c, text, font, size, max_width):
    """Truncate text with ellipsis if too long."""
    if c.stringWidth(text, font, size) <= max_width:
        return text
    while len(text) > 1 and c.stringWidth(text + "...", font, size) > max_width:
        text = text[:-1]
    return text + "..."

def _draw_background(c):
    """Clean white background."""
    c.setFillColor(BG)
    c.rect(0, 0, CW, CH, fill=1, stroke=0)

def _draw_header(c, org_name):
    """Subtle header with organization name."""
    # Navy bar
    c.setFillColor(NAVY)
    c.rect(0, HEADER_TOP, CW, HEADER_H, fill=1, stroke=0)
    
    # Gold accent bar
    c.setFillColor(GOLD)
    c.rect(0, GOLD_BAR_Y, CW, GOLD_BAR_H, fill=1, stroke=0)
    
    # Organization name
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(TEXT_LIGHT)
    c.drawCentredString(CW / 2, HEADER_TOP + HEADER_H * 0.6, org_name.upper())
    
    # "VISITOR PASS" subtle secondary text
    c.setFont("Helvetica", 5)
    c.setFillColor(HexColor("#8DA0BC"))
    c.drawCentredString(CW / 2, HEADER_TOP + HEADER_H * 0.25, "VISITOR PASS")

def _draw_footer(c, visitor):
    """Minimal footer with dates."""
    c.setFillColor(NAVY)
    c.rect(0, 0, CW, FOOTER_H, fill=1, stroke=0)
    
    # Thin gold line above footer
    c.setFillColor(GOLD)
    c.rect(0, FOOTER_H, CW, 0.5, fill=1, stroke=0)
    
    # Format dates
    checkin = (visitor.designated_check_in.strftime("%d %b %Y · %H:%M")
               if visitor.designated_check_in else "—")
    checkout = (visitor.designated_check_out.strftime("%d %b %Y · %H:%M")
                if visitor.designated_check_out else "—")
    
    # Position
    y1 = FOOTER_H * 0.7
    y2 = FOOTER_H * 0.3
    
    # Labels (subtle, muted)
    c.setFont("Helvetica", FONT_TINY)
    c.setFillColor(HexColor("#8DA0BC"))
    c.drawString(PAD, y1, "CHECK-IN")
    c.drawString(PAD, y2, "CHECK-OUT")
    
    # Values (light, readable)
    c.setFont("Helvetica", 4)
    c.setFillColor(TEXT_LIGHT)
    c.drawString(PAD + 12 * mm, y1, checkin)
    c.drawString(PAD + 12 * mm, y2, checkout)
    
    # Timestamp (subtle)
    ts = datetime.now().strftime("%d %b %Y %H:%M")
    c.setFont("Helvetica", FONT_TINY)
    c.setFillColor(HexColor("#6B8BB0"))
    c.drawRightString(CW - PAD, y2, ts)

def _draw_photo(c, visitor, with_photo):
    """Simple photo placeholder or actual photo."""
    loaded = False
    
    if with_photo and getattr(visitor, "photo", None):
        try:
            import requests
            resp = requests.get(str(visitor.photo), timeout=5)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            
            # Crop to square
            side = min(img.size)
            img = img.crop((
                (img.width - side) // 2,
                (img.height - side) // 2,
                (img.width + side) // 2,
                (img.height + side) // 2,
            ))
            img = img.resize((int(PHOTO_W * 3), int(PHOTO_H * 3)), Image.LANCZOS)
            
            buf2 = BytesIO()
            img.save(buf2, format="PNG")
            buf2.seek(0)
            c.drawImage(ImageReader(buf2), PHOTO_X, PHOTO_Y,
                       width=PHOTO_W, height=PHOTO_H,
                       preserveAspectRatio=True, mask="auto")
            loaded = True
        except Exception:
            pass
    
    # Placeholder if no photo
    if not loaded:
        c.setFillColor(PHOTO_FILL)
        c.rect(PHOTO_X, PHOTO_Y, PHOTO_W, PHOTO_H, fill=1, stroke=0)
        c.setStrokeColor(PHOTO_STROKE)
        c.setLineWidth(0.4)
        c.rect(PHOTO_X, PHOTO_Y, PHOTO_W, PHOTO_H, fill=0, stroke=1)
        
        c.setFont("Helvetica", 4.5)
        c.setFillColor(TEXT_MUTED)
        c.drawCentredString(PHOTO_X + PHOTO_W / 2,
                           PHOTO_Y + PHOTO_H / 2 - 1.5,
                           "PHOTO")

def _draw_info(c, visitor):
    """Visitor information with proper spacing."""
    
    # Name (large, prominent)
    c.setFont("Helvetica-Bold", FONT_NAME)
    c.setFillColor(TEXT_DARK)
    name = _truncate(c, visitor.full_name or "—", "Helvetica-Bold", FONT_NAME, INFO_W)
    c.drawString(INFO_X, BODY_TOP - 3.5 * mm, name)
    
    # Thin gold underline below name
    name_width = min(c.stringWidth(visitor.full_name or "", "Helvetica-Bold", FONT_NAME), INFO_W)
    c.setFillColor(GOLD)
    c.rect(INFO_X, BODY_TOP - 5 * mm, name_width, 0.6, fill=1, stroke=0)
    
    # Field definitions
    fields = [
        ("EMAIL", visitor.email or "—"),
        ("PHONE", visitor.phone_number or "—"),
        ("COMPANY", visitor.company_name or "—"),
        ("PURPOSE", (visitor.purpose_of_visit or "—")[:50]),
    ]
    
    # Starting Y position after name
    start_y = BODY_TOP - 8 * mm
    
    for i, (label, value) in enumerate(fields):
        y_pos = start_y - (i * ROW_GAP)
        
        # Label (subtle, uppercase)
        c.setFont("Helvetica", FONT_LABEL)
        c.setFillColor(TEXT_MUTED)
        c.drawString(INFO_X, y_pos + 2, label)
        
        # Value (clear, readable)
        c.setFont("Helvetica", FONT_VALUE)
        c.setFillColor(TEXT_DARK)
        truncated = _truncate(c, value, "Helvetica", FONT_VALUE, INFO_W)
        c.drawString(INFO_X, y_pos - LABEL_VALUE_GAP, truncated)
        
        # Subtle divider line (except last field)
        if i < len(fields) - 1:
            c.setStrokeColor(DIVIDER)
            c.setLineWidth(0.3)
            c.line(INFO_X, y_pos - LABEL_VALUE_GAP - FIELD_GAP,
                  INFO_X + INFO_W, y_pos - LABEL_VALUE_GAP - FIELD_GAP)

def _draw_qr(c, qr_buffer, visitor_id):
    """QR code with minimal labeling."""
    qr_buffer.seek(0)
    c.drawImage(ImageReader(qr_buffer), QR_X, QR_Y,
               width=QR_SIZE, height=QR_SIZE,
               preserveAspectRatio=True, mask="auto")
    
    # Subtle label above QR
    c.setFont("Helvetica", FONT_TINY)
    c.setFillColor(TEXT_MUTED)
    c.drawCentredString(QR_X + QR_SIZE / 2, QR_Y - 2 * mm, "SCAN TO VERIFY")
    
    # Visitor ID (small, bottom)
    c.setFont("Helvetica", FONT_TINY)
    c.setFillColor(TEXT_MID)
    c.drawCentredString(QR_X + QR_SIZE / 2, QR_Y - 3.8 * mm, f"ID: {visitor_id}")

def _draw_border(c):
    """Thin, subtle outer border."""
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.5)
    c.rect(0.5, 0.5, CW - 1, CH - 1, fill=0, stroke=1)


# ── Public API ─────────────────────────────────────────────────────────────

class IDCardGenerator:
    
    @staticmethod
    def generate_qr_code(visitor_id, visitor_data=None):
        """
        Generate QR code with visitor profile URL.
        
        Args:
            visitor_id: Unique visitor identifier
            visitor_data: Unused, kept for compatibility
        
        Returns:
            BytesIO: QR code image buffer
        """
        frontend_url = getattr(
            settings, "FRONTEND_URL",
            "https://vmsfrontend2026.z29.web.core.windows.net"
        )
        url = f"{frontend_url}/#/visitor/{visitor_id}"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=9,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Navy QR code (matches brand)
        img = qr.make_image(fill_color="#0D2257", back_color="#FAFBFC")
        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf
    
    @staticmethod
    def generate_id_card(visitor, qr_code_buffer, visitor_id=None, with_photo=True):
        """
        Generate CR80-sized visitor ID card PDF (85.6 × 54 mm).
        
        Args:
            visitor: Django model instance with visitor data
            qr_code_buffer: BytesIO from generate_qr_code()
            visitor_id: Override visitor ID (defaults to visitor.pk)
            with_photo: Whether to include photo
        
        Returns:
            BytesIO: PDF buffer
        """
        vid = visitor_id if visitor_id is not None else getattr(visitor, "pk", "—")
        org_name = getattr(settings, "ORGANISATION_NAME", "VISITOR MANAGEMENT")
        
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=(CW, CH))
        
        # Build card layers
        _draw_background(c)
        _draw_header(c, org_name)
        _draw_footer(c, visitor)
        _draw_photo(c, visitor, with_photo)
        _draw_info(c, visitor)
        _draw_qr(c, qr_code_buffer, vid)
        _draw_border(c)
        
        c.showPage()
        c.save()
        buf.seek(0)
        return buf
    
    @staticmethod
    def generate_simple_id_card(visitor, qr_code_buffer, visitor_id=None):
        """
        Generate ID card without photo (fallback for compatibility).
        """
        return IDCardGenerator.generate_id_card(
            visitor,
            qr_code_buffer,
            visitor_id=visitor_id,
            with_photo=False,
        )
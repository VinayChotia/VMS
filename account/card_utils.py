# account/id_card_utils.py
import qrcode
import base64
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import os
from django.conf import settings

class IDCardGenerator:
    
    # @staticmethod
    # def generate_qr_code(visitor_id, visitor_data):
    #     """
    #     Generate QR code containing visitor information
    #     """
    #     # Create QR code data
    #     qr_data = {
    #         'visitor_id': visitor_id,
    #         'full_name': visitor_data.get('full_name'),
    #         'email': visitor_data.get('email'),
    #         'phone': visitor_data.get('phone_number'),
    #         'company': visitor_data.get('company_name', ''),
    #         'check_in': str(visitor_data.get('designated_check_in')),
    #         'check_out': str(visitor_data.get('designated_check_out')),
    #         'site': visitor_data.get('site', {}).get('name') if visitor_data.get('site') else None,
    #         'sections': [s.get('name') for s in visitor_data.get('accessible_sections', [])]
    #     }
        
    #     # Convert to string
    #     qr_text = str(qr_data)
        
    #     # Generate QR code
    #     qr = qrcode.QRCode(
    #         version=1,
    #         error_correction=qrcode.constants.ERROR_CORRECT_L,
    #         box_size=10,
    #         border=4,
    #     )
    #     qr.add_data(qr_text)
    #     qr.make(fit=True)
        
    #     # Create QR code image
    #     qr_image = qr.make_image(fill_color="black", back_color="white")
        
    #     # Save to bytes
    #     buffer = BytesIO()
    #     qr_image.save(buffer, format='PNG')
    #     buffer.seek(0)
        
    #     return buffer
    
    @staticmethod
    def generate_qr_code(visitor_id, visitor_data):
        """
        Generate QR code containing visitor information
        visitor_data should be a DICTIONARY
        """
        # Ensure visitor_data is a dictionary
        if not isinstance(visitor_data, dict):
            raise ValueError(f"visitor_data must be a dictionary, got {type(visitor_data)}")
        
        # Create QR code data as a JSON string
        import json
        qr_text = json.dumps(visitor_data, default=str)
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_text)
        qr.make(fit=True)
        
        # Create QR code image
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Save to bytes
        buffer = BytesIO()
        qr_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer

    @staticmethod
    def generate_id_card(visitor, qr_code_buffer, with_photo=False):
        """
        Generate ID card PDF for visitor
        """
        buffer = BytesIO()
        
        # Create PDF canvas (landscape mode for ID card)
        c = canvas.Canvas(buffer, pagesize=landscape(letter))
        width, height = landscape(letter)
        
        # Card dimensions (standard ID card size)
        card_width = width * 0.8
        card_height = height * 0.6
        card_x = (width - card_width) / 2
        card_y = (height - card_height) / 2
        
        # Draw card background
        c.setFillColorRGB(0.95, 0.95, 0.95)
        c.rect(card_x, card_y, card_width, card_height, fill=1, stroke=0)
        
        # Draw border
        c.setStrokeColorRGB(0.2, 0.4, 0.8)
        c.setLineWidth(3)
        c.rect(card_x, card_y, card_width, card_height, fill=0, stroke=1)
        
        # Header background
        c.setFillColorRGB(0.2, 0.4, 0.8)
        c.rect(card_x, card_y + card_height - 50, card_width, 50, fill=1, stroke=0)
        
        # Title
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(card_x + card_width/2 - 50, card_y + card_height - 35, "VISITOR ID CARD")
        
        # Visitor Photo (if available)
        photo_x = card_x + 20
        photo_y = card_y + card_height - 220
        photo_size = 100
        
        if with_photo and visitor.photo:
            try:
                # Download or get photo from URL
                import requests
                response = requests.get(visitor.photo)
                photo_image = Image.open(BytesIO(response.content))
                photo_image = photo_image.resize((photo_size, photo_size))
                photo_buffer = BytesIO()
                photo_image.save(photo_buffer, format='PNG')
                photo_buffer.seek(0)
                
                photo_reader = ImageReader(photo_buffer)
                c.drawImage(photo_reader, photo_x, photo_y, width=photo_size, height=photo_size)
            except Exception as e:
                # Draw placeholder if photo fails
                c.setFillColorRGB(0.8, 0.8, 0.8)
                c.rect(photo_x, photo_y, photo_size, photo_size, fill=1, stroke=0)
                c.setFillColorRGB(0, 0, 0)
                c.setFont("Helvetica", 10)
                c.drawString(photo_x + 35, photo_y + 50, "No Photo")
        else:
            # Draw placeholder
            c.setFillColorRGB(0.8, 0.8, 0.8)
            c.rect(photo_x, photo_y, photo_size, photo_size, fill=1, stroke=0)
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica", 10)
            c.drawString(photo_x + 35, photo_y + 50, "No Photo")
        
        # Visitor Information
        info_x = photo_x + photo_size + 20
        info_y = photo_y + photo_size - 20
        
        c.setFont("Helvetica-Bold", 12)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(info_x, info_y, "Visitor Information")
        
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        
        y_offset = info_y - 20
        info_items = [
            (f"Name: {visitor.full_name}"),
            (f"Email: {visitor.email}"),
            (f"Phone: {visitor.phone_number}"),
            (f"Company: {visitor.company_name or 'N/A'}"),
            (f"Purpose: {visitor.purpose_of_visit[:50] if visitor.purpose_of_visit else 'N/A'}"),
        ]
        
        for item in info_items:
            c.drawString(info_x, y_offset, item)
            y_offset -= 15
        
        # QR Code
        qr_x = card_x + card_width - 130
        qr_y = card_y + 20
        qr_size = 100
        
        qr_reader = ImageReader(qr_code_buffer)
        c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)
        
        # Check-in/out dates
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        checkin_str = f"Check-in: {visitor.designated_check_in.strftime('%Y-%m-%d %H:%M') if visitor.designated_check_in else 'N/A'}"
        checkout_str = f"Check-out: {visitor.designated_check_out.strftime('%Y-%m-%d %H:%M') if visitor.designated_check_out else 'N/A'}"
        c.drawString(card_x + 20, card_y + 15, checkin_str)
        c.drawString(card_x + 20, card_y + 5, checkout_str)
        
        # Footer
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        footer_text = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        c.drawString(card_x + card_width - 150, card_y + 5, footer_text)
        
        c.save()
        buffer.seek(0)
        
        return buffer

    @staticmethod
    def generate_simple_id_card(visitor, qr_code_buffer):
        """
        Generate simple ID card without photo (fallback)
        """
        buffer = BytesIO()
        
        c = canvas.Canvas(buffer, pagesize=landscape(letter))
        width, height = landscape(letter)
        
        card_width = width * 0.7
        card_height = height * 0.5
        card_x = (width - card_width) / 2
        card_y = (height - card_height) / 2
        
        # Card background
        c.setFillColorRGB(0.98, 0.98, 0.98)
        c.rect(card_x, card_y, card_width, card_height, fill=1, stroke=0)
        
        # Border
        c.setStrokeColorRGB(0.2, 0.4, 0.8)
        c.setLineWidth(2)
        c.rect(card_x, card_y, card_width, card_height, fill=0, stroke=1)
        
        # Header
        c.setFillColorRGB(0.2, 0.4, 0.8)
        c.rect(card_x, card_y + card_height - 40, card_width, 40, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(card_x + card_width/2 - 45, card_y + card_height - 28, "VISITOR PASS")
        
        # Visitor name (large)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(card_x + 20, card_y + card_height - 80, visitor.full_name)
        
        # Other info
        c.setFont("Helvetica", 10)
        info_y = card_y + card_height - 110
        info_items = [
            f"Company: {visitor.company_name or 'N/A'}",
            f"Purpose: {visitor.purpose_of_visit[:40] if visitor.purpose_of_visit else 'N/A'}",
            f"Check-in: {visitor.designated_check_in.strftime('%Y-%m-%d %H:%M') if visitor.designated_check_in else 'N/A'}",
        ]
        
        for item in info_items:
            c.drawString(card_x + 20, info_y, item)
            info_y -= 15
        
        # QR Code
        qr_size = 80
        qr_reader = ImageReader(qr_code_buffer)
        c.drawImage(qr_reader, card_x + card_width - qr_size - 20, card_y + 20, width=qr_size, height=qr_size)
        
        c.save()
        buffer.seek(0)
        
        return buffer
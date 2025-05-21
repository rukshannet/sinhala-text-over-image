from PIL import Image, ImageDraw, ImageFont
import os

# --- Constants for QR Code ---
QR_CODE_TARGET_HEIGHT_RATIO = 0.24  # e.g., 24% of main image height
QR_CODE_MARGIN = 20  # pixels from edge

def add_qr_code_to_image(image, main_image_height, qr_code_file_path=None):
    """Loads, resizes, and pastes the QR code onto the main image."""
    if not qr_code_file_path or not os.path.exists(qr_code_file_path):
        if qr_code_file_path: # Only print if a path was given but not found
            print(f"⚠️ QR code file '{qr_code_file_path}' not found. Skipping QR overlay.")
        else:
            # This case is normal if user doesn't select a QR code
            pass # print("ℹ️ No QR code selected. Skipping QR overlay.")
        return

    img_width, img_height = image.size # main image dimensions
    try:
        qr_image_original = Image.open(qr_code_file_path).convert("RGBA") # Ensure RGBA for transparency
        qr_original_width, qr_original_height = qr_image_original.size

        if qr_original_height == 0:
            print(f"⚠️ QR code image '{os.path.basename(qr_code_file_path)}' has zero height. Skipping QR overlay.")
            return

        qr_target_h = int(main_image_height * QR_CODE_TARGET_HEIGHT_RATIO)
        if qr_target_h <= 0:
            print(f"⚠️ Main image height or QR ratio too small for QR code. Skipping QR overlay.")
            return

        qr_aspect_ratio = qr_original_width / qr_original_height
        qr_target_w = int(qr_target_h * qr_aspect_ratio)

        if qr_target_w <= 0:
            print(f"⚠️ Calculated QR code target width is not positive ({qr_target_w}). Skipping QR overlay.")
            return

        qr_image_resized = qr_image_original.resize((qr_target_w, qr_target_h))

        qr_pos_x = QR_CODE_MARGIN
        qr_pos_y = img_height - qr_image_resized.height - QR_CODE_MARGIN

        # Ensure QR is within bounds if image is very small or margins large
        if qr_pos_x < 0: qr_pos_x = 0
        if qr_pos_y < 0: qr_pos_y = 0
        
        image.paste(qr_image_resized, (qr_pos_x, qr_pos_y), qr_image_resized)
        print(f"ℹ️ QR code '{os.path.basename(qr_code_file_path)}' added to image.")

    except Exception as e:
        print(f"⚠️ An error occurred while processing QR code '{os.path.basename(qr_code_file_path)}': {e}. Skipping QR overlay.")

def generate_overlayed_image(base_pil_image, text_to_draw, ttf_path, font_size_px, text_y_offset_percent=50.0, font_color="white", qr_code_file_path=None):
    """
    Draws text and optionally a QR code on a copy of the base_pil_image.
    Returns a new PIL Image object.
    """
    image_with_overlay = base_pil_image.copy().convert("RGBA") # Work on a copy
    draw = ImageDraw.Draw(image_with_overlay)
    width, height = image_with_overlay.size

    try:
        font = ImageFont.truetype(ttf_path, font_size_px)
    except IOError:
        print(f"❌ Error: Font file '{ttf_path}' not found or cannot be read for size {font_size_px}.")
        add_qr_code_to_image(image_with_overlay, height, qr_code_file_path) # Still attempt to add QR
        return image_with_overlay

    text_bbox = draw.textbbox((0, 0), text_to_draw, font=font)
    text_actual_width = text_bbox[2] - text_bbox[0]
    text_actual_height = text_bbox[3] - text_bbox[1]
    x = (width - text_actual_width) / 2 - text_bbox[0]
    y_top_target = height * (text_y_offset_percent / 100.0)
    y = y_top_target - text_bbox[1]
    outline_strength = max(1, int(font_size_px / 25))
    for dx_outline in range(-outline_strength, outline_strength + 1):
        for dy_outline in range(-outline_strength, outline_strength + 1):
            if dx_outline == 0 and dy_outline == 0:
                continue
            draw.text((x + dx_outline, y + dy_outline), text_to_draw, font=font, fill="black")
    draw.text((x, y), text_to_draw, font=font, fill=font_color)
    add_qr_code_to_image(image_with_overlay, height, qr_code_file_path)
    return image_with_overlay
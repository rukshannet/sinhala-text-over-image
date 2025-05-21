from PIL import Image, ImageDraw, ImageFont
import sys
import os
import requests
import tkinter as tk
from tkinter import Scale, filedialog # Explicit import for Scale and filedialog
from PIL import ImageTk

# --- Constants for QR Code ---
# These remain global as they are specific to the QR feature
QR_CODE_FILENAME = "qr_code.png"
QR_CODE_TARGET_HEIGHT_RATIO = 0.30  # e.g., 24% of main image height (2x previous 0.12)
QR_CODE_MARGIN = 20  # pixels from edge

def overlay_sinhala_text(image_path, text, ttf_path, output_path):
    # Load image
    try:
        # This function will now be primarily for the CLI workflow,
        # handling initial image loading from path and auto font-sizing.
        # The core drawing logic will be in generate_overlayed_image.

        image = Image.open(image_path).convert("RGBA")
    except FileNotFoundError:
        print(f"❌ Error: Main image file not found at '{image_path}'.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: Could not open main image '{image_path}': {e}")
        sys.exit(1)

    width, height = image.size

    # Create drawing context
    # Temporarily draw on a copy for size calculation to avoid modifying original 'image' if not needed
    # Or, better, just use the font object directly for textlength.
    # The original 'image' object will be passed to generate_overlayed_image later.
    # For auto-sizing, we need a Draw object to get textlength with a specific font.
    temp_draw_for_sizing = ImageDraw.Draw(Image.new("RGBA", (1,1))) # Dummy for font metrics

    # Estimate target width for text: 50% of image width
    target_text_width = width * 0.5
    current_font_size = 10 # Start with a small font size
    try:
        font_for_sizing = ImageFont.truetype(ttf_path, current_font_size)
    except IOError:
        print(f"❌ Error: Font file not found or cannot be read at '{ttf_path}'.")
        sys.exit(1)

    # Increase font size until text reaches target width
    max_font_size = int(height * 0.8) # Max font size as 80% of image height
    while temp_draw_for_sizing.textlength(text, font=font_for_sizing) < target_text_width and current_font_size < max_font_size:
        current_font_size += 2
        font_for_sizing = ImageFont.truetype(ttf_path, current_font_size)

    final_image = generate_overlayed_image(image, text, ttf_path, current_font_size, add_qr=True)

    # Save
    try:
        final_image.save(output_path)
        print(f"✅ Output saved to {output_path}")
    except Exception as e:
        print(f"❌ Error: Failed to save output image to '{output_path}': {e}")
        sys.exit(1)

def add_qr_code_to_image(image, main_image_height):
    """Loads, resizes, and pastes the QR code onto the main image."""
    img_width, img_height = image.size # main image dimensions
    try:
        qr_image_original = Image.open(QR_CODE_FILENAME).convert("RGBA") # Ensure RGBA for transparency
        qr_original_width, qr_original_height = qr_image_original.size

        if qr_original_height == 0:
            print(f"⚠️ QR code image '{QR_CODE_FILENAME}' has zero height. Skipping QR overlay.")
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
        print(f"ℹ️ QR code '{QR_CODE_FILENAME}' added to image.")

    except FileNotFoundError:
        print(f"⚠️ QR code file '{QR_CODE_FILENAME}' not found. Skipping QR overlay.")
    except Exception as e:
        print(f"⚠️ An error occurred while processing QR code '{QR_CODE_FILENAME}': {e}. Skipping QR overlay.")

def generate_overlayed_image(base_pil_image, text_to_draw, ttf_path, font_size_px, text_y_offset_percent=50.0, add_qr=True):
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
        # Return the image without text if font fails, allowing QR to still be added if enabled
        if add_qr:
            add_qr_code_to_image(image_with_overlay, height)
        return image_with_overlay

    # Calculate text dimensions and position for centering using textbbox
    # textbbox(xy, text, font) returns (left, top, right, bottom) for text anchored at xy
    text_bbox = draw.textbbox((0, 0), text_to_draw, font=font)
    text_actual_width = text_bbox[2] - text_bbox[0]
    text_actual_height = text_bbox[3] - text_bbox[1]

    # Calculate coordinates for text
    # Horizontal centering
    x = (width - text_actual_width) / 2 - text_bbox[0]
    # Vertical position based on offset_percent (top of text bounding box)
    y_top_target = height * (text_y_offset_percent / 100.0)
    y = y_top_target - text_bbox[1] # Adjust by the text_bbox's own top offset relative to (0,0) anchor

    # Improved black outline for better visibility (8-directional)
    outline_strength = max(1, int(font_size_px / 25)) # Outline thickness relative to font size
    for dx_outline in range(-outline_strength, outline_strength + 1):
        for dy_outline in range(-outline_strength, outline_strength + 1):
            if dx_outline == 0 and dy_outline == 0:
                continue # Skip the center (it's for the main text)
            draw.text((x + dx_outline, y + dy_outline), text_to_draw, font=font, fill="black")

    # White main text
    draw.text((x, y), text_to_draw, font=font, fill="white")

    if add_qr:
        add_qr_code_to_image(image_with_overlay, height)

    return image_with_overlay

def convert_unicode_to_legacy(text, output_format="font"):  # options: unicode, font, isi
    url = 'https://singlish.kdj.lk/api.php'
    payload = {
        'text': text,
        'inputType': 'unicode',   # input is Sinhala Unicode
        'format': output_format   # output is legacy font string
    }
    try:
        response = requests.post(url, json=payload, timeout=10) # Added timeout
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        result = response.json()
        if result.get('status') == 'success':
            return result['result']
        else:
            error_message = result.get('message', 'Unknown conversion API error')
            print(f"❌ Sinhala text conversion API error: {error_message}")
            raise Exception(f"Conversion failed: {error_message}")
    except requests.exceptions.Timeout:
        raise Exception("Sinhala text conversion API request timed out.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Sinhala text conversion API request failed: {e}")

class LiveViewApp:
    def __init__(self, master, initial_image_path, initial_ttf_path):
        self.master = master
        master.title("Font Size Live Preview")

        self.image_path = initial_image_path
        self.ttf_path = initial_ttf_path
        self.legacy_text = ""
        self.base_pil_image = None
        self.current_tk_image = None # To prevent garbage collection

        # --- Constants for GUI Preview ---
        self.MAX_PREVIEW_WIDTH = 800  # Max width for the image preview in pixels
        self.MAX_PREVIEW_HEIGHT = 600 # Max height for the image preview in pixels

        # --- Load initial data ---
        if not os.path.exists(self.image_path):
            print(f"❌ Error: Initial image file not found: {self.image_path}")
            # Consider using tkinter.messagebox.showerror for GUI errors
            master.destroy()
            return
        if not os.path.exists(self.ttf_path):
            print(f"❌ Error: Initial font file not found: {self.ttf_path}")
            master.destroy()
            return

        try:
            # self.legacy_text will be set during update_display after fetching from Entry widget
            self.base_pil_image = Image.open(self.image_path).convert("RGBA")
        except Exception as e:
            print(f"❌ Error loading initial image: {e}")
            master.destroy()
            return

        img_width, img_height = self.base_pil_image.size
        slider_min_font_size = 10
        slider_max_font_size = int(img_height * 0.8) # Max font size up to 80% of image height
        initial_font_size = 100 # Default font size set to 100

        self.font_size_var = tk.IntVar(value=initial_font_size)

        # Variable for text vertical offset (percentage)
        self.text_y_offset_var = tk.DoubleVar(value=20.0) # Default to 20% from the top
 

        # --- GUI Elements ---
        # Text input Label and Entry widget
        self.text_label = tk.Label(master, text="Sinhala Text:")
        self.text_label.pack(pady=(10, 0)) # Padding: 10px top, 0px bottom

        # Replace tk.Entry with tk.Text for multi-line input
        self.text_input_widget = tk.Text(master, height=4, width=50, font=('Arial', 10), wrap=tk.WORD)
        self.text_input_widget.insert(tk.END, "සිංහල පෙළ\nමෙහි යොදන්න") # Default placeholder text with a newline example
        self.text_input_widget.pack(fill=tk.X, padx=20, pady=(5, 10)) # Padding: 5px top, 10px bottom

        # Font size slider
        self.font_slider = Scale(master, from_=slider_min_font_size, to=slider_max_font_size,
                                 orient=tk.HORIZONTAL, label="Font Size (px)",
                                 variable=self.font_size_var,
                                 length=max(300, int(img_width * 0.8))) # Make slider reasonably wide
                                 # Removed command=self.on_font_size_change
        
        # Slider for Text Vertical Position
        self.text_y_offset_slider = Scale(master, from_=0.0, to=100.0, resolution=0.5,
                                          orient=tk.HORIZONTAL, label="Text Vertical Start (%)",
                                          variable=self.text_y_offset_var,
                                          length=max(300, int(img_width * 0.8)))
        self.text_y_offset_slider.pack(fill=tk.X, padx=20, pady=(5,5))
        self.font_slider.pack(fill=tk.X, padx=20, pady=(10, 5)) # Add some padding top and bottom

        # --- Action Buttons ---
        # Frame for buttons to sit side-by-side if desired, or just pack them sequentially
        button_frame = tk.Frame(master)
        button_frame.pack(pady=(5,10))

        self.apply_button = tk.Button(button_frame, text="Apply Settings to Preview", command=self.update_display)
        self.apply_button.pack(side=tk.LEFT, padx=(0,5)) # Pack to the left, add some right padding

        # Then pack the image label below the slider
        self.image_label = tk.Label(master)
        self.image_label.pack(pady=(0, 10), padx=10) # Adjusted padding

        self.update_display() # Initial display

        self.download_button = tk.Button(button_frame, text="Download Image", command=self.download_image)
        self.download_button.pack(side=tk.LEFT, padx=(5,0)) # Pack to the left, add some left padding

    def on_font_size_change(self, _=None): # Slider passes value, but we get it from var
        # This method is not actively used for live updates since the "Apply" button was added.
        # If you want the slider to show its current value somewhere, this could be used.
        # For now, we rely on the "Apply Font Size" button to trigger update_display.
        pass

    def update_display(self):
        if not self.base_pil_image or not self.ttf_path:
            print("⚠️ Update display called before base image or font path is ready.")
            return

        # Get text from tk.Text widget
        current_unicode_text = self.text_input_widget.get("1.0", tk.END).strip() # "1.0" to start, tk.END to end, strip trailing newlines
        if not current_unicode_text.strip():
            print("ℹ️ Text input is empty. Displaying image without text overlay (QR code might still be added).")
            current_text_y_offset = self.text_y_offset_var.get()
            processed_pil_image = generate_overlayed_image(self.base_pil_image, "", self.ttf_path, 1, text_y_offset_percent=current_text_y_offset, add_qr=True)
        else:
            try:
                self.legacy_text = convert_unicode_to_legacy(current_unicode_text)
            except Exception as e:
                print(f"❌ Error converting Sinhala text: {e}. Please check your input or API connection.")
                current_text_y_offset = self.text_y_offset_var.get()
                processed_pil_image = generate_overlayed_image(self.base_pil_image, "", self.ttf_path, 1, text_y_offset_percent=current_text_y_offset, add_qr=True)
                # Fallthrough to display this processed_pil_image
            else: # if conversion was successful
                current_font_size = self.font_size_var.get()
                current_text_y_offset = self.text_y_offset_var.get()
                if current_font_size <= 0:
                    return # Should not happen if slider min is > 0
                processed_pil_image = generate_overlayed_image(self.base_pil_image, self.legacy_text, self.ttf_path, current_font_size, text_y_offset_percent=current_text_y_offset, add_qr=True)

        # --- Scale image for display if it's larger than max preview dimensions ---
        display_image = processed_pil_image.copy()
        # Image.Resampling.LANCZOS is a good quality downscaling filter
        # thumbnail resizes in place and maintains aspect ratio
        display_image.thumbnail((self.MAX_PREVIEW_WIDTH, self.MAX_PREVIEW_HEIGHT), Image.Resampling.LANCZOS)

        self.current_tk_image = ImageTk.PhotoImage(display_image)
        self.image_label.config(image=self.current_tk_image)
        # self.image_label.image = self.current_tk_image # Redundant, config does this. Keeping reference is via self.current_tk_image

    def download_image(self):
        """Generates the full-resolution image with current settings and prompts user to save it."""
        if not self.base_pil_image or not self.ttf_path:
            print("⚠️ Cannot download: Base image or font path not ready.")
            # Optionally show a tkinter.messagebox.showerror
            return

        current_unicode_text = self.text_input_widget.get("1.0", tk.END).strip()
        final_legacy_text = ""

        if current_unicode_text.strip():
            try:
                final_legacy_text = convert_unicode_to_legacy(current_unicode_text)
            except Exception as e:
                print(f"❌ Error converting text for download: {e}. Image will be generated without text.")
                # Optionally show a tkinter.messagebox.showwarning
                # Proceed to generate image without text or with an error message on image

        current_font_size = self.font_size_var.get()
        current_text_y_offset = self.text_y_offset_var.get()

        # Generate the full-resolution image using the original self.base_pil_image
        # Do not use the scaled-down preview image for download.
        image_to_download = generate_overlayed_image(
            self.base_pil_image,
            final_legacy_text,
            self.ttf_path,
            current_font_size,
            text_y_offset_percent=current_text_y_offset,
            add_qr=True
        )

        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            title="Save Image As"
        )
        if file_path: # If the user selected a path (didn't cancel)
            try:
                image_to_download.save(file_path)
                print(f"✅ Image saved to {file_path}")
            except Exception as e:
                print(f"❌ Error saving image: {e}")
                # Optionally show a tkinter.messagebox.showerror

if __name__ == "__main__":
    if "--gui" in sys.argv:
        gui_arg_index = sys.argv.index("--gui")
        args = sys.argv[gui_arg_index+1:] # Get arguments after --gui
        if len(args) != 2: # Expected: image_path, ttf_path
            print("GUI Usage: python app.py --gui <image_path> <ttf_path>")
            sys.exit(1)
        
        root = tk.Tk()
        app = LiveViewApp(root, initial_image_path=args[0], initial_ttf_path=args[1])
        root.mainloop()
    elif len(sys.argv) == 5: # CLI mode: image_path, text, ttf_path, output_path
        image_path_cli, text_cli, ttf_path_cli, output_path_cli = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
        if not os.path.exists(image_path_cli) or not os.path.exists(ttf_path_cli):
            print("❌ Invalid image or font path for CLI.")
            sys.exit(1)
        try:
            legacy_text_cli = convert_unicode_to_legacy(text_cli)
            if legacy_text_cli:
                overlay_sinhala_text(image_path_cli, legacy_text_cli, ttf_path_cli, output_path_cli)
        except Exception as e:
            print(f"❌ An error occurred during CLI processing: {e}")
            sys.exit(1)
    else:
        print("Invalid arguments. Choose a mode:")
        print("  CLI Usage: python app.py <image_path> <sinhala_text> <ttf_path> <output_path>")
        print("  GUI Usage: python app.py --gui <image_path> <ttf_path>")
        sys.exit(1)

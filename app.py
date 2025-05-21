from PIL import Image, ImageDraw, ImageFont
import sys
import os
import requests
import tkinter as tk
from tkinter import Scale, filedialog, ttk, font as tkfont # Explicit import for Scale, filedialog, ttk, and tkfont
from PIL import ImageTk

# --- Constants for QR Code ---
# These remain global as they are specific to the QR feature
QR_CODE_FILENAME = "qr_code.png"
QR_CODE_TARGET_HEIGHT_RATIO = 0.30  # e.g., 24% of main image height (2x previous 0.12)
QR_CODE_MARGIN = 20  # pixels from edge

# --- Constants for Fonts ---
FONTS_FOLDER = "fonts" # Folder relative to the script where TTF files are stored
SAMPLE_PREVIEW_TEXT = "úys¿ kï b;sx weïv ;uhs''" # Sample text for font preview

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

def find_ttf_fonts(folder_path):
    """Scans a folder for .ttf files and returns a list of their full paths."""
    font_files = []
    if os.path.isdir(folder_path):
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(".ttf"):
                font_files.append(os.path.join(folder_path, filename))
    return font_files

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
    def __init__(self, master):
        self.master = master
        master.title("Font Size Live Preview")

        self.image_path = None # Will be set when user selects an image
        self.base_pil_image = None
        self.current_tk_image = None # To prevent garbage collection

        # --- Constants for GUI Preview ---
        self.MAX_PREVIEW_WIDTH = 800  # Max width for the image preview in pixels
        self.MAX_PREVIEW_HEIGHT = 600 # Max height for the image preview in pixels

        # --- Load initial data ---
        # --- Scan for fonts ---
        self.available_fonts = find_ttf_fonts(FONTS_FOLDER)
        if not self.available_fonts:
            print(f"❌ Error: No .ttf fonts found in '{FONTS_FOLDER}'. Please place font files in this folder.")
            master.destroy()
            return
        
        # Store the full path of the initially selected font (first one found)
        self.selected_font_path = self.available_fonts[0]

        # Initialize slider variables with default values
        initial_font_size = 100 # Default font size set to 100
        self.font_size_var = tk.IntVar(value=initial_font_size)
        self.text_y_offset_var = tk.DoubleVar(value=20.0) # Default to 20% from the top

        # --- GUI Elements ---
        # Frame for Font Selection and Preview
        font_selection_frame = tk.Frame(master)
        font_selection_frame.pack(fill=tk.X, padx=20, pady=(10,0))

        # Font Selection
        self.font_label = tk.Label(font_selection_frame, text="Select Font:")
        self.font_label.pack(side=tk.LEFT, pady=(0,0)) # Pack to the left within the frame
        font_filenames = [os.path.basename(f) for f in self.available_fonts]
        self.font_combobox = ttk.Combobox(font_selection_frame, values=font_filenames, state="readonly", width=30)
        self.font_combobox.set(font_filenames[0]) # Set default selected font
        self.font_combobox.pack(side=tk.LEFT, padx=(5,10), pady=(0,0))
        self.font_combobox.bind("<<ComboboxSelected>>", self.update_font_preview)

        # Font Preview Label
        self.font_preview_label = tk.Label(font_selection_frame, text=SAMPLE_PREVIEW_TEXT, font=("Arial", 16)) # Initial placeholder
        self.font_preview_label.pack(side=tk.LEFT, pady=(0,0))
 

        # --- GUI Elements ---
        # Text input Label and Entry widget
        self.text_label = tk.Label(master, text="Sinhala Text:")
        self.text_label.pack(pady=(10, 0)) # Padding: 10px top, 0px bottom

        # Replace tk.Entry with tk.Text for multi-line input
        self.text_input_widget = tk.Text(master, height=4, width=50, font=('Arial', 10), wrap=tk.WORD)
        self.text_input_widget.insert(tk.END, "සිංහල පෙළ\nමෙහි යොදන්න") # Default placeholder text with a newline example
        self.text_input_widget.pack(fill=tk.X, padx=20, pady=(5, 10)) # Padding: 5px top, 10px bottom
        # Initially disable text input and sliders until image is loaded
        self.text_input_widget.config(state=tk.DISABLED)
        self.font_combobox.config(state=tk.DISABLED)


        # Font size slider
        self.font_slider = Scale(master, orient=tk.HORIZONTAL, label="Font Size (px)",
                                 variable=self.font_size_var,
                                 # from_, to_, length will be set after image is loaded
                                 )

        # Slider for Text Vertical Position
        self.text_y_offset_slider = Scale(master, orient=tk.HORIZONTAL, label="Text Vertical Start (%)",
                                          variable=self.text_y_offset_var, # Use the variable initialized earlier
                                          # from_, to_, length, resolution will be set after image is loaded
                                          )
        # Initially disable sliders
        self.font_slider.config(state=tk.DISABLED)
        self.text_y_offset_slider.pack(fill=tk.X, padx=20, pady=(5,5))
        self.font_slider.pack(fill=tk.X, padx=20, pady=(10, 5)) # Add some padding top and bottom

        # --- Action Buttons ---
        # Frame for buttons to sit side-by-side if desired, or just pack them sequentially
        button_frame = tk.Frame(master)
        button_frame.pack(pady=(5,10))

        self.apply_button = tk.Button(button_frame, text="Apply Settings to Preview", command=self.update_display)
        self.apply_button.pack(side=tk.LEFT, padx=(0,5))
        # Initially disable apply/download buttons
        self.apply_button.config(state=tk.DISABLED)

        # Then pack the image label below the slider
        self.image_label = tk.Label(master)
        self.image_label.pack(pady=(0, 10), padx=10) # Adjusted padding

        # Add Find Image button
        self.find_image_button = tk.Button(button_frame, text="Find Image", command=self.find_image)
        self.find_image_button.pack(side=tk.LEFT, padx=5)

        # self.update_display() # Don't update display until image is loaded

        self.download_button = tk.Button(button_frame, text="Download Image", command=self.download_image)
        self.download_button.pack(side=tk.LEFT, padx=(5,0)) # Pack to the left, add some left padding

    def on_font_size_change(self, _=None): # Slider passes value, but we get it from var
        # This method is not actively used for live updates since the "Apply" button was added.
        # If you want the slider to show its current value somewhere, this could be used.
        # For now, we rely on the "Apply Font Size" button to trigger update_display.
        pass

    _font_preview_photo_image = None # Class attribute to prevent garbage collection
    def update_font_preview(self, event=None):
        """Updates the font preview label when a new font is selected."""
        selected_font_filename = self.font_combobox.get() # Retrieve the selected filename
        new_selected_font_path = next((f for f in self.available_fonts if os.path.basename(f) == selected_font_filename), None)

        if new_selected_font_path:
            self.selected_font_path = new_selected_font_path # Update the main selected font path
            try:
                # --- Image-based preview ---
                sample_text = "úys¿ kï b;sx weïv ;uhs''"
                font_size = 20 # Adjust size as needed for preview (pixels)
                pil_font = ImageFont.truetype(self.selected_font_path, font_size)

                # Determine text size to create an appropriately sized image
                # Use a dummy draw object to get textbbox
                dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1,1)))
                text_bbox = dummy_draw.textbbox((0,0), sample_text, font=pil_font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]

                # Create a small transparent image for the text
                preview_pil_image = Image.new("RGBA", (text_width + 10, text_height + 10), (0,0,0,0)) # Add some padding
                draw_preview = ImageDraw.Draw(preview_pil_image)
                draw_preview.text((5, 5 - text_bbox[1]), sample_text, font=pil_font, fill="black") # Adjust y by text_bbox[1]

                # Convert to Tkinter PhotoImage and update label
                LiveViewApp._font_preview_photo_image = ImageTk.PhotoImage(preview_pil_image) # Store to prevent GC
                self.font_preview_label.config(image=LiveViewApp._font_preview_photo_image, text="") # Display image, clear text
            except tk.TclError as e:
                print(f"⚠️ TclError setting font preview: {e}. Falling back to system font.")
                self.font_preview_label.config(image=None, text="Preview N/A") # Clear image, show text
            except Exception as e: # Catch other potential errors during image preview generation
                print(f"⚠️ Error generating font preview image: {e}.")
                self.font_preview_label.config(image=None, text="Preview N/A") # Clear image, show text

    def find_image(self):
        """Opens a file dialog to select the base image."""
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")],
            title="Select Base Image"
        )
        if file_path: # If the user selected a file (didn't cancel)
            try:
                self.base_pil_image = Image.open(file_path).convert("RGBA")
                self.image_path = file_path # Store the path if needed later (e.g., for reference)

                # --- Configure sliders based on the newly loaded image size ---
                # These calculations were previously in __init__ but need the image loaded
                img_width, img_height = self.base_pil_image.size

                slider_min_font_size = 10
                slider_max_font_size = int(img_height * 0.8)
                slider_length = max(300, int(img_width * 0.8))

                self.font_slider.config(from_=slider_min_font_size, to=slider_max_font_size, length=slider_length, state=tk.NORMAL)
                self.text_y_offset_slider.config(from_=0.0, to=100.0, resolution=0.5, length=slider_length, state=tk.NORMAL)
                # Ensure current font size is within new range, or reset
                if self.font_size_var.get() > slider_max_font_size or self.font_size_var.get() < slider_min_font_size:
                     self.font_size_var.set(max(slider_min_font_size, int(slider_max_font_size / 4))) # Reset to a sensible default

                # Enable controls
                self.text_input_widget.config(state=tk.NORMAL)
                self.font_combobox.config(state=tk.NORMAL)
                # self.text_y_offset_slider.config(state=tk.NORMAL) # Already enabled by the config above
                self.apply_button.config(state=tk.NORMAL)
                self.download_button.config(state=tk.NORMAL)

                print(f"✅ Image loaded from {file_path}")
                self.update_display() # Update preview with the new image

            except Exception as e:
                print(f"❌ Error loading image '{file_path}': {e}")
                # Optionally show a tkinter.messagebox.showerror

    def update_display(self):
        # Determine the selected font path first
        selected_font_filename = self.font_combobox.get()
        self.selected_font_path = next((f for f in self.available_fonts if os.path.basename(f) == selected_font_filename), None)

        if not self.base_pil_image or not self.selected_font_path:
            print("⚠️ Update display called before base image or selected font is ready.")
            return

        # Get text from tk.Text widget
        current_unicode_text = self.text_input_widget.get("1.0", tk.END).strip() # "1.0" to start, tk.END to end, strip trailing newlines
        if not current_unicode_text.strip():
            print("ℹ️ Text input is empty. Displaying image without text overlay (QR code might still be added).")
            current_text_y_offset = self.text_y_offset_var.get()
            processed_pil_image = generate_overlayed_image(self.base_pil_image, "", self.selected_font_path, 1, text_y_offset_percent=current_text_y_offset, add_qr=True)
        else:
            try:
                self.legacy_text = convert_unicode_to_legacy(current_unicode_text)
            except Exception as e:
                print(f"❌ Error converting Sinhala text: {e}. Please check your input or API connection.")
                current_text_y_offset = self.text_y_offset_var.get()
                processed_pil_image = generate_overlayed_image(self.base_pil_image, "", self.selected_font_path, 1, text_y_offset_percent=current_text_y_offset, add_qr=True)
                # Fallthrough to display this processed_pil_image
            else: # if conversion was successful
                current_font_size = self.font_size_var.get()
                current_text_y_offset = self.text_y_offset_var.get()
                if current_font_size <= 0:
                    return # Should not happen if slider min is > 0
                processed_pil_image = generate_overlayed_image(self.base_pil_image, self.legacy_text, self.selected_font_path, current_font_size, text_y_offset_percent=current_text_y_offset, add_qr=True)
        
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
        # Check if font is selected and available
        selected_font_filename = self.font_combobox.get()
        self.selected_font_path = next((f for f in self.available_fonts if os.path.basename(f) == selected_font_filename), None)

        if not self.base_pil_image or not self.selected_font_path:
            # Check if font is selected and available
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
            self.selected_font_path, # Use the selected font path
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
    # Run GUI mode only
    root = tk.Tk()
    app = LiveViewApp(root)
    # Call update_font_preview once at startup to set the initial preview
    app.update_font_preview()

    root.mainloop()

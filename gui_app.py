import tkinter as tk
from tkinter import Scale, filedialog, ttk, font as tkfont, colorchooser
from PIL import Image, ImageDraw, ImageFont, ImageTk
import os
import sys # For resource_path

# Assuming image_utils.py and font_utils.py are in the same directory or accessible via PYTHONPATH
from image_utils import generate_overlayed_image 
from font_utils import find_ttf_fonts, convert_unicode_to_legacy

FONTS_FOLDER = "fonts" # Folder relative to the script where TTF files are stored
SAMPLE_PREVIEW_TEXT = "úys¿ kï b;sx weïv ;uhs''" 
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

class LiveViewApp:
    def __init__(self, master):
        self.master = master
        master.geometry("850x700") 
        master.title("Sinhala Unicode to TTF Image App")

        self.image_path_var = tk.StringVar(value="No image selected")
        self.base_pil_image = None
        self.current_tk_image = None 

        self.MAX_PREVIEW_WIDTH = 800 
        self.MAX_PREVIEW_HEIGHT = 600

        self.available_fonts = find_ttf_fonts(resource_path(FONTS_FOLDER))
        if not self.available_fonts:
            print(f"❌ Error: No .ttf fonts found in '{FONTS_FOLDER}'. Please place font files in this folder.")
            master.destroy()
            return
        
        self.selected_font_path = self.available_fonts[0]

        initial_font_size = 100 
        self.font_size_var = tk.IntVar(value=initial_font_size)
        self.text_y_offset_var = tk.DoubleVar(value=20.0) 
        self.font_color_var = tk.StringVar(value="#000000") 
        self.qr_code_path_var = tk.StringVar(value="") 

        self._build_ui()

    def _build_ui(self):
        master = self.master

        # Frame for Font Selection and Preview
        font_selection_frame = tk.Frame(master)
        font_selection_frame.pack(fill=tk.X, padx=20, pady=(10,0))

        self.font_label = tk.Label(font_selection_frame, text="Select Font:")
        self.font_label.pack(side=tk.LEFT, pady=(0,0))
        font_filenames = [os.path.basename(f) for f in self.available_fonts]
        self.font_combobox = ttk.Combobox(font_selection_frame, values=font_filenames, state="readonly", width=30)
        self.font_combobox.set(font_filenames[0]) 
        self.font_combobox.pack(side=tk.LEFT, padx=(5,10), pady=(0,0))
        self.font_combobox.bind("<<ComboboxSelected>>", self.update_font_preview)

        self.font_preview_label = tk.Label(font_selection_frame, text=SAMPLE_PREVIEW_TEXT, font=("Arial", 16))
        self.font_preview_label.pack(side=tk.LEFT, pady=(0,0))

        # Frame for Image and QR Selection
        file_selection_frame = tk.Frame(master)
        file_selection_frame.pack(fill=tk.X, padx=20, pady=(10,0))

        self.find_image_button = tk.Button(file_selection_frame, text="Select Base Image", command=self.find_image)
        self.find_image_button.pack(side=tk.LEFT, padx=(0,5))
        self.base_image_display_label = tk.Label(file_selection_frame, textvariable=self.image_path_var, wraplength=250, justify=tk.LEFT)
        self.base_image_display_label.pack(side=tk.LEFT, padx=5)

        self.select_qr_button = tk.Button(file_selection_frame, text="Select QR (Optional)", command=self.select_qr_code)
        self.select_qr_button.pack(side=tk.LEFT, padx=(10,5))
        self.qr_code_display_var = tk.StringVar(value="None")
        self.qr_code_display_label = tk.Label(file_selection_frame, textvariable=self.qr_code_display_var, wraplength=150, justify=tk.LEFT)
        self.qr_code_display_label.pack(side=tk.LEFT, padx=5)
 
        self.text_label = tk.Label(master, text="Sinhala Text:")
        self.text_label.pack(pady=(10, 0)) 

        self.text_input_widget = tk.Text(master, height=4, width=50, font=('Arial', 10), wrap=tk.WORD)
        self.text_input_widget.insert(tk.END, "සිංහල පෙළ\nමෙහි යොදන්න") 
        self.text_input_widget.pack(fill=tk.X, padx=20, pady=(5, 10)) 
        self.text_input_widget.config(state=tk.DISABLED)
        self.font_combobox.config(state=tk.DISABLED)

        self.font_slider = Scale(master, orient=tk.HORIZONTAL, label="Font Size (px)",
                                 variable=self.font_size_var)
        self.text_y_offset_slider = Scale(master, orient=tk.HORIZONTAL, label="Text Vertical Start (%)",
                                          variable=self.text_y_offset_var)
        self.font_slider.config(state=tk.DISABLED)
        self.text_y_offset_slider.pack(fill=tk.X, padx=20, pady=(5,5))
        self.font_slider.pack(fill=tk.X, padx=20, pady=(10, 5)) 

        button_frame = tk.Frame(master)
        button_frame.pack(pady=(5,10))

        self.apply_button = tk.Button(button_frame, text="Apply Settings to Preview", command=self.update_display)
        self.apply_button.pack(side=tk.LEFT, padx=(0,5))
        self.apply_button.config(state=tk.DISABLED)
        
        self.color_button = tk.Button(button_frame, text="Select Font Color", command=self.select_font_color)
        self.color_button.pack(side=tk.LEFT, padx=5)
        self.color_button.config(state=tk.DISABLED) 

        self.image_label = tk.Label(master)
        self.image_label.pack(pady=(0, 10), padx=10) 

        self.download_button = tk.Button(button_frame, text="Download Image", command=self.download_image)
        self.download_button.pack(side=tk.LEFT, padx=(5,0)) 
        self.download_button.config(state=tk.DISABLED) # Initially disable

    _font_preview_photo_image = None 
    def update_font_preview(self, event=None):
        selected_font_filename = self.font_combobox.get() 
        new_selected_font_path = next((f for f in self.available_fonts if os.path.basename(f) == selected_font_filename), None)

        if new_selected_font_path:
            self.selected_font_path = new_selected_font_path 
            try:
                sample_text = SAMPLE_PREVIEW_TEXT
                font_size = 20 
                current_font_color = self.font_color_var.get() 
                pil_font = ImageFont.truetype(self.selected_font_path, font_size)
                dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1,1)))
                text_bbox = dummy_draw.textbbox((0,0), sample_text, font=pil_font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                preview_pil_image = Image.new("RGBA", (text_width + 10, text_height + 10), (0,0,0,0)) 
                draw_preview = ImageDraw.Draw(preview_pil_image)
                draw_preview.text((5, 5 - text_bbox[1]), sample_text, font=pil_font, fill=current_font_color) 
                LiveViewApp._font_preview_photo_image = ImageTk.PhotoImage(preview_pil_image) 
                self.font_preview_label.config(image=LiveViewApp._font_preview_photo_image, text="") 
            except Exception as e: 
                print(f"⚠️ Error generating font preview image: {e}.")
                self.font_preview_label.config(image=None, text="Preview N/A") 

    def select_qr_code(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("PNG files", "*.png"), ("Image files", "*.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")],
            title="Select QR Code Image (Optional)"
        )
        if file_path:
            self.qr_code_path_var.set(file_path)
            self.qr_code_display_var.set(os.path.basename(file_path))
        else: 
            self.qr_code_path_var.set("") 
            self.qr_code_display_var.set("None") 

    def select_font_color(self):
        _ , hex_code = colorchooser.askcolor(initialcolor=self.font_color_var.get(),
                                                     title="Choose Font Color")
        if hex_code: 
            self.font_color_var.set(hex_code)
            print(f"ℹ️ Font color set to {hex_code}")
            self.update_font_preview()

    def find_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")],
            title="Select Base Image"
        )
        if file_path: 
            try:
                self.base_pil_image = Image.open(file_path).convert("RGBA")
                self.image_path_var.set(os.path.basename(file_path)) 

                img_width, img_height = self.base_pil_image.size
                slider_min_font_size = 10
                slider_max_font_size = int(img_height * 0.8)
                slider_length = max(300, int(img_width * 0.8))

                self.font_slider.config(from_=slider_min_font_size, to=slider_max_font_size, length=slider_length, state=tk.NORMAL)
                self.text_y_offset_slider.config(from_=0.0, to=100.0, resolution=0.5, length=slider_length, state=tk.NORMAL)
                if self.font_size_var.get() > slider_max_font_size or self.font_size_var.get() < slider_min_font_size:
                     self.font_size_var.set(max(slider_min_font_size, int(slider_max_font_size / 4))) 

                self.text_input_widget.config(state=tk.NORMAL)
                self.font_combobox.config(state=tk.NORMAL)
                self.apply_button.config(state=tk.NORMAL)
                self.download_button.config(state=tk.NORMAL)
                self.color_button.config(state=tk.NORMAL) 

                print(f"✅ Image loaded from {file_path}")
                self.update_display() 

            except Exception as e:
                print(f"❌ Error loading image '{file_path}': {e}")

    def update_display(self):
        selected_font_filename = self.font_combobox.get()
        self.selected_font_path = next((f for f in self.available_fonts if os.path.basename(f) == selected_font_filename), None)

        if not self.base_pil_image or not self.selected_font_path:
            print("⚠️ Update display called before base image or selected font is ready.")
            return

        current_unicode_text = self.text_input_widget.get("1.0", tk.END).strip() 
        legacy_text_to_draw = ""
        if current_unicode_text:
            try:
                legacy_text_to_draw = convert_unicode_to_legacy(current_unicode_text)
            except Exception as e:
                print(f"❌ Error converting Sinhala text: {e}. Please check your input or API connection.")
                # Display image without text if conversion fails
        
        current_font_size = self.font_size_var.get()
        current_text_y_offset = self.text_y_offset_var.get()
        current_font_color = self.font_color_var.get() 
        current_qr_path = self.qr_code_path_var.get()

        if current_font_size <= 0 and legacy_text_to_draw: # Only an issue if there's text
             print("⚠️ Font size is not positive. Cannot render text.")
             # Still generate image with QR if selected
             processed_pil_image = generate_overlayed_image(self.base_pil_image, "", self.selected_font_path, 1, text_y_offset_percent=current_text_y_offset, font_color=current_font_color, qr_code_file_path=current_qr_path)
        else:
            processed_pil_image = generate_overlayed_image(
                self.base_pil_image, 
                legacy_text_to_draw, 
                self.selected_font_path, 
                current_font_size if legacy_text_to_draw else 1, # Use 1 if no text to avoid error with font size 0
                text_y_offset_percent=current_text_y_offset, 
                font_color=current_font_color, 
                qr_code_file_path=current_qr_path
            )
        
        display_image = processed_pil_image.copy()
        display_image.thumbnail((self.MAX_PREVIEW_WIDTH, self.MAX_PREVIEW_HEIGHT), Image.Resampling.LANCZOS)

        self.current_tk_image = ImageTk.PhotoImage(display_image)
        self.image_label.config(image=self.current_tk_image)

    def download_image(self):
        selected_font_filename = self.font_combobox.get()
        self.selected_font_path = next((f for f in self.available_fonts if os.path.basename(f) == selected_font_filename), None)

        if not self.base_pil_image or not self.selected_font_path:
            print("⚠️ Cannot download: Base image or font path not ready.")
            return

        current_unicode_text = self.text_input_widget.get("1.0", tk.END).strip()
        final_legacy_text = ""

        if current_unicode_text:
            try:
                final_legacy_text = convert_unicode_to_legacy(current_unicode_text)
            except Exception as e:
                print(f"❌ Error converting text for download: {e}. Image will be generated without text.")

        current_font_size = self.font_size_var.get()
        current_text_y_offset = self.text_y_offset_var.get()
        current_font_color = self.font_color_var.get() 
        current_qr_path = self.qr_code_path_var.get()

        image_to_download = generate_overlayed_image(
            self.base_pil_image,
            final_legacy_text,
            self.selected_font_path, 
            current_font_size if final_legacy_text else 1, # Use 1 if no text
            font_color=current_font_color, 
            text_y_offset_percent=current_text_y_offset, 
            qr_code_file_path=current_qr_path 
        )

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            title="Save Image As"
        )
        if file_path: 
            try:
                image_to_download.save(file_path)
                print(f"✅ Image saved to {file_path}")
            except Exception as e:
                print(f"❌ Error saving image: {e}")

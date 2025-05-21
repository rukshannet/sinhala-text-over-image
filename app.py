import sys
import tkinter as tk
from PIL import Image # Still needed for the version check

from gui_app import LiveViewApp # Import the GUI class

if __name__ == "__main__":
    # Run GUI mode only
    # Check if Pillow supports the necessary resampling filter
    if not hasattr(Image, 'Resampling') or not hasattr(Image.Resampling, 'LANCZOS'):
         print("❌ Error: Pillow version is too old. Please upgrade Pillow to version 9.1.0 or later (`pip install --upgrade Pillow`).")
         sys.exit(1)

    root = tk.Tk()
    app = LiveViewApp(root)
    # Call update_font_preview once at startup to set the initial preview
    app.update_font_preview()
    root.mainloop() # Start the Tkinter event loop

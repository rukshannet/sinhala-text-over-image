import os
import requests
import sys # For resource_path if it were to be used here, but it's more general

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # If the script is frozen (e.g., by PyInstaller)
        base_path = sys._MEIPASS
    else:
        # If the script is not frozen
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def find_ttf_fonts(folder_path):
    """Scans a folder for .ttf files and returns a list of their full paths."""
    font_files = []
    # Assuming folder_path is already resolved by the caller if needed for PyInstaller
    if os.path.isdir(folder_path):
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(".ttf"):
                font_files.append(os.path.join(folder_path, filename))
    return font_files

def convert_unicode_to_legacy(text, output_format="font"):  # options: unicode, font, isi
    url = 'https://singlish.kdj.lk/api.php'
    payload = {
        'text': text,
        'inputType': 'unicode',
        'format': output_format
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
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

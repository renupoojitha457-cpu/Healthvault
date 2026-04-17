import pytesseract
from PIL import Image
import io

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def run_ocr(file_bytes, filename):
    try:
        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image)
        print("OCR TEXT:", text)  # debug
        return text
    except Exception as e:
        print("OCR ERROR:", e)
        return ""
"""
Image OCR extraction service.
Extracts text from images using Tesseract OCR.
"""

from PIL import Image
import pytesseract
from io import BytesIO
import logging

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

logger = logging.getLogger(__name__)


def extract_from_image(file_data, options=None):
    """
    Extract text from image using OCR.
    
    Args:
        file_data: Image file as bytes
        options: OCR options (language, etc.)
    
    Returns:
        dict: OCR results
    """
    results = {}
    options = options or {}
    
    try:
        # Open image
        image = Image.open(BytesIO(file_data))
        
        # Get OCR language (default: English)
        lang = options.get('ocr_language', 'eng')
        
        # Perform OCR
        text = pytesseract.image_to_string(image, lang=lang)
        
        # Get detailed OCR data with confidence scores
        ocr_data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
        
        # Calculate average confidence
        confidences = [int(conf) for conf in ocr_data['conf'] if conf != '-1']
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        if text.strip():
            results['extracted_text'] = {
                'text': text.strip(),
                'char_count': len(text.strip()),
                'word_count': len(text.split())
            }
            
            results['ocr_results'] = {
                'text': text.strip(),
                'language': lang,
                'confidence': round(avg_confidence, 2),
                'word_count': len([w for w in ocr_data['text'] if w.strip()]),
                'image_dimensions': {
                    'width': image.width,
                    'height': image.height
                }
            }
        else:
            logger.warning("No text detected in image")
            results['ocr_results'] = {
                'text': '',
                'language': lang,
                'confidence': 0,
                'message': 'No text detected in image'
            }
        
        # Image metadata
        results['document_metadata'] = {
            'format': image.format,
            'mode': image.mode,
            'width': image.width,
            'height': image.height,
            'size_bytes': len(file_data)
        }
        
        logger.info(f"OCR completed: {len(text.strip())} characters, {avg_confidence:.1f}% confidence")
        return results
        
    except Exception as e:
        logger.error(f"Image OCR failed: {e}")
        raise Exception(f"Image OCR failed: {str(e)}")
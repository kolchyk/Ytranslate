"""
Module for translating documents using DeepL API.
"""
import os
import logging
import deepl
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def get_deepl_translator():
    """Get DeepL translator instance."""
    auth_key = os.getenv("DEEPL_API_KEY")
    if not auth_key:
        raise ValueError("DEEPL_API_KEY not found in environment variables.")
    return deepl.DeepLClient(auth_key)

def translate_pdf_with_deepl(pdf_file, target_language: str = "ru") -> bytes:
    """
    Translates a PDF file using DeepL Document Translation API.
    
    Args:
        pdf_file: File-like object or path to PDF
        target_language: Target language code ('ru' or 'uk')
        
    Returns:
        Translated PDF content as bytes
    """
    import tempfile
    
    try:
        translator = get_deepl_translator()
        
        # Mapping app language codes to DeepL language codes
        # DeepL uses 'RU' for Russian and 'UK' for Ukrainian
        lang_map = {
            "ru": "RU",
            "uk": "UK"
        }
        deepl_target_lang = lang_map.get(target_language.lower(), "RU")
        
        logger.info(f"Uploading PDF for translation to {deepl_target_lang}...")
        
        # Create a temporary file for the output
        # Use delete=False so we can read it after translate_document completes
        tmp_output = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        output_path = tmp_output.name
        tmp_output.close()  # Close the file so we can open it in write mode
        
        try:
            # Ensure pdf_file is a file-like object
            # If it's a Streamlit UploadedFile, it should already be file-like
            # If it's a path string, we need to open it
            if isinstance(pdf_file, str):
                input_file = open(pdf_file, "rb")
                should_close_input = True
            else:
                input_file = pdf_file
                should_close_input = False
                # Reset file pointer to beginning in case it was read before
                if hasattr(input_file, 'seek'):
                    input_file.seek(0)
            
            try:
                # DeepL SDK's translate_document requires file objects for both input and output
                # Open output file in write binary mode
                with open(output_path, "wb") as output_file:
                    translator.translate_document(
                        input_file,
                        output_file,
                        target_lang=deepl_target_lang
                    )
            finally:
                if should_close_input:
                    input_file.close()
            
            # Read the translated document
            with open(output_path, "rb") as f:
                translated_data = f.read()
                
            return translated_data
            
        finally:
            # Clean up temporary file
            if os.path.exists(output_path):
                os.remove(output_path)
                
    except Exception as e:
        logger.error(f"Error during DeepL PDF translation: {e}")
        raise e

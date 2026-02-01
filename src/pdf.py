"""
PDF processing module - minimal version after switching to DeepL API.
Original extraction and creation functions removed as DeepL handles everything.
"""
import logging

logger = logging.getLogger(__name__)

# Note: extract_text_from_pdf, split_text_into_chunks, and create_translated_pdf 
# have been removed as they are no longer needed with DeepL Document API.
# DeepL preserves layout and formatting automatically.

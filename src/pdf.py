"""
PDF processing module for extracting text and chunking for translation.
"""
import io
import logging
from typing import List, Dict, Any
import pdfplumber
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_file) -> str:
    """
    Extracts text from a PDF file using pdfplumber.
    
    Args:
        pdf_file: File-like object or path to PDF
        
    Returns:
        Extracted text as a string
    """
    text = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""

def split_text_into_chunks(text: str, max_chars: int = 1500) -> List[Dict[str, Any]]:
    """
    Splits text into chunks for translation, attempting to preserve paragraph boundaries.
    
    Args:
        text: Full text to split
        max_chars: Target maximum characters per chunk
        
    Returns:
        List of dictionaries with 'text' key
    """
    if not text:
        return []
        
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk_text = ""
    
    for para in paragraphs:
        if not para.strip():
            continue
            
        # If a single paragraph is larger than max_chars, split it by sentences (roughly)
        if len(para) > max_chars:
            if current_chunk_text:
                chunks.append({"text": current_chunk_text.strip()})
                current_chunk_text = ""
            
            # Simple sentence splitting
            sentences = para.replace(". ", ".\n").split("\n")
            for sentence in sentences:
                if len(current_chunk_text) + len(sentence) > max_chars and current_chunk_text:
                    chunks.append({"text": current_chunk_text.strip()})
                    current_chunk_text = sentence + " "
                else:
                    current_chunk_text += sentence + " "
        else:
            if len(current_chunk_text) + len(para) > max_chars and current_chunk_text:
                chunks.append({"text": current_chunk_text.strip()})
                current_chunk_text = para + "\n\n"
            else:
                current_chunk_text += para + "\n\n"
                
    if current_chunk_text:
        chunks.append({"text": current_chunk_text.strip()})
        
    return chunks


def create_translated_pdf(translated_chunks: List[Dict[str, Any]], output_path: str) -> bool:
    """
    Creates a PDF file from translated chunks.
    
    Args:
        translated_chunks: List of dictionaries with 'text' key containing translated text
        output_path: Path where the PDF file should be saved
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create PDF document
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)
        
        # Container for the 'Flowable' objects
        story = []
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Create a custom style for body text
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=12,
        )
        
        # Add translated text
        for chunk in translated_chunks:
            text = chunk.get('text', '').strip()
            if text:
                # Replace newlines with HTML breaks for proper formatting
                text = text.replace('\n', '<br/>')
                para = Paragraph(text, body_style)
                story.append(para)
                story.append(Spacer(1, 0.2*inch))
        
        # Build PDF
        doc.build(story)
        return True
        
    except Exception as e:
        logger.error(f"Error creating translated PDF: {e}")
        return False

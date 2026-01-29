"""
Translation module using OpenAI GPT API.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_openai_client() -> OpenAI:
    """Get OpenAI client instance."""
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def translate_text(text: str, target_language: str = "ru") -> str:
    """
    Translates text to the target language using OpenAI GPT.
    
    Args:
        text: Text to translate
        target_language: Target language code ('ru' or 'uk')
        
    Returns:
        Translated text or original text on failure
    """
    if not text or not text.strip():
        return ""
    
    language_map = {
        "ru": "Russian",
        "uk": "Ukrainian"
    }
    
    target_lang_full = language_map.get(target_language, "Russian")
    
    prompt = (
        f"Translate the following text from a YouTube video transcript into {target_lang_full}. "
        f"The translation should be natural-sounding for voice-over, simplified if necessary, "
        f"and maintain the original meaning. Only return the translated text.\n\nText:\n{text}"
    )
    
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional translator specializing in video dubbing and subtitles."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error during translation: {e}")
        return text  # Fallback to original text


def translate_transcript_chunks(
    chunks: List[List[Dict[str, Any]]],
    target_language: str = "ru"
) -> List[Dict[str, Any]]:
    """
    Translates a list of transcript chunks, preserving timing information.
    
    Args:
        chunks: List of transcript chunks (each chunk is a list of segments)
        target_language: Target language code
        
    Returns:
        List of translated chunks with timing info
    """
    if not chunks:
        return []

    # Helper function for parallel execution
    def process_chunk(i, chunk):
        if not chunk:
            return None
            
        # Combine all text in the chunk for translation
        combined_text = "\n".join([segment['text'] for segment in chunk])
        translated_text = translate_text(combined_text, target_language)
        
        # Calculate chunk timing - use first segment's start and last segment's end
        start_time = chunk[0]['start']
        
        # Calculate end time from last segment
        last_segment = chunk[-1]
        if 'duration' in last_segment:
            end_time = last_segment['start'] + last_segment['duration']
        elif len(chunk) > 1:
            # Estimate duration based on segment length
            avg_duration = (last_segment['start'] - start_time) / (len(chunk) - 1)
            end_time = last_segment['start'] + avg_duration
        else:
            # Single segment, estimate duration from text length
            # Rough estimate: ~150 words per minute, ~5 chars per word
            estimated_duration = len(last_segment['text']) / 5 / 150 * 60
            end_time = start_time + max(estimated_duration, 2.0)
        
        logger.debug(f"Translated chunk {i}: {start_time:.1f}s - {end_time:.1f}s")
        
        return {
            'index': i,
            'start': start_time,
            'end': end_time,
            'text': translated_text,
            'original_text': combined_text
        }

    # Execute in parallel
    with ThreadPoolExecutor(max_workers=min(len(chunks), 10)) as executor:
        results = list(executor.map(lambda p: process_chunk(*p), enumerate(chunks)))
    
    # Filter out None results and sort by original index to preserve order
    translated_chunks = [r for r in results if r is not None]
    translated_chunks.sort(key=lambda x: x['index'])
    
    # Remove index key before returning
    for chunk in translated_chunks:
        del chunk['index']
        
    return translated_chunks


def translate_segments_individually(
    segments: List[Dict[str, Any]],
    target_language: str = "ru"
) -> List[Dict[str, Any]]:
    """
    Translates each segment individually, preserving exact timing.
    More expensive but better for sync-critical applications.
    
    Args:
        segments: List of transcript segments
        target_language: Target language code
        
    Returns:
        List of translated segments with original timing
    """
    translated_segments = []
    
    for i, segment in enumerate(segments):
        translated_text = translate_text(segment['text'], target_language)
        
        translated_segment = {
            'start': segment['start'],
            'text': translated_text,
            'original_text': segment['text']
        }
        
        # Preserve duration if available
        if 'duration' in segment:
            translated_segment['end'] = segment['start'] + segment['duration']
            translated_segment['duration'] = segment['duration']
        
        translated_segments.append(translated_segment)
        logger.debug(f"Translated segment {i}: {segment['start']:.1f}s")
    
    return translated_segments

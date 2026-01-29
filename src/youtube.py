"""
YouTube video processing module for extracting video IDs and transcripts.
"""
import re
import logging
from typing import Optional, List, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> Optional[str]:
    """
    Extracts the video ID from a YouTube URL.
    
    Args:
        url: YouTube video URL
        
    Returns:
        Video ID or None if not found
    """
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/|v\/|youtu.be\/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_transcript(
    video_id: str,
    languages: List[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Fetches the transcript for a given video ID.
    
    Args:
        video_id: YouTube video ID
        languages: List of preferred languages (default: ['en', 'ru', 'uk'])
        
    Returns:
        List of transcript segments or None if not found
    """
    if languages is None:
        languages = ['en', 'ru', 'uk']
    
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        # Try to find a transcript in requested languages
        try:
            transcript = transcript_list.find_transcript(languages)
            data = transcript.fetch().to_raw_data()
            logger.info(f"Found transcript in language: {transcript.language_code}")
            return data
        except NoTranscriptFound:
            # Fallback: get any available transcript (e.g. auto-generated)
            transcript = transcript_list.find_generated_transcript(['en'])
            data = transcript.fetch().to_raw_data()
            logger.info("Using auto-generated English transcript")
            return data
            
    except TranscriptsDisabled:
        logger.error(f"Transcripts are disabled for video: {video_id}")
        return None
    except NoTranscriptFound:
        logger.error(f"No transcript found for video: {video_id}")
        return None
    except Exception as e:
        logger.error(f"Error fetching transcript: {e}")
        return None


def format_transcript_for_translation(
    transcript: List[Dict[str, Any]],
    max_chunk_chars: int = 1000
) -> List[List[Dict[str, Any]]]:
    """
    Groups transcript segments into chunks for efficient translation.
    
    Args:
        transcript: List of transcript segments
        max_chunk_chars: Maximum characters per chunk
        
    Returns:
        List of chunks (each chunk is a list of segments)
    """
    if not transcript:
        return []
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for segment in transcript:
        text = segment.get('text', '')
        text_length = len(text)
        
        # If adding this segment would exceed limit, start new chunk
        if current_length + text_length > max_chunk_chars and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_length = 0
        
        current_chunk.append(segment)
        current_length += text_length
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    logger.info(f"Formatted {len(transcript)} segments into {len(chunks)} chunks")
    return chunks


def get_transcript_duration(transcript: List[Dict[str, Any]]) -> float:
    """
    Calculates the total duration of the transcript.
    
    Args:
        transcript: List of transcript segments
        
    Returns:
        Total duration in seconds
    """
    if not transcript:
        return 0.0
    
    last_segment = transcript[-1]
    start = last_segment.get('start', 0)
    duration = last_segment.get('duration', 0)
    
    return start + duration

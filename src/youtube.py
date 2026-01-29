"""
YouTube video processing module for extracting video IDs and transcripts.
"""
import re
import logging
import os
import requests
from http.cookiejar import MozillaCookieJar
from typing import Optional, List, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.proxies import GenericProxyConfig

logger = logging.getLogger(__name__)


def get_youtube_config() -> Dict[str, Any]:
    """
    Returns YouTube-related configuration (cookies, proxies).
    """
    config = {}
    
    # Cookies
    cookies_file = os.getenv("YOUTUBE_COOKIES_PATH", "cookies.txt")
    if os.path.exists(cookies_file):
        config["cookies"] = cookies_file
        logger.info(f"Using YouTube cookies from: {cookies_file}")
    
    # Proxies
    proxy = os.getenv("YOUTUBE_PROXY")
    if proxy:
        config["proxy"] = proxy  # Store the single URL
        logger.info("Using YouTube proxy")
        
    return config


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
    
    config = get_youtube_config()
    cookies_file = config.get("cookies")
    proxy_url = config.get("proxy")
    
    try:
        # Configure the API instance
        proxy_config = None
        if proxy_url:
            proxy_config = GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
            
        http_client = None
        if cookies_file:
            try:
                session = requests.Session()
                cookie_jar = MozillaCookieJar(cookies_file)
                cookie_jar.load(ignore_discard=True, ignore_expires=True)
                session.cookies = cookie_jar
                http_client = session
            except Exception as ce:
                logger.error(f"Error loading cookies: {ce}")
        
        # Instantiate the API with config
        api = YouTubeTranscriptApi(
            proxy_config=proxy_config,
            http_client=http_client
        )
        
        # Get the transcript list
        transcript_list = api.list(video_id)
        
        # Try to find a transcript in requested languages
        try:
            transcript = transcript_list.find_transcript(languages)
            data = transcript.fetch() # Returns a list of dicts directly in newer versions, or needs to_raw_data()
            
            # In newer versions, fetch() might return a list of dicts or a Transcript object.
            # Based on the repo, it returns a list of dictionaries.
            if hasattr(data, 'to_raw_data'):
                data = data.to_raw_data()
                
            logger.info(f"Found transcript in language: {transcript.language_code}")
            return data
        except NoTranscriptFound:
            # Fallback: get any available transcript (e.g. auto-generated)
            # Try English as a fallback
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
                data = transcript.fetch()
                if hasattr(data, 'to_raw_data'):
                    data = data.to_raw_data()
                logger.info("Using auto-generated English transcript")
                return data
            except Exception as e:
                logger.error(f"No auto-generated English transcript: {e}")
                # Last resort: just get the first one
                for transcript in transcript_list:
                    data = transcript.fetch()
                    if hasattr(data, 'to_raw_data'):
                        data = data.to_raw_data()
                    logger.info(f"Using first available transcript: {transcript.language_code}")
                    return data
                return None
            
    except TranscriptsDisabled:
        logger.error(f"Transcripts are disabled for video: {video_id}")
        return None
    except NoTranscriptFound:
        logger.error(f"No transcript found for video: {video_id}")
        return None
    except Exception as e:
        logger.error(f"Error fetching transcript: {e}")
        import traceback
        logger.error(traceback.format_exc())
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

"""
YTranslate - YouTube Video Translator and TTS
"""
import logging

# Configure logging for the package
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from .youtube import extract_video_id, get_transcript, format_transcript_for_translation, get_transcript_duration
from .translator import translate_text, translate_transcript_chunks, translate_segments_individually
from .tts import generate_audio, create_full_audio, create_audio_for_video
from .video import download_video, merge_audio_video, get_video_duration, cleanup_temp_files, cleanup_temp_dir

__all__ = [
    # YouTube
    'extract_video_id',
    'get_transcript',
    'format_transcript_for_translation',
    'get_transcript_duration',
    # Translator
    'translate_text',
    'translate_transcript_chunks',
    'translate_segments_individually',
    # TTS
    'generate_audio',
    'create_full_audio',
    'create_audio_for_video',
    # Video
    'download_video',
    'merge_audio_video',
    'get_video_duration',
    'cleanup_temp_files',
    'cleanup_temp_dir',
]

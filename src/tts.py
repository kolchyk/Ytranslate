"""
Text-to-Speech module using OpenAI TTS API with timing synchronization.
"""
import os
import io
import shutil
import sys
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Python 3.13+ compatibility for audioop (required by pydub)
try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
        sys.modules['audioop'] = audioop
    except ImportError:
        try:
            import pyaudioop as audioop
            sys.modules['audioop'] = audioop
        except ImportError:
            pass

from openai import OpenAI
from pydub import AudioSegment
from dotenv import load_dotenv

load_dotenv()

# Check for ffmpeg and ffprobe
FFMPEG_PATH = shutil.which("ffmpeg")
FFPROBE_PATH = shutil.which("ffprobe")

if not FFMPEG_PATH:
    logger.warning("ffmpeg not found. Audio processing may fail.")
if not FFPROBE_PATH:
    logger.warning("ffprobe not found. Audio processing may fail.")


def get_openai_client() -> OpenAI:
    """Get OpenAI client instance."""
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_audio(
    text: str,
    voice: str = "alloy",
    model: str = "gpt-4o-mini-tts",
    speed: float = 1.0
) -> Optional[AudioSegment]:
    """
    Generates audio from text using OpenAI TTS.
    
    Args:
        text: Text to convert to speech
        voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
        model: TTS model to use
        speed: Speech speed (0.25 to 4.0)
        
    Returns:
        AudioSegment object or None on failure
    """
    if not text or not text.strip():
        return None
    
    try:
        client = get_openai_client()
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            speed=speed
        )
        
        # Read the response content into a byte stream
        audio_data = io.BytesIO(response.content)
        return AudioSegment.from_file(audio_data, format="mp3")
    except Exception as e:
        logger.error(f"Error during TTS generation: {e}")
        return None


def adjust_audio_duration(
    audio: AudioSegment,
    target_duration_ms: int,
    min_speed: float = 0.75,
    max_speed: float = 1.5
) -> AudioSegment:
    """
    Adjusts audio duration to fit target duration using speed change.
    
    Args:
        audio: AudioSegment to adjust
        target_duration_ms: Target duration in milliseconds
        min_speed: Minimum allowed speed factor
        max_speed: Maximum allowed speed factor
        
    Returns:
        Adjusted AudioSegment
    """
    if target_duration_ms <= 0 or len(audio) == 0:
        return audio
    
    current_duration = len(audio)
    
    # Calculate required speed change
    speed_factor = current_duration / target_duration_ms
    
    # Clamp speed factor to acceptable range
    speed_factor = max(min_speed, min(max_speed, speed_factor))
    
    if abs(speed_factor - 1.0) < 0.05:
        # Speed change too small, not worth processing
        return audio
    
    try:
        # Change speed using frame rate manipulation
        # This changes speed without changing pitch significantly
        new_frame_rate = int(audio.frame_rate * speed_factor)
        adjusted = audio._spawn(audio.raw_data, overrides={
            "frame_rate": new_frame_rate
        }).set_frame_rate(audio.frame_rate)
        
        logger.debug(f"Adjusted audio from {current_duration}ms to {len(adjusted)}ms (speed: {speed_factor:.2f}x)")
        return adjusted
    except Exception as e:
        logger.warning(f"Failed to adjust audio duration: {e}")
        return audio


def create_full_audio(
    translated_chunks: List[Dict[str, Any]],
    output_path: str = "output.mp3",
    voice: str = "alloy",
    sync_to_timing: bool = True
) -> Optional[str]:
    """
    Creates a full audio file from translated chunks with proper timing synchronization.
    
    Args:
        translated_chunks: List of dicts with 'start', 'end' (optional), and 'text' keys
        output_path: Path for the output audio file
        voice: Voice to use for TTS
        sync_to_timing: If True, adjust audio speed to fit original timing
        
    Returns:
        Output path on success, None on failure
    """
    if not translated_chunks:
        logger.error("No chunks provided for audio generation")
        return None
    
    full_audio = AudioSegment.silent(duration=0)
    current_time_ms = 0
    
    for i, chunk in enumerate(translated_chunks):
        start_time_ms = int(chunk['start'] * 1000)
        
        # Calculate available duration for this chunk
        if 'end' in chunk:
            end_time_ms = int(chunk['end'] * 1000)
            available_duration_ms = end_time_ms - start_time_ms
        elif i + 1 < len(translated_chunks):
            # Use next chunk's start time as end
            next_start_ms = int(translated_chunks[i + 1]['start'] * 1000)
            available_duration_ms = next_start_ms - start_time_ms
        else:
            # Last chunk - no duration constraint
            available_duration_ms = 0
        
        # Add silence if there's a gap before this chunk
        if start_time_ms > current_time_ms:
            silence_duration = start_time_ms - current_time_ms
            full_audio += AudioSegment.silent(duration=silence_duration)
            current_time_ms = start_time_ms
            logger.debug(f"Added {silence_duration}ms silence before chunk {i}")
        
        # Generate audio for this chunk
        chunk_audio = generate_audio(chunk['text'], voice=voice)
        
        if chunk_audio:
            # Adjust audio duration if sync is enabled and we have a target duration
            if sync_to_timing and available_duration_ms > 0:
                chunk_audio = adjust_audio_duration(chunk_audio, available_duration_ms)
            
            full_audio += chunk_audio
            current_time_ms += len(chunk_audio)
            logger.debug(f"Chunk {i}: {len(chunk_audio)}ms at position {start_time_ms}ms")
        else:
            logger.warning(f"Failed to generate audio for chunk {i}")
    
    try:
        full_audio.export(output_path, format="mp3")
        logger.info(f"Audio saved to: {output_path} (duration: {len(full_audio)}ms)")
        return output_path
    except Exception as e:
        logger.error(f"Failed to export audio: {e}")
        return None


def create_audio_for_video(
    translated_chunks: List[Dict[str, Any]],
    video_duration_ms: int,
    output_path: str = "output.mp3",
    voice: str = "alloy"
) -> Optional[str]:
    """
    Creates audio file synced to video duration.
    
    Args:
        translated_chunks: List of translated chunks with timing info
        video_duration_ms: Total video duration in milliseconds
        output_path: Path for the output audio file
        voice: Voice to use for TTS
        
    Returns:
        Output path on success, None on failure
    """
    result = create_full_audio(translated_chunks, output_path, voice, sync_to_timing=True)
    
    if result:
        # Pad with silence if audio is shorter than video
        try:
            audio = AudioSegment.from_mp3(output_path)
            if len(audio) < video_duration_ms:
                padding = AudioSegment.silent(duration=video_duration_ms - len(audio))
                audio = audio + padding
                audio.export(output_path, format="mp3")
                logger.info(f"Padded audio to match video duration: {video_duration_ms}ms")
        except Exception as e:
            logger.warning(f"Failed to pad audio: {e}")
    
    return result

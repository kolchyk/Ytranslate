"""
Text-to-Speech module using OpenAI TTS API with timing synchronization.
"""
import os
import io
import shutil
import sys
import logging
import warnings
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Suppress pydub warnings about invalid escape sequences (from third-party library)
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub")

# Python 3.13+ compatibility for audioop (required by pydub)
try:
    import audioop  # type: ignore
except ImportError:
    try:
        import audioop_lts as audioop  # type: ignore
        sys.modules['audioop'] = audioop
    except ImportError:
        try:
            import pyaudioop as audioop  # type: ignore
            sys.modules['audioop'] = audioop
        except ImportError:
            pass

from dotenv import load_dotenv  # type: ignore
load_dotenv()

# Check for ffmpeg and ffprobe BEFORE importing pydub
def find_binary(name: str) -> Optional[str]:
    """Finds a binary in the system PATH or common installation locations."""
    # First check PATH
    path = shutil.which(name)
    if path:
        return path
    
    # Check environment variable
    env_var = os.getenv(f"{name.upper()}_PATH") or os.getenv("FFMPEG_PATH")
    if env_var and os.path.exists(env_var):
        return env_var
    
    # Check common Windows installation paths
    if sys.platform == "win32":
        # Get user's home directory
        user_home = os.path.expanduser("~")
        windows_paths = [
            # Standard installation paths
            os.path.join("C:\\", "ffmpeg", "bin", f"{name}.exe"),
            os.path.join("C:\\", "Program Files", "ffmpeg", "bin", f"{name}.exe"),
            os.path.join("C:\\", "Program Files (x86)", "ffmpeg", "bin", f"{name}.exe"),
            # User installation paths
            os.path.join(user_home, "ffmpeg", "bin", f"{name}.exe"),
            os.path.join(user_home, "AppData", "Local", "ffmpeg", "bin", f"{name}.exe"),
            # Chocolatey installation path
            os.path.join("C:\\", "ProgramData", "chocolatey", "bin", f"{name}.exe"),
            # Scoop installation path
            os.path.join(user_home, "scoop", "apps", "ffmpeg", "current", "bin", f"{name}.exe"),
            # Portable installation in project directory
            os.path.join(os.getcwd(), "ffmpeg", "bin", f"{name}.exe"),
            os.path.join(os.path.dirname(os.getcwd()), "ffmpeg", "bin", f"{name}.exe"),
        ]
        for win_path in windows_paths:
            if os.path.exists(win_path):
                return win_path
    
    # Check common Heroku apt locations
    heroku_apt_path = os.path.join(os.getcwd(), ".apt", "usr", "bin", name)
    if os.path.exists(heroku_apt_path):
        return heroku_apt_path
        
    return None

# Find binaries and convert to absolute paths immediately
_ffmpeg_path = find_binary("ffmpeg")
_ffprobe_path = find_binary("ffprobe")

FFMPEG_PATH = os.path.normpath(os.path.abspath(_ffmpeg_path)) if _ffmpeg_path else None
FFPROBE_PATH = os.path.normpath(os.path.abspath(_ffprobe_path)) if _ffprobe_path else None

# Suppress RuntimeWarning from pydub about ffmpeg (we handle detection ourselves)
warnings.filterwarnings("ignore", message=".*Couldn't find ffmpeg.*", category=RuntimeWarning, module="pydub")
warnings.filterwarnings("ignore", message=".*ffmpeg.*", category=RuntimeWarning, module="pydub")


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg is available for audio processing."""
    return FFMPEG_PATH is not None and os.path.exists(FFMPEG_PATH)


def get_ffmpeg_installation_instructions() -> str:
    """Get platform-specific instructions for installing ffmpeg."""
    if sys.platform == "win32":
        return (
            "**Установка ffmpeg на Windows:**\n\n"
            "1. **Chocolatey** (рекомендуется):\n"
            "   ```powershell\n"
            "   choco install ffmpeg\n"
            "   ```\n\n"
            "2. **Scoop**:\n"
            "   ```powershell\n"
            "   scoop install ffmpeg\n"
            "   ```\n\n"
            "3. **Ручная установка**:\n"
            "   - Скачайте с https://ffmpeg.org/download.html\n"
            "   - Распакуйте в `C:\\ffmpeg`\n"
            "   - Добавьте `C:\\ffmpeg\\bin` в PATH\n\n"
            "4. **Портативная версия**:\n"
            "   - Скачайте и распакуйте в папку проекта `ffmpeg\\bin\\`\n\n"
            "После установки перезапустите приложение."
        )
    else:
        return (
            "**Установка ffmpeg:**\n\n"
            "- Ubuntu/Debian: `sudo apt-get install ffmpeg`\n"
            "- macOS: `brew install ffmpeg`\n"
            "- Или скачайте с https://ffmpeg.org/download.html"
        )

# Now import pydub after configuring paths
from openai import OpenAI  # type: ignore
from pydub import AudioSegment  # type: ignore

# Configure pydub to use found ffmpeg/ffprobe paths
if FFMPEG_PATH:
    AudioSegment.converter = FFMPEG_PATH
    logger.info(f"Using ffmpeg at: {FFMPEG_PATH}")
    # Add ffmpeg directory to PATH so subprocess can find it
    ffmpeg_dir = os.path.dirname(FFMPEG_PATH)
    current_path = os.environ.get("PATH", "")
    if ffmpeg_dir not in current_path:
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + current_path
else:
    logger.warning("ffmpeg not found. Audio processing may fail.")
    
if FFPROBE_PATH:
    AudioSegment.ffprobe = FFPROBE_PATH
    logger.info(f"Using ffprobe at: {FFPROBE_PATH}")
    # Add ffprobe directory to PATH so subprocess can find it
    ffprobe_dir = os.path.dirname(FFPROBE_PATH)
    current_path = os.environ.get("PATH", "")
    if ffprobe_dir not in current_path:
        os.environ["PATH"] = ffprobe_dir + os.pathsep + current_path
else:
    logger.warning("ffprobe not found. Audio processing may fail.")
    
# Also set environment variable as fallback (some pydub operations use subprocess)
if FFMPEG_PATH:
    os.environ["FFMPEG_BINARY"] = FFMPEG_PATH
if FFPROBE_PATH:
    os.environ["FFPROBE_BINARY"] = FFPROBE_PATH


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
        
        # Check if ffmpeg is available before trying to process audio
        if not FFMPEG_PATH:
            error_msg = (
                "ffmpeg not found. Please install ffmpeg to process audio files.\n"
                f"{get_ffmpeg_installation_instructions()}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Ensure ffprobe is also available (pydub needs it for some operations)
        if not FFPROBE_PATH:
            logger.warning("ffprobe not found. Some audio operations may fail.")
        
        return AudioSegment.from_file(audio_data, format="mp3")
    except FileNotFoundError as e:
        error_msg = (
            f"ffmpeg executable not found: {e}\n"
            f"{get_ffmpeg_installation_instructions()}"
        )
        logger.error(error_msg)
        return None
    except Exception as e:
        # Check if error is related to ffmpeg/ffprobe
        error_str = str(e).lower()
        if "ffmpeg" in error_str or "ffprobe" in error_str or "couldn't find" in error_str:
            error_msg = (
                f"Audio processing failed - ffmpeg/ffprobe issue: {e}\n"
                f"{get_ffmpeg_installation_instructions()}"
            )
            logger.error(error_msg)
        else:
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
        if not FFMPEG_PATH:
            error_msg = (
                "ffmpeg not found. Cannot export audio file.\n"
                "Please install ffmpeg:\n"
                "Windows: Download from https://ffmpeg.org/download.html or use: choco install ffmpeg"
            )
            logger.error(error_msg)
            return None
        
        full_audio.export(output_path, format="mp3")
        logger.info(f"Audio saved to: {output_path} (duration: {len(full_audio)}ms)")
        return output_path
    except FileNotFoundError as e:
        error_msg = (
            f"ffmpeg executable not found: {e}\n"
            "Please install ffmpeg and ensure it's in your PATH."
        )
        logger.error(error_msg)
        return None
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
            if not FFMPEG_PATH:
                logger.warning("ffmpeg not found. Skipping audio padding.")
                return result
                
            audio = AudioSegment.from_mp3(output_path)
            if len(audio) < video_duration_ms:
                padding = AudioSegment.silent(duration=video_duration_ms - len(audio))
                audio = audio + padding
                audio.export(output_path, format="mp3")
                logger.info(f"Padded audio to match video duration: {video_duration_ms}ms")
        except FileNotFoundError as e:
            logger.warning(f"ffmpeg not found, skipping audio padding: {e}")
        except Exception as e:
            logger.warning(f"Failed to pad audio: {e}")
    
    return result

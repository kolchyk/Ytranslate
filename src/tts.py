"""
Text-to-Speech module using OpenAI TTS API with timing synchronization using ffmpeg.
"""
import os
import io
import shutil
import sys
import logging
import warnings
import subprocess
import tempfile
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Check for ffmpeg and ffprobe
def find_binary(name: str) -> Optional[str]:
    """Finds a binary in the system PATH or common installation locations."""
    # Check Heroku apt locations FIRST
    heroku_apt_path = os.path.join(os.getcwd(), ".apt", "usr", "bin", name)
    if os.path.exists(heroku_apt_path):
        return heroku_apt_path
    
    # Check environment variable
    env_var = os.getenv(f"{name.upper()}_PATH") or os.getenv("FFMPEG_PATH")
    if env_var and os.path.exists(env_var):
        return env_var
    
    # Then check PATH
    path = shutil.which(name)
    if path:
        return path
    
    # Check common Windows installation paths
    if sys.platform == "win32":
        user_home = os.path.expanduser("~")
        windows_paths = [
            os.path.join("C:\\", "ffmpeg", "bin", f"{name}.exe"),
            os.path.join("C:\\", "Program Files", "ffmpeg", "bin", f"{name}.exe"),
            os.path.join("C:\\", "Program Files (x86)", "ffmpeg", "bin", f"{name}.exe"),
            os.path.join(user_home, "ffmpeg", "bin", f"{name}.exe"),
            os.path.join(user_home, "AppData", "Local", "ffmpeg", "bin", f"{name}.exe"),
            os.path.join("C:\\", "ProgramData", "chocolatey", "bin", f"{name}.exe"),
            os.path.join(user_home, "scoop", "apps", "ffmpeg", "current", "bin", f"{name}.exe"),
            os.path.join(os.getcwd(), "ffmpeg", "bin", f"{name}.exe"),
        ]
        for win_path in windows_paths:
            if os.path.exists(win_path):
                return win_path
        
    return None

# Find binaries and convert to absolute paths immediately
_ffmpeg_path = find_binary("ffmpeg")
_ffprobe_path = find_binary("ffprobe")

FFMPEG_PATH = os.path.normpath(os.path.abspath(_ffmpeg_path)) if _ffmpeg_path else None
FFPROBE_PATH = os.path.normpath(os.path.abspath(_ffprobe_path)) if _ffprobe_path else None

# Set environment variables for subprocesses
if FFMPEG_PATH:
    os.environ["FFMPEG_BINARY"] = FFMPEG_PATH
    ffmpeg_dir = os.path.dirname(FFMPEG_PATH)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

if FFPROBE_PATH:
    os.environ["FFPROBE_BINARY"] = FFPROBE_PATH
    ffprobe_dir = os.path.dirname(FFPROBE_PATH)
    if ffprobe_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffprobe_dir + os.pathsep + os.environ.get("PATH", "")


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


def get_openai_client() -> OpenAI:
    """Get OpenAI client instance."""
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_audio_duration_ms(file_path: str) -> int:
    """Gets audio duration in milliseconds using ffprobe."""
    if not FFPROBE_PATH or not os.path.exists(file_path):
        return 0
    try:
        cmd = [
            FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return int(float(result.stdout.strip()) * 1000)
    except Exception as e:
        logger.error(f"Error getting audio duration: {e}")
        return 0


def generate_audio(
    text: str,
    voice: str = "alloy",
    model: str = "gpt-4o-mini-tts",
    speed: float = 1.0,
    output_dir: Optional[str] = None
) -> Optional[str]:
    """
    Generates audio from text using OpenAI TTS and saves to a temporary file.
    
    Returns:
        Path to the generated MP3 file or None on failure
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
        
        # Create a temporary file to store the audio
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=output_dir)
        temp_file.write(response.content)
        temp_file.close()
        
        return temp_file.name
    except Exception as e:
        logger.error(f"Error during TTS generation: {e}")
        return None


def adjust_audio_duration(
    input_path: str,
    target_duration_ms: int,
    output_path: Optional[str] = None,
    min_speed: float = 0.5,
    max_speed: float = 2.0
) -> Optional[str]:
    """
    Adjusts audio duration to fit target duration using ffmpeg's atempo filter.
    """
    if not FFMPEG_PATH or not os.path.exists(input_path) or target_duration_ms <= 0:
        return input_path
    
    current_duration_ms = get_audio_duration_ms(input_path)
    if current_duration_ms == 0:
        return input_path
    
    speed_factor = current_duration_ms / target_duration_ms
    
    # ffmpeg's atempo filter supports 0.5 to 2.0. For larger values, we need to chain them.
    # But for our purposes, clamping to 0.5-2.0 is usually enough.
    speed_factor = max(min_speed, min(max_speed, speed_factor))
    
    if abs(speed_factor - 1.0) < 0.05:
        return input_path
    
    if not output_path:
        output_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        output_path = output_file.name
        output_file.close()
        
    try:
        # atempo filter changes speed without changing pitch
        cmd = [
            FFMPEG_PATH, "-i", input_path,
            "-filter:a", f"atempo={speed_factor}",
            "-y", output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    except Exception as e:
        logger.error(f"Failed to adjust audio duration with ffmpeg: {e}")
        return input_path


def create_full_audio(
    translated_chunks: List[Dict[str, Any]],
    output_path: str = "output.mp3",
    voice: str = "alloy",
    sync_to_timing: bool = True
) -> Optional[str]:
    """
    Creates a full audio file from translated chunks using ffmpeg concat.
    """
    if not translated_chunks:
        logger.error("No chunks provided for audio generation")
        return None
        
    temp_dir = tempfile.mkdtemp(prefix="tts_concat_")
    
    try:
        def process_chunk_audio(i, chunk):
            start_time_ms = int(chunk['start'] * 1000)
            
            # Calculate available duration for this chunk
            if 'end' in chunk:
                end_time_ms = int(chunk['end'] * 1000)
                available_duration_ms = end_time_ms - start_time_ms
            elif i + 1 < len(translated_chunks):
                next_start_ms = int(translated_chunks[i + 1]['start'] * 1000)
                available_duration_ms = next_start_ms - start_time_ms
            else:
                available_duration_ms = 0
                
            chunk_file = generate_audio(chunk['text'], voice=voice, output_dir=temp_dir)
            
            if chunk_file and sync_to_timing and available_duration_ms > 0:
                adjusted_file = os.path.join(temp_dir, f"adj_{i}.mp3")
                result_file = adjust_audio_duration(chunk_file, available_duration_ms, adjusted_file)
                chunk_file = result_file
                
            return i, start_time_ms, chunk_file

        with ThreadPoolExecutor(max_workers=min(len(translated_chunks), 10)) as executor:
            results = list(executor.map(lambda p: process_chunk_audio(*p), enumerate(translated_chunks)))
        
        results.sort(key=lambda x: x[0])
        
        # Build concat list for ffmpeg
        concat_file_path = os.path.join(temp_dir, "concat_list.txt")
        current_time_ms = 0
        
        with open(concat_file_path, "w", encoding="utf-8") as f:
            for i, start_time_ms, chunk_file in results:
                if not chunk_file:
                    continue
                
                # Add silence if there's a gap
                if start_time_ms > current_time_ms:
                    silence_ms = start_time_ms - current_time_ms
                    silence_file = os.path.join(temp_dir, f"silence_{i}.mp3")
                    # Generate silence using ffmpeg
                    silence_cmd = [
                        FFMPEG_PATH, "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
                        "-t", f"{silence_ms/1000:.3f}", "-y", silence_file
                    ]
                    subprocess.run(silence_cmd, capture_output=True, check=True)
                    f.write(f"file '{os.path.abspath(silence_file).replace('\\', '/')}'\n")
                    current_time_ms = start_time_ms
                
                f.write(f"file '{os.path.abspath(chunk_file).replace('\\', '/')}'\n")
                duration_ms = get_audio_duration_ms(chunk_file)
                current_time_ms += duration_ms
                
        # Run ffmpeg concat
        concat_cmd = [
            FFMPEG_PATH, "-f", "concat", "-safe", "0", "-i", concat_file_path,
            "-c", "libmp3lame", "-q:a", "2", "-y", output_path
        ]
        subprocess.run(concat_cmd, capture_output=True, check=True)
        
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to create full audio: {e}")
        return None
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")


def create_audio_for_video(
    translated_chunks: List[Dict[str, Any]],
    video_duration_ms: int,
    output_path: str = "output.mp3",
    voice: str = "alloy"
) -> Optional[str]:
    """
    Creates audio file synced to video duration.
    """
    result = create_full_audio(translated_chunks, output_path, voice, sync_to_timing=True)
    
    if result and os.path.exists(output_path):
        current_duration_ms = get_audio_duration_ms(output_path)
        if current_duration_ms < video_duration_ms:
            # Pad with silence
            padding_ms = video_duration_ms - current_duration_ms
            temp_dir = os.path.dirname(output_path)
            padding_file = os.path.join(temp_dir, "padding_temp.mp3")
            
            try:
                # Generate padding silence
                silence_cmd = [
                    FFMPEG_PATH, "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
                    "-t", f"{padding_ms/1000:.3f}", "-y", padding_file
                ]
                subprocess.run(silence_cmd, capture_output=True, check=True)
                
                # Append padding
                final_output = os.path.join(temp_dir, "final_padded.mp3")
                concat_list = os.path.join(temp_dir, "pad_concat.txt")
                with open(concat_list, "w") as f:
                    f.write(f"file '{os.path.abspath(output_path).replace('\\', '/')}'\n")
                    f.write(f"file '{os.path.abspath(padding_file).replace('\\', '/')}'\n")
                
                append_cmd = [
                    FFMPEG_PATH, "-f", "concat", "-safe", "0", "-i", concat_list,
                    "-c", "copy", "-y", final_output
                ]
                subprocess.run(append_cmd, capture_output=True, check=True)
                
                shutil.move(final_output, output_path)
                os.remove(concat_list)
                os.remove(padding_file)
            except Exception as e:
                logger.warning(f"Failed to pad audio: {e}")
                
    return result

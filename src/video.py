"""
Video processing module for downloading YouTube videos and merging audio.
"""
import os
import shutil
import tempfile
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Check for ffmpeg
FFMPEG_PATH = shutil.which("ffmpeg")
FFPROBE_PATH = shutil.which("ffprobe")

if not FFMPEG_PATH:
    logger.warning("ffmpeg not found. Video processing will fail.")
if not FFPROBE_PATH:
    logger.warning("ffprobe not found. Video processing may fail.")


def download_video(video_id: str, output_dir: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Downloads a YouTube video and extracts its audio.
    
    Args:
        video_id: YouTube video ID
        output_dir: Directory to save files (uses temp dir if None)
        
    Returns:
        Tuple of (video_path, original_audio_path) or (None, None) on failure
    """
    try:
        import yt_dlp
    except ImportError:
        logger.error("yt-dlp is not installed. Run: pip install yt-dlp")
        return None, None
    
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="ytranslate_")
    
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    video_path = os.path.join(output_dir, f"{video_id}.mp4")
    audio_path = os.path.join(output_dir, f"{video_id}_original.mp3")
    
    # Download video with audio
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': video_path,
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
    }
    
    try:
        logger.info(f"Downloading video: {video_id}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # Extract original audio using ffmpeg
        if FFMPEG_PATH and os.path.exists(video_path):
            logger.info("Extracting original audio...")
            import subprocess
            result = subprocess.run([
                FFMPEG_PATH, '-i', video_path,
                '-vn', '-acodec', 'libmp3lame', '-q:a', '2',
                '-y', audio_path
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning(f"Failed to extract audio: {result.stderr}")
                audio_path = None
        else:
            audio_path = None
            
        return video_path, audio_path
        
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None, None


def get_video_duration(video_path: str) -> Optional[float]:
    """
    Gets the duration of a video file in seconds.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Duration in seconds or None on failure
    """
    if not FFPROBE_PATH:
        logger.error("ffprobe not found")
        return None
        
    try:
        import subprocess
        result = subprocess.run([
            FFPROBE_PATH, '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"Error getting video duration: {e}")
    
    return None


def merge_audio_video(
    video_path: str,
    translated_audio_path: str,
    output_path: str,
    original_audio_path: Optional[str] = None,
    original_audio_volume: float = 0.1
) -> Optional[str]:
    """
    Merges translated audio with video, optionally mixing in original audio.
    
    Args:
        video_path: Path to the source video file
        translated_audio_path: Path to the translated audio file
        output_path: Path for the output video file
        original_audio_path: Optional path to original audio for background mixing
        original_audio_volume: Volume level for original audio (0.0 to 1.0)
        
    Returns:
        Output path on success, None on failure
    """
    if not FFMPEG_PATH:
        logger.error("ffmpeg not found. Cannot merge audio and video.")
        return None
    
    try:
        import subprocess
        
        if original_audio_path and os.path.exists(original_audio_path) and original_audio_volume > 0:
            # Mix translated audio with quieted original audio
            logger.info("Merging video with mixed audio (translated + original background)...")
            cmd = [
                FFMPEG_PATH,
                '-i', video_path,
                '-i', translated_audio_path,
                '-i', original_audio_path,
                '-filter_complex', 
                f'[1:a]volume=1.0[translated];'
                f'[2:a]volume={original_audio_volume}[original];'
                f'[translated][original]amix=inputs=2:duration=longest[aout]',
                '-map', '0:v',
                '-map', '[aout]',
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-shortest',
                '-y', output_path
            ]
        else:
            # Replace audio completely
            logger.info("Merging video with translated audio...")
            cmd = [
                FFMPEG_PATH,
                '-i', video_path,
                '-i', translated_audio_path,
                '-map', '0:v',
                '-map', '1:a',
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-shortest',
                '-y', output_path
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"ffmpeg error: {result.stderr}")
            return None
            
        logger.info(f"Video saved to: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error merging audio and video: {e}")
        return None


def cleanup_temp_files(*paths: str) -> None:
    """
    Safely removes temporary files.
    
    Args:
        *paths: File paths to remove
    """
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
                logger.debug(f"Removed temp file: {path}")
            except Exception as e:
                logger.warning(f"Failed to remove temp file {path}: {e}")


def cleanup_temp_dir(dir_path: str) -> None:
    """
    Safely removes a temporary directory and its contents.
    
    Args:
        dir_path: Directory path to remove
    """
    if dir_path and os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
            logger.debug(f"Removed temp directory: {dir_path}")
        except Exception as e:
            logger.warning(f"Failed to remove temp directory {dir_path}: {e}")

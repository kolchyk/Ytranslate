import os
import io
import shutil
import sys

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
    print("Warning: ffmpeg not found. Audio processing may fail.")
if not FFPROBE_PATH:
    print("Warning: ffprobe not found. Audio processing may fail.")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_audio(text, voice="alloy", model="gpt-4o-mini-tts"):
    """
    Generates audio from text using OpenAI TTS.
    Returns an AudioSegment object.
    """
    if not text:
        return None
    
    try:
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text
        )
        
        # Read the response content into a byte stream
        audio_data = io.BytesIO(response.content)
        return AudioSegment.from_file(audio_data, format="mp3")
    except Exception as e:
        print(f"Error during TTS generation: {e}")
        return None

def create_full_audio(translated_chunks, output_path="output.mp3"):
    """
    Creates a full audio file from translated chunks.
    Handles timing by adding silence between chunks.
    """
    if not translated_chunks:
        return None
    
    full_audio = AudioSegment.silent(duration=0)
    current_time_ms = 0
    
    for chunk in translated_chunks:
        start_time_ms = int(chunk['start'] * 1000)
        
        # Add silence if there's a gap between the current time and the next chunk
        if start_time_ms > current_time_ms:
            silence_duration = start_time_ms - current_time_ms
            full_audio += AudioSegment.silent(duration=silence_duration)
            current_time_ms = start_time_ms
            
        chunk_audio = generate_audio(chunk['text'])
        if chunk_audio:
            full_audio += chunk_audio
            current_time_ms += len(chunk_audio)
            
    full_audio.export(output_path, format="mp3")
    return output_path

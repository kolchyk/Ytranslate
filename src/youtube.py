import re
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

def extract_video_id(url):
    """
    Extracts the video ID from a YouTube URL.
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

def get_transcript(video_id, languages=['en', 'ru', 'uk']):
    """
    Fetches the transcript for a given video ID.
    Returns a list of transcript segments or None if not found.
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to find a transcript in requested languages
        try:
            transcript = transcript_list.find_transcript(languages)
            return transcript.fetch()
        except NoTranscriptFound:
            # Fallback: just get any available transcript (e.g. auto-generated)
            # and let the translation service handle it if it's not in the desired language
            transcript = transcript_list.find_generated_transcript(['en'])
            return transcript.fetch()
            
    except (TranscriptsDisabled, NoTranscriptFound, Exception) as e:
        print(f"Error fetching transcript: {e}")
        return None

def format_transcript_for_translation(transcript):
    """
    Groups transcript segments to avoid too many small requests to the translator.
    """
    if not transcript:
        return []
    
    # Simple grouping logic: combine segments into chunks of ~1000 characters
    chunks = []
    current_chunk = []
    current_length = 0
    
    for segment in transcript:
        text = segment['text']
        if current_length + len(text) > 1000:
            chunks.append(current_chunk)
            current_chunk = [segment]
            current_length = len(text)
        else:
            current_chunk.append(segment)
            current_length += len(text)
            
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

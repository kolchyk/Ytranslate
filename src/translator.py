import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def translate_text(text, target_language="ru"):
    """
    Translates text to the target language using OpenAI GPT.
    """
    if not text:
        return ""
    
    language_map = {
        "ru": "Russian",
        "uk": "Ukrainian"
    }
    
    target_lang_full = language_map.get(target_language, "Russian")
    
    prompt = f"Translate the following text from a YouTube video transcript into {target_lang_full}. " \
             f"The translation should be natural-sounding for voice-over, simplified if necessary, " \
             f"and maintain the original meaning. Only return the translated text.\n\nText:\n{text}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # or gpt-4
            messages=[
                {"role": "system", "content": "You are a professional translator specializing in video dubbing and subtitles."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error during translation: {e}")
        return text # Fallback to original text

def translate_transcript_chunks(chunks, target_language="ru"):
    """
    Translates a list of transcript chunks.
    """
    translated_chunks = []
    
    for chunk in chunks:
        # Combine all text in the chunk for translation
        combined_text = "\n".join([segment['text'] for segment in chunk])
        translated_text = translate_text(combined_text, target_language)
        
        # Split translated text back into segments (best effort)
        # Note: This is tricky since GPT might not return the same number of lines.
        # A more robust way would be to ask GPT to return JSON with IDs.
        # For simplicity, we'll just use the translated text as a single block for that chunk's timing.
        
        # We'll return the first segment's start time for the whole chunk for TTS purposes
        translated_chunks.append({
            'start': chunk[0]['start'],
            'text': translated_text
        })
        
    return translated_chunks

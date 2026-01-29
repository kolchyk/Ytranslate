import streamlit as st
import os
import tempfile
from src.youtube import extract_video_id, get_transcript, format_transcript_for_translation
from src.translator import translate_transcript_chunks
from src.tts import create_full_audio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

st.set_page_config(page_title="YTranslate - YouTube Video Translator", page_icon="🎥")

def main():
    st.title("🎥 YTranslate")
    st.subheader("Перевод и озвучка YouTube видео")
    
    # Check for API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("Ошибка: OPENAI_API_KEY не найден в переменных окружения.")
        st.info("Пожалуйста, добавьте свой OpenAI API ключ в файл .env или настройки Heroku.")
        return

    # User Input
    video_url = st.text_input("Введите URL YouTube видео:", placeholder="https://www.youtube.com/watch?v=...")
    
    target_language = st.selectbox(
        "Выберите язык перевода:",
        options=["ru", "uk"],
        format_func=lambda x: "Русский" if x == "ru" else "Украинский"
    )
    
    if st.button("Перевести и озвучить", type="primary"):
        if not video_url:
            st.warning("Пожалуйста, введите URL видео.")
            return
            
        video_id = extract_video_id(video_url)
        if not video_id:
            st.error("Неверный формат URL YouTube.")
            return
            
        process_video(video_id, target_language)

def process_video(video_id, target_language):
    try:
        with st.status("Обработка видео...", expanded=True) as status:
            # 1. Get Transcript
            st.write("Получение субтитров...")
            transcript = get_transcript(video_id)
            if not transcript:
                st.error("Для этого видео субтитры недоступны.")
                status.update(label="Ошибка!", state="error")
                return
            
            # 2. Format Transcript
            st.write("Подготовка текста...")
            chunks = format_transcript_for_translation(transcript)
            
            # 3. Translate
            st.write(f"Перевод на {'русский' if target_language == 'ru' else 'украинский'} язык...")
            translated_chunks = translate_transcript_chunks(chunks, target_language)
            
            # 4. TTS
            st.write("Генерация озвучки (OpenAI TTS)...")
            
            # Use a temporary file for the output audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                output_path = tmp_file.name
                
            create_full_audio(translated_chunks, output_path)
            
            status.update(label="Готово!", state="complete", expanded=False)
        
        # Display Results
        st.success("Перевод завершен!")
        
        # Audio Player
        with open(output_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format="audio/mp3")
            
        # Download Button
        st.download_button(
            label="Скачать MP3",
            data=audio_bytes,
            file_name=f"translated_audio_{video_id}.mp3",
            mime="audio/mp3"
        )
        
        # Cleanup
        os.unlink(output_path)
        
    except Exception as e:
        st.error(f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    main()

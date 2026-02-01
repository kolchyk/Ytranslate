"""
streamlit run app.py

YTranslate - YouTube Video & PDF Article Translator
Streamlit web application for translating and dubbing YouTube videos and PDF articles.
"""
import streamlit as st
import os
import sys
import tempfile
import logging
from contextlib import contextmanager
from typing import Optional, Tuple, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

# Add Heroku apt binaries to PATH before importing modules that check for them
heroku_apt_path = os.path.join(os.getcwd(), ".apt", "usr", "bin")
if os.path.exists(heroku_apt_path):
    os.environ["PATH"] = heroku_apt_path + os.pathsep + os.environ["PATH"]

from src.youtube import extract_video_id, get_transcript, format_transcript_for_translation
from src.translator import translate_transcript_chunks, translate_article_chunks
from src.tts import create_full_audio, create_audio_for_video, is_ffmpeg_available, get_ffmpeg_installation_instructions
from src.video import download_video, merge_audio_video, get_video_duration, cleanup_temp_dir
from src.deepl_translator import translate_pdf_with_deepl
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="YTranslate - Translator & Dubber", page_icon="🎥")


@contextmanager
def temp_directory():
    """Context manager for temporary directory with automatic cleanup."""
    temp_dir = tempfile.mkdtemp(prefix="ytranslate_")
    try:
        yield temp_dir
    finally:
        cleanup_temp_dir(temp_dir)


def main():
    st.title("🎥 YTranslate")
    
    # Check for API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("Ошибка: OPENAI_API_KEY не найден в переменных окружения.")
        st.info("Пожалуйста, добавьте свой OpenAI API ключ в файл .env или настройки Heroku.")
        return
    
    # Check for ffmpeg (skip warning on Heroku where it's installed via Aptfile)
    is_heroku = os.getenv("DYNO") is not None or os.getenv("HEROKU_APP_NAME") is not None
    heroku_apt_ffmpeg = os.path.join(os.getcwd(), ".apt", "usr", "bin", "ffmpeg")
    is_heroku_with_apt = is_heroku and os.path.exists(heroku_apt_ffmpeg)
    
    if not is_ffmpeg_available() and not is_heroku_with_apt:
        st.warning("⚠️ **ffmpeg не найден!**")
        with st.expander("Как установить ffmpeg", expanded=True):
            st.markdown(get_ffmpeg_installation_instructions())
        st.info("💡 Вы можете продолжить, но обработка аудио может завершиться ошибкой.")

    tab_yt, tab_pdf = st.tabs(["📺 YouTube видео", "📄 PDF статьи"])
    
    with tab_yt:
        youtube_tab()
        
    with tab_pdf:
        pdf_tab()


def youtube_tab():
    st.subheader("Перевод и озвучка YouTube видео")
    
    # User Input
    video_url = st.text_input(
        "Введите URL YouTube видео:",
        placeholder="https://www.youtube.com/watch?v=...",
        key="yt_url"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        target_language = st.selectbox(
            "Выберите язык перевода:",
            options=["ru", "uk"],
            format_func=lambda x: "Русский" if x == "ru" else "Украинский",
            key="yt_lang"
        )
    
    with col2:
        output_format = st.selectbox(
            "Формат вывода:",
            options=["audio", "video"],
            format_func=lambda x: "Только аудио (MP3)" if x == "audio" else "Видео с озвучкой (MP4)",
            key="yt_format"
        )
    
    # Advanced options
    with st.expander("Расширенные настройки"):
        # YouTube configuration check
        cookies_file = os.getenv("YOUTUBE_COOKIES_PATH", "cookies.txt")
        proxy_env = os.getenv("YOUTUBE_PROXY")
        
        if os.path.exists(cookies_file):
            st.info(f"✅ Файл cookies найден: `{cookies_file}`")
        elif proxy_env:
            proxies = [p.strip() for p in proxy_env.split(",") if p.strip()]
            if len(proxies) > 1:
                st.info(f"✅ Настроено {len(proxies)} прокси для ротации")
            else:
                st.info("✅ Прокси настроен")
        else:
            st.warning(
                "⚠️ **YouTube может блокировать запросы с облачных провайдеров (Heroku, AWS и т.д.)**\n\n"
                "Для решения проблемы:\n"
                "1. **Добавьте файл `cookies.txt`** в корень проекта (рекомендуется)\n"
                "2. **Или установите переменную окружения `YOUTUBE_PROXY`** с адресом прокси-сервера\n"
                "   Пример: `http://user:password@host:port`\n"
                "   Можно указать несколько через запятую для автоматической ротации"
            )

        voice = st.selectbox(
            "Голос озвучки:",
            options=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            index=0,
            key="yt_voice"
        )
        
        if output_format == "video":
            keep_original_audio = st.checkbox(
                "Сохранить оригинальное аудио на фоне",
                value=True,
                help="Оригинальный звук будет приглушен и добавлен на фон",
                key="yt_keep_audio"
            )
            original_volume = st.slider(
                "Громкость оригинального звука:",
                min_value=0.0,
                max_value=0.5,
                value=0.1,
                step=0.05,
                disabled=not keep_original_audio,
                key="yt_vol"
            )
        else:
            keep_original_audio = False
            original_volume = 0.0
    
    if st.button("Перевести и озвучить видео", type="primary", key="yt_btn"):
        if not video_url:
            st.warning("Пожалуйста, введите URL видео.")
            return
            
        video_id = extract_video_id(video_url)
        if not video_id:
            st.error("Неверный формат URL YouTube.")
            return
        
        process_video(
            video_id=video_id,
            target_language=target_language,
            output_format=output_format,
            voice=voice,
            keep_original_audio=keep_original_audio,
            original_volume=original_volume
        )


def pdf_tab():
    st.subheader("Перевод PDF статей")
    
    uploaded_file = st.file_uploader("Выберите PDF файл (на английском):", type="pdf")
    
    target_language = st.selectbox(
        "Выберите язык перевода:",
        options=["ru", "uk"],
        format_func=lambda x: "Русский" if x == "ru" else "Украинский",
        key="pdf_lang"
    )
    
    if st.button("Перевести статью", type="primary", key="pdf_btn"):
        if not uploaded_file:
            st.warning("Пожалуйста, загрузите PDF файл.")
            return
            
        process_pdf_article_ui(uploaded_file, target_language)


def process_video(
    video_id: str,
    target_language: str,
    output_format: str,
    voice: str = "alloy",
    keep_original_audio: bool = False,
    original_volume: float = 0.1
):
    """
    Process a YouTube video: extract transcript, translate, generate TTS, and optionally merge with video.
    """
    try:
        with temp_directory() as temp_dir:
            with st.status("Обработка видео...", expanded=True) as status:
                
                # 1. Get Transcript
                st.write("📝 Получение субтитров...")
                transcript = get_transcript(video_id)
                if not transcript:
                    st.error("Для этого видео субтитры недоступны.")
                    status.update(label="Ошибка!", state="error")
                    return
                
                # 2. Format Transcript
                st.write("📋 Подготовка текста...")
                chunks = format_transcript_for_translation(transcript)
                
                # 3 & 4. Translate and Download in parallel
                lang_name = 'русский' if target_language == 'ru' else 'украинский'
                st.write(f"🌐 Перевод на {lang_name} и подготовка медиа...")
                
                with ThreadPoolExecutor(max_workers=2) as executor:
                    # Start translation
                    translation_future = executor.submit(translate_transcript_chunks, chunks, target_language)
                    
                    # Start download if needed
                    download_future = None
                    if output_format == "video":
                        download_future = executor.submit(download_video, video_id, temp_dir)
                    
                    # Wait for results
                    translated_chunks = translation_future.result()
                    
                    video_path = None
                    original_audio_path = None
                    if download_future:
                        video_path, original_audio_path = download_future.result()
                
                if output_format == "video" and not video_path:
                    st.error("Не удалось скачать видео. Попробуйте только аудио.")
                    status.update(label="Ошибка!", state="error")
                    return
                
                # 5. TTS
                st.write("🔊 Генерация озвучки (OpenAI TTS)...")
                audio_path = os.path.join(temp_dir, f"translated_{video_id}.mp3")
                
                if output_format == "video" and video_path:
                    video_duration_ms = int((get_video_duration(video_path) or 0) * 1000)
                    create_audio_for_video(translated_chunks, video_duration_ms, audio_path, voice)
                else:
                    create_full_audio(translated_chunks, audio_path, voice)
                
                if not os.path.exists(audio_path):
                    st.error("Не удалось сгенерировать аудио.")
                    status.update(label="Ошибка!", state="error")
                    return
                
                # 6. Merge video if needed
                if output_format == "video" and video_path:
                    st.write("🎬 Наложение озвучки на видео...")
                    output_video_path = os.path.join(temp_dir, f"output_{video_id}.mp4")
                    
                    result = merge_audio_video(
                        video_path=video_path,
                        translated_audio_path=audio_path,
                        output_path=output_video_path,
                        original_audio_path=original_audio_path if keep_original_audio else None,
                        original_audio_volume=original_volume
                    )
                    
                    if not result:
                        st.error("Не удалось наложить аудио на видео.")
                        status.update(label="Ошибка!", state="error")
                        return
                    
                    output_path = output_video_path
                    output_mime = "video/mp4"
                    output_ext = "mp4"
                else:
                    output_path = audio_path
                    output_mime = "audio/mp3"
                    output_ext = "mp3"
                
                status.update(label="Готово!", state="complete", expanded=False)
            
            # Read file for display and download BEFORE cleanup
            with open(output_path, "rb") as f:
                output_bytes = f.read()
            
            # Store in session state to persist after temp directory cleanup
            session_key = f"media_{video_id}_{output_format}"
            st.session_state[session_key] = {
                'bytes': output_bytes,
                'mime': output_mime,
                'ext': output_ext,
                'filename': f"translated_{video_id}.{output_ext}",
                'chunks': translated_chunks
            }
        
        # Display Results (outside temp_directory context)
        st.success("Перевод завершен!")
        
        # Retrieve from session state
        session_key = f"media_{video_id}_{output_format}"
        if session_key in st.session_state:
            media_data = st.session_state[session_key]
            output_bytes = media_data['bytes']
            output_mime = media_data['mime']
            output_ext = media_data['ext']
            filename = media_data['filename']
            
            # Media Player
            try:
                if output_format == "video":
                    st.video(output_bytes, format="video/mp4")
                else:
                    st.audio(output_bytes, format="audio/mp3")
            except Exception as e:
                # Handle Streamlit media file storage errors gracefully
                logger.warning(f"Error displaying media: {e}")
                st.info("Медиа файл доступен для скачивания ниже.")
            
            # Download Button
            st.download_button(
                label=f"Скачать {output_ext.upper()}",
                data=output_bytes,
                file_name=filename,
                mime=output_mime
            )
            
            # Show translated text
            if 'chunks' in media_data:
                with st.expander("Показать переведенный текст"):
                    for i, chunk in enumerate(media_data['chunks']):
                        st.markdown(f"**[{chunk['start']:.1f}s - {chunk.get('end', 0):.1f}s]**")
                        st.text(chunk['text'])
                        st.divider()
                    
    except Exception as e:
        logger.exception("Error processing video")
        st.error(f"Произошла ошибка: {str(e)}")


def process_pdf_article_ui(uploaded_file, target_language: str):
    """
    UI wrapper for PDF processing using DeepL API.
    """
    try:
        # Check for DeepL API Key
        if not os.getenv("DEEPL_API_KEY"):
            st.error("Ошибка: DEEPL_API_KEY не найден в переменных окружения.")
            return

        # Get original filename without extension
        original_filename = uploaded_file.name
        base_name = os.path.splitext(original_filename)[0]
        
        # Clean filename: remove invalid characters for Windows filesystem
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            base_name = base_name.replace(char, '_')
        
        with temp_directory() as temp_dir:
            with st.status("Перевод PDF статьи через DeepL...", expanded=True) as status:
                
                # 1. Translate PDF using DeepL
                lang_name = 'русский' if target_language == 'ru' else 'украинский'
                st.write(f"🌐 Перевод на {lang_name} (DeepL Document API)...")
                
                try:
                    translated_pdf_bytes = translate_pdf_with_deepl(uploaded_file, target_language)
                except Exception as e:
                    st.error(f"Ошибка DeepL: {str(e)}")
                    status.update(label="Ошибка!", state="error")
                    return
                
                pdf_filename = f"{base_name}_translated.pdf"
                pdf_path = os.path.join(temp_dir, pdf_filename)
                
                with open(pdf_path, "wb") as f:
                    f.write(translated_pdf_bytes)
                
                status.update(label="Готово!", state="complete", expanded=False)
            
            # Store in session state to persist after temp directory cleanup
            session_key = "pdf_article_files"
            st.session_state[session_key] = {
                'pdf_bytes': translated_pdf_bytes,
                'pdf_filename': pdf_filename
            }
        
        # Display Results (outside temp_directory context)
        st.success("Перевод статьи завершен!")
        
        # Retrieve from session state
        session_key = "pdf_article_files"
        if session_key in st.session_state:
            media_data = st.session_state[session_key]
            pdf_bytes = media_data['pdf_bytes']
            
            # Download button
            st.download_button(
                label="📄 Скачать переведенный PDF",
                data=pdf_bytes,
                file_name=media_data['pdf_filename'],
                mime='application/pdf'
            )
                    
    except Exception as e:
        logger.exception("Error processing PDF")
        st.error(f"Произошла ошибка: {str(e)}")


if __name__ == "__main__":
    # Check if running in Streamlit runtime context
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx is None:
            raise RuntimeError("Not running in Streamlit context")
    except (ImportError, RuntimeError):
        print("\n" + "="*60)
        print("ERROR: This is a Streamlit application.")
        print("="*60)
        print("\nPlease run this app using:")
        print("  streamlit run app.py")
        print("\nOr if you're in a virtual environment:")
        print("  .venv\\Scripts\\streamlit.exe run app.py")
        print("\n" + "="*60 + "\n")
        sys.exit(1)
    main()

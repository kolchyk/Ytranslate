# YTranslate - YouTube Video Translator

YouTube video translator and text-to-speech application using OpenAI.

## Setup with uv

This project uses [uv](https://github.com/astral-sh/uv) for fast Python package management.

### Prerequisites

Install `uv` if you haven't already:

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or using pip
pip install uv
```

### Installation

1. **Sync dependencies** (creates virtual environment and installs packages):
   ```bash
   uv sync
   ```

2. **Activate the virtual environment**:
   ```bash
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   
   # Windows (CMD)
   .venv\Scripts\activate.bat
   
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

### Running the Application

```bash
streamlit run app.py
```

### Working around YouTube IP blocks

If you are running this application on a cloud provider (like Heroku, AWS, etc.), YouTube might block your requests. You can work around this by using cookies or a proxy.

#### Using Cookies (Recommended for Cloud)

1. Install the "Get cookies.txt LOCALLY" extension in your browser (Chrome or Firefox).
2. Go to YouTube and log in (if not already).
3. Use the extension to export cookies as `cookies.txt`.
4. Place the `cookies.txt` file in the root directory of this project.
5. Alternatively, set the `YOUTUBE_COOKIES_PATH` environment variable to the path of your cookies file.

#### Using Proxies

Set the `YOUTUBE_PROXY` environment variable to your proxy URL (e.g., `http://user:password@host:port`).

### Common uv Commands

- **Install dependencies**: `uv sync`
- **Add a new package**: `uv add package-name`
- **Remove a package**: `uv remove package-name`
- **Update dependencies**: `uv sync --upgrade`
- **Run a command in the environment**: `uv run streamlit run app.py`
- **Lock dependencies**: `uv lock`

### Alternative: Using requirements.txt

The project also includes `requirements.txt` for compatibility. You can still use pip if needed:

```bash
pip install -r requirements.txt
```

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

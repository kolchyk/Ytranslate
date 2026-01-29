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

**⚠️ Important for OneDrive Users:** If your project is in a OneDrive folder, OneDrive doesn't support hard links used by `uv`. You have two options:

**Option 1: Exclude .venv from OneDrive sync (Easiest)**
1. Run `uv sync` normally (it will fail initially)
2. Right-click the `.venv` folder in File Explorer
3. Select "Always keep on this device" (this prevents OneDrive from syncing it)
4. Run `uv sync` again

**Option 2: Use the workaround script**
```powershell
.\uv-sync.ps1
```
This script creates the virtual environment outside OneDrive (`%LOCALAPPDATA%\uv\venvs\YTranslate`) and creates a symlink in your project.

1. **Sync dependencies** (creates virtual environment and installs packages):
   
   **For OneDrive users:**
   ```powershell
   # Option 1: Exclude .venv from sync (recommended)
   uv sync
   # Then right-click .venv → "Always keep on this device"
   
   # Option 2: Use workaround script
   .\uv-sync.ps1
   ```
   
   **For non-OneDrive users:**
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

Set the `YOUTUBE_PROXY` environment variable to your proxy URL. The application supports multiple proxies (comma-separated) and will automatically rotate through them if one fails.

**Single proxy:**
```bash
export YOUTUBE_PROXY="http://user:password@host:port"
```

**Multiple proxies (for rotation):**
```bash
export YOUTUBE_PROXY="http://proxy1:port,http://proxy2:port,http://proxy3:port"
```

**For Heroku deployment:**

1. Set the proxy via Heroku CLI:
   ```bash
   heroku config:set YOUTUBE_PROXY="http://user:password@host:port"
   ```

2. Or set it in the Heroku Dashboard:
   - Go to your app → Settings → Config Vars
   - Add `YOUTUBE_PROXY` with your proxy URL

3. **Important**: Make sure your proxy supports HTTPS connections to YouTube. SOCKS5 proxies are also supported (format: `socks5://user:pass@host:port`).

**Proxy format examples:**
- HTTP proxy: `http://username:password@proxy.example.com:8080`
- HTTPS proxy: `https://username:password@proxy.example.com:8080`
- SOCKS5 proxy: `socks5://username:password@proxy.example.com:1080`
- No authentication: `http://proxy.example.com:8080`

**Where to get proxy servers:**

1. **Free proxy lists** (not recommended for production):
   - [FreeProxyList](https://free-proxy-list.net/)
   - [ProxyScrape](https://proxyscrape.com/)
   - ⚠️ Free proxies are often slow, unreliable, and may be blocked by YouTube

2. **Paid proxy services** (recommended):
   - **Residential proxies**: 
     - [Bright Data](https://brightdata.com/) (formerly Luminati)
     - [Smartproxy](https://smartproxy.com/)
     - [Oxylabs](https://oxylabs.io/)
   - **Datacenter proxies**:
     - [ProxyMesh](https://proxymesh.com/)
     - [ProxyRack](https://www.proxyrack.com/)
   - **SOCKS5 proxies**:
     - [SOCKS5 Proxies](https://socks5proxies.net/)

3. **Self-hosted proxy** (advanced):
   - Set up your own proxy server using Squid, Shadowsocks, or similar
   - Use a VPS with a non-cloud IP address

**Important notes:**
- YouTube often blocks datacenter IPs (AWS, Google Cloud, Azure, etc.)
- Residential proxies work best but are more expensive
- Free proxies are unreliable and may expose your data
- For Heroku, consider using cookies instead (see below) - it's simpler and often more reliable

**Alternative: Using Cookies (Easier and Free)**

Instead of proxies, you can use YouTube cookies which is often simpler:

1. Install browser extension "Get cookies.txt LOCALLY" (Chrome/Firefox)
2. Log in to YouTube in your browser
3. Export cookies as `cookies.txt` using the extension
4. Upload `cookies.txt` to your Heroku app root directory
5. The app will automatically use cookies for authentication

This method is free and often more reliable than free proxies, though cookies expire and need to be refreshed periodically.

**Note**: If you don't set a proxy and YouTube blocks your requests, you'll see error messages in the logs. The application will automatically retry with different proxies if multiple are configured.

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

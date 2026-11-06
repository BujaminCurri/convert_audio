# Quiet Transcribe

Upload an audio file, transcribe it with Google Gemini, read the text, and download it as a PDF.
Supports English, Albanian, Macedonian and Arabic. No database. Nothing is stored on the server.

## How it works

1. **Home** (`/`): short description and a button to start.
2. **Transcribe** (`/transcribe/`): choose an audio file, enter your Gemini API key, edit the prompt if needed.
   The page sends the form to `/api/transcribe` and waits for the result.
3. **Result** (`/result/`): shows the transcript. The button posts the text to `/generate_pdf/`, which returns a PDF download.

The API key is used for a single request and is never saved. The transcript is kept only in the browser (`sessionStorage`).

## Project structure

```
manage.py
render.yaml
requirements.txt
fonts/
  DejaVuSans.ttf
  DejaVuSans-Bold.ttf
  NotoNaskhArabic-Regular.ttf
static/
  style.css
templates/
  home.html
  transcribe.html
  result.html
yourproject/
  settings.py, urls.py, wsgi.py
app/
  views.py
```

## requirements.txt

```
django
gunicorn
whitenoise
google-genai
reportlab
arabic-reshaper
python-bidi
```

## Run locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Settings needed for Render

```python
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-key")
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = ["https://*.onrender.com"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # right after SecurityMiddleware
    # ...the rest
]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
```

## Deploy on Render

1. Push the project to GitHub, including the `fonts/` folder.
2. In Render choose **New > Blueprint** and select the repository. Render reads `render.yaml`.
3. Edit `startCommand` in `render.yaml` so `yourproject` matches your project folder name.
4. Deploy. The app is available at `https://quiet-transcribe.onrender.com` (or the name you chose).

## Notes

- **File size:** audio is sent to Gemini inline, so keep files under about 20 MB. Larger files need the Gemini Files API.
- **Timeouts:** gunicorn is set to 300 seconds. Very long recordings may need more.
- **Free plan:** the service sleeps after inactivity, so the first visit can take around a minute to wake up.
- **Supported audio:** mp3, wav, m4a, aac, flac, ogg, opus, webm.
- **Get a Gemini API key:** https://aistudio.google.com/apikey

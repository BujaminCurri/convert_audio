from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from google import genai
from google.genai import types
from django.http import HttpResponse
import os
from django.conf import settings
from fpdf import FPDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.utils.html import escape
import re
import arabic_reshaper
from bidi.algorithm import get_display

def home(request):
    return render(request, 'home.html')


def transcribe(request):
    return render(request, 'transcribe.html')

def generate_pdf(request):
    return render(request, 'generate_pdf.html')

MIME_MAP = {
    'mp3': 'audio/mpeg',
    'wav': 'audio/wav',
    'm4a': 'audio/mp4',
    'aac': 'audio/aac',
    'flac': 'audio/flac',
    'ogg': 'audio/ogg',
    'opus': 'audio/ogg',
    'webm': 'audio/webm',
}

@require_POST
def api_transcribe(request):
    api_key = (request.POST.get('api_key') or '').strip()
    prompt = (request.POST.get('prompt') or '').strip()
    audio = request.FILES.get('audio')

    if not audio:
        return JsonResponse({'error': 'No audio file received.'}, status=400)
    if not api_key:
        return JsonResponse({'error': 'Please enter your Gemini API key.'}, status=400)
    if not prompt:
        prompt = 'Transcribe this audio word for word. Return only the transcript.'

    ext = audio.name.rsplit('.', 1)[-1].lower() if '.' in audio.name else ''
    mime_type = MIME_MAP.get(ext) or audio.content_type
    if not mime_type or not mime_type.startswith('audio/'):
        return JsonResponse({'error': f'Unsupported file type: .{ext}'}, status=400)

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                prompt,
                types.Part.from_bytes(data=audio.read(), mime_type=mime_type),
            ],
        )
        text = (response.text or '').strip()
    except Exception as e:
        print('Gemini error:', repr(e))          # full detail in your terminal / Render logs
        return JsonResponse({'error': f'Gemini error: {e}'}, status=502)

    if not text:
        return JsonResponse({'error': 'Gemini returned no text for this file.'}, status=502)

    return JsonResponse({'text': text})


FONT_DIR = os.path.join(settings.BASE_DIR, 'fonts')

# Register once. Helvetica has no Cyrillic, so DejaVu covers English, Albanian and Macedonian.
for name, file in [
    ('DejaVuSans', 'DejaVuSans.ttf'),
    ('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'),
    ('NotoNaskhArabic', 'NotoNaskhArabic-Regular.ttf'),   # skip if you already register it elsewhere
]:
    try:
        pdfmetrics.getFont(name)
    except KeyError:
        pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, file)))

FONT_DIR = os.path.join(settings.BASE_DIR, "static", "fonts")
ARABIC_FONT_PATH = os.path.join(FONT_DIR, "NotoNaskhArabic-Regular.ttf")

pdfmetrics.registerFont(TTFont("NotoNaskhArabic", ARABIC_FONT_PATH))

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
LATIN_RE = re.compile(r"[A-Za-zÀ-ž]")
ARABIC_CHUNK_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\s،؛؟ـًٌٍَُِّْٰ]*"
)

def prepare_mixed_pdf_text(text):
    text = text or ""
    parts = []
    last_end = 0

    for match in ARABIC_CHUNK_RE.finditer(text):
        start, end = match.span()

        if start > last_end:
            parts.append(escape(text[last_end:start]))

        arabic_part = match.group()
        shaped_arabic = prepare_arabic_text(arabic_part)

        parts.append(
            f'<font name="NotoNaskhArabic">{escape(shaped_arabic)}</font>'
        )

        last_end = end

    if last_end < len(text):
        parts.append(escape(text[last_end:]))

    return "".join(parts)

def contains_arabic(text):
    return bool(ARABIC_RE.search(text or ""))


def contains_latin(text):
    return bool(LATIN_RE.search(text or ""))


def prepare_arabic_text(text):
    reshaped_text = arabic_reshaper.reshape(text or "")
    return get_display(reshaped_text)

def is_arabic_line(text):
    text = text or ""
    return contains_arabic(text) and not contains_latin(text)

@require_POST
def make_pdf(request):
    text = (request.POST.get('text') or '').strip()
    if not text:
        return HttpResponse('No text to convert.', status=400)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="transcript.pdf"'

    doc = SimpleDocTemplate(
        response, pagesize=A4,
        leftMargin=58, rightMargin=58, topMargin=62, bottomMargin=58,
        title='Transcript',
    )

    styles = getSampleStyleSheet()
    ink = colors.HexColor('#17201d')
    muted = colors.HexColor('#667085')
    rule = colors.HexColor('#d7e7e4')
    body_color = colors.HexColor('#242927')

    title_style = ParagraphStyle(
        'Title', parent=styles['Heading2'], fontName='DejaVuSans-Bold',
        fontSize=21, leading=27, textColor=ink, spaceAfter=8)

    transcript_style = ParagraphStyle(
        'Transcript', parent=styles['BodyText'], fontName='DejaVuSans',
        fontSize=11, leading=16, firstLineIndent=22,
        alignment=TA_JUSTIFY, textColor=body_color, spaceAfter=4)

    arabic_style = ParagraphStyle(
        'ArabicTranscript', parent=styles['BodyText'], fontName='NotoNaskhArabic',
        fontSize=12, leading=18, firstLineIndent=22,
        alignment=TA_JUSTIFY, textColor=body_color, spaceAfter=4)

    mixed_style = ParagraphStyle(
        'MixedTranscript', parent=styles['BodyText'], fontName='DejaVuSans',
        fontSize=11, leading=18, alignment=TA_JUSTIFY,
        textColor=body_color, spaceAfter=5)

    story = [
        Paragraph('Transcript', title_style),
        Spacer(1, 6),
        HRFlowable(width='100%', thickness=0.8, color=rule),
        Spacer(1, 18),
    ]

    for line in text.replace('\r\n', '\n').split('\n'):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue

        if is_arabic_line(line):
            story.append(Paragraph(escape(prepare_arabic_text(line)), arabic_style))
        elif contains_arabic(line):
            story.append(Paragraph(prepare_mixed_pdf_text(line), mixed_style))
        else:
            story.append(Paragraph(escape(line), transcript_style))

    doc.build(story)
    return response
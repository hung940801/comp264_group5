from chalice import Chalice, Response, CORSConfig
from chalicelib import storage_service
from chalicelib import recognition_service
from chalicelib import translation_service

import base64
import json
import boto3

from docx import Document
import io
import time
import fitz  # PyMuPDF
import docx

import os, glob
import calendar
import re

#####
# chalice app configuration
#####
app = Chalice(app_name='Capabilities')
app.debug = True

cors_config = CORSConfig(
    allow_origin='*',
    allow_headers=['Content-Type', 'X-Requested-With', 'Authorization'],
    max_age=600,
    expose_headers=['Content-Disposition']
)

#####
# services initialization
#####
storage_location = 'contentcen301269827.aws.ai'
storage_service = storage_service.StorageService(storage_location)
recognition_service = recognition_service.RecognitionService(storage_service)
translation_service = translation_service.TranslationService()

textract_client = boto3.client('textract')
region_name = 'us-east-1'

#####
# RESTful endpoints
#####
@app.route('/')  # This will serve as your home page
def index_page():
    # Define the path to Website directory where index.html is located
    project_root = os.path.dirname(__file__)
    website_path = os.path.join(project_root, '..', 'Website', 'index.html')
    
    # Read the contents of the index.html file
    with open(website_path, 'r', encoding='utf-8') as html_file:
        html_content = html_file.read()
    
    # Return the contents of the HTML file as the response
    return Response(body=html_content, status_code=200, headers={'Content-Type': 'text/html; charset=utf-8'})

# handle CORS problem
@app.route('/scripts.js', methods=['GET'])
def serve_js():
    try:
        # Go to `Website` directory
        scripts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Website', 'scripts.js'))
        with open(scripts_path, 'rb') as file:
            return Response(body=file.read(), status_code=200, headers={'Content-Type': 'text/javascript'})
    except Exception as e:
        # Log the exception to Chalice logs for debugging
        app.log.error(f"Failed to serve scripts.js: {e}")
        # Return a more descriptive error for debugging purposes
        return Response(body=f'Failed to load scripts.js: {e}', status_code=500)

# handle CORS problem
@app.route('/audio/{file_name}', methods=['GET'], cors=cors_config)
def serve_audio(file_name):
    # Check if the file_name has a valid MP3 extension
    if not file_name.endswith('.mp3'):
        return Response(body='Invalid file type', status_code=400)

    # Construct the full file path
    audio_file_path = os.path.join(os.path.dirname(__file__), '..', 'Website', file_name)

    # Check if the file exists
    if not os.path.exists(audio_file_path):
        return Response(body='File not found', status_code=404)

    try:
        # Open the file and return it as a response
        with open(audio_file_path, 'rb') as audio:
            return Response(
                body=audio.read(),
                status_code=200,
                headers={'Content-Type': 'audio/mpeg'}
            )
    except IOError as e:
        return Response(body=str(e), status_code=500)

# add a new API endpoint
@app.route('/files', methods = ['POST'], cors=cors_config)
def upload_image():
    """processes file upload and saves file to storage service"""

    request_data = json.loads(app.current_request.raw_body)
    file_name = request_data['filename']
    file_bytes = base64.b64decode(request_data['filebytes'])
    
    if file_name.endswith('.pdf'):
        text = extract_text_pdf(file_bytes)
    elif file_name.endswith('.docx'):
        text = extract_text_docx(file_bytes)
    elif file_name.endswith('.txt'):
        text = extract_text_txt(file_bytes)
    elif file_name.endswith('.jpg') or file_name.endswith('.jpeg') or file_name.endswith('.png'):
        image_info = storage_service.upload_file(file_bytes, file_name)
        text_lines = recognition_service.detect_text(image_info['fileId'])
        text = ""
        for t in text_lines:
            text += t['text']
        # clean up text if html character existed
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', text)
    else:
        return {'error': 'Unsupported file type'}
    
    return {'text': text}

def extract_text_pdf(file_bytes):
    text = ""
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def extract_text_docx(file_bytes):
    file_stream = io.BytesIO(file_bytes)
    document = docx.Document(file_stream)
    return "\n".join([paragraph.text for paragraph in document.paragraphs])

def extract_text_txt(file_bytes):
    return file_bytes.decode('utf-8')

@app.route('/files/translate-text', methods = ['POST'], cors=cors_config)
def translate_image_text():
    """detects then translates text in the specified image"""
    request_data = json.loads(app.current_request.raw_body)
    from_lang = request_data['fromLang']
    to_lang = request_data['toLang']

    text = request_data['text']

    translated_lines = []
    translated_line = translation_service.translate_text(text, from_lang, to_lang)
    translated_lines.append({
        'text': text,
        'translation': translated_line,
    })

    return translated_lines

# add a new API endpoint
@app.route('/files/translate-text-to-speech', methods = ['POST'], cors=cors_config)
def text_to_speech(language_code='en-US'):
    # Create a Polly client
    polly_client = boto3.client('polly')

    request_data = json.loads(app.current_request.raw_body)
    text = request_data['translations']

    # Call Polly to synthesize speech
    response = polly_client.synthesize_speech(
        Text=text,
        OutputFormat='mp3',
        VoiceId='Joanna',  # Choose a voice ID based on your preferences and supported languages
        LanguageCode=language_code
    )

    for filename in glob.glob("../Website/output*"):
        os.remove(filename) 

    current_GMT = time.gmtime()
    ts = calendar.timegm(current_GMT)

    # Save the audio stream to a file
    audio_file = f'output_{ts}.mp3'
    with open('../Website/' + audio_file, 'wb') as file:
        file.write(response['AudioStream'].read())
    audio_file_path = audio_file
    result = {"audio_file_path": audio_file_path}
    return result
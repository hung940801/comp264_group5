from chalice import Chalice, Response
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

#####
# services initialization
#####
storage_location = 'contentcen301273830.aws.ai'
storage_service = storage_service.StorageService(storage_location)
recognition_service = recognition_service.RecognitionService(storage_service)
translation_service = translation_service.TranslationService()

textract_client = boto3.client('textract')
region_name = 'us-east-1'

#####
# RESTful endpoints
#####
@app.route('/files', methods = ['POST'], cors = True)
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
    elif file_name.endswith('.jpg') or file_name.endswith('.png'):
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

@app.route('/files/translate-text', methods = ['POST'], cors = True)
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
@app.route('/files/translate-text-to-speech', methods = ['POST'], cors = True)
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
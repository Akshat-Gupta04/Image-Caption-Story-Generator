
from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer, MarianMTModel, MarianTokenizer
import torch
from PIL import Image
import os
import time
import json
from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
import uuid
from threading import Thread

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global variable to track processing status
processing_status = {}

# Initialize image captioning model
model = VisionEncoderDecoderModel.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
feature_extractor = ViTImageProcessor.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
tokenizer = AutoTokenizer.from_pretrained("nlpconnect/vit-gpt2-image-captioning")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Initialize OpenAI model
llm = ChatOpenAI(temperature=0.7)

# Initialize translation model (English to Hindi)
print("Loading translation model...")
# Using Helsinki-NLP's Marian model specifically for English to Hindi translation
translation_model_name = "Helsinki-NLP/opus-mt-en-hi"
translation_tokenizer = MarianTokenizer.from_pretrained(translation_model_name)
translation_model = MarianMTModel.from_pretrained(translation_model_name)
translation_model.to(device)
print("Translation model loaded!")

# Image captioning parameters
max_length = 16
num_beams = 4
gen_kwargs = {"max_length": max_length, "num_beams": num_beams}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def predict_step(image_paths):
    """Generate captions for a list of image paths"""
    images = []
    for image_path in image_paths:
        i_image = Image.open(image_path)
        if i_image.mode != "RGB":
            i_image = i_image.convert(mode="RGB")
        images.append(i_image)

    pixel_values = feature_extractor(images=images, return_tensors="pt").pixel_values
    pixel_values = pixel_values.to(device)

    output_ids = model.generate(pixel_values, **gen_kwargs)

    preds = tokenizer.batch_decode(output_ids, skip_special_tokens=True)
    preds = [pred.strip() for pred in preds]
    return preds

def translate_text(text):
    """Translate text from English to Hindi using Helsinki-NLP's Marian model"""
    # Split text into paragraphs for better translation
    paragraphs = text.split('\n\n')
    translated_paragraphs = []

    for paragraph in paragraphs:
        if not paragraph.strip():
            translated_paragraphs.append('')
            continue

        # Prepare the text for translation
        formatted_text = paragraph.replace('\n', ' ').strip()

        # Tokenize
        inputs = translation_tokenizer(formatted_text, return_tensors="pt", padding=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Translate
        with torch.no_grad():
            output_ids = translation_model.generate(
                **inputs,
                max_length=512,
                num_beams=4,
                length_penalty=1.2,  # Encourage longer outputs
                no_repeat_ngram_size=3
            )

        # Decode
        translated_text = translation_tokenizer.decode(output_ids[0], skip_special_tokens=True)
        translated_paragraphs.append(translated_text)

    # Join paragraphs with double newlines
    result = '\n\n'.join(translated_paragraphs)

    return result

def generate_story(captions):
    """Generate a story based on image captions using LangChain and OpenAI"""
    # Create a prompt template
    template = """
    You are a creative storyteller. Based on the following image captions, create a coherent and engaging story
    that connects all the images in a meaningful way. The story should be 3-4 paragraphs long.

    Image captions:
    {captions}

    Story:
    """

    prompt = PromptTemplate(
        input_variables=["captions"],
        template=template,
    )

    # Create the LLMChain
    story_chain = LLMChain(llm=llm, prompt=prompt)

    # Format the captions as a numbered list
    formatted_captions = "\n".join([f"{i+1}. {caption}" for i, caption in enumerate(captions)])

    # Generate the story
    story = story_chain.invoke({"captions": formatted_captions})

    return story["text"].strip()

@app.route('/', methods=['GET'])
def index():
    """Home page with image upload form"""
    return render_template('index.html')

def process_images_background(session_id, saved_paths):
    """Process images in background thread and update status"""
    global processing_status

    try:
        # Update status to indicate captioning started
        processing_status[session_id] = {
            'status': 'processing',
            'step': 'captioning',
            'progress': 25,
            'message': 'Generating captions for images...'
        }
        time.sleep(1)  # Simulate processing time

        # Generate captions for the images
        captions = predict_step(saved_paths)

        # Update status to indicate story generation started
        processing_status[session_id] = {
            'status': 'processing',
            'step': 'story',
            'progress': 75,
            'message': 'Creating story from captions...'
        }
        time.sleep(1)  # Simulate processing time

        # Generate a story based on the captions
        story = generate_story(captions)

        # Store results in session data
        processing_status[session_id] = {
            'status': 'complete',
            'progress': 100,
            'message': 'Processing complete!',
            'data': {
                'captions': captions,
                'image_paths': [os.path.join(session_id, os.path.basename(path)) for path in saved_paths],
                'story': story
            }
        }
    except Exception as e:
        # Handle any errors
        processing_status[session_id] = {
            'status': 'error',
            'message': f'Error processing images: {str(e)}'
        }

@app.route('/upload', methods=['POST'])
def upload_images():
    """Handle image uploads, generate captions, and create a story"""
    if 'images' not in request.files:
        flash('No file part')
        return redirect(request.url)

    files = request.files.getlist('images')

    if not files or files[0].filename == '':
        flash('No selected files')
        return redirect(request.url)

    # Check if we have between 2-5 images
    if len(files) < 2 or len(files) > 5:
        flash('Please upload between 2 and 5 images')
        return redirect(request.url)

    # Create a unique session ID for this upload
    session_id = str(uuid.uuid4())
    session['processing_id'] = session_id
    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    os.makedirs(session_folder, exist_ok=True)

    # Initialize processing status
    processing_status[session_id] = {
        'status': 'uploading',
        'progress': 10,
        'message': 'Uploading images...'
    }

    # Save uploaded files
    saved_paths = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(session_folder, filename)
            file.save(file_path)
            saved_paths.append(file_path)

    # Start background processing
    thread = Thread(target=process_images_background, args=(session_id, saved_paths))
    thread.daemon = True
    thread.start()

    return redirect(url_for('processing'))

@app.route('/processing')
def processing():
    """Show processing page with real-time updates"""
    if 'processing_id' not in session:
        flash('No processing task found')
        return redirect(url_for('index'))

    return render_template('processing.html')

@app.route('/status')
def status():
    """Return the current processing status as JSON"""
    if 'processing_id' not in session:
        return jsonify({'status': 'error', 'message': 'No processing task found'})

    session_id = session['processing_id']

    if session_id not in processing_status:
        return jsonify({'status': 'error', 'message': 'Processing task not found'})

    current_status = processing_status[session_id]

    # If processing is complete, store the results in the session
    if current_status.get('status') == 'complete' and 'data' in current_status:
        session['captions'] = current_status['data']['captions']
        session['image_paths'] = current_status['data']['image_paths']
        session['story'] = current_status['data']['story']

    return jsonify(current_status)

@app.route('/translate', methods=['POST'])
def translate():
    """Translate the story from English to Hindi"""
    if 'story' not in session:
        return jsonify({'status': 'error', 'message': 'No story to translate'})

    try:
        # Get the story from the session
        story = session['story']

        # Update status to indicate translation started
        session_id = session.get('processing_id', 'unknown')
        if session_id in processing_status:
            processing_status[session_id] = {
                'status': 'translating',
                'progress': 25,
                'message': 'Translating story to Hindi...'
            }

        # Log the original story length for debugging
        print(f"Original story length: {len(story)} characters")

        # Update progress
        if session_id in processing_status:
            processing_status[session_id]['progress'] = 50
            processing_status[session_id]['message'] = 'Processing Hindi translation...'

        # Translate the story
        translated_story = translate_text(story)

        # Log the translated story length for debugging
        print(f"Translated story length: {len(translated_story)} characters")

        # Store the translated story in the session
        session['translated_story'] = translated_story

        # Update status to indicate translation completed
        if session_id in processing_status:
            processing_status[session_id]['status'] = 'complete'
            processing_status[session_id]['progress'] = 100
            processing_status[session_id]['message'] = 'Translation complete!'

        return jsonify({
            'status': 'success',
            'translated_story': translated_story
        })
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Translation error: {str(e)}'
        })

@app.route('/results')
def results():
    """Display the results page with images, captions, and story"""
    if 'captions' not in session or 'image_paths' not in session or 'story' not in session:
        flash('No results to display')
        return redirect(url_for('index'))

    return render_template(
        'results.html',
        image_captions=zip(session['image_paths'], session['captions']),
        story=session['story'],
        translated_story=session.get('translated_story', None)
    )

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, session
import os
import pandas as pd
import numpy as np
import pickle
import logging
import json
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
import shutil
import time
from pathlib import Path

# Try to import face_recognition, but provide a fallback
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("WARNING: face_recognition module not found. Face detection features will be disabled.")
    print("Please install with: pip install face-recognition")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('image_classifier.log'),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Paths
CACHE_DIR = os.path.join(os.getcwd(), 'cache')
IMAGES_DIR = os.path.join(CACHE_DIR, 'images')
OCR_DIR = os.path.join(CACHE_DIR, 'ocr')
LABELS_CSV = os.path.join(CACHE_DIR, 'labels.csv')
FACES_PKL = os.path.join(CACHE_DIR, 'faces.pkl')

# Ensure directories exist
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(OCR_DIR, exist_ok=True)

# Image cache for performance
image_cache = {}
CACHE_SIZE = 10

logger.info("Application starting up...")
logger.info(f"Cache directory: {CACHE_DIR}")
logger.info(f"Images directory: {IMAGES_DIR}")
logger.info(f"OCR directory: {OCR_DIR}")
logger.info(f"Labels CSV: {LABELS_CSV}")
logger.info(f"Faces PKL: {FACES_PKL}")

def load_labels():
    """Load the labels from CSV or create empty DataFrame"""
    if os.path.exists(LABELS_CSV):
        try:
            df = pd.read_csv(LABELS_CSV)
            logger.info(f"Loaded {len(df)} labeled images from CSV")
            return df
        except Exception as e:
            logger.error(f"Error loading labels CSV: {e}")
            
    # Create a new DataFrame if file doesn't exist or there's an error
    df = pd.DataFrame(columns=['filename', 'keep'])
    logger.info("Created new labels DataFrame")
    return df

def save_labels(labels_df):
    """Save the labels to CSV"""
    try:
        labels_df.to_csv(LABELS_CSV, index=False)
        logger.info(f"Saved {len(labels_df)} labels to {LABELS_CSV}")
    except Exception as e:
        logger.error(f"Error saving labels to CSV: {e}")

def load_faces():
    """Load known face encodings and names"""
    if os.path.exists(FACES_PKL):
        try:
            with open(FACES_PKL, 'rb') as f:
                known_faces = pickle.load(f)
                logger.info(f"Loaded {len(known_faces['encodings'])} known faces")
                return known_faces
        except Exception as e:
            logger.error(f"Error loading faces PKL: {e}")
    
    # Create empty faces dict if file doesn't exist or there's an error
    known_faces = {
        'encodings': [],
        'names': []
    }
    logger.info("Created new faces dictionary")
    return known_faces

def save_faces(known_faces):
    """Save face encodings and names"""
    try:
        with open(FACES_PKL, 'wb') as f:
            pickle.dump(known_faces, f)
        logger.info(f"Saved {len(known_faces['encodings'])} faces to {FACES_PKL}")
    except Exception as e:
        logger.error(f"Error saving faces to PKL: {e}")

# Default categories with keyboard shortcuts
DEFAULT_CATEGORIES = {
    'keep': {'name': 'Keep', 'key': '1'},
    'delete': {'name': 'Delete', 'key': '2'},
    'favorite': {'name': 'Favorite', 'key': '3'},
    'archive': {'name': 'Archive', 'key': '4'}
}

def get_unlabeled_images(labels_df):
    """Get list of unlabeled images"""
    labeled_files = set(labels_df['filename'])
    all_image_files = []
    
    try:
        all_image_files = [f for f in os.listdir(IMAGES_DIR) 
                         if f.lower().endswith(('jpg', 'jpeg', 'png', 'webp', 'bmp'))]
    except Exception as e:
        logger.error(f"Error listing images directory: {e}")
    
    unlabeled = [f for f in all_image_files if f not in labeled_files]
    logger.info(f"Found {len(unlabeled)}/{len(all_image_files)} unlabeled images")
    return unlabeled

def get_next_image(labels_df):
    """Get next unlabeled image"""
    unlabeled = get_unlabeled_images(labels_df)
    return unlabeled[0] if unlabeled else None

def load_image(filename):
    """Load an image from cache or file system"""
    if filename in image_cache:
        logger.debug(f"Loading {filename} from cache")
        return image_cache[filename]['image']
    
    try:
        filepath = os.path.join(IMAGES_DIR, filename)
        image = face_recognition.load_image_file(filepath)
        
        # Store in cache
        if len(image_cache) >= CACHE_SIZE:
            # Remove oldest item
            oldest = min(image_cache.items(), key=lambda x: x[1]['timestamp'])
            del image_cache[oldest[0]]
        
        image_cache[filename] = {
            'image': image,
            'timestamp': datetime.now().timestamp()
        }
        logger.info(f"Loaded {filename} from file system and added to cache")
        return image
    except Exception as e:
        logger.error(f"Error loading image {filename}: {e}")
        return None

def detect_faces(image, filename):
    """Detect and encode faces in an image"""
    if not FACE_RECOGNITION_AVAILABLE:
        logger.warning(f"Face recognition not available, skipping face detection for {filename}")
        return [], []
    
    try:
        face_locations = face_recognition.face_locations(image)
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        logger.info(f"Detected {len(face_locations)} faces in {filename}")
        return face_locations, face_encodings
    except Exception as e:
        logger.error(f"Error detecting faces in {filename}: {e}")
        return [], []

def identify_faces(face_encodings, known_faces):
    """Match face encodings with known faces"""
    if not FACE_RECOGNITION_AVAILABLE:
        return ["Face recognition not available"] * len(face_encodings) if face_encodings else []
    
    names = []
    
    for face_encoding in face_encodings:
        name = "Unknown"
        # If we have known faces, compare
        if known_faces['encodings']:
            # Compare with all known face encodings
            matches = face_recognition.compare_faces(
                known_faces['encodings'], face_encoding, tolerance=0.6
            )
            
            # Find the best match
            if True in matches:
                match_index = matches.index(True)
                name = known_faces['names'][match_index]
                
        names.append(name)
    
    logger.debug(f"Identified faces: {names}")
    return names

def get_ocr_text(filename):
    """Get OCR text for an image if available"""
    base_name = os.path.splitext(filename)[0]
    ocr_path = os.path.join(OCR_DIR, f"{base_name}.txt")
    
    if os.path.exists(ocr_path):
        try:
            with open(ocr_path, 'r', encoding='utf-8') as f:
                ocr_text = f.read()
            logger.debug(f"Loaded OCR text for {filename}")
            return ocr_text
        except Exception as e:
            logger.error(f"Error loading OCR text for {filename}: {e}")
    
    logger.debug(f"No OCR text found for {filename}")
    return ""

def get_next_image(labeled):
    logger.debug("Finding next image to label...")
    labeled_images = {row[0] for row in labeled}
    try:
        unlabeled_files = [f for f in os.listdir(UNLABELLED_FOLDER) 
                          if f.lower().endswith(('jpg', 'jpeg', 'png', 'webp', 'bmp', 'gif')) 
                          and f not in labeled_images]
        
        if unlabeled_files:
            next_image = unlabeled_files[0]
            logger.info(f"Next image to label: {next_image} ({len(unlabeled_files)} remaining)")
            return next_image
        else:
            logger.info("No more images to label")
            return None
    except FileNotFoundError:
        logger.error(f"Unlabelled folder not found: {UNLABELLED_FOLDER}")
        return None
    except Exception as e:
        logger.error(f"Error finding next image: {e}")
        return None

def get_next_images(labeled, count=5):
    """Get next several images for preloading"""
    logger.debug(f"Getting next {count} images for preloading...")
    labeled_images = {row[0] for row in labeled}
    try:
        unlabeled_files = [f for f in os.listdir(UNLABELLED_FOLDER) 
                          if f.lower().endswith(('jpg', 'jpeg', 'png', 'webp', 'bmp', 'gif')) 
                          and f not in labeled_images]
        next_images = unlabeled_files[:count]
        logger.info(f"Found {len(next_images)} images for preloading: {next_images}")
        return next_images
    except FileNotFoundError:
        logger.error(f"Unlabelled folder not found: {UNLABELLED_FOLDER}")
        return []
    except Exception as e:
        logger.error(f"Error getting next images: {e}")
        return []

def load_image_to_cache(filename):
    """Load image to cache in background"""
    if filename in image_cache:
        logger.debug(f"Image {filename} already in cache, skipping")
        return
    
    logger.debug(f"Loading image to cache: {filename}")
    try:
        file_path = os.path.join(UNLABELLED_FOLDER, filename)
        with open(file_path, 'rb') as f:
            image_data = f.read()
            # Store as base64 for easy serving
            image_cache[filename] = {
                'data': base64.b64encode(image_data).decode('utf-8'),
                'timestamp': time.time(),
                'size': len(image_data)
            }
        
        logger.info(f"Cached image: {filename} ({len(image_data)} bytes)")
        
        # Manage cache size
        if len(image_cache) > CACHE_SIZE:
            logger.debug(f"Cache size ({len(image_cache)}) exceeds limit ({CACHE_SIZE}), cleaning up...")
            # Remove oldest entries
            sorted_cache = sorted(image_cache.items(), key=lambda x: x[1]['timestamp'])
            removed_count = 0
            for filename_to_remove, _ in sorted_cache[:-CACHE_SIZE]:
                del image_cache[filename_to_remove]
                removed_count += 1
            logger.info(f"Removed {removed_count} old images from cache")
                
    except Exception as e:
        logger.error(f"Error caching image {filename}: {e}")

def preload_images(filenames):
    """Preload multiple images asynchronously"""
    if not filenames:
        logger.debug("No images to preload")
        return
    
    logger.info(f"Starting preload for {len(filenames)} images: {filenames}")
    submitted_count = 0
    for filename in filenames:
        if filename not in image_cache:
            preload_executor.submit(load_image_to_cache, filename)
            submitted_count += 1
        else:
            logger.debug(f"Image {filename} already cached, skipping preload")
    
    if submitted_count > 0:
        logger.info(f"Submitted {submitted_count} images for background loading")

def get_total_images():
    logger.debug("Counting total images in unlabelled folder...")
    try:
        total = len([f for f in os.listdir(UNLABELLED_FOLDER) 
                   if f.lower().endswith(('jpg', 'jpeg', 'png', 'webp', 'bmp', 'gif'))])
        logger.info(f"Total images in folder: {total}")
        return total
    except FileNotFoundError:
        logger.error(f"Unlabelled folder not found: {UNLABELLED_FOLDER}")
        return 0
    except Exception as e:
        logger.error(f"Error counting images: {e}")
        return 0

@app.route('/')
def index():
    logger.info("=== INDEX PAGE REQUEST ===")
    logger.info("Starting index page load...")
    
    # Load labels and known faces
    labels_df = load_labels()
    known_faces = load_faces()
    
    # Get next unlabeled image
    next_image = get_next_image(labels_df)
    total_images = len([f for f in os.listdir(IMAGES_DIR) 
                     if f.lower().endswith(('jpg', 'jpeg', 'png', 'webp', 'bmp'))])
    progress = len(labels_df)
    
    logger.info(f"Progress: {progress}/{total_images} images labeled")
    
    # Load categories
    categories = DEFAULT_CATEGORIES
    try:
        if os.path.exists('categories.json'):
            with open('categories.json', 'r') as f:
                categories = json.load(f)
                logger.info(f"Loaded {len(categories)} categories from JSON")
    except Exception as e:
        logger.error(f"Error loading categories: {e}")
    
    if next_image:
        logger.info(f"Displaying image: {next_image}")
        
        # Process image for faces
        image = load_image(next_image)
        face_locations = []
        face_names = []
        ocr_text = ""
        
        if image is not None:
            # Detect faces
            face_locations, face_encodings = detect_faces(image, next_image)
            face_names = identify_faces(face_encodings, known_faces)
            
            # Get OCR text if available
            ocr_text = get_ocr_text(next_image)
        
        logger.info("Rendering index template")
        return render_template('index.html', 
                             image=next_image, 
                             progress=progress, 
                             total=total_images,
                             categories=categories,
                             face_count=len(face_locations),
                             face_names=face_names,
                             face_locations=face_locations,
                             ocr_text=ocr_text)
    else:
        logger.info("All images completed, showing completion page")
        return render_template('completed.html', progress=progress, total=total_images)

@app.route('/label', methods=['POST'])
def label():
    logger.info("=== LABEL REQUEST ===")
    image = request.form['image']
    label = request.form['label']
    logger.info(f"Labeling image '{image}' as '{label}'")
    
    # Process face names if submitted
    face_names = request.form.getlist('face_name')
    face_encodings_str = request.form.getlist('face_encoding')
    
    # Process face encodings - convert from string back to array
    face_encodings = []
    for encoding_str in face_encodings_str:
        try:
            encoding = np.fromstring(encoding_str, sep=',')
            face_encodings.append(encoding)
        except Exception as e:
            logger.error(f"Error processing face encoding: {e}")
    
    logger.info(f"Processing {len(face_names)} face names with {len(face_encodings)} encodings")
    
    # Update known faces if names were provided
    if face_names and face_encodings:
        known_faces = load_faces()
        for i, name in enumerate(face_names):
            if name and name != "Unknown" and i < len(face_encodings):
                # Add to known faces
                known_faces['encodings'].append(face_encodings[i])
                known_faces['names'].append(name)
                logger.info(f"Added new face: {name}")
        save_faces(known_faces)
    
    # Load and update labels dataframe
    labels_df = load_labels()
    
    # Add new label
    new_row = pd.DataFrame({'filename': [image], 'keep': [label]})
    labels_df = pd.concat([labels_df, new_row], ignore_index=True)
    save_labels(labels_df)
    logger.info(f"Saved label to CSV: {image} -> {label}")
    
    # Create symlink in labeled folder if using new architecture
    labeled_dir = os.path.join(os.getcwd(), 'labeled', label)
    os.makedirs(labeled_dir, exist_ok=True)
    
    # Move file if needed (now we just maintain a symlink)
    src_path = os.path.join(IMAGES_DIR, image)
    dst_path = os.path.join(labeled_dir, image)
    
    # Remove existing symlink if it exists
    if os.path.exists(dst_path):
        try:
            os.unlink(dst_path)
            logger.debug(f"Removed existing symlink: {dst_path}")
        except Exception as e:
            logger.error(f"Error removing existing symlink: {e}")
    
    # Create symlink
    try:
        if os.name == 'nt':  # Windows
            import ctypes
            kdll = ctypes.windll.LoadLibrary("kernel32.dll")
            # Use Windows API to create symlink
            flags = 0
            if os.path.isdir(src_path):
                flags = 1  # SYMBOLIC_LINK_FLAG_DIRECTORY
            res = kdll.CreateSymbolicLinkW(dst_path, src_path, flags)
            if res == 0:
                logger.error(f"Failed to create symlink: {dst_path} -> {src_path}")
            else:
                logger.info(f"Created symlink: {dst_path} -> {src_path}")
        else:  # Unix/Linux
            os.symlink(src_path, dst_path)
            logger.info(f"Created symlink: {dst_path} -> {src_path}")
    except Exception as e:
        logger.error(f"Error creating symlink: {e}")

    # Remove from cache to ensure it's reloaded next time
    if image in image_cache:
        del image_cache[image]
        logger.debug(f"Removed {image} from cache")

    logger.info("Redirecting to index page")
    return redirect(url_for('index'))

@app.route('/undo')
def undo():
    logger.info("=== UNDO REQUEST ===")
    labels_df = load_labels()
    
    if len(labels_df) == 0:
        logger.info("No labeled images to undo")
        return redirect(url_for('index'))
    
    # Get last labeled image
    last_row = labels_df.iloc[-1]
    last_image = last_row['filename']
    last_label = last_row['keep']
    
    logger.info(f"Undoing last label: {last_image} ({last_label})")

    # Remove last row from dataframe
    labels_df = labels_df.iloc[:-1]
    save_labels(labels_df)
    logger.info(f"Removed last entry from labels CSV")
    
    # Remove symlink from labeled folder if it exists
    symlink_path = os.path.join(os.getcwd(), 'labeled', last_label, last_image)
    
    if os.path.exists(symlink_path):
        try:
            os.unlink(symlink_path)
            logger.info(f"Removed symlink: {symlink_path}")
        except Exception as e:
            logger.error(f"Error removing symlink: {e}")
    
    # Remove from cache to ensure fresh load
    if last_image in image_cache:
        del image_cache[last_image]
        logger.debug(f"Removed {last_image} from cache")

    logger.info("Redirecting to index page")
    return redirect(url_for('index'))

@app.route('/categories')
def manage_categories():
    logger.info("=== CATEGORY MANAGEMENT REQUEST ===")
    categories = load_categories()
    logger.info(f"Loading category management page with {len(categories)} categories")
    return render_template('categories.html', categories=categories)

@app.route('/categories/add', methods=['POST'])
def add_category():
    logger.info("=== ADD CATEGORY REQUEST ===")
    data = request.get_json()
    logger.info(f"Adding category: {data}")
    
    categories = load_categories()
    
    category_id = data['id'].lower().replace(' ', '_')
    if category_id not in categories:
        categories[category_id] = {
            'name': data['name'],
            'key': data['key']
        }
        save_categories(categories)
        ensure_category_folders()
        logger.info(f"Successfully added category: {category_id}")
        return jsonify({'success': True})
    else:
        logger.warning(f"Category already exists: {category_id}")
        return jsonify({'success': False, 'error': 'Category already exists'})

@app.route('/categories/delete', methods=['POST'])
def delete_category():
    logger.info("=== DELETE CATEGORY REQUEST ===")
    data = request.get_json()
    logger.info(f"Deleting category: {data}")
    
    categories = load_categories()
    
    category_id = data['id']
    if category_id in categories and len(categories) > 1:  # Keep at least one category
        del categories[category_id]
        save_categories(categories)
        logger.info(f"Successfully deleted category: {category_id}")
        return jsonify({'success': True})
    else:
        logger.warning(f"Cannot delete category: {category_id} (not found or last category)")
        return jsonify({'success': False, 'error': 'Cannot delete category'})

@app.route('/categories/update', methods=['POST'])
def update_category():
    logger.info("=== UPDATE CATEGORY REQUEST ===")
    data = request.get_json()
    logger.info(f"Updating category: {data}")
    
    categories = load_categories()
    
    category_id = data['id']
    if category_id in categories:
        categories[category_id].update({
            'name': data['name'],
            'key': data['key']
        })
        save_categories(categories)
        logger.info(f"Successfully updated category: {category_id}")
        return jsonify({'success': True})
    else:
        logger.warning(f"Category not found for update: {category_id}")
        return jsonify({'success': False, 'error': 'Category not found'})

# Serve images from cache directory
@app.route('/image/<filename>')
def serve_image(filename):
    logger.debug(f"=== IMAGE REQUEST: {filename} ===")
    from flask import send_file, Response
    
    try:
        file_path = os.path.join(IMAGES_DIR, filename)
        logger.debug(f"Serving from path: {file_path}")
        return send_file(file_path)
    except FileNotFoundError:
        logger.error(f"Image not found: {filename}")
        return "Image not found", 404
    except Exception as e:
        logger.error(f"Error serving image {filename}: {e}")
        return "Error serving image", 500

# API endpoint to get next image info for preloading
@app.route('/api/next-image')
def get_next_image_api():
    logger.debug("=== NEXT IMAGE API REQUEST ===")
    labeled = load_labeled_images()
    next_images = get_next_images(labeled, 3)
    cache_status = {img: img in image_cache for img in next_images}
    
    logger.info(f"API returning {len(next_images)} next images")
    logger.debug(f"Cache status: {cache_status}")
    
    return jsonify({
        'next_images': next_images,
        'cache_status': cache_status
    })

# API endpoints for face recognition
@app.route('/face/<filename>/<int:face_id>')
def serve_face(filename, face_id):
    logger.info(f"=== FACE REQUEST: {filename}, face #{face_id} ===")
    try:
        # Load the image
        image = load_image(filename)
        if image is None:
            logger.error(f"Failed to load image for face extraction: {filename}")
            return "Image not found", 404
        
        # Get face locations
        face_locations, _ = detect_faces(image, filename)
        
        if face_id >= len(face_locations):
            logger.error(f"Face index out of range: {face_id} >= {len(face_locations)}")
            return "Face not found", 404
        
        # Extract the face
        face_location = face_locations[face_id]
        top, right, bottom, left = face_location
        face_image = image[top:bottom, left:right]
        
        # Convert the face to a PIL image and serve it
        pil_image = Image.fromarray(face_image)
        img_io = BytesIO()
        pil_image.save(img_io, 'JPEG')
        img_io.seek(0)
        
        logger.info(f"Serving face #{face_id} from {filename}")
        return send_file(img_io, mimetype='image/jpeg')
    except Exception as e:
        logger.error(f"Error serving face: {e}")
        return "Error processing face", 500

@app.route('/assign-name', methods=['POST'])
def assign_name():
    logger.info("=== ASSIGN NAME REQUEST ===")
    try:
        data = request.get_json()
        filename = data.get('filename')
        face_id = int(data.get('face_id'))
        name = data.get('name')
        
        logger.info(f"Assigning name {name} to face #{face_id} in {filename}")
        
        # Load image and get face encoding
        image = load_image(filename)
        if image is None:
            logger.error(f"Failed to load image: {filename}")
            return jsonify({"success": False, "error": "Image not found"})
        
        face_locations, face_encodings = detect_faces(image, filename)
        
        if face_id >= len(face_locations) or face_id >= len(face_encodings):
            logger.error(f"Face index out of range: {face_id}")
            return jsonify({"success": False, "error": "Face not found"})
        
        # Add face to known faces
        known_faces = load_faces()
        face_encoding = face_encodings[face_id]
        
        # Check if this is an update to an existing face
        updated = False
        for i, existing_name in enumerate(known_faces['names']):
            # Compare face with existing faces
            if face_recognition.compare_faces([known_faces['encodings'][i]], face_encoding, tolerance=0.6)[0]:
                # Update existing face name
                known_faces['names'][i] = name
                updated = True
                logger.info(f"Updated existing face: {name}")
                break
        
        if not updated:
            # Add as new face
            known_faces['encodings'].append(face_encoding)
            known_faces['names'].append(name)
            logger.info(f"Added new face: {name}")
        
        # Save updated faces
        save_faces(known_faces)
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error assigning name: {e}")
        return jsonify({"success": False, "error": str(e)})
        
if __name__ == '__main__':
    logger.info("Starting Flask application...")
    logger.info(f"Debug mode: {True}")
    logger.info("Application ready to serve requests")
    app.run(debug=True)

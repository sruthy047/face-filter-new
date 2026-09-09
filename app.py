import os
import requests
from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import base64

app = Flask(__name__)

# Constants and Setup
PROPS_DIR = os.path.join(app.root_path, 'static', 'props')
os.makedirs(PROPS_DIR, exist_ok=True)

# Twemoji CDN base URL (72x72 PNGs are good, or SVG)
TWEMOJI_BASE = "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/"

EMOJIS = {
    'sunglasses': '1f60e.png',
    'cat': '1f431.png',
    'crown': '1f451.png',
    'heart_eyes': '1f60d.png',
    'mustache': '1f978.png', # Disguised face
    'robot': '1f916.png'
}

# Download emojis if they don't exist
for name, filename in EMOJIS.items():
    filepath = os.path.join(PROPS_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Downloading {filename}...")
        url = TWEMOJI_BASE + filename
        response = requests.get(url)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)

# Load OpenCV face detector
cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cascade_path)

# Pre-load emoji images into memory (with alpha channel)
emoji_images = {}
for name, filename in EMOJIS.items():
    filepath = os.path.join(PROPS_DIR, filename)
    if os.path.exists(filepath):
        img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED) # Load with alpha
        if img is not None:
            emoji_images[name] = img

def overlay_transparent(background, overlay, x, y):
    """Overlays a transparent PNG onto a background image at (x, y)"""
    bg_h, bg_w, bg_channels = background.shape
    ol_h, ol_w, ol_channels = overlay.shape

    # Check if overlay is completely out of bounds
    if x >= bg_w or y >= bg_h or (x + ol_w) <= 0 or (y + ol_h) <= 0:
        return background

    # Calculate clipping coordinates
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(bg_w, x + ol_w)
    y2 = min(bg_h, y + ol_h)

    # Calculate overlay crop coordinates
    ox1 = max(0, -x)
    oy1 = max(0, -y)
    ox2 = ol_w - max(0, (x + ol_w) - bg_w)
    oy2 = ol_h - max(0, (y + ol_h) - bg_h)

    # Extract alpha channel and create masks
    alpha_mask = overlay[oy1:oy2, ox1:ox2, 3] / 255.0
    alpha_inv = 1.0 - alpha_mask

    # Overlay RGB channels
    for c in range(0, 3):
        background[y1:y2, x1:x2, c] = (alpha_mask * overlay[oy1:oy2, ox1:ox2, c] +
                                      alpha_inv * background[y1:y2, x1:x2, c])
    return background

def apply_filter(image, filter_type):
    if filter_type == 'none' or filter_type not in emoji_images:
        return image

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Detect faces
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    overlay_img = emoji_images[filter_type]

    for (x, y, w, h) in faces:
        if filter_type == 'cat':
            # Draw cute cat nose and whiskers using OpenCV!
            # Nose
            nose_x, nose_y = x + int(w / 2), y + int(h * 0.6)
            cv2.circle(image, (nose_x, nose_y), int(w * 0.08), (147, 20, 255), -1) # Pink nose
            
            # Whiskers
            color = (50, 50, 50)
            thickness = max(1, int(w * 0.01))
            # Left whiskers
            cv2.line(image, (nose_x - int(w*0.1), nose_y), (nose_x - int(w*0.4), nose_y - int(h*0.1)), color, thickness)
            cv2.line(image, (nose_x - int(w*0.1), nose_y + int(h*0.05)), (nose_x - int(w*0.4), nose_y + int(h*0.05)), color, thickness)
            cv2.line(image, (nose_x - int(w*0.1), nose_y + int(h*0.1)), (nose_x - int(w*0.4), nose_y + int(h*0.2)), color, thickness)
            # Right whiskers
            cv2.line(image, (nose_x + int(w*0.1), nose_y), (nose_x + int(w*0.4), nose_y - int(h*0.1)), color, thickness)
            cv2.line(image, (nose_x + int(w*0.1), nose_y + int(h*0.05)), (nose_x + int(w*0.4), nose_y + int(h*0.05)), color, thickness)
            cv2.line(image, (nose_x + int(w*0.1), nose_y + int(h*0.1)), (nose_x + int(w*0.4), nose_y + int(h*0.2)), color, thickness)
            continue
            
        elif filter_type == 'robot':
            # Draw a cute robot HUD over the face
            color = (0, 255, 0)
            thickness = max(2, int(w * 0.02))
            # Draw targeting brackets
            cv2.line(image, (x, y), (x + int(w*0.2), y), color, thickness)
            cv2.line(image, (x, y), (x, y + int(h*0.2)), color, thickness)
            
            cv2.line(image, (x + w, y), (x + int(w*0.8), y), color, thickness)
            cv2.line(image, (x + w, y), (x + w, y + int(h*0.2)), color, thickness)
            
            cv2.line(image, (x, y + h), (x + int(w*0.2), y + h), color, thickness)
            cv2.line(image, (x, y + h), (x, y + int(h*0.8)), color, thickness)
            
            cv2.line(image, (x + w, y + h), (x + int(w*0.8), y + h), color, thickness)
            cv2.line(image, (x + w, y + h), (x + w, y + int(h*0.8)), color, thickness)
            continue

        # For emoji props, calculate specific cute placement
        overlay_img = emoji_images[filter_type]
        new_w, new_h, draw_x, draw_y = w, h, x, y
        
        if filter_type in ['sunglasses', 'heart_eyes']:
            new_w = int(w * 0.9)
            new_h = int(h * 0.4)
            draw_x = x + int(w * 0.05)
            draw_y = y + int(h * 0.25)
            
        elif filter_type == 'mustache':
            new_w = int(w * 0.6)
            new_h = int(h * 0.25)
            draw_x = x + int(w * 0.2)
            draw_y = y + int(h * 0.65)
            
        elif filter_type == 'crown':
            new_w = int(w * 0.8)
            new_h = int(h * 0.6)
            draw_x = x + int(w * 0.1)
            draw_y = y - int(h * 0.4)
        
        resized_overlay = cv2.resize(overlay_img, (new_w, new_h))
        image = overlay_transparent(image, resized_overlay, draw_x, draw_y)

    return image

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_frame', methods=['POST'])
def process_frame():
    data = request.json
    if not data or 'image' not in data:
        return jsonify({'error': 'No image provided'}), 400
        
    filter_type = data.get('filter', 'none')
    
    # Extract base64 image data (remove 'data:image/jpeg;base64,' prefix)
    img_data = data['image'].split(',')[1]
    
    # Decode base64 to numpy array
    nparr = np.frombuffer(base64.b64decode(img_data), np.uint8)
    
    # Decode image array to OpenCV format (BGR)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Apply OpenCV filter
    processed_img = apply_filter(img, filter_type)
    
    # Encode back to JPEG
    _, buffer = cv2.imencode('.jpg', processed_img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    
    # Convert to base64
    b64_str = base64.b64encode(buffer).decode('utf-8')
    
    return jsonify({
        'image': f"data:image/jpeg;base64,{b64_str}"
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

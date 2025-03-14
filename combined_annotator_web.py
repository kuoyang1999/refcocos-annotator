import os
import json
import base64
from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_from_directory
from PIL import Image

# Configuration
IMAGE_BASE_DIR = "."
JSON_FILE = "data-coco-multiple-instances.json"  # Using the filtered dataset

# Create necessary directories
os.makedirs('static', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Create HTML template that combines both annotator and labeler
with open('templates/combined_annotator.html', 'w') as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Combined Bounding Box Annotator and Category Labeler</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        #canvas-container { border: 2px solid #333; margin: 10px 0; position: relative; display: inline-block; }
        canvas { display: block; }
        #status { font-weight: bold; color: blue; margin: 10px 0; }
        button { padding: 5px 10px; margin-right: 10px; }
        button:disabled { opacity: 0.5; }
        .form-section { margin: 15px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background-color: #f9f9f9; }
        .form-section h3 { margin-top: 0; }
        .option-group { margin: 10px 0; }
        .checkbox-group label { margin-right: 15px; display: inline-block; }
        .saved-indicator { color: green; font-weight: bold; display: none; }
        #main-container { display: flex; flex-wrap: wrap; }
        #left-panel { flex: 1; min-width: 400px; }
        #right-panel { flex: 1; min-width: 300px; padding-left: 20px; }
        #coords { margin: 10px 0; }
    </style>
</head>
<body>
    <h2>Combined Bounding Box Annotator and Category Labeler</h2>
    
    <div>
        <button id="prev-btn">Previous</button>
        <button id="next-btn">Next</button>
        <button id="redraw-btn">Redraw Box</button>
        <button id="save-btn">Save All</button>
        <span id="progress" style="margin-left: 20px;">Image 0/0</span>
        <span id="saved-indicator" class="saved-indicator">✓ Saved</span>
    </div>
    
    <div id="status">Loading...</div>
    <div id="caption"></div>
    <div id="image-path"></div>
    <div id="coords">Box: None</div>
    
    <div id="main-container">
        <div id="left-panel">
            <div id="canvas-container">
                <canvas id="canvas"></canvas>
            </div>
        </div>
        
        <div id="right-panel">
            <div class="form-section">
                <h3>Category Labels</h3>
                
                <div id="empty-case-container" class="option-group">
                    <label>Empty Case: </label>
                    <span id="empty-case-value">No</span>
                    <span>(auto-detected)</span>
                </div>
                
                <div class="option-group">
                    <label><b>1. Hops:</b></label><br>
                    <div id="hops-options">
                        <label><input type="radio" name="hops" value="1"> 1</label>
                        <label><input type="radio" name="hops" value="2"> 2</label>
                        <label><input type="radio" name="hops" value="3"> 3</label>
                        <label><input type="radio" name="hops" value="4"> 4</label>
                    </div>
                </div>
                
                <div class="option-group">
                    <label><b>2. Type:</b></label><br>
                    <div id="type-options" class="checkbox-group">
                        <label><input type="checkbox" name="type" value="spatial"> Spatial</label>
                        <label><input type="checkbox" name="type" value="exclude"> Exclude</label>
                        <label><input type="checkbox" name="type" value="verb"> Verb</label>
                    </div>
                </div>
                
                <div class="option-group">
                    <label><b>3. Hidden:</b></label><br>
                    <div id="hidden-options">
                        <label><input type="radio" name="hidden" value="true"> Yes</label>
                        <label><input type="radio" name="hidden" value="false"> No</label>
                    </div>
                </div>
                
                <div class="option-group">
                    <label><b>4. Distractors:</b></label><br>
                    <div id="distractors-options">
                        <label><input type="radio" name="distractors" value="3"> 3</label>
                        <label><input type="radio" name="distractors" value="4"> 4</label>
                        <label><input type="radio" name="distractors" value="5+"> 5+</label>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Prevent any default browser behaviors
        document.addEventListener('dragstart', e => e.preventDefault(), false);
        document.addEventListener('contextmenu', e => e.preventDefault(), false);
        
        // Elements
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        const status = document.getElementById('status');
        const caption = document.getElementById('caption');
        const imagePath = document.getElementById('image-path');
        const coords = document.getElementById('coords');
        const progress = document.getElementById('progress');
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        const redrawBtn = document.getElementById('redraw-btn');
        const saveBtn = document.getElementById('save-btn');
        const savedIndicator = document.getElementById('saved-indicator');
        const emptyCase = document.getElementById('empty-case-value');
        
        // Form elements
        const hopsOptions = document.querySelectorAll('input[name="hops"]');
        const typeOptions = document.querySelectorAll('input[name="type"]');
        const hiddenOptions = document.querySelectorAll('input[name="hidden"]');
        const distractorsOptions = document.querySelectorAll('input[name="distractors"]');
        
        // Variables
        let currentIndex = 0;
        let dataIndex = 0;
        let totalImages = 0;
        let imageWidth = 0;
        let imageHeight = 0;
        let currentImage = new Image();
        let currentCategories = {};
        let annotationCoords = null;
        let isDragging = false;
        let startX = 0;
        let startY = 0;
        
        // Add cache-busting parameter to all API requests
        const cacheBuster = Date.now();
        
        // Debug flag - set to true for verbose console logging
        const DEBUG = true;
        
        function debug(...args) {
            if (DEBUG) console.log(...args);
        }
        
        // Canvas drawing events for bounding box
        canvas.addEventListener('mousedown', function(e) {
            debug('Canvas mousedown', e);
            const rect = canvas.getBoundingClientRect();
            startX = Math.round(e.clientX - rect.left);
            startY = Math.round(e.clientY - rect.top);
            
            debug('Drag start position:', startX, startY);
            
            // Start dragging
            isDragging = true;
            
            // Clear canvas and redraw image
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(currentImage, 0, 0, canvas.width, canvas.height);
            
            // Prevent default browser behavior
            e.preventDefault();
        });
        
        canvas.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            
            const rect = canvas.getBoundingClientRect();
            const currentX = Math.round(e.clientX - rect.left);
            const currentY = Math.round(e.clientY - rect.top);
            
            // Redraw the image
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(currentImage, 0, 0, canvas.width, canvas.height);
            
            // Calculate the rectangle coordinates
            const rectX = Math.min(startX, currentX);
            const rectY = Math.min(startY, currentY);
            const rectWidth = Math.abs(currentX - startX);
            const rectHeight = Math.abs(currentY - startY);
            
            // Draw rectangle
            ctx.strokeStyle = 'red';
            ctx.lineWidth = 3;
            ctx.strokeRect(rectX, rectY, rectWidth, rectHeight);
            
            // Fill with semi-transparent red
            ctx.fillStyle = 'rgba(255, 0, 0, 0.2)';
            ctx.fillRect(rectX, rectY, rectWidth, rectHeight);
            
            status.textContent = "Drag to set the bounding box size";
            
            // Prevent default browser behavior
            e.preventDefault();
        });
        
        // Handle both mouseup and mouseleave to ensure we complete the drawing
        function finishDrag(e) {
            if (!isDragging) return;
            
            const rect = canvas.getBoundingClientRect();
            const endX = Math.round(e.clientX - rect.left);
            const endY = Math.round(e.clientY - rect.top);
            
            debug('Drag end position:', endX, endY);
            
            // End dragging
            isDragging = false;
            
            // Only create a box if it has some size
            if (Math.abs(endX - startX) < 5 || Math.abs(endY - startY) < 5) {
                debug('Box too small, ignoring');
                status.textContent = "Box too small. Try again with a larger selection.";
                return;
            }
            
            // Redraw the image
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(currentImage, 0, 0, canvas.width, canvas.height);
            
            // Calculate the rectangle coordinates
            const rectX = Math.min(startX, endX);
            const rectY = Math.min(startY, endY);
            const rectWidth = Math.abs(endX - startX);
            const rectHeight = Math.abs(endY - startY);
            
            // Draw final rectangle
            ctx.strokeStyle = 'red';
            ctx.lineWidth = 3;
            ctx.strokeRect(rectX, rectY, rectWidth, rectHeight);
            
            // Fill with semi-transparent red
            ctx.fillStyle = 'rgba(255, 0, 0, 0.2)';
            ctx.fillRect(rectX, rectY, rectWidth, rectHeight);
            
            // Calculate original image coordinates
            const scaleX = imageWidth / canvas.width;
            const scaleY = imageHeight / canvas.height;
            
            const imgX1 = Math.round(Math.min(startX, endX) * scaleX);
            const imgY1 = Math.round(Math.min(startY, endY) * scaleY);
            const imgX2 = Math.round(Math.max(startX, endX) * scaleX);
            const imgY2 = Math.round(Math.max(startY, endY) * scaleY);
            
            // Store coordinates for saving
            annotationCoords = [imgX1, imgY1, imgX2, imgY2];
            
            // Update empty case based on whether a box exists
            updateEmptyCaseStatus(false);
            
            // Show coordinates
            coords.textContent = `Box: [${imgX1}, ${imgY1}, ${imgX2}, ${imgY2}]`;
            
            // Update status
            status.textContent = "Bounding box created. Fill in category labels and save.";
            
            // Prevent default browser behavior
            e.preventDefault();
        }
        
        canvas.addEventListener('mouseup', finishDrag);
        canvas.addEventListener('mouseleave', finishDrag);
        
        // Button events
        prevBtn.addEventListener('click', function() {
            if (currentIndex > 0) {
                checkIfDataChanged(() => loadImage(currentIndex - 1));
            }
        });
        
        nextBtn.addEventListener('click', function() {
            if (currentIndex < totalImages - 1) {
                checkIfDataChanged(() => loadImage(currentIndex + 1));
            }
        });
        
        redrawBtn.addEventListener('click', function() {
            // Clear canvas and redraw the image
            debug('Redraw clicked');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(currentImage, 0, 0, canvas.width, canvas.height);
            
            // Reset variables
            annotationCoords = null;
            coords.textContent = "Box: None";
            status.textContent = "Draw a new bounding box";
            
            // Update empty case status
            updateEmptyCaseStatus(true);
        });
        
        saveBtn.addEventListener('click', function() {
            saveAnnotation();
        });
        
        // Check if data has changed before navigating
        function checkIfDataChanged(callback) {
            const formData = getFormData();
            const categoriesChanged = JSON.stringify(formData) !== JSON.stringify(currentCategories);
            const coordsChanged = annotationCoords !== null;
            
            if (categoriesChanged || coordsChanged) {
                if (confirm('You have unsaved changes. Do you want to save before continuing?')) {
                    saveAnnotation(() => callback());
                } else {
                    callback();
                }
            } else {
                callback();
            }
        }
        
        // Update the empty case status
        function updateEmptyCaseStatus(isEmpty) {
            emptyCase.textContent = isEmpty ? 'Yes' : 'No';
        }
        
        // Get all form data as an object
        function getFormData() {
            const formData = {
                empty_case: emptyCase.textContent === 'Yes',
                hops: getSelectedRadioValue(hopsOptions),
                type: Array.from(typeOptions)
                    .filter(cb => cb.checked)
                    .map(cb => cb.value),
                hidden: getSelectedRadioValue(hiddenOptions) === 'true',
                distractors: getSelectedRadioValue(distractorsOptions)
            };
            
            return formData;
        }
        
        // Get the value of a selected radio button
        function getSelectedRadioValue(radioButtons) {
            for (const radio of radioButtons) {
                if (radio.checked) {
                    return radio.value;
                }
            }
            return null;
        }
        
        // Set form values based on loaded data
        function setFormValues(data) {
            // Set empty case status based on solution
            const isEmptyCase = !data.solution || 
                                (Array.isArray(data.solution) && 
                                 data.solution.length === 0) || 
                                (Array.isArray(data.solution) && 
                                 data.solution.every(v => v === 0));
                                 
            updateEmptyCaseStatus(isEmptyCase);
            
            // Set saved category values if they exist
            if (data.categories) {
                currentCategories = data.categories;
                
                // Set hops
                if (data.categories.hops) {
                    setRadioValue(hopsOptions, data.categories.hops.toString());
                }
                
                // Set type (multiple selection)
                if (data.categories.type && Array.isArray(data.categories.type)) {
                    typeOptions.forEach(option => {
                        option.checked = data.categories.type.includes(option.value);
                    });
                }
                
                // Set hidden
                if (data.categories.hidden !== undefined) {
                    setRadioValue(hiddenOptions, data.categories.hidden.toString());
                }
                
                // Set distractors
                if (data.categories.distractors) {
                    setRadioValue(distractorsOptions, data.categories.distractors.toString());
                }
            } else {
                // Initialize with default values
                currentCategories = {
                    empty_case: isEmptyCase,
                    hops: null,
                    type: [],
                    hidden: false,
                    distractors: null
                };
                
                // Clear all form selections
                clearFormSelections();
            }
        }
        
        // Set a radio button value
        function setRadioValue(radioButtons, value) {
            for (const radio of radioButtons) {
                radio.checked = radio.value === value;
            }
        }
        
        // Clear all form selections
        function clearFormSelections() {
            // Clear hops
            hopsOptions.forEach(radio => radio.checked = false);
            
            // Clear type
            typeOptions.forEach(checkbox => checkbox.checked = false);
            
            // Set hidden to "No" by default
            setRadioValue(hiddenOptions, 'false');
            
            // Clear distractors
            distractorsOptions.forEach(radio => radio.checked = false);
        }
        
        // Save both the bounding box and categories
        function saveAnnotation(callback) {
            const formData = getFormData();
            
            // Check if we have valid data
            if (!annotationCoords && !formData.empty_case) {
                if (!confirm('No bounding box drawn. Do you want to mark this as an empty case?')) {
                    return;
                }
                updateEmptyCaseStatus(true);
                formData.empty_case = true;
            }
            
            debug('Saving annotation', {coords: annotationCoords, categories: formData});
            
            fetch(`/api/save_combined?cache=${cacheBuster}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    data_index: dataIndex,
                    coords: annotationCoords,
                    categories: formData
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update current categories
                    currentCategories = formData;
                    
                    // Show saved indicator
                    savedIndicator.style.display = 'inline';
                    setTimeout(() => {
                        savedIndicator.style.display = 'none';
                    }, 2000);
                    
                    status.textContent = "Annotation saved successfully!";
                    
                    if (callback) callback();
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(err => {
                console.error('Save error:', err);
                alert('Failed to save annotation');
            });
        }
        
        // Load image and associated data
        function loadImage(index) {
            debug('Loading image', index);
            savedIndicator.style.display = 'none';
            
            fetch(`/api/image/${index}?cache=${cacheBuster}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        status.textContent = "Error: " + data.error;
                        return;
                    }
                    
                    // Store metadata
                    currentIndex = data.index;
                    dataIndex = data.data_index;
                    totalImages = data.total;
                    imageWidth = data.width;
                    imageHeight = data.height;
                    
                    // Update UI
                    caption.textContent = "Caption: " + data.caption;
                    imagePath.textContent = "Image path: " + data.image_path;
                    progress.textContent = `Image ${data.index + 1}/${data.total}`;
                    prevBtn.disabled = currentIndex === 0;
                    nextBtn.disabled = currentIndex === totalImages - 1;
                    
                    // Reset annotation state
                    annotationCoords = null;
                    coords.textContent = "Box: None";
                    
                    debug('Loading image source', data.image_path);
                    
                    // Load the image
                    currentImage = new Image();
                    currentImage.onload = function() {
                        debug('Image loaded', this.width, this.height);
                        
                        // Calculate canvas size (max width 800px)
                        const maxWidth = Math.min(800, window.innerWidth - 400);
                        const scale = Math.min(1, maxWidth / this.width);
                        
                        canvas.width = Math.floor(this.width * scale);
                        canvas.height = Math.floor(this.height * scale);
                        
                        // Draw image
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        ctx.drawImage(this, 0, 0, canvas.width, canvas.height);
                        
                        // Show existing annotation if available
                        if (data.solution && data.solution.length === 4 && !data.solution.every(v => v === 0)) {
                            const [x1, y1, x2, y2] = data.solution;
                            
                            // Calculate canvas coordinates
                            const canvasX1 = Math.round(x1 / imageWidth * canvas.width);
                            const canvasY1 = Math.round(y1 / imageHeight * canvas.height);
                            const canvasX2 = Math.round(x2 / imageWidth * canvas.width);
                            const canvasY2 = Math.round(y2 / imageHeight * canvas.height);
                            
                            // Draw the box
                            ctx.strokeStyle = 'red';
                            ctx.lineWidth = 3;
                            ctx.strokeRect(
                                canvasX1, 
                                canvasY1, 
                                canvasX2 - canvasX1, 
                                canvasY2 - canvasY1
                            );
                            
                            // Fill with semi-transparent red
                            ctx.fillStyle = 'rgba(255, 0, 0, 0.2)';
                            ctx.fillRect(
                                canvasX1, 
                                canvasY1, 
                                canvasX2 - canvasX1, 
                                canvasY2 - canvasY1
                            );
                            
                            // Update UI
                            annotationCoords = data.solution;
                            coords.textContent = `Box: [${x1}, ${y1}, ${x2}, ${y2}]`;
                            status.textContent = "Existing annotation loaded. Edit or save.";
                        } else {
                            status.textContent = "Draw a bounding box and select categories";
                        }
                        
                        // Set form values based on data
                        setFormValues(data);
                    };
                    
                    currentImage.src = data.image_data;
                })
                .catch(err => {
                    console.error('Error loading image:', err);
                    status.textContent = "Failed to load image data";
                });
        }
        
        // Load the first image on page load
        window.onload = function() {
            debug('Page loaded');
            loadImage(0);
        };
    </script>
</body>
</html>""")

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Global variables
data = []
valid_indices = []

def load_data():
    """Load dataset from JSON file"""
    global data, valid_indices
    
    try:
        with open(JSON_FILE, "r") as f:
            data = json.load(f)
        
        # For this combined annotator, we want all images
        valid_indices = list(range(len(data)))
        
        if not valid_indices:
            return False, "No valid data found."
            
        return True, f"Loaded {len(valid_indices)} images for annotation"
        
    except Exception as e:
        return False, f"Failed to load data: {str(e)}"

def get_image_data(index):
    """Get image data and metadata for the given index"""
    if not valid_indices or index >= len(valid_indices):
        return None
        
    data_index = valid_indices[index]
    item = data[data_index]
    
    image_path = os.path.join(IMAGE_BASE_DIR, item["image"])
    
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            
            # Convert to base64 for embedding in HTML
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            result = {
                "index": index,
                "data_index": data_index,
                "total": len(valid_indices),
                "image_data": f"data:image/jpeg;base64,{img_str}",
                "caption": item["normal_caption"],
                "image_path": item["image"],
                "width": width,
                "height": height,
                "solution": item.get("solution", [])
            }
            
            # Include categories if they exist
            if "categories" in item:
                result["categories"] = item["categories"]
            
            return result
    except Exception as e:
        return {"error": f"Failed to load image: {str(e)}"}

def save_combined_annotation(data_index, coords, categories):
    """Save both bounding box coordinates and category annotations"""
    try:
        if data_index >= len(data):
            return False, "Invalid data index"

        # Update the coordinates if provided
        if coords:
            x1, y1, x2, y2 = map(float, coords)
            width = data[data_index]["width"]
            height = data[data_index]["height"]
            
            # Handle zero values
            width = width if width > 0 else 1
            height = height if height > 0 else 1
            
            # Calculate normalized coordinates
            norm_x1 = int(x1 / width * 1000)
            norm_y1 = int(y1 / height * 1000)
            norm_x2 = int(x2 / width * 1000)
            norm_y2 = int(y2 / height * 1000)
            
            # Update the data
            data[data_index]["solution"] = [x1, y1, x2, y2]
            data[data_index]["normalized_solution"] = [norm_x1, norm_y1, norm_x2, norm_y2]
        elif categories.get("empty_case", False):
            # If marked as empty case and no coordinates, set solution to empty
            data[data_index]["solution"] = []
            data[data_index]["normalized_solution"] = []
        
        # Update categories
        data[data_index]["categories"] = categories
        
        # Save to file
        with open(JSON_FILE, "w") as f:
            json.dump(data, f, indent=2)
            
        return True, "Annotation saved successfully"
        
    except Exception as e:
        return False, f"Failed to save annotation: {str(e)}"

# Routes
@app.route('/')
def index():
    """Render the main annotation page"""
    return render_template('combined_annotator.html')

@app.route('/api/image/<int:index>')
def get_image(index):
    """API endpoint to get image data"""
    result = get_image_data(int(index))
    if result:
        return jsonify(result)
    return jsonify({"error": "Image not found"}), 404

@app.route('/api/save_combined', methods=['POST'])
def save_combined():
    """API endpoint to save both bounding box and category annotations"""
    try:
        data = request.json
        data_index = data.get('data_index')
        coords = data.get('coords')
        categories = data.get('categories')
        
        if data_index is None or categories is None:
            return jsonify({"success": False, "message": "Invalid data"}), 400
            
        success, message = save_combined_annotation(data_index, coords, categories)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/reload')
def reload_data():
    """API endpoint to reload data"""
    success, message = load_data()
    return jsonify({"success": success, "message": message})

if __name__ == '__main__':
    # Load data at startup
    success, message = load_data()
    print(message)
    
    # Use port 5000 by default, can be changed
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 
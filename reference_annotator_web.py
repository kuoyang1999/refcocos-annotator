import os
import json
import base64
import re
from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_from_directory
from PIL import Image

# Configuration
IMAGE_BASE_DIR = "."
MULTIPLE_INSTANCES_FILE = "val2017_multiple_instances.json"
OUTPUT_FILE = "refcocos_test.json"

# Create necessary directories
os.makedirs('static', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Create HTML template for the reference annotator
with open('templates/reference_annotator.html', 'w') as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reference Bounding Box Selector and Category Labeler</title>
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
        #main-container { display: flex; flex-wrap: nowrap; height: calc(100vh - 150px); }
        #left-panel { width: 350px; overflow-y: auto; padding-right: 15px; }
        #right-panel { flex: 1; display: flex; flex-direction: column; min-width: 500px; overflow: hidden; }
        #coords { margin: 10px 0; }
        #bbox-selector { margin: 10px 0; max-height: 300px; overflow-y: auto; }
        .bbox-option { margin: 5px 0; cursor: pointer; padding: 5px; border-radius: 3px; }
        .bbox-option:hover { background-color: #eee; }
        .bbox-option.selected { background-color: #dff0d8; border: 1px solid #d6e9c6; }
        .category-info { font-weight: bold; margin: 5px 0; }
        #caption-input { width: 95%; padding: 8px; margin: 10px 0; }
        #problem-container { margin-top: 10px; }
        #image-container { flex: 1; display: flex; flex-direction: column; }
        #canvas-container { flex: 1; overflow: hidden; display: flex; align-items: center; justify-content: center; }
        #save-status { margin-left: 10px; font-weight: bold; padding: 3px 8px; border-radius: 4px; display: inline-block; }
        .status-saved { background-color: #dff0d8; color: #3c763d; border: 1px solid #d6e9c6; }
        .status-unsaved { background-color: #f2dede; color: #a94442; border: 1px solid #ebccd1; }
    </style>
</head>
<body>
    <h2>Reference Bounding Box Selector and Category Labeler</h2>
    
    <div>
        <button id="prev-btn">Previous</button>
        <button id="next-btn">Next</button>
        <button id="save-btn">Save Annotation</button>
        <span id="progress" style="margin-left: 20px;">Image 0/0</span>
        <span id="saved-indicator" class="saved-indicator">✓ Saved</span>
        <span id="save-status" class="status-unsaved">Unsaved</span>
    </div>
    
    <div id="status">Loading...</div>
    <div id="image-path"></div>
    
    <div id="main-container">
        <div id="left-panel">
            <div>
                <label for="caption-input">Caption:</label>
                <input type="text" id="caption-input" placeholder="Enter a descriptive caption for the selected object">
            </div>
            <div id="problem-container">
                <div id="problem-text"></div>
            </div>
            
            <div class="form-section">
                <h3>Available Bounding Boxes</h3>
                <div id="category-info" class="category-info">No categories with multiple instances</div>
                <div id="bbox-selector"></div>
            </div>
            
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
                        <label><input type="radio" name="hops" value="2"> 2</label>
                        <label><input type="radio" name="hops" value="3"> 3</label>
                        <label><input type="radio" name="hops" value="4"> 4</label>
                        <label><input type="radio" name="hops" value="5"> 5</label>
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
                    <div id="distractors-container">
                        <span id="distractors-value">N/A</span>
                        <span>(auto-calculated)</span>
                    </div>
                </div>
                
                <div id="coords">Selected Box: None</div>
            </div>
        </div>
        
        <div id="right-panel">
            <div id="image-container">
                <div id="canvas-container">
                    <canvas id="canvas"></canvas>
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
        const captionInput = document.getElementById('caption-input');
        const problemText = document.getElementById('problem-text');
        const imagePath = document.getElementById('image-path');
        const coords = document.getElementById('coords');
        const progress = document.getElementById('progress');
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        const saveBtn = document.getElementById('save-btn');
        const savedIndicator = document.getElementById('saved-indicator');
        const emptyCase = document.getElementById('empty-case-value');
        const distractor = document.getElementById('distractors-value');
        const bboxSelector = document.getElementById('bbox-selector');
        const categoryInfo = document.getElementById('category-info');
        
        // Form elements
        const hopsOptions = document.querySelectorAll('input[name="hops"]');
        const typeOptions = document.querySelectorAll('input[name="type"]');
        const hiddenOptions = document.querySelectorAll('input[name="hidden"]');
        
        // Variables
        let currentIndex = 0;
        let totalImages = 0;
        let currentImageData = null;
        let currentImage = new Image();
        let currentCategories = {};
        let selectedBbox = null;
        let selectedBboxIndex = -1;
        let selectedCategoryIndex = -1;
        let bboxes = [];
        let savedData = {};
        let isSavedToFile = false;
        
        // Add cache-busting parameter to all API requests
        const cacheBuster = Date.now();
        
        // Debug flag - set to true for verbose console logging
        const DEBUG = true;
        
        function debug(...args) {
            if (DEBUG) console.log(...args);
        }
        
        // Update the save status indicator
        function updateSaveStatus() {
            const saveStatus = document.getElementById('save-status');
            if (isSavedToFile) {
                saveStatus.textContent = 'Saved';
                saveStatus.className = 'status-saved';
            } else {
                saveStatus.textContent = 'Unsaved';
                saveStatus.className = 'status-unsaved';
            }
        }
        
        // Button events
        prevBtn.addEventListener('click', function() {
            if (currentIndex > 0) {
                loadImage(currentIndex - 1);
            }
        });
        
        nextBtn.addEventListener('click', function() {
            if (currentIndex < totalImages - 1) {
                loadImage(currentIndex + 1);
            }
        });
        
        saveBtn.addEventListener('click', function() {
            saveAnnotation();
        });
        
        // Caption input event
        captionInput.addEventListener('input', function() {
            updateProblemText();
            isSavedToFile = false;
            updateSaveStatus();
        });
        
        // Update problem text based on caption
        function updateProblemText() {
            const caption = captionInput.value.trim();
            if (caption) {
                problemText.textContent = `Problem: Please provide the bounding box coordinate of the region this sentence describes: ${caption}.`;
            } else {
                problemText.textContent = '';
            }
        }
        
        // Update the empty case status
        function updateEmptyCaseStatus(isEmpty) {
            emptyCase.textContent = isEmpty ? 'Yes' : 'No';
        }
        
        // Calculate distractors value based on selected bbox and category
        function calculateDistractors() {
            if (selectedBbox === null) {
                distractor.textContent = 'N/A';
                return;
            }
            
            // Check if this is an empty case
            if (selectedBbox.every(coord => coord === 0)) {
                // Sum all instances across all categories
                let totalInstances = 0;
                currentImageData.categories_with_multiple_instances.forEach(category => {
                    totalInstances += category.count;
                });
                
                // Set distractors to the total count (always showing the exact number)
                distractor.textContent = totalInstances.toString();
                return distractor.textContent;
            }
            
            if (selectedCategoryIndex === -1) {
                distractor.textContent = 'N/A';
                return;
            }
            
            const categoryData = currentImageData.categories_with_multiple_instances[selectedCategoryIndex];
            
            // Count is the total number of instances
            const totalInstances = categoryData.count;
            
            // Distractors is total - 1 (the selected one)
            const distractorsValue = totalInstances - 1;
            
            // Always show the exact number
            distractor.textContent = distractorsValue.toString();
            
            return distractor.textContent;
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
                distractors: distractor.textContent
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
            if (data && data.categories) {
                currentCategories = data.categories;
                
                // Set empty case
                updateEmptyCaseStatus(data.categories.empty_case || false);
                
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
                
                // Distractors is auto-calculated
            } else {
                // Initialize with default values
                currentCategories = {
                    empty_case: false,
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
            
            // Distractors is auto-calculated
            distractor.textContent = 'N/A';
        }
        
        // Convert COCO bbox format [x, y, width, height] to [x1, y1, x2, y2]
        function convertBboxFormat(bbox) {
            return [
                bbox[0],                 // x1
                bbox[1],                 // y1
                bbox[0] + bbox[2],       // x2 = x + width
                bbox[1] + bbox[3]        // y2 = y + height
            ];
        }
        
        // Draw bounding boxes on the canvas
        function drawBboxes() {
            // Clear the canvas and redraw the image
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(currentImage, 0, 0, canvas.width, canvas.height);
            
            if (!currentImageData || !currentImageData.categories_with_multiple_instances) {
                return;
            }
            
            const imageWidth = currentImageData.width;
            const imageHeight = currentImageData.height;
            
            // Draw all bounding boxes
            currentImageData.categories_with_multiple_instances.forEach((category, catIndex) => {
                const color = catIndex === selectedCategoryIndex ? 'red' : 'rgba(0, 0, 255, 0.7)';
                
                category.instances.forEach((bbox, bboxIndex) => {
                    // Convert from image coordinates to canvas coordinates
                    const canvasX = bbox[0] / imageWidth * canvas.width;
                    const canvasY = bbox[1] / imageHeight * canvas.height;
                    const canvasWidth = bbox[2] / imageWidth * canvas.width;
                    const canvasHeight = bbox[3] / imageHeight * canvas.height;
                    
                    // Set styling based on whether this is the selected bbox
                    const isSelected = catIndex === selectedCategoryIndex && bboxIndex === selectedBboxIndex;
                    
                    if (isSelected) {
                        // Draw selected bbox with red outline and semi-transparent fill
                        ctx.lineWidth = 3;
                        ctx.strokeStyle = 'red';
                        ctx.fillStyle = 'rgba(255, 0, 0, 0.2)';
                        
                        // Draw rectangle with fill
                        ctx.strokeRect(canvasX, canvasY, canvasWidth, canvasHeight);
                        ctx.fillRect(canvasX, canvasY, canvasWidth, canvasHeight);
                        
                        // Add category label above the bbox
                        ctx.fillStyle = 'red';
                        ctx.font = 'bold 12px Arial';
                        ctx.fillText(`${category.category_name} #${bboxIndex+1}`, canvasX, canvasY - 5);
                    } else {
                        // Draw unselected bbox with blue outline only (no fill)
                        ctx.lineWidth = 1;
                        ctx.strokeStyle = color;
                        
                        // Draw rectangle outline only
                        ctx.strokeRect(canvasX, canvasY, canvasWidth, canvasHeight);
                        
                        // Draw center point
                        const centerX = canvasX + canvasWidth / 2;
                        const centerY = canvasY + canvasHeight / 2;
                        
                        ctx.beginPath();
                        ctx.arc(centerX, centerY, 3, 0, 2 * Math.PI);
                        ctx.fillStyle = color;
                        ctx.fill();
                    }
                });
            });
        }
        
        // Create interactive bbox selector
        function createBboxSelector() {
            // Clear the selector
            bboxSelector.innerHTML = '';
            
            if (!currentImageData || !currentImageData.categories_with_multiple_instances) {
                categoryInfo.textContent = 'No categories with multiple instances';
                return;
            }
            
            if (currentImageData.categories_with_multiple_instances.length === 0) {
                categoryInfo.textContent = 'No categories with multiple instances';
                return;
            }
            
            categoryInfo.textContent = `${currentImageData.categories_with_multiple_instances.length} categories with multiple instances:`;
            
            // Add Empty Case option at the top
            const emptyDiv = document.createElement('div');
            emptyDiv.className = 'category-section';
            emptyDiv.innerHTML = `<div style="margin: 10px 0; font-weight: bold; color: ${selectedBbox && selectedBbox.every(coord => coord === 0) ? 'red' : 'blue'};">Empty Case Option</div>`;
            
            const emptyBboxDiv = document.createElement('div');
            emptyBboxDiv.className = 'bbox-option';
            if (selectedBbox && selectedBbox.every(coord => coord === 0)) {
                emptyBboxDiv.classList.add('selected');
            }
            
            emptyBboxDiv.textContent = `No bounding box [0, 0, 0, 0]`;
            
            // Selection event for empty case
            emptyBboxDiv.addEventListener('click', () => {
                // Update selection to empty case
                selectedCategoryIndex = -1;
                selectedBboxIndex = -1;
                selectedBbox = [0, 0, 0, 0];
                
                // Update UI
                coords.textContent = `Selected Box: [0, 0, 0, 0] (Empty Case)`;
                updateEmptyCaseStatus(true);
                calculateDistractors();
                isSavedToFile = false;
                updateSaveStatus();
                
                // Redraw all bboxes with new selection
                createBboxSelector();
                drawBboxes();
            });
            
            emptyDiv.appendChild(emptyBboxDiv);
            bboxSelector.appendChild(emptyDiv);
            
            // For each category with multiple instances
            currentImageData.categories_with_multiple_instances.forEach((category, catIndex) => {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'category-section';
                categoryDiv.innerHTML = `<div style="margin: 10px 0; font-weight: bold; color: ${catIndex === selectedCategoryIndex ? 'red' : 'blue'};">${category.category_name} (${category.count} instances)</div>`;
                
                // For each bbox in this category
                category.instances.forEach((bbox, bboxIndex) => {
                    const bboxDiv = document.createElement('div');
                    bboxDiv.className = 'bbox-option';
                    if (catIndex === selectedCategoryIndex && bboxIndex === selectedBboxIndex) {
                        bboxDiv.classList.add('selected');
                    }
                    
                    // Format coordinates
                    const [x, y, w, h] = bbox;
                    bboxDiv.textContent = `Box ${bboxIndex + 1}: [${Math.round(x)}, ${Math.round(y)}, ${Math.round(w)}, ${Math.round(h)}]`;
                    
                    // Selection event
                    bboxDiv.addEventListener('click', () => {
                        // Update selection
                        selectedCategoryIndex = catIndex;
                        selectedBboxIndex = bboxIndex;
                        selectedBbox = convertBboxFormat(bbox);
                        
                        // Update UI
                        coords.textContent = `Selected Box: [${selectedBbox.join(', ')}]`;
                        updateEmptyCaseStatus(false);
                        calculateDistractors();
                        isSavedToFile = false;
                        updateSaveStatus();
                        
                        // Redraw all bboxes with new selection
                        createBboxSelector();
                        drawBboxes();
                    });
                    
                    categoryDiv.appendChild(bboxDiv);
                });
                
                bboxSelector.appendChild(categoryDiv);
            });
        }
        
        // Check if the annotation is valid for saving
        function validateAnnotation() {
            // Get caption and validate
            const caption = captionInput.value.trim();
            if (!caption) {
                alert('Please enter a caption for the selected region');
                return false;
            }
            
            // Check if bbox is selected
            if (selectedBbox === null) {
                alert('Please select a bounding box or mark as empty case');
                return false;
            }
            
            // Get form data
            const formData = getFormData();
            
            // Check if hops is selected
            if (!formData.hops) {
                alert('Please select hops value');
                return false;
            }
            
            // Check if hidden is selected
            if (formData.hidden === null) {
                alert('Please select whether it is hidden or not');
                return false;
            }
            
            return true;
        }
        
        // Check if the annotation is already saved in the output file
        function checkIfSavedInFile(imageId, annotationData) {
            // This uses the savedData cache which is loaded from the output file
            return !!savedData[imageId];
        }
        
        // Save annotation with selected bbox and categories
        function saveAnnotation(callback) {
            if (!validateAnnotation()) {
                return;
            }
            
            // Get caption
            const caption = captionInput.value.trim();
            
            // Get category form data
            const formData = getFormData();
            
            // Create annotation data
            const annotationData = {
                dataset: "refcocos_test",
                text_type: "caption",
                height: currentImageData.height,
                width: currentImageData.width,
                normal_caption: caption,
                image: "val2017/" + currentImageData.file_name,
                problem: `Please provide the bounding box coordinate of the region this sentence describes: ${caption}.`,
                solution: selectedBbox,
                normalized_solution: calculateNormalizedSolution(selectedBbox, currentImageData.width, currentImageData.height),
                categories: formData
            };
            
            debug('Saving annotation', annotationData);
            
            // Send to server to save
            fetch(`/api/save_reference?cache=${cacheBuster}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image_id: currentImageData.image_id,
                    annotation: annotationData
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Store saved data for this image
                    savedData[currentImageData.image_id] = annotationData;
                    
                    // Update current categories
                    currentCategories = formData;
                    
                    // Mark as saved
                    isSavedToFile = true;
                    updateSaveStatus();
                    
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
        
        // Calculate normalized solution coordinates
        function calculateNormalizedSolution(bbox, width, height) {
            if (!bbox) return [];
            
            const [x1, y1, x2, y2] = bbox;
            
            // Calculate normalized coordinates (0-1000 range)
            const norm_x1 = Math.round(x1 / width * 1000);
            const norm_y1 = Math.round(y1 / height * 1000);
            const norm_x2 = Math.round(x2 / width * 1000);
            const norm_y2 = Math.round(y2 / height * 1000);
            
            return [norm_x1, norm_y1, norm_x2, norm_y2];
        }
        
        // Format image path to val2017/xxxxx
        function formatImagePath(path) {
            const regex = /.*\/([^\/]+)$/;
            const match = path.match(regex);
            if (match && match[1]) {
                return "val2017/" + match[1];
            }
            return path;
        }
        
        // Find the index of the first unsaved image
        function findFirstUnsavedImageIndex() {
            debug('Finding first unsaved image...');
            
            return new Promise((resolve, reject) => {
                // First get the total images from the loaded data
                fetch(`/api/image_status?cache=${cacheBuster}`)
                    .then(response => response.json())
                    .then(data => {
                        const totalImages = data.total_images;
                        const savedImageIds = data.saved_image_ids;
                        const savedAnnotations = data.saved_annotations || {};
                        
                        // Store saved annotations in the savedData object
                        for (const [imageId, annotation] of Object.entries(savedAnnotations)) {
                            savedData[imageId] = annotation;
                        }
                        
                        debug(`Found ${totalImages} total images, ${savedImageIds.length} already saved`);
                        debug('Saved data loaded:', Object.keys(savedData).length, 'images');
                        
                        // Function to check each image sequentially
                        function checkImageSequentially(index) {
                            if (index >= totalImages) {
                                // If we've checked all images and none are unsaved, return to the first image
                                debug('All images appear to be saved, starting at image 0');
                                resolve(0);
                                return;
                            }
                            
                            fetch(`/api/image/${index}?cache=${cacheBuster}`)
                                .then(response => response.json())
                                .then(data => {
                                    if (data.error) {
                                        checkImageSequentially(index + 1);
                                        return;
                                    }
                                    
                                    // Check if this image's ID is in the saved list
                                    const isSaved = savedImageIds.includes(data.image_id);
                                    
                                    if (!isSaved) {
                                        // Found an unsaved image
                                        debug(`Found unsaved image at index ${index}, image_id: ${data.image_id}`);
                                        resolve(index);
                                    } else {
                                        // This image is saved, check the next one
                                        debug(`Image at index ${index} is already saved, checking next`);
                                        checkImageSequentially(index + 1);
                                    }
                                })
                                .catch(err => {
                                    console.error('Error checking image:', err);
                                    checkImageSequentially(index + 1);
                                });
                        }
                        
                        // Start checking from the first image
                        checkImageSequentially(0);
                    })
                    .catch(err => {
                        console.error('Error getting image status:', err);
                        resolve(0); // Default to first image on error
                    });
            });
        }
        
        // Load image and bbox data
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
                    
                    // Store current image data
                    currentIndex = index;
                    currentImageData = data;
                    totalImages = data.total_images;
                    
                    // Reset selection
                    selectedBbox = null;
                    selectedBboxIndex = -1;
                    selectedCategoryIndex = -1;
                    
                    // Update UI
                    progress.textContent = `Image ${index + 1}/${totalImages}`;
                    const formattedPath = formatImagePath(data.path);
                    imagePath.textContent = `Image: ${formattedPath}`;
                    prevBtn.disabled = currentIndex === 0;
                    nextBtn.disabled = currentIndex === totalImages - 1;
                    
                    // Clear caption and coords
                    captionInput.value = '';
                    problemText.textContent = '';
                    coords.textContent = 'Selected Box: None';
                    
                    // Check if this image has saved data
                    debug('Checking for saved data for image ID:', data.image_id);
                    debug('Available saved data keys:', Object.keys(savedData));
                    
                    // Load previously saved data for this image if available
                    if (savedData[data.image_id]) {
                        debug('Found saved data for image:', data.image_id);
                        const saved = savedData[data.image_id];
                        captionInput.value = saved.normal_caption || '';
                        updateProblemText();
                        
                        if (saved.solution && saved.solution.length === 4) {
                            selectedBbox = saved.solution;
                            coords.textContent = `Selected Box: [${selectedBbox.join(', ')}]`;
                            
                            // Try to find the matching bbox in the current data
                            let matchFound = false;
                            const isEmptyBox = selectedBbox.every(coord => coord === 0);
                            
                            if (isEmptyBox) {
                                // This is an empty case
                                updateEmptyCaseStatus(true);
                                matchFound = true;
                            } else {
                                data.categories_with_multiple_instances.forEach((category, catIndex) => {
                                    category.instances.forEach((bbox, bboxIndex) => {
                                        const convertedBbox = convertBboxFormat(bbox);
                                        if (JSON.stringify(convertedBbox) === JSON.stringify(selectedBbox)) {
                                            selectedCategoryIndex = catIndex;
                                            selectedBboxIndex = bboxIndex;
                                            matchFound = true;
                                        }
                                    });
                                });
                            }
                            
                            if (!matchFound) {
                                debug('Warning: Could not match the saved bbox to any current bbox');
                            }
                        }
                        
                        setFormValues(saved);
                        isSavedToFile = true;
                        debug('Marked as saved in file');
                    } else {
                        debug('No saved data found for this image');
                        // Initialize with default values
                        updateEmptyCaseStatus(false);
                        clearFormSelections();
                        isSavedToFile = false;
                    }
                    
                    // Update save status indicator
                    updateSaveStatus();
                    
                    // Calculate distractors
                    calculateDistractors();
                    
                    // Load the image
                    debug('Loading image source', data.path);
                    currentImage = new Image();
                    currentImage.onload = function() {
                        debug('Image loaded', this.width, this.height);
                        
                        // Calculate canvas size to fill the container
                        const container = document.getElementById('canvas-container');
                        const containerWidth = container.clientWidth;
                        const containerHeight = container.clientHeight;
                        
                        const imageRatio = this.width / this.height;
                        const containerRatio = containerWidth / containerHeight;
                        
                        let canvasWidth, canvasHeight;
                        
                        if (imageRatio > containerRatio) {
                            // Image is wider than container
                            canvasWidth = containerWidth;
                            canvasHeight = containerWidth / imageRatio;
                        } else {
                            // Image is taller than container
                            canvasHeight = containerHeight;
                            canvasWidth = containerHeight * imageRatio;
                        }
                        
                        canvas.width = canvasWidth;
                        canvas.height = canvasHeight;
                        
                        // Draw image and bboxes
                        drawBboxes();
                        
                        // Create interactive bbox selector
                        createBboxSelector();
                        
                        status.textContent = isSavedToFile ? 
                            "This image has been previously annotated" : 
                            "Select a bounding box and add a caption";
                    };
                    
                    currentImage.onerror = function() {
                        console.error('Failed to load image');
                        status.textContent = "Error loading image";
                    };
                    
                    currentImage.src = data.image_data;
                })
                .catch(err => {
                    console.error('Error loading image data:', err);
                    status.textContent = "Failed to load image data";
                });
        }
        
        // Load the first image on page load
        window.onload = function() {
            debug('Page loaded');
            
            // Fetch initial data
            fetch(`/api/reload?cache=${cacheBuster}`)
                .then(response => response.json())
                .then(data => {
                    debug('Initial data loaded');
                    
                    // First load all saved data
                    return fetch(`/api/saved_data?cache=${cacheBuster}`)
                        .then(response => response.json())
                        .then(data => {
                            // Store all saved data
                            savedData = data;
                            debug('Loaded saved data for', Object.keys(savedData).length, 'images');
                            
                            // Now find the first unsaved image
                            return findFirstUnsavedImageIndex();
                        });
                })
                .then(index => {
                    debug('Starting with image at index:', index);
                    loadImage(index);
                    updateSaveStatus();
                })
                .catch(err => {
                    console.error('Error during initialization:', err);
                    loadImage(0); // Default to first image on error
                    updateSaveStatus();
                });
            
            // Handle window resize
            window.addEventListener('resize', function() {
                if (currentImage.complete) {
                    // Recalculate canvas size
                    const container = document.getElementById('canvas-container');
                    const containerWidth = container.clientWidth;
                    const containerHeight = container.clientHeight;
                    
                    const imageRatio = currentImage.width / currentImage.height;
                    const containerRatio = containerWidth / containerHeight;
                    
                    let canvasWidth, canvasHeight;
                    
                    if (imageRatio > containerRatio) {
                        // Image is wider than container
                        canvasWidth = containerWidth;
                        canvasHeight = containerWidth / imageRatio;
                    } else {
                        // Image is taller than container
                        canvasHeight = containerHeight;
                        canvasWidth = containerHeight * imageRatio;
                    }
                    
                    canvas.width = canvasWidth;
                    canvas.height = canvasHeight;
                    
                    // Redraw image and bboxes
                    drawBboxes();
                }
            });
        };
    </script>
</body>
</html>""")

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Global variables
multiple_instances_data = None
output_data = []

def load_data():
    """Load multiple instances data and any existing output data"""
    global multiple_instances_data, output_data
    
    try:
        # Load multiple instances data
        with open(MULTIPLE_INSTANCES_FILE, "r") as f:
            multiple_instances_data = json.load(f)
        
        # Try to load existing output data if it exists
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, "r") as f:
                output_data = json.load(f)
        
        # If output file doesn't exist yet, initialize with empty array
        if not isinstance(output_data, list):
            output_data = []
        
        return True, f"Loaded {len(multiple_instances_data['images'])} images with multiple instances"
    except Exception as e:
        return False, f"Failed to load data: {str(e)}"

def get_image_data(index):
    """Get image data and metadata for the given index"""
    if not multiple_instances_data or index >= len(multiple_instances_data["images"]):
        return {"error": "Image not found"}
    
    image_data = multiple_instances_data["images"][index]
    
    # Load the image
    image_path = image_data["path"]
    
    try:
        with Image.open(image_path) as img:
            # Convert to base64 for embedding in HTML
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Create response with image data and all information
            result = {
                "index": index,
                "total_images": len(multiple_instances_data["images"]),
                "image_data": f"data:image/jpeg;base64,{img_str}",
                "image_id": image_data["image_id"],
                "file_name": image_data["file_name"],
                "width": image_data["width"],
                "height": image_data["height"],
                "path": image_data["path"],
                "categories_with_multiple_instances": image_data["categories_with_multiple_instances"]
            }
            
            return result
    except Exception as e:
        return {"error": f"Failed to load image: {str(e)}"}

def save_reference_annotation(image_id, annotation):
    """Save a reference annotation for the specified image"""
    global output_data
    
    try:
        # Check if this image already has an annotation
        existing_index = -1
        for i, item in enumerate(output_data):
            if item.get("image") == annotation["image"]:
                existing_index = i
                break
        
        # Update existing or add new
        if existing_index >= 0:
            output_data[existing_index] = annotation
        else:
            output_data.append(annotation)
        
        # Save to file
        with open(OUTPUT_FILE, "w") as f:
            json.dump(output_data, f, indent=2)
            
        return True, "Annotation saved successfully"
    except Exception as e:
        return False, f"Failed to save annotation: {str(e)}"

# Routes
@app.route('/')
def index():
    """Render the main annotation page"""
    return render_template('reference_annotator.html')

@app.route('/api/image/<int:index>')
def get_image(index):
    """API endpoint to get image data"""
    result = get_image_data(int(index))
    return jsonify(result)

@app.route('/api/save_reference', methods=['POST'])
def save_reference():
    """API endpoint to save reference annotation"""
    try:
        data = request.json
        image_id = data.get('image_id')
        annotation = data.get('annotation')
        
        if image_id is None or annotation is None:
            return jsonify({"success": False, "message": "Invalid data"}), 400
            
        success, message = save_reference_annotation(image_id, annotation)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/reload')
def reload_data():
    """API endpoint to reload data"""
    success, message = load_data()
    return jsonify({"success": success, "message": message})

@app.route('/api/image_status')
def get_image_status():
    """API endpoint to get image status information"""
    if not multiple_instances_data:
        return jsonify({"error": "No data loaded"}), 404
        
    # Get total number of images
    total_images = len(multiple_instances_data["images"])
    
    # Get list of saved image IDs
    saved_image_ids = []
    saved_annotations = {}
    for item in output_data:
        # Extract image ID from path
        image_path = item.get("image", "")
        if image_path:
            # Try to find matching image from multiple_instances_data
            for img in multiple_instances_data["images"]:
                if "val2017/" + img["file_name"] == image_path:
                    img_id = img["image_id"]
                    saved_image_ids.append(img_id)
                    saved_annotations[img_id] = item
                    break
    
    return jsonify({
        "total_images": total_images,
        "saved_image_ids": saved_image_ids,
        "saved_annotations": saved_annotations
    })

# Create a new endpoint to provide saved data
@app.route('/api/saved_data')
def get_saved_data():
    """API endpoint to get all saved annotations"""
    # Create a dictionary mapping image IDs to saved annotations
    saved_data = {}
    
    for item in output_data:
        # Extract image ID from path
        image_path = item.get("image", "")
        if image_path:
            # Try to find matching image from multiple_instances_data
            for img in multiple_instances_data["images"]:
                if "val2017/" + img["file_name"] == image_path:
                    saved_data[img["image_id"]] = item
                    break
    
    return jsonify(saved_data)

if __name__ == '__main__':
    # Load data at startup
    success, message = load_data()
    print(message)
    
    # Use port 5000 by default, can be changed
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 
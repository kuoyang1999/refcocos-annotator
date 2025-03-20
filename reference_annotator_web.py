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
        #canvas-container { flex: 1; overflow: hidden; display: flex; align-items: center; justify-content: center; position: relative; }
        #save-status { margin-left: 10px; font-weight: bold; padding: 3px 8px; border-radius: 4px; display: inline-block; }
        .status-saved { background-color: #dff0d8; color: #3c763d; border: 1px solid #d6e9c6; }
        .status-unsaved { background-color: #f2dede; color: #a94442; border: 1px solid #ebccd1; }
        .toggle-active { background-color: #5cb85c; color: white; }
        #toggle-view-icon { 
            position: absolute; 
            top: 10px; 
            left: 10px; 
            font-size: 20px; 
            cursor: pointer; 
            background-color: rgba(255,255,255,0.7); 
            border-radius: 4px; 
            width: 34px; 
            height: 34px; 
            display: flex; 
            align-items: center; 
            justify-content: center;
            z-index: 100;
            transition: all 0.2s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        }
        #toggle-view-icon:hover {
            background-color: rgba(255,255,255,0.9);
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        #toggle-view-icon.active {
            color: #5cb85c;
        }
        .button-group {
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }
        .danger-button {
            background-color: #d9534f;
            color: white;
            border: 1px solid #d43f3a;
        }
        .danger-button:hover:not(:disabled) {
            background-color: #c9302c;
        }
    </style>
</head>
<body>
    <div class="button-group">
        <button id="prev-btn">Previous</button>
        <button id="next-btn">Next</button>
        <span id="progress" style="margin-left: 20px;">Image 0/0</span>
        <span id="saved-indicator" class="saved-indicator">✓ Saved</span>
        <span id="save-status" class="status-unsaved">Unsaved</span>
    </div>
    
    <div class="button-group">
        <button id="prev-annotation-btn">Previous Annotation</button>
        <button id="next-annotation-btn">Next Annotation</button>
        <button id="new-annotation-btn">New Annotation</button>
        <button id="save-btn">Save Annotation</button>
        <button id="delete-annotation-btn" class="danger-button">Delete Annotation</button>
        <span id="annotation-progress" style="margin-left: 20px;">Annotation 0/0</span>
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
                        <label><input type="checkbox" name="type" value="attr"> Attr</label>
                    </div>
                </div>

                <div class="option-group">
                    <label><b>3. Occluded:</b></label><br>
                    <div id="occluded-options">
                        <label><input type="radio" name="occluded" value="true"> Yes</label>
                        <label><input type="radio" name="occluded" value="false"> No</label>
                    </div>
                </div>

                <div class="option-group">
                    <label><b>4. Distractors:</b></label><br>
                    <div id="distractors-container">
                        <span id="distractors-value">N/A</span>
                        <span>(auto-calculated)</span>
                    </div>
                </div>
            </div>
        </div>

        <div id="right-panel">
            <div id="image-container">
                <div id="canvas-container">
                    <div id="toggle-view-icon" title="Toggle view mode">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="show-all-icon">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                        </svg>
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="show-selected-icon" style="display: none;">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                            <line x1="1" y1="1" x2="23" y2="23"></line>
                        </svg>
                    </div>
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
        const toggleViewIcon = document.getElementById('toggle-view-icon');
        const showAllIcon = toggleViewIcon.querySelector('.show-all-icon');
        const showSelectedIcon = toggleViewIcon.querySelector('.show-selected-icon');

        // Form elements
        const hopsOptions = document.querySelectorAll('input[name="hops"]');
        const typeOptions = document.querySelectorAll('input[name="type"]');
        const occludedOptions = document.querySelectorAll('input[name="occluded"]');

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
        let showOnlySelected = false;
        let isDrawingCustomBox = false;
        let customBoxStartX = 0;
        let customBoxStartY = 0;
        let customBoxCoords = null;
        let savedCustomBoxCoords = null;  // Store custom box coordinates when switching selections
        let currentAnnotationIndex = 0;
        let totalAnnotations = 0;
        let currentAnnotationId = null;

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

        // Annotation navigation buttons
        const prevAnnotationBtn = document.getElementById('prev-annotation-btn');
        const nextAnnotationBtn = document.getElementById('next-annotation-btn');
        const newAnnotationBtn = document.getElementById('new-annotation-btn');
        const deleteAnnotationBtn = document.getElementById('delete-annotation-btn');
        const annotationProgress = document.getElementById('annotation-progress');

        prevAnnotationBtn.addEventListener('click', function() {
            if (currentAnnotationIndex > 0) {
                loadAnnotation(currentIndex, currentAnnotationIndex - 1);
            }
        });

        nextAnnotationBtn.addEventListener('click', function() {
            if (currentAnnotationIndex < totalAnnotations - 1) {
                loadAnnotation(currentIndex, currentAnnotationIndex + 1);
            }
        });

        newAnnotationBtn.addEventListener('click', function() {
            // Create a new annotation for the current image
            createNewAnnotation();
        });
        
        // Add delete annotation functionality
        deleteAnnotationBtn.addEventListener('click', function() {
            if (!savedData[currentImageData.image_id] || 
                savedData[currentImageData.image_id].length === 0 || 
                !currentAnnotationId) {
                alert('No annotation to delete');
                return;
            }
            
            if (confirm('Are you sure you want to delete this annotation?')) {
                deleteAnnotation();
            }
        });

        // Replace toggle boxes button with eye icon
        toggleViewIcon.addEventListener('click', function() {
            showOnlySelected = !showOnlySelected;
            if (showOnlySelected) {
                toggleViewIcon.classList.add('active');
                toggleViewIcon.title = 'Show all boxes';
                showAllIcon.style.display = 'none';
                showSelectedIcon.style.display = 'block';
            } else {
                toggleViewIcon.classList.remove('active');
                toggleViewIcon.title = 'Show only selected';
                showAllIcon.style.display = 'block';
                showSelectedIcon.style.display = 'none';
            }
            drawBboxes();
        });

        saveBtn.addEventListener('click', function() {
            saveAnnotation();
        });

        // Caption input event
        captionInput.addEventListener('input', function() {
            updateProblemText();
            isSavedToFile = false;
            updateSaveStatus();
            updateStatusMessage();
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

            // When changing to empty case, ensure selectedBbox is null
            if (isEmpty && selectedBbox !== null) {
                selectedBbox = null;
                coords.textContent = `Selected Box: null (Empty Case)`;
            }
        }

        // Calculate distractors value based on selected bbox and category
        function calculateDistractors() {
            if (selectedBbox === null) {
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

        // Add distractors manual edit functionality
        function setupDistractorEdit() {
            const distractorContainer = document.getElementById('distractors-container');
            
            // Clear existing content
            distractorContainer.innerHTML = '';
            
            // Create input field for manual editing
            const inputField = document.createElement('input');
            inputField.type = 'number';
            inputField.min = '0';
            inputField.id = 'distractors-input';
            inputField.value = distractor.textContent === 'N/A' ? '0' : distractor.textContent;
            inputField.style.width = '60px';
            inputField.style.marginRight = '10px';
            
            // Add label and auto-calculated info
            const label = document.createElement('span');
            label.innerHTML = '(auto: <span id="auto-distractor-value">' + 
                (distractor.textContent === 'N/A' ? '0' : distractor.textContent) + 
                '</span>)';
            
            // Add event listener for input changes
            inputField.addEventListener('input', function() {
                distractor.textContent = this.value;
                isSavedToFile = false;
                updateSaveStatus();
            });
            
            // Append elements to container
            distractorContainer.appendChild(inputField);
            distractorContainer.appendChild(label);
        }

        // Update setupDistractorEdit call after calculateDistractors
        const originalCalculateDistractors = calculateDistractors;
        calculateDistractors = function() {
            const result = originalCalculateDistractors.apply(this, arguments);
            setupDistractorEdit();
            return result;
        };

        // Remove the coords element completely
        const coordsElement = document.getElementById('coords');
        if (coordsElement) {
            coordsElement.parentNode.removeChild(coordsElement);
        }

        // Alternatively, just hide it if removal causes layout issues
        // if (coordsElement) {
        //     coordsElement.style.display = 'none';
        // }

        // Get all form data as an object
        function getFormData() {
            const formData = {
                empty_case: emptyCase.textContent === 'Yes',
                hops: getSelectedRadioValue(hopsOptions),
                type: Array.from(typeOptions)
                    .filter(cb => cb.checked)
                    .map(cb => cb.value),
                occluded: getSelectedRadioValue(occludedOptions) === 'true',
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

                // Set occluded
                if (data.categories.occluded !== undefined) {
                    setRadioValue(occludedOptions, data.categories.occluded.toString());
                }

                // Distractors is auto-calculated
            } else {
                // Initialize with default values
                currentCategories = {
                    empty_case: false,
                    hops: null,
                    type: [],
                    occluded: false,
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

            // Set occluded to "No" by default
            setRadioValue(occludedOptions, 'false');

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
                    const isSelected = catIndex === selectedCategoryIndex && bboxIndex === selectedBboxIndex;

                    // Skip drawing unselected boxes if showOnlySelected is true
                    if (showOnlySelected && !isSelected) {
                        return;
                    }

                    // Convert from image coordinates to canvas coordinates
                    const canvasX = bbox[0] / imageWidth * canvas.width;
                    const canvasY = bbox[1] / imageHeight * canvas.height;
                    const canvasWidth = bbox[2] / imageWidth * canvas.width;
                    const canvasHeight = bbox[3] / imageHeight * canvas.height;

                    // Set styling based on whether this is the selected bbox
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

            // Draw custom box if it exists
            if (customBoxCoords) {
                const [x1, y1, x2, y2] = customBoxCoords;
                const canvasX1 = x1 / imageWidth * canvas.width;
                const canvasY1 = y1 / imageHeight * canvas.height;
                const canvasX2 = x2 / imageWidth * canvas.width;
                const canvasY2 = y2 / imageHeight * canvas.height;

                ctx.lineWidth = 3;
                ctx.strokeStyle = 'green';
                ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
                ctx.strokeRect(canvasX1, canvasY1, canvasX2 - canvasX1, canvasY2 - canvasY1);
                ctx.fillRect(canvasX1, canvasY1, canvasX2 - canvasX1, canvasY2 - canvasY1);
            }
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
            emptyDiv.innerHTML = `<div style="margin: 10px 0; font-weight: bold; color: ${selectedBbox === null && !customBoxCoords && !isDrawingCustomBox ? 'red' : 'blue'};">Empty Case Option</div>`;

            const emptyBboxDiv = document.createElement('div');
            emptyBboxDiv.className = 'bbox-option';
            if (selectedBbox === null && !customBoxCoords && !isDrawingCustomBox) {
                emptyBboxDiv.classList.add('selected');
            }

            emptyBboxDiv.textContent = `No bounding box (Empty Case)`;

            // Selection event for empty case
            emptyBboxDiv.addEventListener('click', () => {
                // Save custom box coords before changing selection
                if (customBoxCoords !== null) {
                    savedCustomBoxCoords = [...customBoxCoords];
                }
                
                // Update selection to empty case
                selectedCategoryIndex = -1;
                selectedBboxIndex = -1;
                selectedBbox = null;
                customBoxCoords = null;
                isDrawingCustomBox = false;

                // Update UI
                updateEmptyCaseStatus(true);
                calculateDistractors();
                isSavedToFile = false;
                updateSaveStatus();
                updateStatusMessage();

                // Redraw all bboxes with new selection
                createBboxSelector();
                drawBboxes();
            });

            emptyDiv.appendChild(emptyBboxDiv);
            bboxSelector.appendChild(emptyDiv);

            // Add Custom Box option
            const customDiv = document.createElement('div');
            customDiv.className = 'category-section';
            customDiv.innerHTML = `<div style="margin: 10px 0; font-weight: bold; color: ${customBoxCoords !== null || isDrawingCustomBox ? 'red' : 'blue'};">Custom Box Option</div>`;

            const customBboxDiv = document.createElement('div');
            customBboxDiv.className = 'bbox-option';
            if (customBoxCoords !== null || isDrawingCustomBox) {
                customBboxDiv.classList.add('selected');
            }

            customBboxDiv.textContent = customBoxCoords ? 
                `Custom Box: [${customBoxCoords.join(', ')}]` : 
                `Draw custom bounding box`;

            // Selection event for custom box
            customBboxDiv.addEventListener('click', () => {
                // Restore saved custom box coords if they exist
                if (savedCustomBoxCoords !== null) {
                    customBoxCoords = [...savedCustomBoxCoords];
                }
                
                // Always activate drawing mode
                isDrawingCustomBox = true;
                
                // Clear other selections
                selectedCategoryIndex = -1;
                selectedBboxIndex = -1;
                selectedBbox = null;
                
                // Update UI
                updateEmptyCaseStatus(false);
                calculateDistractors();
                isSavedToFile = false;
                updateSaveStatus();
                status.textContent = "Click and drag to draw a custom bounding box";

                // Redraw all bboxes with new selection
                createBboxSelector();
                drawBboxes();
            });

            customDiv.appendChild(customBboxDiv);
            bboxSelector.appendChild(customDiv);

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
                        // Save custom box coords before changing selection
                        if (customBoxCoords !== null) {
                            savedCustomBoxCoords = [...customBoxCoords];
                        }
                        
                        // Update selection
                        selectedCategoryIndex = catIndex;
                        selectedBboxIndex = bboxIndex;
                        selectedBbox = convertBboxFormat(bbox);
                        customBoxCoords = null;
                        isDrawingCustomBox = false;

                        // Update UI
                        updateEmptyCaseStatus(false);
                        calculateDistractors();
                        isSavedToFile = false;
                        updateSaveStatus();
                        updateStatusMessage();

                        // Redraw all bboxes with new selection
                        createBboxSelector();
                        drawBboxes();
                    });

                    categoryDiv.appendChild(bboxDiv);
                });

                bboxSelector.appendChild(categoryDiv);
            });
        }

        // Add function to update status message based on current state
        function updateStatusMessage() {
            // Check what's missing: bbox, caption, category labels
            const hasBbox = selectedBbox !== null || customBoxCoords !== null;
            const hasCaption = captionInput.value.trim() !== '';
            const hasHops = getSelectedRadioValue(hopsOptions) !== null;
            const hasType = Array.from(typeOptions).some(cb => cb.checked);
            const hasOccluded = getSelectedRadioValue(occludedOptions) !== null;
            
            // Build status message
            let message = "";
            let missing = [];
            
            if (!hasBbox) missing.push("bounding box");
            if (!hasCaption) missing.push("caption");
            if (!hasHops) missing.push("hops value");
            if (!hasType) missing.push("type");
            if (!hasOccluded) missing.push("occluded status");
            
            if (missing.length > 0) {
                message = "Please select/provide " + missing.join(", ");
            } else {
                message = "Ready to save";
            }
            
            status.textContent = message;
        }

        // Check if the annotation is valid for saving
        function validateAnnotation() {
            // Get caption and validate
            const caption = captionInput.value.trim();
            if (!caption) {
                alert('Please enter a caption for the selected region');
                return false;
            }

            // Get form data
            const formData = getFormData();

            // For empty cases, selectedBbox should be null
            if (formData.empty_case) {
                if (selectedBbox !== null) {
                    alert('Empty case should have null bounding box');
                    return false;
                }
            } else {
                // For non-empty cases, selectedBbox should not be null
                if (selectedBbox === null) {
                    alert('Please select a bounding box');
                    return false;
                }
            }

            // Check if hops is selected
            if (!formData.hops) {
                alert('Please select hops value');
                return false;
            }

            // Check if occluded is selected
            if (formData.occluded === null) {
                alert('Please select whether it is occluded or not');
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
                annotation_id: currentAnnotationId || `${currentImageData.image_id}_${Date.now()}`,
                dataset: "refcocos_test",
                text_type: "caption",
                height: currentImageData.height,
                width: currentImageData.width,
                normal_caption: caption,
                image: "val2017/" + currentImageData.file_name,
                file_name: currentImageData.file_name,
                problem: `Please provide the bounding box coordinate of the region this sentence describes: ${caption}.`,
                solution: customBoxCoords || selectedBbox,
                normalized_solution: calculateNormalizedSolution(customBoxCoords || selectedBbox, currentImageData.width, currentImageData.height),
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
                    // Store current annotation ID
                    currentAnnotationId = annotationData.annotation_id;
                    
                    // Update saved data for this image
                    if (!savedData[currentImageData.image_id]) {
                        savedData[currentImageData.image_id] = [];
                    }
                    
                    // Update or add the annotation in the savedData array
                    let found = false;
                    for (let i = 0; i < savedData[currentImageData.image_id].length; i++) {
                        if (savedData[currentImageData.image_id][i].annotation_id === currentAnnotationId) {
                            savedData[currentImageData.image_id][i] = annotationData;
                            found = true;
                            break;
                        }
                    }
                    
                    if (!found) {
                        savedData[currentImageData.image_id].push(annotationData);
                        totalAnnotations = savedData[currentImageData.image_id].length;
                        currentAnnotationIndex = totalAnnotations - 1;
                        updateAnnotationProgress();
                    }

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
            if (!bbox) return null;

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

        // Find the index of the last saved image based on the order in val2017_multiple_instance.json
        function findLastSavedImageIndex() {
            debug('Finding last saved image...');

            return new Promise((resolve, reject) => {
                // Use the dedicated endpoint to get the last saved index directly
                fetch(`/api/last_saved_index?cache=${cacheBuster}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            debug('Error getting last saved index:', data.error);
                            resolve(0); // Default to first image
                            return;
                        }

                        const lastIndex = data.index;
                        debug(`Last saved image found at index ${lastIndex}`);
                        
                        // First load all saved data
                        return fetch(`/api/saved_data?cache=${cacheBuster}`)
                            .then(response => response.json())
                            .then(savedDataResponse => {
                                // Store all saved data
                                savedData = savedDataResponse;
                                debug('Loaded saved data for', Object.keys(savedData).length, 'images');
                                resolve(lastIndex);
                            });
                    })
                    .catch(err => {
                        console.error('Error finding last saved image:', err);
                        resolve(0); // Default to first image on error
                    });
            });
        }

        // Load image and bbox data
        function loadImage(index, callback) {
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

                    // Reset selection - at initial stage nothing should be selected
                    selectedBbox = null;
                    selectedBboxIndex = -1;
                    selectedCategoryIndex = -1;
                    customBoxCoords = null;
                    savedCustomBoxCoords = null;
                    isDrawingCustomBox = false;
                    currentAnnotationId = null;
                    currentAnnotationIndex = 0;
                    totalAnnotations = 0;

                    // Update UI
                    progress.textContent = `Image ${index + 1}/${totalImages}`;
                    const formattedPath = formatImagePath(data.path);
                    imagePath.textContent = `Image ${index + 1}/${totalImages}: ${formattedPath}`;
                    prevBtn.disabled = currentIndex === 0;
                    nextBtn.disabled = currentIndex === totalImages - 1;

                    // Clear caption and problem text
                    captionInput.value = '';
                    problemText.textContent = '';

                    // Check if this image has saved data
                    debug('Checking for saved data for image ID:', data.image_id);
                    debug('Available saved data keys:', Object.keys(savedData));

                    // Load first annotation if available
                    if (savedData[data.image_id] && savedData[data.image_id].length > 0) {
                        debug('Found saved annotations for image:', data.image_id, savedData[data.image_id].length);
                        totalAnnotations = savedData[data.image_id].length;
                        // Load the first annotation by default
                        loadAnnotation(currentIndex, 0);
                    } else {
                        debug('No saved annotations found for this image');
                        // Initialize with default values
                        updateEmptyCaseStatus(false);
                        clearFormSelections();
                        isSavedToFile = false;
                        updateSaveStatus();
                        updateAnnotationProgress();
                    }

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

                        if (callback) callback();
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

                            // Now find the last saved image
                            return findLastSavedImageIndex();
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

            // Add canvas event listeners for custom box drawing
            canvas.addEventListener('mousedown', function(e) {
                if (!isDrawingCustomBox) return;
                
                const rect = canvas.getBoundingClientRect();
                customBoxStartX = Math.round(e.clientX - rect.left);
                customBoxStartY = Math.round(e.clientY - rect.top);
                
                // Clear canvas and redraw image
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                drawBboxes();
                
                e.preventDefault();
            });
            
            canvas.addEventListener('mousemove', function(e) {
                if (!isDrawingCustomBox || !customBoxStartX) return;  // Only draw if we have a start point
                
                const rect = canvas.getBoundingClientRect();
                const currentX = Math.round(e.clientX - rect.left);
                const currentY = Math.round(e.clientY - rect.top);
                
                // Redraw the image and existing boxes
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                drawBboxes();
                
                // Calculate the rectangle coordinates
                const rectX = Math.min(customBoxStartX, currentX);
                const rectY = Math.min(customBoxStartY, currentY);
                const rectWidth = Math.abs(currentX - customBoxStartX);
                const rectHeight = Math.abs(currentY - customBoxStartY);
                
                // Draw rectangle
                ctx.strokeStyle = 'green';
                ctx.lineWidth = 3;
                ctx.strokeRect(rectX, rectY, rectWidth, rectHeight);
                
                // Fill with semi-transparent green
                ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
                ctx.fillRect(rectX, rectY, rectWidth, rectHeight);
                
                e.preventDefault();
            });
            
            canvas.addEventListener('mouseup', function(e) {
                if (!isDrawingCustomBox || !customBoxStartX) return;  // Only process if we have a start point
                
                const rect = canvas.getBoundingClientRect();
                const endX = Math.round(e.clientX - rect.left);
                const endY = Math.round(e.clientY - rect.top);
                
                // Only create a box if it has some size
                if (Math.abs(endX - customBoxStartX) < 5 || Math.abs(endY - customBoxStartY) < 5) {
                    status.textContent = "Box too small. Try again with a larger selection.";
                    // Reset drawing state
                    customBoxStartX = 0;
                    customBoxStartY = 0;
                    return;
                }
                
                // Calculate original image coordinates
                const scaleX = currentImageData.width / canvas.width;
                const scaleY = currentImageData.height / canvas.height;
                
                const imgX1 = Math.round(Math.min(customBoxStartX, endX) * scaleX);
                const imgY1 = Math.round(Math.min(customBoxStartY, endY) * scaleY);
                const imgX2 = Math.round(Math.max(customBoxStartX, endX) * scaleX);
                const imgY2 = Math.round(Math.max(customBoxStartY, endY) * scaleY);
                
                // Ensure no values are below 0
                const safeX1 = Math.max(0, imgX1);
                const safeY1 = Math.max(0, imgY1);
                const safeX2 = Math.max(0, imgX2);
                const safeY2 = Math.max(0, imgY2);
                
                // Store coordinates with safe values
                customBoxCoords = [safeX1, safeY1, safeX2, safeY2];
                
                // Reset drawing state
                isDrawingCustomBox = false;
                customBoxStartX = 0;
                customBoxStartY = 0;
                updateStatusMessage();
                
                // Redraw with the new custom box
                drawBboxes();
                createBboxSelector();
                
                e.preventDefault();
            });
            
            canvas.addEventListener('mouseleave', function(e) {
                if (!isDrawingCustomBox || !customBoxStartX) return;  // Only process if we have a start point
                
                // Cancel drawing if mouse leaves canvas
                isDrawingCustomBox = false;
                customBoxStartX = 0;
                customBoxStartY = 0;
                status.textContent = "Custom box drawing cancelled";
                customBoxCoords = null;
                drawBboxes();
                
                e.preventDefault();
            });
        };

        // Create a new function to handle loading a specific annotation
        function loadAnnotation(imageIndex, annotationIndex) {
            debug('Loading annotation', imageIndex, annotationIndex);
            
            // First ensure we have the right image data
            if (currentIndex !== imageIndex) {
                // If we're changing images, load that image first then set the annotation
                loadImage(imageIndex, function() {
                    loadAnnotation(imageIndex, annotationIndex);
                });
                return;
            }
            
            // Ensure we have saved data for this image
            if (!savedData[currentImageData.image_id] || !savedData[currentImageData.image_id].length) {
                debug('No saved annotations for this image');
                createNewAnnotation();
                return;
            }
            
            // Ensure annotation index is valid
            if (annotationIndex < 0 || annotationIndex >= savedData[currentImageData.image_id].length) {
                debug('Invalid annotation index, defaulting to 0');
                annotationIndex = 0;
            }
            
            currentAnnotationIndex = annotationIndex;
            totalAnnotations = savedData[currentImageData.image_id].length;
            
            // Load the selected annotation
            const annotation = savedData[currentImageData.image_id][annotationIndex];
            currentAnnotationId = annotation.annotation_id;
            
            // Reset UI elements
            selectedBbox = null;
            selectedBboxIndex = -1;
            selectedCategoryIndex = -1;
            customBoxCoords = null;
            savedCustomBoxCoords = null;
            isDrawingCustomBox = false;
            
            // Load caption
            captionInput.value = annotation.normal_caption || '';
            updateProblemText();
            
            // Load bounding box
            if (annotation.solution) {
                const solution = annotation.solution;
                
                // Check if it's an empty case
                const isEmptyCase = annotation.categories && annotation.categories.empty_case === true;
                
                if (isEmptyCase) {
                    // Empty case handling
                    selectedBbox = null;
                    updateEmptyCaseStatus(true);
                } else {
                    // Try to match with existing boxes
                    let matchFound = false;
                    
                    currentImageData.categories_with_multiple_instances.forEach((category, catIndex) => {
                        category.instances.forEach((bbox, bboxIndex) => {
                            const convertedBbox = convertBboxFormat(bbox);
                            if (JSON.stringify(convertedBbox) === JSON.stringify(solution)) {
                                selectedBbox = convertedBbox;
                                selectedCategoryIndex = catIndex;
                                selectedBboxIndex = bboxIndex;
                                matchFound = true;
                            }
                        });
                    });
                    
                    if (!matchFound) {
                        // Treat as custom box
                        customBoxCoords = solution;
                        selectedBbox = null;
                        selectedCategoryIndex = -1;
                        selectedBboxIndex = -1;
                    }
                    
                    updateEmptyCaseStatus(false);
                }
            }
            
            // Load categories
            setFormValues(annotation);
            
            // Update status
            isSavedToFile = true;
            updateSaveStatus();
            calculateDistractors();
            updateStatusMessage();
            updateAnnotationProgress();
            
            // Redraw
            drawBboxes();
            createBboxSelector();
        }
        
        // Function to handle creating a new annotation
        function createNewAnnotation() {
            debug('Creating new annotation');
            
            // Reset UI elements
            selectedBbox = null;
            selectedBboxIndex = -1;
            selectedCategoryIndex = -1;
            customBoxCoords = null;
            savedCustomBoxCoords = null;
            isDrawingCustomBox = false;
            currentAnnotationId = null;
            
            // Clear caption
            captionInput.value = '';
            updateProblemText();
            
            // Reset form values
            clearFormSelections();
            
            // Update status
            isSavedToFile = false;
            updateSaveStatus();
            updateEmptyCaseStatus(false);
            calculateDistractors();
            updateStatusMessage();
            
            // Set annotation index to one past the end
            if (!savedData[currentImageData.image_id]) {
                totalAnnotations = 0;
                currentAnnotationIndex = 0;
            } else {
                totalAnnotations = savedData[currentImageData.image_id].length;
                currentAnnotationIndex = totalAnnotations;
            }
            
            updateAnnotationProgress();
            
            // Redraw
            drawBboxes();
            createBboxSelector();
        }
        
        // Update annotation progress display
        function updateAnnotationProgress() {
            // Show format: "current / (saved + 1)" when creating a new annotation
            const total = savedData[currentImageData.image_id] ? 
                (currentAnnotationIndex >= savedData[currentImageData.image_id].length ? 
                    savedData[currentImageData.image_id].length + 1 : 
                    savedData[currentImageData.image_id].length) : 
                1;
                
            annotationProgress.textContent = `Annotation ${currentAnnotationIndex + 1}/${total}`;
            
            // Update navigation buttons
            prevAnnotationBtn.disabled = currentAnnotationIndex <= 0;
            nextAnnotationBtn.disabled = currentAnnotationIndex >= totalAnnotations - 1;
            
            // Update delete button
            deleteAnnotationBtn.disabled = !currentAnnotationId || 
                !savedData[currentImageData.image_id] || 
                savedData[currentImageData.image_id].length === 0;
        }

        function deleteAnnotation() {
            // Delete the current annotation
            fetch(`/api/delete_annotation?cache=${cacheBuster}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image_id: currentImageData.image_id,
                    annotation_id: currentAnnotationId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update savedData
                    if (savedData[currentImageData.image_id]) {
                        savedData[currentImageData.image_id] = savedData[currentImageData.image_id].filter(
                            a => a.annotation_id !== currentAnnotationId
                        );
                        
                        totalAnnotations = savedData[currentImageData.image_id].length;
                        
                        if (totalAnnotations === 0) {
                            // If no annotations left, create a new blank one
                            createNewAnnotation();
                        } else {
                            // Load the previous annotation or the first one
                            const newIndex = Math.min(currentAnnotationIndex, totalAnnotations - 1);
                            loadAnnotation(currentIndex, newIndex);
                        }
                    } else {
                        createNewAnnotation();
                    }
                    
                    status.textContent = "Annotation deleted successfully!";
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(err => {
                console.error('Delete error:', err);
                alert('Failed to delete annotation');
            });
        }
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
        # Each image can have multiple annotations
        # Check if this particular annotation already exists
        existing_index = -1
        annotation_id = annotation.get("annotation_id", None)
        
        if annotation_id is not None:
            for i, item in enumerate(output_data):
                if item.get("image") == annotation["image"] and item.get("annotation_id") == annotation_id:
                    existing_index = i
                    break

        # Update existing or add new
        if existing_index >= 0:
            output_data[existing_index] = annotation
        else:
            # Generate a new annotation ID if not provided
            if not annotation_id:
                annotation["annotation_id"] = f"{image_id}_{len([a for a in output_data if a.get('image') == 'val2017/' + annotation['file_name']])}"
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

    # Get list of saved image IDs and annotations
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
                    if img_id not in saved_image_ids:
                        saved_image_ids.append(img_id)
                    
                    # Group annotations by image_id
                    if img_id not in saved_annotations:
                        saved_annotations[img_id] = []
                    
                    saved_annotations[img_id].append(item)
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
    # Create a dictionary mapping image IDs to saved annotations (multiple per image)
    saved_data = {}

    for item in output_data:
        # Extract image ID from path
        image_path = item.get("image", "")
        if image_path:
            # Try to find matching image from multiple_instances_data
            for img in multiple_instances_data["images"]:
                if "val2017/" + img["file_name"] == image_path:
                    if img["image_id"] not in saved_data:
                        saved_data[img["image_id"]] = []
                    
                    saved_data[img["image_id"]].append(item)
                    break

    return jsonify(saved_data)

@app.route('/api/delete_annotation', methods=['POST'])
def delete_annotation():
    """API endpoint to delete a reference annotation"""
    try:
        data = request.json
        image_id = data.get('image_id')
        annotation_id = data.get('annotation_id')

        if image_id is None or annotation_id is None:
            return jsonify({"success": False, "message": "Invalid data"}), 400

        # Find and remove the annotation from output_data
        found = False
        for i, item in enumerate(output_data):
            if item.get("annotation_id") == annotation_id:
                output_data.pop(i)
                found = True
                break
        
        if not found:
            return jsonify({"success": False, "message": "Annotation not found"}), 404
        
        # Save updated data to file
        with open(OUTPUT_FILE, "w") as f:
            json.dump(output_data, f, indent=2)
            
        return jsonify({"success": True, "message": "Annotation deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# Add a new server endpoint to get the last saved image index
@app.route('/api/last_saved_index')
def get_last_saved_index():
    """API endpoint to get the index of the last saved image according to original order"""
    if not multiple_instances_data:
        return jsonify({"error": "No data loaded"}), 404

    # If no output data, return the first image
    if not output_data:
        return jsonify({"index": 0})

    # Create a lookup of image IDs to their indices in the original JSON
    image_id_to_index = {}
    for i, img in enumerate(multiple_instances_data["images"]):
        image_id_to_index[img["image_id"]] = i

    # Find all image IDs that have saved annotations
    saved_image_ids = set()
    for item in output_data:
        image_path = item.get("image", "")
        if image_path:
            for img in multiple_instances_data["images"]:
                if "val2017/" + img["file_name"] == image_path:
                    saved_image_ids.add(img["image_id"])
                    break

    # Find the highest index (last in sequence) with saved annotations
    last_index = 0
    for img_id in saved_image_ids:
        if img_id in image_id_to_index:
            last_index = max(last_index, image_id_to_index[img_id])

    return jsonify({"index": last_index})

if __name__ == '__main__':
    # Load data at startup
    success, message = load_data()
    print(message)

    # Use port 5000 by default, can be changed
    port = int(os.environ.get('PORT', 5555))
    app.run(host='0.0.0.0', port=port, debug=True)
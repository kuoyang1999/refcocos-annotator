// JavaScript for RefCOCOS Annotator
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
        const jumpBtn = document.getElementById('jump-btn');
        const jumpInput = document.getElementById('jump-input');
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
        const attributeOptions = document.querySelectorAll('input[name="attribute"]');

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
        let hiddenCategoryIndices = new Set();
        
        // Filter state variables
        let filterSettings = {
            showOnlyAnnotated: false,
            excludedCategories: new Set()
        };
        let allImagesMetadata = []; // Store all image metadata for filtering
        let filteredToRealIndexMap = []; // Maps filtered index → real index
        let realToFilteredIndexMap = []; // Maps real index → filtered index (or -1 if filtered out)
        let filteredTotalImages = 0; // Count of images after filtering
        let currentFilteredIndex = 0; // Current position in filtered view
        let isFilterDataInitialized = false; // Track if excluded categories have been loaded

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
            if (filteredTotalImages > 0) {
                // Using filtered navigation
                if (currentFilteredIndex > 0) {
                    loadFilteredImage(currentFilteredIndex - 1);
                }
            } else {
                // Fallback to unfiltered navigation
                if (currentIndex > 0) {
                    loadImage(currentIndex - 1);
                }
            }
        });

        nextBtn.addEventListener('click', function() {
            if (filteredTotalImages > 0) {
                // Using filtered navigation
                if (currentFilteredIndex < filteredTotalImages - 1) {
                    loadFilteredImage(currentFilteredIndex + 1);
                }
            } else {
                // Fallback to unfiltered navigation
                if (currentIndex < totalImages - 1) {
                    loadImage(currentIndex + 1);
                }
            }
        });

        // Jump to button event
        jumpBtn.addEventListener('click', function() {
            const targetIndex = parseInt(jumpInput.value, 10);
            
            if (filteredTotalImages > 0) {
                // When filters are active, the input is for filtered indexes
                if (!isNaN(targetIndex) && targetIndex >= 1 && targetIndex <= filteredTotalImages) {
                    loadFilteredImage(targetIndex - 1); // Convert from 1-indexed to 0-indexed
                } else {
                    status.textContent = `Please enter a valid image number between 1 and ${filteredTotalImages}`;
                }
            } else {
                // Unfiltered navigation fallback
                if (!isNaN(targetIndex) && targetIndex >= 1 && targetIndex <= totalImages) {
                    loadImage(targetIndex - 1); // Convert from 1-indexed to 0-indexed
                } else {
                    status.textContent = `Please enter a valid image number between 1 and ${totalImages}`;
                }
            }
        });

        // Jump input event
        jumpInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                jumpBtn.click();
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
            // Check if we have saved data and annotations for the current image
            if (!savedData[currentImageData.image_id] || 
                savedData[currentImageData.image_id].length === 0) {
                alert('No annotation to delete');
                return;
            }
            
            // Check if we're looking at a valid annotation index
            if (currentAnnotationIndex < 0 || currentAnnotationIndex >= savedData[currentImageData.image_id].length) {
                alert('Invalid annotation index');
                return;
            }
            
            // Get current annotation even if it doesn't have an ID
            const currentAnnotation = savedData[currentImageData.image_id][currentAnnotationIndex];
            
            if (confirm('Are you sure you want to delete this annotation?')) {
                deleteAnnotation(currentAnnotation);
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

        // Event listener for changes to the form inputs that should affect the save status
        function setupFormChangeListeners() {
            // Add event listeners to all form elements
            hopsOptions.forEach(option => {
                option.addEventListener('change', function() {
                    isSavedToFile = false;
                    updateSaveStatus();
                    updateStatusMessage();
                });
            });
            
            typeOptions.forEach(option => {
                option.addEventListener('change', function() {
                    isSavedToFile = false;
                    updateSaveStatus();
                    updateStatusMessage();
                });
            });
            
            occludedOptions.forEach(option => {
                option.addEventListener('change', function() {
                    isSavedToFile = false;
                    updateSaveStatus();
                    updateStatusMessage();
                });
            });

            attributeOptions.forEach(option => {
                option.addEventListener('change', function() {
                    isSavedToFile = false;
                    updateSaveStatus();
                    updateStatusMessage();
                });
            });
        }
        
        // Call the setup function
        setupFormChangeListeners();

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
            
            // 'distractor' is the global const distractor = document.getElementById('distractors-value');
            // originalCalculateDistractors (called via the patched calculateDistractors) 
            // has just updated distractor.textContent with the suggested value.
            const suggestedDisplayValue = (distractor.textContent === 'N/A' || distractor.textContent === '') ? '0' : distractor.textContent;

            let inputField = document.getElementById('distractors-input');
            let labelElement = distractorContainer.querySelector('span#distractor-suggestion-label'); 

            if (!inputField) {
                distractorContainer.innerHTML = ''; // Clear only if we need to create elements from scratch

                inputField = document.createElement('input');
                inputField.type = 'number';
                inputField.min = '0';
                inputField.id = 'distractors-input';
                // Value will be set by setFormValues or remain empty for new annotations.
                // Placeholder will be shown if value is empty.
                inputField.placeholder = 'Enter #'; 
                inputField.style.width = '60px';
                inputField.style.marginRight = '10px';
                
                labelElement = document.createElement('span');
                labelElement.id = 'distractor-suggestion-label'; // Add an ID for easier targeting
                
                inputField.addEventListener('input', function() {
                    isSavedToFile = false;
                    updateSaveStatus();
                    updateStatusMessage(); // To re-check validation status
                });
                
                distractorContainer.appendChild(inputField);
                distractorContainer.appendChild(labelElement);
            }
            
            // Always update the suggestion text in the label
            if (labelElement) { // Ensure labelElement exists before setting innerHTML
                labelElement.innerHTML = '(suggest: <span id="suggested-distractor-value">' + 
                    suggestedDisplayValue + 
                    '</span>)';
            }
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
            const distractorsInputElement = document.getElementById('distractors-input');
            const formData = {
                empty_case: emptyCase.textContent === 'Yes',
                hops: getSelectedRadioValue(hopsOptions),
                type: Array.from(typeOptions)
                    .filter(cb => cb.checked)
                    .map(cb => cb.value),
                attribute: Array.from(attributeOptions) 
                            .filter(cb => cb.checked)
                            .map(cb => cb.value),
                // occluded: getSelectedRadioValue(occludedOptions) === 'true', // Keep temporarily, may need adjustment based on how data is saved/loaded
                distractors: distractorsInputElement ? distractorsInputElement.value.trim() : '' // Read from input field, trim whitespace
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
            // Ensure the input field exists because setupDistractorEdit might not have run yet
            // if this is called very early, though calculateDistractors should ensure it runs.
            let distractorsInputElement = document.getElementById('distractors-input');
            if (!distractorsInputElement && document.getElementById('distractors-container')) {
                 // If input doesn't exist but container does, force setup
                 setupDistractorEdit(); 
                 distractorsInputElement = document.getElementById('distractors-input');
            }

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
                } else { // Ensure it's cleared if not in saved data or wrong format
                    typeOptions.forEach(option => option.checked = false);
                }

                // Set attribute (Handle new data format with arrays)
                if (data.categories.attribute !== undefined && Array.isArray(data.categories.attribute)) {
                    attributeOptions.forEach(option => { 
                        option.checked = data.categories.attribute.includes(option.value);
                    });
                } else {
                     // Clear if data format is wrong or missing
                     attributeOptions.forEach(option => option.checked = false);
                }
                
                // Set distractors from saved data into the input field
                if (distractorsInputElement) {
                    if (data.categories.distractors !== undefined && data.categories.distractors !== null) {
                        distractorsInputElement.value = data.categories.distractors;
                    } else {
                        distractorsInputElement.value = ''; // Clear if not in saved data
                    }
                } else {
                    console.warn('Distractors input field not found when trying to set value.');
                }

                // Distractors suggestion is updated later by calculateDistractors
            } else {
                // Initialize with default values
                currentCategories = {
                    empty_case: false,
                    hops: null,
                    type: [],
                    attribute: [], // Default to empty array for checkboxes
                    // occluded: false, // Keep temporarily for old data?
                    distractors: null
                };

                // Clear all form selections
                clearFormSelections(); // This will clear distractors input too
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

            // Set occluded to "No" by default (Keep temporarily)
            // setRadioValue(occludedOptions, 'false'); 
            
            // Clear attribute selection
            attributeOptions.forEach(checkbox => checkbox.checked = false);

            // Clear distractors input field
            const distractorsInputElement = document.getElementById('distractors-input');
            if (distractorsInputElement) {
                distractorsInputElement.value = '';
            }

            // Distractors suggestion is updated separately by calculateDistractors/setupDistractorEdit
            // distractor.textContent = 'N/A'; // No longer needed to set the span here
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
                // Skip drawing if category is hidden
                if (hiddenCategoryIndices.has(catIndex)) {
                    return; // Don't draw this category
                }

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

                // Clear all attribute checkboxes for empty case
                attributeOptions.forEach(checkbox => checkbox.checked = false);

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
                    // Update status message after restoring the box
                    updateStatusMessage();
                }
                
                // Always activate drawing mode
                isDrawingCustomBox = true;
                
                // Clear other selections
                selectedCategoryIndex = -1;
                selectedBboxIndex = -1;
                selectedBbox = null;

                // Clear all attribute checkboxes for custom box
                attributeOptions.forEach(checkbox => checkbox.checked = false);
                
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

                // Create header container with flex layout
                const headerDiv = document.createElement('div');
                headerDiv.style.display = 'flex';
                headerDiv.style.justifyContent = 'space-between';
                headerDiv.style.alignItems = 'center';
                headerDiv.style.margin = '10px 0';

                // Category name and count
                const categoryLabel = document.createElement('span');
                categoryLabel.style.fontWeight = 'bold';
                categoryLabel.style.color = catIndex === selectedCategoryIndex ? 'red' : 'blue';
                categoryLabel.textContent = `${category.category_name} (${category.count} instances)`;
                headerDiv.appendChild(categoryLabel);

                // Add Hide/Show button with SVG icon
                const toggleBtn = document.createElement('button');
                toggleBtn.className = 'toggle-category-btn';
                toggleBtn.dataset.catIndex = catIndex;
                toggleBtn.style.background = 'none';
                toggleBtn.style.border = 'none';
                toggleBtn.style.cursor = 'pointer';
                toggleBtn.style.padding = '0 5px';
                toggleBtn.innerHTML = hiddenCategoryIndices.has(catIndex) ? 
                    `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-eye-off"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>` : // Eye-off icon
                    `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-eye"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`; // Eye icon
                
                // Toggle event listener
                toggleBtn.addEventListener('click', (e) => {
                    e.stopPropagation(); // Prevent click from bubbling to category selection
                    const index = parseInt(e.currentTarget.dataset.catIndex);
                    if (hiddenCategoryIndices.has(index)) {
                        hiddenCategoryIndices.delete(index);
                        // Update icon to eye
                        e.currentTarget.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-eye"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
                    } else {
                        hiddenCategoryIndices.add(index);
                        // Update icon to eye-off
                        e.currentTarget.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-eye-off"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`;
                    }
                    drawBboxes(); // Redraw canvas with updated visibility
                });

                headerDiv.appendChild(toggleBtn);
                categoryDiv.appendChild(headerDiv);

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

                        // Clear all attribute checkboxes first
                        attributeOptions.forEach(checkbox => checkbox.checked = false);

                        // Auto-select attributes based on instance data
                        if (currentImageData.categories_with_multiple_instances[catIndex].instance_attributes) {
                            const instanceAttributes = currentImageData.categories_with_multiple_instances[catIndex].instance_attributes[bboxIndex];
                            for (const attrName in instanceAttributes) {
                                if (instanceAttributes.hasOwnProperty(attrName) && instanceAttributes[attrName] === 1) {
                                    const checkbox = document.getElementById(`attr-${attrName.substring(2).toLowerCase()}`);
                                    if (checkbox) {
                                        checkbox.checked = true;
                                    }
                                }
                            }
                        }

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
            const hasType = Array.from(typeOptions).some(cb => cb.checked); // Still useful to know if any selected
            const hasAttribute = Array.from(attributeOptions).some(cb => cb.checked); // Still useful to know if any selected
            
            // Check distractors input
            const distractorsInputElement = document.getElementById('distractors-input');
            const hasDistractors = distractorsInputElement && distractorsInputElement.value.trim() !== '';

            // Build status message
            let message = "";
            let missing = [];
            
            if (!hasBbox) missing.push("bounding box");
            if (!hasCaption) missing.push("caption");
            if (!hasHops) missing.push("hops value");
            if (!hasDistractors) missing.push("distractors value"); // Add distractors
            
            // Type and Attribute are now optional, so don't add them to missing list
            // if (!hasType) missing.push("type");
            // if (!hasAttribute) missing.push("attribute");
            
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
            const formData = getFormData(); // Ensure this reads from the input field now

            // For empty cases, selectedBbox should be null
            if (formData.empty_case) {
                if (selectedBbox !== null || customBoxCoords !== null) {
                    alert('Empty case should have null bounding box');
                    return false;
                }
            } else {
                // For non-empty cases, selectedBbox should not be null
                if (selectedBbox === null && customBoxCoords === null) {
                    alert('Please select or draw a bounding box');
                    return false;
                }
            }

            // Check if hops is selected
            if (!formData.hops) {
                alert('Please select hops value');
                return false;
            }

            // Check if distractors is provided and is a valid non-negative number
            if (formData.distractors === '' || formData.distractors === null) { // Check if empty or null
                alert('Please enter the number of distractors.');
                return false;
            }
            const distractorsVal = parseInt(formData.distractors, 10);
            if (isNaN(distractorsVal) || distractorsVal < 0) {
                alert('Please enter a valid non-negative number for distractors.');
                return false;
            }

            // Type and Attribute are optional and multi-choice, so validation removed earlier.

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
                image: "open_image_v7/" + currentImageData.file_name,
                file_name: currentImageData.file_name,
                problem: `Please provide the bounding box coordinate of the region this sentence describes: ${caption}.`,
                solution: customBoxCoords || selectedBbox,
                normalized_solution: calculateNormalizedSolution(customBoxCoords || selectedBbox, currentImageData.width, currentImageData.height),
                categories: formData,
                image_index: currentImageData.image_id
            };

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
                            debug('Updated existing annotation:', currentAnnotationId);
                            break;
                        }
                    }
                    
                    if (!found) {
                        savedData[currentImageData.image_id].push(annotationData);
                        totalAnnotations = savedData[currentImageData.image_id].length;
                        currentAnnotationIndex = totalAnnotations - 1;
                        debug('Created new annotation:', currentAnnotationId);
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

                    // Update the reference count
                    updateReferenceCount();

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

        // Format image path to open_image_v7/xxxxx
        function formatImagePath(path) {
            const regex = /.*\/([^\/]+)$/;
            const match = path.match(regex);
            if (match && match[1]) {
                return "open_image_v7/" + match[1];
            }
            return path;
        }

        // Find the index of the most recently created annotation image
        function findLastCreatedAnnotationIndex() {
            debug('Finding most recently created annotation image...');

            return new Promise((resolve, reject) => {
                // Use the new endpoint to get the index of the image with the most recently created annotation
                fetch(`/api/last_created_annotation_index?cache=${cacheBuster}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            debug('Error getting last created annotation index:', data.error);
                            resolve(0); // Default to first image
                            return;
                        }

                        const lastIndex = data.index;
                        debug(`Most recently annotated image found at index ${lastIndex}`);
                        
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
                        console.error('Error finding most recently annotated image:', err);
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

                    // Update filtered index if we're using filters
                    if (filteredTotalImages > 0) {
                        currentFilteredIndex = realToFilteredIndexMap[index] !== -1 ? 
                            realToFilteredIndexMap[index] : currentFilteredIndex;
                    }

                    // Reset selection variables
                    selectedBbox = null;
                    selectedBboxIndex = -1;
                    selectedCategoryIndex = -1;
                    customBoxCoords = null;
                    savedCustomBoxCoords = null;
                    isDrawingCustomBox = false;
                    hiddenCategoryIndices = new Set();
                    
                    // Reset annotation variables - we'll set these after checking for saved data
                    currentAnnotationId = null;
                    currentAnnotationIndex = 0;
                    totalAnnotations = 0;

                    // Default to Empty Case state initially
                    updateEmptyCaseStatus(true); // Select Empty Case by default
                    clearFormSelections();       // Clear forms
                    calculateDistractors();      // Recalculate distractors for empty case
                    isSavedToFile = false;       // Mark as unsaved
                    updateSaveStatus();
                    updateAnnotationProgress();  // Update annotation counter

                    // Update UI
                    updateProgressDisplay(); // Use the updated function instead of directly setting progress.textContent
                    const formattedPath = formatImagePath(data.path);
                    imagePath.textContent = `Image ${index + 1}/${totalImages}: ${formattedPath}`;
                    
                    // Update navigation buttons for filtered or unfiltered navigation
                    if (filteredTotalImages > 0) {
                        prevBtn.disabled = currentFilteredIndex === 0;
                        nextBtn.disabled = currentFilteredIndex === filteredTotalImages - 1;
                        jumpInput.value = currentFilteredIndex + 1; // Set jump input to current filtered index (1-indexed)
                    } else {
                        prevBtn.disabled = currentIndex === 0;
                        nextBtn.disabled = currentIndex === totalImages - 1;
                        jumpInput.value = index + 1; // Set jump input to current image index (1-indexed)
                    }

                    // Clear caption and problem text
                    captionInput.value = '';
                    problemText.textContent = '';
                    status.textContent = 'Please select a bounding box and provide a caption';

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
                            
                            // Update the reference count
                            updateReferenceCount();

                            // Load excluded categories from server
                            return loadExcludedCategories()
                                .then(() => {
                                    debug('Loaded excluded categories, count:', filterSettings.excludedCategories.size);
                                    
                                    // Load all images metadata for filtering
                                    return loadAllImagesMetadata();
                                });
                        })
                        .then(() => {
                            isFilterDataInitialized = true;
                            
                            // Find the most recently created annotation image first
                            return findLastCreatedAnnotationIndex()
                                .then(index => {
                                    debug('Starting with image at index:', index);
                                    
                                    // Load the image first
                                    return new Promise(resolve => {
                                        loadImage(index, () => {
                                            debug('Initial image loaded');
                                            resolve(index);
                                        });
                                    });
                                })
                                .then(index => {
                                    // Only apply filters after the initial image is loaded
                                    if (filterSettings.excludedCategories.size > 0) {
                                        debug('Applying saved filters');
                                        applyFilters();
                                    }
                                    
                                    updateSaveStatus();
                                    return index;
                                });
                        });
                })
                .then(index => {
                    debug('Starting with image at index:', index);
                    loadImage(index);
                    updateSaveStatus();
                })
                .then(index => {
                    // No-op, already handled in the chain above
                    debug('Initialization completed successfully');
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
                debug('Invalid annotation index', annotationIndex, 'defaulting to 0');
                annotationIndex = 0;
            }
            
            currentAnnotationIndex = annotationIndex;
            totalAnnotations = savedData[currentImageData.image_id].length;
            
            debug('Set currentAnnotationIndex to:', currentAnnotationIndex, 'of', totalAnnotations);
            
            // Load the selected annotation
            const annotation = savedData[currentImageData.image_id][annotationIndex];
            
            // Handle missing annotation_id
            if (!annotation.annotation_id) {
                debug('Found annotation without ID, generating temporary ID');
                annotation.annotation_id = `${currentImageData.image_id}_${Date.now()}`;
                debug('Generated annotation_id:', annotation.annotation_id);
            }
            
            currentAnnotationId = annotation.annotation_id;
            debug('Set currentAnnotationId to:', currentAnnotationId);
            
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
            
            // Explicitly set to null to ensure a new ID is generated when saving
            currentAnnotationId = null;
            
            // Clear caption
            captionInput.value = '';
            updateProblemText();
            
            // Reset form values
            clearFormSelections(); // This will now clear attribute checkboxes too
            
            // Update status
            isSavedToFile = false;
            updateSaveStatus();
            updateEmptyCaseStatus(true); // Explicitly set Empty Case for new annotation
            calculateDistractors();
            status.textContent = 'Please select a bounding box and provide a caption';
            
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
            
            // Update delete button - enable if we have a valid annotation ID
            const hasValidAnnotation = currentAnnotationId !== null && 
                savedData[currentImageData.image_id] && 
                savedData[currentImageData.image_id].length > 0;
                
            deleteAnnotationBtn.disabled = !hasValidAnnotation;
            
            debug('Update annotation progress:', 
                'currentAnnotationIndex =', currentAnnotationIndex, 
                'totalAnnotations =', totalAnnotations,
                'hasValidAnnotation =', hasValidAnnotation,
                'currentAnnotationId =', currentAnnotationId);
        }

        function deleteAnnotation(annotation) {
            // If the annotation doesn't have an annotation_id, use the index in the array instead
            if (!annotation.annotation_id) {
                debug('Annotation has no ID, using index-based deletion');
                
                // Find the index of this annotation in the array
                const indexToDelete = savedData[currentImageData.image_id].findIndex(a => 
                    a === annotation || 
                    (a.normal_caption === annotation.normal_caption && 
                     JSON.stringify(a.solution) === JSON.stringify(annotation.solution))
                );
                
                if (indexToDelete === -1) {
                    debug('Could not find annotation in saved data');
                    status.textContent = "Error: Could not find annotation in saved data";
                    return;
                }
                
                // Remove the annotation from the array
                savedData[currentImageData.image_id].splice(indexToDelete, 1);
                
                totalAnnotations = savedData[currentImageData.image_id].length;
                debug('Remaining annotations:', totalAnnotations);
                
                // Update the reference count
                updateReferenceCount();
                
                // Update UI after deletion
                if (totalAnnotations === 0) {
                    debug('No annotations remaining, creating new one');
                    createNewAnnotation();
                } else {
                    // Load the first annotation or the previous one
                    const newIndex = Math.min(indexToDelete, totalAnnotations - 1);
                    debug('Loading new annotation at index:', newIndex);
                    loadAnnotation(currentIndex, newIndex);
                }
                
                status.textContent = "Annotation deleted successfully!";
                return;
            }
            
            debug('Deleting annotation', annotation.annotation_id);
            
            // Delete the current annotation via API
            fetch(`/api/delete_annotation?cache=${cacheBuster}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image_id: currentImageData.image_id,
                    annotation_id: annotation.annotation_id
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    debug('Annotation deleted successfully:', annotation.annotation_id);
                    
                    // Update savedData
                    if (savedData[currentImageData.image_id]) {
                        // Store current index before deleting
                        const wasFirstAnnotation = currentAnnotationIndex === 0;
                        
                        // Find the index of the deleted annotation
                        const indexToDelete = savedData[currentImageData.image_id].findIndex(
                            a => a.annotation_id === annotation.annotation_id
                        );
                        
                        debug('Deleting annotation at index:', indexToDelete);
                        
                        // Ensure we found it
                        if (indexToDelete === -1) {
                            debug('Could not find annotation in saved data:', annotation.annotation_id);
                            status.textContent = "Error: Could not find annotation in saved data";
                            return;
                        }
                        
                        // Remove the annotation from the array
                        savedData[currentImageData.image_id].splice(indexToDelete, 1);
                        
                        totalAnnotations = savedData[currentImageData.image_id].length;
                        debug('Remaining annotations:', totalAnnotations);
                        
                        // Update the reference count
                        updateReferenceCount();
                        
                        // Determine which annotation to load next
                        if (totalAnnotations === 0) {
                            // If no annotations left, create a new blank one
                            debug('No annotations remaining, creating new one');
                            createNewAnnotation();
                        } else {
                            // If we deleted the first annotation, load index 0 (new first annotation)
                            // If we deleted another annotation, go to the previous one or stay at same index
                            let newIndex = 0;
                            
                            if (wasFirstAnnotation) {
                                // If we deleted the first annotation, load the new first annotation
                                newIndex = 0;
                            } else {
                                // If we deleted annotation > 0, go to previous index
                                newIndex = Math.min(indexToDelete - 1, totalAnnotations - 1);
                                // But never go below 0
                                newIndex = Math.max(0, newIndex);
                            }
                            
                            debug('Loading new annotation at index:', newIndex);
                            loadAnnotation(currentIndex, newIndex);
                        }
                    } else {
                        debug('No saved data found for image, creating new annotation');
                        createNewAnnotation();
                    }
                    
                    status.textContent = "Annotation deleted successfully!";
                } else {
                    // If server says annotation not found, handle it client-side anyway
                    if (data.message && data.message.includes("not found")) {
                        debug('Server could not find annotation, deleting client-side');
                        
                        // Find the index of this annotation in the array
                        const indexToDelete = savedData[currentImageData.image_id].findIndex(a => 
                            a === annotation || 
                            a.annotation_id === annotation.annotation_id ||
                            (a.normal_caption === annotation.normal_caption && 
                             JSON.stringify(a.solution) === JSON.stringify(annotation.solution))
                        );
                        
                        if (indexToDelete === -1) {
                            debug('Could not find annotation in saved data');
                            status.textContent = "Error: Could not find annotation in saved data";
                            return;
                        }
                        
                        // Store if this was the first annotation
                        const wasFirstAnnotation = indexToDelete === 0;
                        
                        // Remove the annotation from the client-side array
                        savedData[currentImageData.image_id].splice(indexToDelete, 1);
                        
                        totalAnnotations = savedData[currentImageData.image_id].length;
                        debug('Remaining annotations:', totalAnnotations);
                        
                        // Update the reference count
                        updateReferenceCount();
                        
                        // Update UI after deletion
                        if (totalAnnotations === 0) {
                            debug('No annotations remaining, creating new one');
                            createNewAnnotation();
                        } else {
                            // Load the first annotation or the previous one
                            let newIndex = 0;
                            
                            if (wasFirstAnnotation) {
                                // If we deleted the first annotation, load the new first annotation
                                newIndex = 0;
                            } else {
                                // If we deleted annotation > 0, go to previous index
                                newIndex = Math.min(indexToDelete - 1, totalAnnotations - 1);
                                // But never go below 0
                                newIndex = Math.max(0, newIndex);
                            }
                            
                            debug('Loading new annotation at index:', newIndex);
                            loadAnnotation(currentIndex, newIndex);
                        }
                        
                        status.textContent = "Annotation deleted client-side successfully!";
                    } else {
                        alert('Error: ' + data.message);
                    }
                }
            })
            .catch(err => {
                console.error('Delete error:', err);
                alert('Failed to delete annotation');
            });
        }

        // Fix the updateReferenceCount function to correctly count references
        function updateReferenceCount() {
            // Count all annotations across all images in savedData
            let totalReferences = 0;
            
            // Iterate through each image in savedData
            for (const imageId in savedData) {
                if (savedData.hasOwnProperty(imageId)) {
                    // Each image has an array of annotations
                    totalReferences += savedData[imageId].length;
                }
            }
            
            document.getElementById('reference-count-value').textContent = totalReferences;
        }

        // Filter Functions
        function applyFilters() {
            // Don't apply filters until metadata is loaded
            if (!allImagesMetadata || allImagesMetadata.length === 0) {
                debug('Cannot apply filters: metadata not loaded yet');
                return;
            }
            
            updateFilteredIndexes();
            
            if (filteredTotalImages === 0) {
                // Only show alert if this isn't during initial page load
                if (isFilterDataInitialized) {
                    alert("No images match the current filters. Resetting filters.");
                    resetFilters();
                } else {
                    debug('No images match filters during initialization, resetting silently');
                    resetFilters();
                }
                return;
            }
            
            // Find the filtered index for the current image
            let newFilteredIndex = realToFilteredIndexMap[currentIndex];
            
            // If current image is filtered out, find nearest one that passes
            if (newFilteredIndex === -1) {
                newFilteredIndex = findNearestFilteredIndex(currentIndex);
                
                if (newFilteredIndex === -1) {
                    // This should not happen since we check for empty results above
                    if (isFilterDataInitialized) {
                        alert("No images match the current filters. Resetting filters.");
                    }
                    resetFilters();
                    return;
                }
            }
            
            // Load the filtered image
            loadFilteredImage(newFilteredIndex);
            
            // Comment out status update as requested
            // status.textContent = `Filters applied: Showing ${filteredTotalImages} of ${totalImages} images`;
        }

        function resetFilters() {
            // Reset filter settings
            filterSettings.showOnlyAnnotated = false;
            filterSettings.excludedCategories.clear();
            
            // Reset UI elements
            document.getElementById('filter-annotated').checked = false;
            
            // Clear category checkboxes
            const categoryCheckboxes = document.querySelectorAll('.exclude-category-checkbox');
            categoryCheckboxes.forEach(checkbox => {
                checkbox.checked = false;
            });
            
            // Clear filter mappings
            filteredToRealIndexMap = [];
            realToFilteredIndexMap = [];
            filteredTotalImages = 0;
            
            // Save excluded categories (empty now)
            saveExcludedCategories();
            
            // Load the current image without filtering
            loadImage(currentIndex);
            
            status.textContent = "Filters reset";
        }

        function updateFilteredIndexes() {
            filteredToRealIndexMap = [];
            realToFilteredIndexMap = new Array(totalImages).fill(-1);
            
            // Loop through all images and include those that pass filters
            for (let i = 0; i < totalImages; i++) {
                if (passesFilters(i)) {
                    realToFilteredIndexMap[i] = filteredToRealIndexMap.length;
                    filteredToRealIndexMap.push(i);
                }
            }
            
            filteredTotalImages = filteredToRealIndexMap.length;
            
            // Update UI to reflect filtered counts
            updateProgressDisplay();
        }

        function passesFilters(realIndex) {
            // Get the image data for this index
            const imageData = allImagesMetadata[realIndex];
            if (!imageData) return true; // Default to show if no metadata available
            
            // Check if the image has annotations
            const hasAnnotation = savedData[imageData.image_id] && 
                                 savedData[imageData.image_id].length > 0;
            
            // Filter 1: Show only annotated images
            if (filterSettings.showOnlyAnnotated && !hasAnnotation) {
                return false;
            }
            
            // Filter 2: Exclude by category
            // Only apply category exclusion if either:
            // a) "Show only annotated" is off, or
            // b) "Show only annotated" is on but this image has no annotations
            if (!filterSettings.showOnlyAnnotated || !hasAnnotation) {
                if (filterSettings.excludedCategories.size > 0 && 
                    imageData.categories_with_multiple_instances && 
                    imageData.categories_with_multiple_instances.length > 0) {
                    
                    // Check if any of the image's categories are in the excluded set
                    for (const category of imageData.categories_with_multiple_instances) {
                        if (filterSettings.excludedCategories.has(category.category_id)) {
                            return false;
                        }
                    }
                }
            }
            
            return true;
        }

        function findNearestFilteredIndex(realIndex) {
            if (realToFilteredIndexMap[realIndex] !== -1) {
                return realToFilteredIndexMap[realIndex]; // This image passes the filter
            }
            
            // Search forward and backward from the current index
            let forwardIndex = realIndex;
            let backwardIndex = realIndex;
            
            while (forwardIndex < totalImages - 1 || backwardIndex > 0) {
                // Check forward
                if (forwardIndex < totalImages - 1) {
                    forwardIndex++;
                    if (realToFilteredIndexMap[forwardIndex] !== -1) {
                        return realToFilteredIndexMap[forwardIndex];
                    }
                }
                
                // Check backward
                if (backwardIndex > 0) {
                    backwardIndex--;
                    if (realToFilteredIndexMap[backwardIndex] !== -1) {
                        return realToFilteredIndexMap[backwardIndex];
                    }
                }
            }
            
            return -1; // No valid images found
        }

        function loadFilteredImage(filteredIndex) {
            if (filteredIndex >= 0 && filteredIndex < filteredToRealIndexMap.length) {
                const realIndex = filteredToRealIndexMap[filteredIndex];
                
                // Store current filtered index
                currentFilteredIndex = filteredIndex;
                
                // Load the real image
                loadImage(realIndex);
            } else {
                status.textContent = "Invalid filtered image index";
            }
        }

        function updateProgressDisplay() {
            if (filteredTotalImages > 0 && filteredTotalImages < totalImages) {
                // Show filtered count
                progress.innerHTML = `Image ${currentFilteredIndex + 1}/${filteredTotalImages} <span class="filtered-count">(filtered from ${totalImages})</span>`;
                
                // Also update jump input placeholder to indicate the new range
                jumpInput.setAttribute('max', filteredTotalImages);
                jumpInput.setAttribute('placeholder', `1-${filteredTotalImages}`);
            } else {
                // Show normal count
                progress.textContent = `Image ${currentIndex + 1}/${totalImages}`;
                jumpInput.setAttribute('max', totalImages);
                jumpInput.setAttribute('placeholder', `1-${totalImages}`);
            }
        }

        // Populate category filter checkboxes
        function populateCategoryFilters() {
            // Get all unique categories across all images
            const uniqueCategories = new Map(); // category_id -> {name, count}
            
            for (const imageData of allImagesMetadata) {
                if (imageData.categories_with_multiple_instances) {
                    for (const category of imageData.categories_with_multiple_instances) {
                        if (!uniqueCategories.has(category.category_id)) {
                            uniqueCategories.set(category.category_id, {
                                name: category.category_name,
                                count: 1
                            });
                        } else {
                            const existing = uniqueCategories.get(category.category_id);
                            existing.count++;
                        }
                    }
                }
            }
            
            // Clear loading message
            const container = document.getElementById('exclude-categories-container');
            container.innerHTML = '';
            
            if (uniqueCategories.size === 0) {
                container.innerHTML = '<p>No categories found.</p>';
                return;
            }
            
            // Sort categories by name
            const sortedCategories = Array.from(uniqueCategories.entries())
                .sort((a, b) => a[1].name.localeCompare(b[1].name));
            
            // Create a checkbox for each category
            for (const [categoryId, info] of sortedCategories) {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'filter-category-option';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `exclude-category-${categoryId.replace(/[^a-zA-Z0-9]/g, '-')}`;
                checkbox.className = 'exclude-category-checkbox';
                checkbox.dataset.categoryId = categoryId;
                
                // Check the box if this category is in the excluded set
                if (filterSettings.excludedCategories.has(categoryId)) {
                    checkbox.checked = true;
                }
                
                checkbox.addEventListener('change', function() {
                    if (this.checked) {
                        filterSettings.excludedCategories.add(this.dataset.categoryId);
                    } else {
                        filterSettings.excludedCategories.delete(this.dataset.categoryId);
                    }
                    
                    // Save excluded categories when changed
                    saveExcludedCategories();
                    
                    // Apply filters immediately
                    applyFilters();
                });
                
                const label = document.createElement('label');
                label.htmlFor = checkbox.id;
                label.textContent = `${info.name} (${info.count})`;
                
                categoryDiv.appendChild(checkbox);
                categoryDiv.appendChild(label);
                container.appendChild(categoryDiv);
            }
        }

        // Add a function to load all image metadata for filtering
        function loadAllImagesMetadata() {
            return fetch(`/api/all_images_metadata?cache=${cacheBuster}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error loading all images metadata:', data.error);
                        return false;
                    }
                    
                    allImagesMetadata = data;
                    debug('Loaded metadata for', allImagesMetadata.length, 'images');
                    
                    // Populate category filters based on this data
                    populateCategoryFilters();
                    return true;
                })
                .catch(err => {
                    console.error('Error loading all images metadata:', err);
                    return false;
                });
        }

        // Apply filters button event
        document.getElementById('apply-filters-btn').addEventListener('click', function() {
            applyFilters();
        });

        // Reset filters button event
        document.getElementById('reset-filters-btn').addEventListener('click', function() {
            resetFilters();
        });

        // Show annotated only filter checkbox event
        document.getElementById('filter-annotated').addEventListener('change', function() {
            filterSettings.showOnlyAnnotated = this.checked;
            // Apply filters immediately
            applyFilters();
        });

        // New function to save excluded categories to server
        function saveExcludedCategories() {
            const excludedCategoriesArray = Array.from(filterSettings.excludedCategories);
            
            fetch(`/api/save_excluded_categories?cache=${cacheBuster}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    excluded_categories: excludedCategoriesArray,
                })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    console.error('Failed to save excluded categories:', data.message);
                }
            })
            .catch(err => {
                console.error('Error saving excluded categories:', err);
            });
        }

        // New function to load excluded categories from server
        function loadExcludedCategories() {
            return fetch(`/api/excluded_categories?cache=${cacheBuster}`)
                .then(response => response.json())
                .then(data => {
                    if (data.excluded_categories) {
                        // Clear current set
                        filterSettings.excludedCategories.clear();
                        
                        // Add each category from the server
                        data.excluded_categories.forEach(category => {
                            filterSettings.excludedCategories.add(category);
                        });
                        return true;
                    }
                    return false;
                })
                .catch(err => {
                    console.error('Error loading excluded categories:', err);
                    return false;
                });
        }

        // Function to toggle show only annotated images filter (called directly from HTML)
        function toggleShowAnnotated(checked) {
            debug('Toggle show annotated:', checked);
            filterSettings.showOnlyAnnotated = checked;
            applyFilters();
        }

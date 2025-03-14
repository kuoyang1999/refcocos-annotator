# COCO Bounding Box Annotation Tool

This tool allows you to interactively annotate images with bounding boxes for the COCO dataset.

## Prerequisites

- Python 3.6+
- For PyQt5 version: PyQt5 and Pillow
- For Tkinter version: Tkinter (usually included with Python) and Pillow
- For Web version: Flask and Pillow

You can install the required packages using pip:

```bash
# For PyQt5 version:
pip install PyQt5 Pillow

# For Tkinter version:
pip install Pillow

# For Web version:
pip install Flask Pillow
```

## Usage

1. Ensure `data-coco.json` is in the same directory as the script
2. Make sure the images are accessible at `../r1v-seg/data/trainval2017/`
3. Run the annotation tool:

### PyQt5 Version (Desktop GUI)
```bash
# Using script:
./run_annotator.sh

# Or manually:
python3 bbox_annotator.py
```

### Tkinter Version (Desktop GUI with Better Compatibility)
```bash
# Using script:
./run_annotator_tk.sh

# Or manually:
python3 bbox_annotator_tk.py
```

### Web Version (Server-Based Access)
```bash
# Using script:
./run_annotator_web.sh [port]  # Default port is 5000 if not specified

# Or manually:
export FLASK_APP=bbox_annotator_web.py
python3 -m flask run --host=0.0.0.0 --port=5000
```

Once the web server is running, you can access the annotation tool from any browser:
- Local access: http://localhost:5000
- Remote access: http://[server-ip-address]:5000

### Category Labeler (Web-Based)
```bash
# Using script:
./run_category_labeler.sh

# Or manually:
python3 category_labeler_web.py
```

The category labeler tool provides a form-based interface for labeling images with multiple categories.
Once the server is running, access it through your browser at:
- Local access: http://localhost:5000
- Remote access: http://[server-ip-address]:5000

### Reference Annotator (Web-Based)
```bash
# Run manually:
python reference_annotator_web.py
```

The reference annotator tool allows you to select from existing bounding boxes in images with multiple instances and annotate them with captions and category metadata. It loads data from `val2017_multiple_instances.json` and saves to `refcocos_test.json`.

Once the server is running, access it through your browser at:
- Local access: http://localhost:5000
- Remote access: http://[server-ip-address]:5000

**Note:** The combined annotator web application (`combined_annotator_web.py`) is now deprecated. Please use the reference annotator instead.

## Which Version Should I Use?

- **Use the Web version for server environments** - allows access from any browser and is ideal for remote work
- **Try the Tkinter version for desktop use** if you're having issues with the PyQt5 version
- The Tkinter version has fewer dependencies and better cross-platform compatibility
- The PyQt5 version has a more polished interface but can have dependency issues on some platforms
- **Use the Category Labeler when you need to label images with category metadata** instead of bounding boxes
- **Use the Reference Annotator for selecting existing bounding boxes** in images with multiple instances
- All versions have the same core functionality for their respective tasks

## Known Issues with PyQt5 Version

If you encounter the error "Could not load the Qt platform plugin 'xcb'", you'll need to install additional system dependencies:

```bash
# On Ubuntu/Debian:
sudo apt-get install libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xkb1 libxkbcommon-x11-0

# On Fedora:
sudo dnf install libxcb libX11-xcb

# On Arch Linux:
sudo pacman -S libxcb
```

The `run_annotator.sh` script will attempt to install these dependencies automatically.

## Features

### Bounding Box Annotation Tools:
- **Display Image and Caption**: The tool displays each image with its corresponding caption
- **Draw Bounding Box**: Click and drag on the image to create a bounding box
- **Navigation**: Use Previous and Next buttons to navigate through images
- **Save Annotations**: Click Save to store the bounding box coordinates
- **Redraw**: If you make a mistake, click Redraw to start over
- **Smart Skip**: The tool automatically skips images that have null solutions (empty cases)
- **Coordinate Display**: Both pixel coordinates and normalized coordinates are shown
- **Auto-Advance**: After saving, automatically moves to the next image

### Category Labeler Tool:
- **Display Image and Caption**: Shows the image with its caption
- **Reference Bounding Box**: Displays existing bounding boxes as reference
- **Category Form**: Provides form controls for labeling multiple categories:
  1. **Hops**: Single choice (1, 2, 3, 4)
  2. **Type**: Multiple choice (spatial, exclude, verb)
  3. **Hidden**: Single choice (Yes/No)
  4. **Distractors**: Single choice (3, 4, 5+)
  5. **Empty Case**: Auto-detected based on whether the ground truth is null
- **Navigation**: Previous and Next buttons with unsaved changes detection
- **Save Categories**: Save button to store all category labels
- **Visual Feedback**: Shows a save confirmation indicator
- **No Skip Logic**: Processes all images, including those with null solutions

### Reference Annotator Tool:
- **Smart Navigation**: Automatically starts with the first unsaved image
- **Bounding Box Selection**: Select from existing bounding boxes instead of drawing new ones
- **Empty Case Option**: Support for selecting "empty case" with [0, 0, 0, 0] coordinates
- **Distractors Calculation**: Automatically calculates distractors based on the selected box
- **Caption Input**: Add captions to selected bounding boxes
- **Category Form**: Provides form controls for labeling multiple categories:
  1. **Hops**: Single choice (2, 3, 4, 5)
  2. **Type**: Multiple choice (spatial, exclude, verb)
  3. **Hidden**: Single choice (Yes/No)
  4. **Distractors**: Auto-calculated based on selected bounding box
  5. **Empty Case**: Auto-detected or can be manually selected
- **Visual Save Status**: Persistent indicator showing whether the current image is saved
- **Improved Visualization**: Bounding boxes are shown with outlines and center points for better visibility
- **Data Persistence**: Properly loads and displays previously saved annotations

## Annotation Workflow

### Bounding Box Annotation:
1. When you start the tool, it loads the first image that needs annotation
2. Read the caption to understand what region needs to be annotated
3. Click and drag on the image to create a bounding box
4. The coordinates will update in real-time
5. Click "Save" to save the annotation
6. The tool will automatically move to the next image
7. Use "Previous" if you need to go back and fix an annotation
8. Use "Redraw" if you want to redraw the current bounding box

### Category Labeling:
1. Launch the category labeler and it loads the first image
2. View the image and its caption to understand the content
3. If present, a reference bounding box is shown in red
4. The "Empty Case" field is automatically set based on the ground truth
5. Select appropriate values for each category:
   - Hops: Select one of (1, 2, 3, 4)
   - Type: Select one or more of (spatial, exclude, verb)
   - Hidden: Select Yes or No
   - Distractors: Select one of (3, 4, 5+)
6. Click "Save" to store your category selections
7. Navigate through images using "Previous" and "Next" buttons
8. The tool will prompt you to save unsaved changes when navigating

### Reference Annotation:
1. Launch the reference annotator and it automatically loads the first unsaved image
2. The available bounding boxes are displayed in the left panel, organized by category
3. Click on a bounding box in the list to select it (or choose "Empty Case" option)
4. The selected box will be highlighted in red on the image
5. Enter a descriptive caption for the selected region
6. Select appropriate values for categories:
   - Hops: Select one of (2, 3, 4, 5)
   - Type: Select one or more of (spatial, exclude, verb)
   - Hidden: Select Yes or No
   - Distractors: Auto-calculated based on the number of instances (minus the selected one)
7. Click "Save Annotation" to store your selections
8. Navigate through images using "Previous" and "Next" buttons
9. The save status indicator shows whether the current image has been saved

## Data Format

### Bounding Box Annotations:
- **solution**: Pixel coordinates [x1, y1, x2, y2]
- **normalized_solution**: Normalized coordinates (0-1000) for width and height

### Category Labels:
- **categories**: Object with the following properties:
  - **empty_case**: Boolean (true/false)
  - **hops**: Number (1, 2, 3, 4)
  - **type**: Array of strings (spatial, exclude, verb)
  - **hidden**: Boolean (true/false)
  - **distractors**: String (3, 4, 5+)

### Reference Annotations:
- **normal_caption**: The descriptive caption for the selected region
- **problem**: Automatically generated problem statement using the caption
- **solution**: Pixel coordinates [x1, y1, x2, y2] of the selected bounding box
- **normalized_solution**: Normalized coordinates (0-1000) for width and height
- **categories**: Same format as the Category Labels
- **image**: Path to the image file (val2017/filename.jpg)

## Troubleshooting

- If images aren't loading, check that the image paths are correct
- If the app crashes, ensure your JSON files are properly formatted
- For PyQt5 version issues, try installing the necessary system dependencies or use the Tkinter or Web version
- Make sure you have the necessary permissions to read/write files in the directories 
- For the web version, ensure your server allows connections on the specified port 
- If the reference annotator doesn't show saved status correctly, try reloading the page 
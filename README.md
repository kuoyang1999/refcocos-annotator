# COCO Bounding Box Annotation Tool

This tool allows you to interactively annotate images with bounding boxes for the COCO dataset.

## Prerequisites

```bash
pip install Flask Pillow
```

## Usage

1. Download the COCO val2017 dataset and annotations:
   ```bash
   # Create data directory
   mkdir -p data/val2017 data/annotations

   # Download val2017 images
   wget http://images.cocodataset.org/zips/val2017.zip
   unzip val2017.zip -d ./data/

   # Download COCO annotations
   wget http://images.cocodataset.org/annotations/annotations_trainval2017.zip
   unzip annotations_trainval2017.zip -d ./data/
   ```

2. Run the find_multiple_instances.py script to prepare the data:
   ```bash
   python find_multiple_instances.py
   ```
   This will generate `val2017_multiple_instances.json` in the current directory

3. Run the reference annotator web application:
   ```bash
   python reference_annotator_web.py
   ```

The reference annotator tool allows you to select from existing bounding boxes in images with multiple instances and annotate them with captions and category metadata. It loads data from `val2017_multiple_instances.json` and saves to `refcocos_test.json`.

Once the server is running, access it through your browser at:
- Local access: http://localhost:5000
- Remote access: http://[server-ip-address]:5000

## Features
- **Smart Navigation**: Automatically starts with the first unsaved image
- **Bounding Box Selection**: Select from existing bounding boxes instead of drawing new ones
- **Empty Case Option**: Support for selecting "empty case" with [0, 0, 0, 0] coordinates
- **Distractors Calculation**: Automatically calculates distractors based on the selected box
- **Caption Input**: Add captions to selected bounding boxes
- **Category Form**: Provides form controls for labeling multiple categories:
  1. **Hops**: Single choice (2, 3, 4, 5)
  2. **Type**: Multiple choice (spatial, exclude, verb, attr)
  3. **Occluded**: Single choice (Yes/No)
  4. **Distractors**: Auto-calculated based on selected bounding box
  5. **Empty Case**: Auto-detected or can be manually selected
- **Visual Save Status**: Persistent indicator showing whether the current image is saved
- **Improved Visualization**: Bounding boxes are shown with outlines and center points for better visibility
- **Data Persistence**: Properly loads and displays previously saved annotations

## Annotation Workflow
1. Launch the reference annotator and it automatically loads the first unsaved image
2. The available bounding boxes are displayed in the left panel, organized by category
3. Click on a bounding box in the list to select it (or choose "Empty Case" option)
4. The selected box will be highlighted in red on the image
5. Enter a descriptive caption for the selected region
6. Select appropriate values for categories:
   - Hops: Select one of (2, 3, 4, 5)
   - Type: Select one or more of (spatial, exclude, verb, attr)
   - Occluded: Select Yes or No
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
  - **hops**: Number (2, 3, 4, 5)
  - **type**: Array of strings (spatial, exclude, verb, attr)
  - **occluded**: Boolean (true/false)
  - **distractors**: String (number)

### Reference Annotations:
- **normal_caption**: The descriptive caption for the selected region
- **problem**: Automatically generated problem statement using the caption
- **solution**: Pixel coordinates [x1, y1, x2, y2] of the selected bounding box
- **normalized_solution**: Normalized coordinates (0-1000) for width and height
- **categories**: Same format as the Category Labels
- **image**: Path to the image file (val2017/filename.jpg)
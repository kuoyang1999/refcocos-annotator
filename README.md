# RefCOCOS Annotator

A tool for creating reference expression annotations for the COCO dataset.

## Overview

The RefCOCOS Annotator is a web interface that allows annotators to create referring expressions for objects in the COCO dataset. The tool displays images with multiple instances of the same category and allows annotators to:

1. Select a bounding box for an object instance
2. Provide a descriptive caption that uniquely identifies that instance
3. Add metadata about the annotation (hops, type, occlusion status)
4. Save multiple annotations per image

## Directory Structure

```
refcocos_annotator/
├── __init__.py            # Package initialization
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── routes/                # Web and API routes
│   ├── __init__.py
│   ├── api.py             # API endpoints
│   └── views.py           # Web routes
├── services/              # Business logic
│   ├── __init__.py
│   ├── data_service.py    # Data loading and processing
│   └── image_service.py   # Image handling
├── static/                # Static assets
│   ├── css/
│   │   └── style.css      # Application styles
│   └── js/
│       └── script.js      # Application JavaScript
├── templates/             # HTML templates
│   └── reference_annotator.html
└── utils/                 # Utility functions
    └── __init__.py
```

## Installation

### From Source

1. Clone the repository:
   ```
   git clone https://github.com/cocodataset/refcocos-annotator.git
   cd refcocos-annotator
   ```

2. Install the package in development mode:
   ```
   pip install -e .
   ```

### Using pip

```
pip install refcocos-annotator
```

## Configuration

The tool is configured via environment variables or by modifying `config.py`:

- `PORT`: Port number (default: 5555)
- `HOST`: Host address (default: 0.0.0.0)
- `DEBUG`: Debug mode (default: True)
- `IMAGE_BASE_DIR`: Base directory for images (default: current directory)
- `MULTIPLE_INSTANCES_FILE`: Path to the instances data file (default: val2017_multiple_instances.json)
- `OUTPUT_FILE`: Path to save annotations (default: refcocos_test.json)

## Usage

### Running the Server

You have two options to run the server:

#### For Development

```bash
python run.py
```

#### For Production (using a WSGI server)

```bash
# Option 1: Directly with Python
python wsgi.py

# Option 2: Using Gunicorn (install with: pip install gunicorn)
gunicorn wsgi:app

# Option 3: Using uWSGI (install with: pip install uwsgi)
uwsgi --http :5555 --module wsgi:app
```

The web interface will be available at http://localhost:5555

### Command Line Tool

Alternatively, you can use the command-line tool that's installed with the package:

```bash
refcocos-annotator
```

### Annotation Process

1. View an image with multiple instances of the same category
2. Select a bounding box or create a custom one
3. Write a descriptive caption that uniquely identifies the object
4. Set the annotation metadata:
   - Hops: Number of relationships needed to identify the object
   - Type: Categorize the reference expression (spatial, exclusion, verb, attribute)
   - Occluded: Whether the object is occluded
5. Save the annotation
6. Create multiple annotations per image if desired

## Development

### Requirements

- Python 3.6+
- Flask
- Pillow

### Running Tests

```
pytest
```

## License

MIT License
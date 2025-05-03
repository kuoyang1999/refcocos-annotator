"""Configuration settings for the RefCOCOS Annotator."""
import os

# Default configuration
IMAGE_BASE_DIR = "."
MULTIPLE_INSTANCES_FILE = "data/test_images_multiple_instances_filtered.json"
OUTPUT_FILE = "results/openimages_test.json"

# Flask configuration
DEBUG = True
PORT = int(os.environ.get('PORT', 5555))
HOST = '0.0.0.0'

# Configure paths based on package location
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_FOLDER = os.path.join(PACKAGE_DIR, 'static')
TEMPLATE_FOLDER = os.path.join(PACKAGE_DIR, 'templates') 
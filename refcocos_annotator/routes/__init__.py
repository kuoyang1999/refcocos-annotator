"""Routes for the RefCOCOS Annotator."""

from flask import Blueprint

# Create blueprint for web routes
web_bp = Blueprint('web', __name__)

# Create blueprint for API routes
api_bp = Blueprint('api', __name__, url_prefix='/api') 
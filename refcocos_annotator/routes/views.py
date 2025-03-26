"""Web view routes for the RefCOCOS Annotator."""
from flask import render_template
from refcocos_annotator.routes import web_bp

@web_bp.route('/')
def index():
    """Render the main annotation page."""
    return render_template('reference_annotator.html') 
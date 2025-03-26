"""Main Flask application for the RefCOCOS Annotator."""
import os
from flask import Flask

from refcocos_annotator.config import DEBUG, HOST, PORT, STATIC_FOLDER, TEMPLATE_FOLDER
from refcocos_annotator.routes import web_bp, api_bp
from refcocos_annotator.services import data_service

# Import routes to ensure they're registered
import refcocos_annotator.routes.views
import refcocos_annotator.routes.api

def create_app():
    """Create and configure the Flask application.
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__, 
                static_folder=STATIC_FOLDER,
                template_folder=TEMPLATE_FOLDER)
    
    # Register blueprints
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)
    
    return app

def init_data():
    """Initialize the application data.
    
    Returns:
        Tuple of success status and message
    """
    # Make sure directories exist
    os.makedirs('static', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    # Load data
    return data_service.load_data()

def run_app():
    """Run the Flask application."""
    app = create_app()
    
    # Initialize data
    success, message = init_data()
    print(message)
    
    # Run the application
    app.run(host=HOST, port=PORT, debug=DEBUG)

if __name__ == '__main__':
    run_app() 
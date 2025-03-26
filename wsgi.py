#!/usr/bin/env python
"""WSGI entry point for the RefCOCOS Annotator."""

from refcocos_annotator.app import create_app, init_data

# Initialize the application
app = create_app()

# Initialize the data
init_data()

if __name__ == "__main__":
    from refcocos_annotator.config import DEBUG, HOST, PORT
    app.run(host=HOST, port=PORT, debug=DEBUG) 
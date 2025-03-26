"""API routes for the RefCOCOS Annotator."""
from flask import jsonify, request
from refcocos_annotator.routes import api_bp
from refcocos_annotator.services import data_service

@api_bp.route('/image/<int:index>')
def get_image(index):
    """API endpoint to get image data.
    
    Args:
        index: The index of the image to get
        
    Returns:
        JSON response with image data
    """
    result = data_service.get_image_data(int(index))
    return jsonify(result)

@api_bp.route('/save_reference', methods=['POST'])
def save_reference():
    """API endpoint to save reference annotation.
    
    Returns:
        JSON response with success status
    """
    try:
        data = request.json
        image_id = data.get('image_id')
        annotation = data.get('annotation')

        if image_id is None or annotation is None:
            return jsonify({"success": False, "message": "Invalid data"}), 400

        success, message = data_service.save_reference_annotation(image_id, annotation)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@api_bp.route('/reload')
def reload_data():
    """API endpoint to reload data.
    
    Returns:
        JSON response with success status
    """
    success, message = data_service.load_data()
    return jsonify({"success": success, "message": message})

@api_bp.route('/image_status')
def get_image_status():
    """API endpoint to get image status information.
    
    Returns:
        JSON response with status information
    """
    status = data_service.get_image_status()
    if "error" in status:
        return jsonify(status), 404
    return jsonify(status)

@api_bp.route('/saved_data')
def get_saved_data():
    """API endpoint to get all saved annotations.
    
    Returns:
        JSON response with saved annotations
    """
    return jsonify(data_service.get_saved_data())

@api_bp.route('/delete_annotation', methods=['POST'])
def delete_annotation():
    """API endpoint to delete a reference annotation.
    
    Returns:
        JSON response with success status
    """
    try:
        data = request.json
        image_id = data.get('image_id')
        annotation_id = data.get('annotation_id')

        if image_id is None or annotation_id is None:
            return jsonify({"success": False, "message": "Invalid data"}), 400

        success, message = data_service.delete_annotation(annotation_id)
        if not success:
            return jsonify({"success": False, "message": message}), 404
        
        return jsonify({"success": True, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@api_bp.route('/last_saved_index')
def get_last_saved_index():
    """API endpoint to get the index of the last saved image.
    
    Returns:
        JSON response with the last saved index
    """
    index = data_service.get_last_saved_index()
    return jsonify({"index": index}) 
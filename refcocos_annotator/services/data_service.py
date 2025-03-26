"""Data handling service for the RefCOCOS Annotator."""
import json
import os
from typing import Dict, List, Tuple, Any

from refcocos_annotator.config import MULTIPLE_INSTANCES_FILE, OUTPUT_FILE

# Global variables
multiple_instances_data = None
output_data = []

def load_data() -> Tuple[bool, str]:
    """Load multiple instances data and any existing output data.
    
    Returns:
        Tuple[bool, str]: Success status and message
    """
    global multiple_instances_data, output_data

    try:
        # Load multiple instances data
        with open(MULTIPLE_INSTANCES_FILE, "r") as f:
            multiple_instances_data = json.load(f)

        # Try to load existing output data if it exists
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, "r") as f:
                output_data = json.load(f)

        # If output file doesn't exist yet, initialize with empty array
        if not isinstance(output_data, list):
            output_data = []

        return True, f"Loaded {len(multiple_instances_data['images'])} images with multiple instances"
    except Exception as e:
        return False, f"Failed to load data: {str(e)}"

def save_reference_annotation(image_id: str, annotation: Dict[str, Any]) -> Tuple[bool, str]:
    """Save a reference annotation for the specified image.
    
    Args:
        image_id: The ID of the image
        annotation: The annotation data to save
        
    Returns:
        Tuple[bool, str]: Success status and message
    """
    global output_data

    try:
        # Each image can have multiple annotations
        # Check if this particular annotation already exists
        existing_index = -1
        annotation_id = annotation.get("annotation_id", None)
        
        if annotation_id is not None:
            for i, item in enumerate(output_data):
                if item.get("image") == annotation["image"] and item.get("annotation_id") == annotation_id:
                    existing_index = i
                    break

        # Update existing or add new
        if existing_index >= 0:
            output_data[existing_index] = annotation
        else:
            # Generate a new annotation ID if not provided
            if not annotation_id:
                annotation["annotation_id"] = f"{image_id}_{len([a for a in output_data if a.get('image') == 'val2017/' + annotation['file_name']])}"
            output_data.append(annotation)

        # Save to file
        with open(OUTPUT_FILE, "w") as f:
            json.dump(output_data, f, indent=2)

        return True, "Annotation saved successfully"
    except Exception as e:
        return False, f"Failed to save annotation: {str(e)}"

def delete_annotation(annotation_id: str) -> Tuple[bool, str]:
    """Delete an annotation by ID.
    
    Args:
        annotation_id: The ID of the annotation to delete
        
    Returns:
        Tuple[bool, str]: Success status and message
    """
    global output_data
    
    try:
        # Find and remove the annotation from output_data
        found = False
        for i, item in enumerate(output_data):
            if item.get("annotation_id") == annotation_id:
                output_data.pop(i)
                found = True
                break
        
        if not found:
            return False, "Annotation not found"
        
        # Save updated data to file
        with open(OUTPUT_FILE, "w") as f:
            json.dump(output_data, f, indent=2)
            
        return True, "Annotation deleted successfully"
    except Exception as e:
        return False, f"Failed to delete annotation: {str(e)}"

def get_image_data(index: int) -> Dict[str, Any]:
    """Get image data for the given index.
    
    Args:
        index: The index of the image in the dataset
        
    Returns:
        Dict: Image data or error
    """
    from refcocos_annotator.services.image_service import encode_image
    
    if not multiple_instances_data or index >= len(multiple_instances_data["images"]):
        return {"error": "Image not found"}

    image_data = multiple_instances_data["images"][index]

    # Load the image
    image_path = image_data["path"]

    try:
        # Get base64 encoded image
        img_str = encode_image(image_path)

        # Create response with image data and all information
        result = {
            "index": index,
            "total_images": len(multiple_instances_data["images"]),
            "image_data": f"data:image/jpeg;base64,{img_str}",
            "image_id": image_data["image_id"],
            "file_name": image_data["file_name"],
            "width": image_data["width"],
            "height": image_data["height"],
            "path": image_data["path"],
            "categories_with_multiple_instances": image_data["categories_with_multiple_instances"]
        }

        return result
    except Exception as e:
        return {"error": f"Failed to load image: {str(e)}"}

def get_saved_data() -> Dict[str, List[Dict[str, Any]]]:
    """Get all saved annotations grouped by image ID.
    
    Returns:
        Dict: Annotations by image ID
    """
    # Create a dictionary mapping image IDs to saved annotations (multiple per image)
    saved_data = {}

    for item in output_data:
        # Extract image ID from path
        image_path = item.get("image", "")
        if image_path:
            # Try to find matching image from multiple_instances_data
            for img in multiple_instances_data["images"]:
                if "val2017/" + img["file_name"] == image_path:
                    if img["image_id"] not in saved_data:
                        saved_data[img["image_id"]] = []
                    
                    saved_data[img["image_id"]].append(item)
                    break

    return saved_data

def get_last_saved_index() -> int:
    """Get the index of the last saved image according to original order.
    
    Returns:
        int: Index of the last saved image
    """
    if not multiple_instances_data:
        return 0

    # If no output data, return the first image
    if not output_data:
        return 0

    # Create a lookup of image IDs to their indices in the original JSON
    image_id_to_index = {}
    for i, img in enumerate(multiple_instances_data["images"]):
        image_id_to_index[img["image_id"]] = i

    # Find all image IDs that have saved annotations
    saved_image_ids = set()
    for item in output_data:
        image_path = item.get("image", "")
        if image_path:
            for img in multiple_instances_data["images"]:
                if "val2017/" + img["file_name"] == image_path:
                    saved_image_ids.add(img["image_id"])
                    break

    # Find the highest index (last in sequence) with saved annotations
    last_index = 0
    for img_id in saved_image_ids:
        if img_id in image_id_to_index:
            last_index = max(last_index, image_id_to_index[img_id])

    return last_index

def get_image_status() -> Dict[str, Any]:
    """Get image status information.
    
    Returns:
        Dict: Status information
    """
    if not multiple_instances_data:
        return {"error": "No data loaded"}

    # Get total number of images
    total_images = len(multiple_instances_data["images"])

    # Get list of saved image IDs and annotations
    saved_image_ids = []
    saved_annotations = {}
    
    for item in output_data:
        # Extract image ID from path
        image_path = item.get("image", "")
        if image_path:
            # Try to find matching image from multiple_instances_data
            for img in multiple_instances_data["images"]:
                if "val2017/" + img["file_name"] == image_path:
                    img_id = img["image_id"]
                    if img_id not in saved_image_ids:
                        saved_image_ids.append(img_id)
                    
                    # Group annotations by image_id
                    if img_id not in saved_annotations:
                        saved_annotations[img_id] = []
                    
                    saved_annotations[img_id].append(item)
                    break

    return {
        "total_images": total_images,
        "saved_image_ids": saved_image_ids,
        "saved_annotations": saved_annotations
    } 
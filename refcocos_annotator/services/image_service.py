"""Image handling service for the RefCOCOS Annotator."""
import base64
from io import BytesIO
from typing import List, Tuple
from PIL import Image

def encode_image(image_path: str) -> str:
    """Encode an image to base64 for embedding in HTML.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        str: Base64 encoded image string
    """
    with Image.open(image_path) as img:
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return img_str

def calculate_normalized_solution(bbox: List[float], width: int, height: int) -> List[int]:
    """Calculate normalized solution coordinates in 0-1000 range.
    
    Args:
        bbox: Bounding box coordinates [x1, y1, x2, y2]
        width: Image width
        height: Image height
        
    Returns:
        List[int]: Normalized coordinates [norm_x1, norm_y1, norm_x2, norm_y2]
    """
    if not bbox:
        return None

    [x1, y1, x2, y2] = bbox

    # Calculate normalized coordinates (0-1000 range)
    norm_x1 = round(x1 / width * 1000)
    norm_y1 = round(y1 / height * 1000)
    norm_x2 = round(x2 / width * 1000)
    norm_y2 = round(y2 / height * 1000)

    return [norm_x1, norm_y1, norm_x2, norm_y2]

def convert_bbox_format(bbox: List[float]) -> List[float]:
    """Convert COCO bbox format [x, y, width, height] to [x1, y1, x2, y2].
    
    Args:
        bbox: Bounding box in COCO format [x, y, width, height]
        
    Returns:
        List[float]: Bounding box in [x1, y1, x2, y2] format
    """
    return [
        bbox[0],                 # x1
        bbox[1],                 # y1
        bbox[0] + bbox[2],       # x2 = x + width
        bbox[1] + bbox[3]        # y2 = y + height
    ] 
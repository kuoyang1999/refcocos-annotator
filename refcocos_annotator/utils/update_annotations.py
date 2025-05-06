"""Script to update existing annotations with image_index attribute."""
import json
import os
import sys
import time
from typing import Dict, List, Any

# Add parent directory to path to import from refcocos_annotator
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from refcocos_annotator.config import MULTIPLE_INSTANCES_FILE, OUTPUT_FILE

def update_annotations():
    """Add image_index attribute to all existing annotations."""
    print(f"Reading output file: {OUTPUT_FILE}")
    
    # Load output data
    try:
        with open(OUTPUT_FILE, "r") as f:
            output_data = json.load(f)
    except Exception as e:
        print(f"Error loading output data: {str(e)}")
        return
    
    # Load multiple instances data
    try:
        with open(MULTIPLE_INSTANCES_FILE, "r") as f:
            multiple_instances_data = json.load(f)
    except Exception as e:
        print(f"Error loading multiple instances data: {str(e)}")
        return
    
    # Create a mapping from image path to index
    image_path_to_index = {}
    for i, img in enumerate(multiple_instances_data["images"]):
        image_path = "open_image_v7/" + img["file_name"]
        image_path_to_index[image_path] = i
    
    # Update annotations with image_index
    updated_count = 0
    annotations_with_id_added = 0
    
    for item in output_data:
        # Get image path
        image_path = item.get("image", "")
        
        # Skip if already has image_index
        # if "image_index" in item:
        #     continue
        
        # Find the index for this image
        if image_path in image_path_to_index:
            item["image_index"] = image_path_to_index[image_path]
            updated_count += 1
            
            # Check for missing annotation_id
            if "annotation_id" not in item:
                # Extract file_name from image path if not present
                if "file_name" not in item and image_path:
                    img_filename = image_path.split("/")[-1]
                    item["file_name"] = img_filename
                    print(f"Added missing file_name: {img_filename}")
                
                # Generate annotation_id using file_name or image path
                if "file_name" in item:
                    img_id = item["file_name"].split(".")[0]
                    item["annotation_id"] = f"{img_id}_{int(time.time() * 1000)}"
                    annotations_with_id_added += 1
                    print(f"Added missing annotation_id: {item['annotation_id']}")
                elif image_path:
                    img_id = image_path.split("/")[-1].split(".")[0]
                    item["annotation_id"] = f"{img_id}_{int(time.time() * 1000)}"
                    annotations_with_id_added += 1
                    print(f"Added missing annotation_id from image path: {item['annotation_id']}")
                else:
                    # Fallback to a random ID
                    item["annotation_id"] = f"unknown_{int(time.time() * 1000)}"
                    annotations_with_id_added += 1
                    print(f"Added fallback annotation_id: {item['annotation_id']}")
        else:
            print(f"Warning: Could not find index for image {image_path}")
    
    # Save updated data back to file
    try:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"Successfully updated {updated_count} annotations with image_index")
        print(f"Added annotation_id to {annotations_with_id_added} annotations")
    except Exception as e:
        print(f"Error saving updated data: {str(e)}")

def force_update_annotations():
    """Force update all annotations to ensure they have annotation_id, regardless of image_index."""
    print(f"Reading output file: {OUTPUT_FILE}")
    
    # Load output data
    try:
        with open(OUTPUT_FILE, "r") as f:
            output_data = json.load(f)
    except Exception as e:
        print(f"Error loading output data: {str(e)}")
        return
    
    # Load multiple instances data
    try:
        with open(MULTIPLE_INSTANCES_FILE, "r") as f:
            multiple_instances_data = json.load(f)
    except Exception as e:
        print(f"Error loading multiple instances data: {str(e)}")
        return
    
    # Create a mapping from image path to index
    image_path_to_index = {}
    for i, img in enumerate(multiple_instances_data["images"]):
        image_path = "open_image_v7/" + img["file_name"]
        image_path_to_index[image_path] = i
    
    # Update all annotations regardless of image_index
    updated_count = 0
    annotations_with_id_added = 0
    
    for i, item in enumerate(output_data):
        updated = False
        
        # Get image path
        image_path = item.get("image", "")
        
        # Add image_index if missing
        if "image_index" not in item and image_path in image_path_to_index:
            item["image_index"] = image_path_to_index[image_path]
            updated = True
            updated_count += 1
        
        # Add file_name if missing but image is present
        if "file_name" not in item and image_path:
            img_filename = image_path.split("/")[-1]
            item["file_name"] = img_filename
            updated = True
            print(f"Item {i}: Added missing file_name: {img_filename}")
        
        # Always ensure annotation_id is present
        if "annotation_id" not in item:
            if "file_name" in item:
                img_id = item["file_name"].split(".")[0]
                item["annotation_id"] = f"{img_id}_{int(time.time() * 1000)}"
            elif image_path:
                img_id = image_path.split("/")[-1].split(".")[0]
                item["annotation_id"] = f"{img_id}_{int(time.time() * 1000)}"
            else:
                # Fallback to a random ID + position
                item["annotation_id"] = f"unknown_{i}_{int(time.time() * 1000)}"
            
            annotations_with_id_added += 1
            updated = True
            print(f"Item {i}: Added missing annotation_id: {item['annotation_id']}")
        
        # Add small delay to ensure different timestamps
        if updated:
            time.sleep(0.001)
    
    # Save updated data back to file
    try:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"Successfully updated {updated_count} annotations with image_index")
        print(f"Added annotation_id to {annotations_with_id_added} annotations")
        print(f"Total items processed: {len(output_data)}")
    except Exception as e:
        print(f"Error saving updated data: {str(e)}")

if __name__ == "__main__":
    # Choose which function to run
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("Running force update to ensure all annotations have IDs")
        force_update_annotations()
    else:
        print("Running normal update for annotations missing image_index")
        update_annotations() 
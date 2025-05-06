#!/usr/bin/env python3
"""
Consolidate person-related categories in the RefCOCOS dataset.

This script reads a JSON file containing image annotations and:
1. Renames standalone person-related categories to "Person"
2. For images with multiple person-related categories, calculates IoU and merges overlapping instances
3. Reindexes all image IDs to ensure consistency
4. Outputs the consolidated data to a new JSON file
"""

import json
import os
import argparse
from collections import defaultdict

# Define person-related categories to consolidate
PERSON_CATEGORIES = [
    "Man", "Woman", "Boy", "Girl", "Person", "Human", "Child", "Adult", "Human body",
    "Mammal"
]

# IoU threshold for considering two boxes as the same object
IOU_THRESHOLD = 0.75  # Adjust this value based on your needs

def calculate_iou(box1, box2):
    """
    Calculate the Intersection over Union (IoU) between two bounding boxes.
    
    Each box is expected to be in format [x, y, width, height]
    """
    # Convert to [x1, y1, x2, y2] format
    box1_x1, box1_y1 = box1[0], box1[1]
    box1_x2, box1_y2 = box1[0] + box1[2], box1[1] + box1[3]
    
    box2_x1, box2_y1 = box2[0], box2[1]
    box2_x2, box2_y2 = box2[0] + box2[2], box2[1] + box2[3]
    
    # Calculate intersection area
    x_left = max(box1_x1, box2_x1)
    y_top = max(box1_y1, box2_y1)
    x_right = min(box1_x2, box2_x2)
    y_bottom = min(box1_y2, box2_y2)
    
    if x_right < x_left or y_bottom < y_top:
        # No intersection
        return 0.0
    
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    
    # Calculate union area
    box1_area = (box1_x2 - box1_x1) * (box1_y2 - box1_y1)
    box2_area = (box2_x2 - box2_x1) * (box2_y2 - box2_y1)
    union_area = box1_area + box2_area - intersection_area
    
    # Calculate IoU
    iou = intersection_area / union_area if union_area > 0 else 0.0
    
    return iou

def process_image(image_data):
    """Process a single image's data to consolidate person categories."""
    if "categories_with_multiple_instances" not in image_data:
        return image_data
    
    # Identify person-related categories
    person_categories = []
    other_categories = []
    
    for category in image_data["categories_with_multiple_instances"]:
        if category["category_name"] in PERSON_CATEGORIES:
            person_categories.append(category)
        else:
            other_categories.append(category)
    
    # If no person categories found, return unchanged
    if not person_categories:
        return image_data
    
    # If only one person category, rename it to "Person"
    if len(person_categories) == 1:
        person_categories[0]["category_name"] = "Person"
        image_data["categories_with_multiple_instances"] = other_categories + person_categories
        if "primary_category" in image_data and image_data["primary_category"] in PERSON_CATEGORIES:
            image_data["primary_category"] = "Person"
        return image_data
    
    # Multiple person categories - need to consolidate
    all_instances = []
    all_attributes = []
    
    # Collect all instances and attributes from person categories
    for category in person_categories:
        for i, bbox in enumerate(category["instances"]):
            all_instances.append({
                "bbox": bbox,
                "original_category": category["category_name"],
                "attributes": category["instance_attributes"][i] if "instance_attributes" in category else {}
            })
    
    # Group instances based on IoU
    merged_instances = []
    merged_attributes = []
    used_indices = set()
    
    for i, instance1 in enumerate(all_instances):
        if i in used_indices:
            continue
            
        current_group = [instance1]
        current_indices = [i]
        
        for j, instance2 in enumerate(all_instances):
            if j in used_indices or i == j:
                continue
                
            iou = calculate_iou(instance1["bbox"], instance2["bbox"])
            if iou >= IOU_THRESHOLD:
                current_group.append(instance2)
                current_indices.append(j)
        
        # Mark all these instances as used
        used_indices.update(current_indices)
        
        # Use the first instance's bbox
        merged_instances.append(instance1["bbox"])
        
        # Merge attributes by taking the max value for each
        merged_attr = {}
        for instance in current_group:
            for attr_name, attr_value in instance.get("attributes", {}).items():
                if attr_name not in merged_attr or attr_value > merged_attr[attr_name]:
                    merged_attr[attr_name] = attr_value
        
        merged_attributes.append(merged_attr)
    
    # Create a new "Person" category with the merged instances
    person_category = {
        "category_id": "/m/01g317", # Standard category ID for person
        "category_name": "Person",
        "count": len(merged_instances),
        "instances": merged_instances,
        "instance_attributes": merged_attributes
    }
    
    # Update the image data
    image_data["categories_with_multiple_instances"] = other_categories + [person_category]
    
    # Update primary category if it was a person
    if "primary_category" in image_data and image_data["primary_category"] in PERSON_CATEGORIES:
        image_data["primary_category"] = "Person"
    
    return image_data

def consolidate_categories(input_file, output_file):
    """Consolidate categories in the input file and write to output file."""
    print(f"Reading input file: {input_file}")
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    print(f"Total images: {len(data['images'])}")
    print("Processing images...")
    
    # Process each image
    processed_images = []
    person_category_count = 0
    consolidated_count = 0
    
    for i, image_data in enumerate(data["images"]):
        original_person_categories = sum(1 for cat in image_data.get("categories_with_multiple_instances", []) 
                                        if cat["category_name"] in PERSON_CATEGORIES)
        
        if original_person_categories > 0:
            person_category_count += 1
            
        processed_image = process_image(image_data)
        
        # Check if consolidation happened
        new_person_categories = sum(1 for cat in processed_image.get("categories_with_multiple_instances", []) 
                                   if cat["category_name"] == "Person")
        if original_person_categories > new_person_categories:
            consolidated_count += 1
            
        processed_images.append(processed_image)
        
        # Print progress
        if (i + 1) % 1000 == 0:
            print(f"Processed {i + 1}/{len(data['images'])} images")
    
    # Update the data with processed images
    data["images"] = processed_images
    
    # Reindex image IDs
    print("Reindexing image IDs...")
    for new_id, image in enumerate(data["images"]):
        image["image_id"] = new_id
    
    print(f"Writing output file: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print("\nStatistics:")
    print(f"Total images with person categories: {person_category_count}")
    print(f"Images with consolidated categories: {consolidated_count}")
    print(f"Total images reindexed: {len(data['images'])}")
    print("Done!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Consolidate person-related categories in RefCOCOS dataset')
    parser.add_argument('--input', default='data/test_images_multiple_instances_filtered.json',
                        help='Input JSON file')
    parser.add_argument('--output', default='data/open_image_v7.json',
                        help='Output JSON file')
    args = parser.parse_args()
    
    consolidate_categories(args.input, args.output) 
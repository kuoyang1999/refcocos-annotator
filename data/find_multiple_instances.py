#!/usr/bin/env python3
import os
import json
import argparse
from collections import defaultdict

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Find images with 3 or more instances of the same object category')
    
    parser.add_argument('--min-instances', type=int, default=3,
                        help='Minimum number of instances of a category to be considered (default: 3)')
    parser.add_argument('--annotation-file', type=str, default="./data/annotations/instances_val2017.json",
                        help='Path to COCO annotation file (default: ./data/annotations/instances_val2017.json)')
    parser.add_argument('--img-dir', type=str, default="./data/val2017",
                        help='Path to image directory (default: ./data/val2017)')
    parser.add_argument('--output-file', type=str, default="./data/val2017_multiple_instances.json",
                        help='Path to output JSON file (default: val2017_multiple_instances.json)')
    
    return parser.parse_args()

def filter_images_with_multiple_instances(args):
    """Find images with multiple instances of the same object category"""
    # Load annotations
    print(f"Loading COCO annotations from {args.annotation_file}...")
    try:
        with open(args.annotation_file, 'r') as f:
            coco_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Annotation file {args.annotation_file} not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {args.annotation_file}.")
        return
    
    # Create mapping from image_id to image info
    image_id_to_info = {}
    for image_info in coco_data.get('images', []):
        image_id_to_info[image_info['id']] = image_info
    
    # Get category information
    category_id_to_name = {cat['id']: cat['name'] for cat in coco_data.get('categories', [])}
    
    # Group annotations by image_id
    print("Organizing annotations by image...")
    image_annotations = defaultdict(list)
    for annotation in coco_data.get('annotations', []):
        image_id = annotation['image_id']
        image_annotations[image_id].append(annotation)
    
    # Count object instances per category per image and collect annotations
    print("Analyzing annotations...")
    image_category_counts = defaultdict(lambda: defaultdict(int))
    image_category_annotations = defaultdict(lambda: defaultdict(list))
    
    for image_id, annotations in image_annotations.items():
        for annotation in annotations:
            category_id = annotation['category_id']
            image_category_counts[image_id][category_id] += 1
            image_category_annotations[image_id][category_id].append(annotation)
    
    # Filter images: keep those with at least min_instances of at least one category
    valid_images = []
    for image_id, category_counts in image_category_counts.items():
        has_enough_instances = False
        categories_with_instances = []
        
        for category_id, count in category_counts.items():
            if count >= args.min_instances:
                has_enough_instances = True
                # Get all bbox annotations for this category
                bbox_annotations = []
                for ann in image_category_annotations[image_id][category_id]:
                    bbox_annotations.append(ann['bbox'])  # Just store the bbox coordinates [x, y, width, height]
                
                categories_with_instances.append({
                    "category_id": category_id,
                    "category_name": category_id_to_name[category_id],
                    "count": count,
                    "instances": bbox_annotations
                })
        
        if has_enough_instances and image_id in image_id_to_info:
            # Verify that the image file exists
            image_info = image_id_to_info[image_id]
            file_name = image_info['file_name']
            img_path = os.path.join(args.img_dir, file_name)
            
            if os.path.exists(img_path):
                valid_images.append({
                    "image_id": image_id,
                    "file_name": file_name,
                    "width": image_info['width'],
                    "height": image_info['height'],
                    "path": img_path,
                    "categories_with_multiple_instances": categories_with_instances
                })
    
    print(f"Found {len(valid_images)} images with at least {args.min_instances} instances of the same object category")
    
    # Save results to output file
    print(f"Saving results to {args.output_file}...")
    with open(args.output_file, 'w') as f:
        json.dump({
            "min_instances": args.min_instances,
            "total_images_found": len(valid_images),
            "images": valid_images
        }, f, indent=2)
    
    print(f"Results saved to {args.output_file}")
    
    # Print some examples
    if valid_images:
        print("\nExample images with multiple instances:")
        for i, img in enumerate(valid_images[:5]):  # Show up to 5 examples
            print(f"\n{i+1}. {img['file_name']} (Image ID: {img['image_id']})")
            print("   Categories with 3+ instances:")
            for cat in img['categories_with_multiple_instances']:
                print(f"   - {cat['category_name']}: {cat['count']} instances")
                print(f"     First few bounding boxes: {cat['instances'][:2]}")
        
        if len(valid_images) > 5:
            print(f"\n... and {len(valid_images) - 5} more images.")

def main():
    # Parse command-line arguments
    args = parse_args()
    
    # Check if the image directory exists
    if not os.path.exists(args.img_dir):
        print(f"Error: Image directory {args.img_dir} not found.")
        return
    
    # Filter the images
    filter_images_with_multiple_instances(args)
    
    print("Done!")

if __name__ == "__main__":
    main() 
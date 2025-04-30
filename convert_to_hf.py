import json
import os
from datasets import Dataset, Features, Value, Sequence, ClassLabel, Image
from PIL import Image as PILImage
import numpy as np

def convert_refcocos_to_hf(json_path, output_dir=None, image_root=""):
    """
    Convert RefCOCOS JSON to HuggingFace dataset format

    Args:
        json_path: Path to the input JSON file
        output_dir: Directory to save the HF dataset (if None, will not save)
        image_root: Root directory containing the images

    Returns:
        HuggingFace Dataset object
    """
    # Load the JSON data
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Initialize dictionaries to hold our features
    features = {
        'annotation_id': [],
        'dataset': [],
        'text_type': [],
        'height': [],
        'width': [],
        'caption': [],
        'image_path': [],
        'file_name': [],
        'problem': [],
        'bbox': [],
        'normalized_bbox': [],
        'empty_case': [],
        'hops': [],
        'type': [],
        'occluded': [],
        'distractors': [],
        'image_index': [],
        'image': []
    }

    # Process each entry
    for entry in data:
        features['annotation_id'].append(entry.get('annotation_id', ''))
        features['dataset'].append(entry.get('dataset', ''))
        features['text_type'].append(entry.get('text_type', ''))
        features['height'].append(entry.get('height', 0))
        features['width'].append(entry.get('width', 0))
        features['caption'].append(entry.get('normal_caption', ''))
        features['image_path'].append(entry.get('image', ''))
        features['file_name'].append(entry.get('file_name', ''))
        features['problem'].append(entry.get('problem', ''))

        # Handle bounding box coordinates as integers
        solution = entry.get('solution', [0, 0, 0, 0])
        features['bbox'].append([int(round(coord)) for coord in solution]
                                if solution is not None else None)

        features['normalized_bbox'].append(entry.get('normalized_solution', [0, 0, 0, 0]))

        # Handle categories
        categories = entry.get('categories', {})
        features['empty_case'].append(categories.get('empty_case', False))
        features['hops'].append(categories.get('hops', '0'))

        # Handle type as a list
        type_list = categories.get('type', [])
        features['type'].append(type_list if isinstance(type_list, list) else [])

        features['occluded'].append(categories.get('occluded', False))
        features['distractors'].append(categories.get('distractors', '0'))

        # Handle image index
        features['image_index'].append(entry.get('image_index', 0))

        # Load and add the image
        image_path = os.path.join(image_root, entry.get('image', ''))
        try:
            if os.path.exists(image_path):
                img = PILImage.open(image_path)
                features['image'].append(img)
            else:
                # Add a placeholder if image doesn't exist
                features['image'].append(None)
                print(f"Warning: Image not found at {image_path}")
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            features['image'].append(None)

    # Define explicit feature types for the dataset
    feature_types = Features({
        'image': Image(),
        'caption': Value('string'),
        'bbox': Sequence(Value('int32')),
        'problem': Value('string'),
        'annotation_id': Value('string'),
        'dataset': Value('string'),
        'text_type': Value('string'),
        'height': Value('int32'),
        'width': Value('int32'),
        'image_path': Value('string'),
        'file_name': Value('string'),
        'normalized_bbox': Sequence(Value('int32')),
        'empty_case': Value('bool'),
        'hops': Value('string'),
        'type': Sequence(Value('string')),
        'occluded': Value('bool'),
        'distractors': Value('string'),
        'image_index': Value('int32'),
    })

    # Create HuggingFace Dataset with explicit features
    hf_dataset = Dataset.from_dict(features, features=feature_types)

    # Save the dataset if output_dir is provided
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        hf_dataset.save_to_disk(output_dir)
        print(f"Dataset saved to {output_dir}")

    return hf_dataset

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Convert RefCOCOS JSON to HuggingFace dataset')
    parser.add_argument('--json_path', '-j', type=str, required=True, help='Path to the RefCOCOS JSON file')
    parser.add_argument('--output_dir', '-o', type=str, default='hf_dataset', help='Directory to save the HuggingFace dataset')
    parser.add_argument('--image_root', '-i', type=str, default='', help='Root directory containing the images')
    parser.add_argument('--push_to_hub', '-p', type=str, default=None,
                       help='If provided, will push the dataset to this HuggingFace Hub repository')

    args = parser.parse_args()

    # Convert the dataset
    hf_dataset = convert_refcocos_to_hf(args.json_path, args.output_dir, args.image_root)

    # Push to Hub if requested
    if args.push_to_hub:
        # hf_dataset.push_to_hub('dddraxxx/'+args.push_to_hub, split='test_1')
        hf_dataset.push_to_hub('dddraxxx/'+args.push_to_hub, split='test')
        print(f"Dataset pushed to HuggingFace Hub: {args.push_to_hub}")

    # Print dataset information
    print(f"Dataset created with {len(hf_dataset)} examples")
    print(f"Dataset features: {hf_dataset.features}")

"""
python convert_to_hf.py -j /mnt/data/kuo/qh/refcocos-annotator/results/refcocos_test.json -i /mnt/data/kuo/qh/refcocos-annotator/images -p refcocos
"""
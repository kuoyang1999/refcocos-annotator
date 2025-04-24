#!/usr/bin/env python
"""
Example usage of the RefCOCOS dataset after conversion to HuggingFace format.
This script demonstrates:
1. Loading the dataset
2. Basic dataset exploration
3. A simple visualization of an image with its bounding box
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
from datasets import load_from_disk
import argparse

def visualize_example(dataset, index=0, image_root=""):
    """
    Visualize an example from the dataset with its bounding box

    Args:
        dataset: HuggingFace dataset
        index: Index of the example to visualize
        image_root: Root directory containing the images (optional, only used if dataset doesn't contain images)
    """
    example = dataset[index]

    # Print example information
    print(f"Caption: {example['caption']}")
    print(f"Problem: {example['problem']}")
    print(f"Bounding Box: {example['bbox']}")

    # Check if image is in the dataset
    if 'image' in example and example['image'] is not None:
        img = example['image']
    else:
        # Load the image from file if not in dataset
        image_path = os.path.join(image_root, example['image_path'])
        if not os.path.exists(image_path):
            print(f"Image not found at {image_path}")
            print("Please provide the correct image_root directory")
            return
        img = Image.open(image_path)

    # Plot the image with bounding box
    fig, ax = plt.subplots(1)
    ax.imshow(img)

    # Extract bounding box coordinates
    x1, y1, x2, y2 = example['bbox']

    # Create a Rectangle patch
    rect = patches.Rectangle(
        (x1, y1), x2-x1, y2-y1,
        linewidth=2, edgecolor='r', facecolor='none'
    )

    # Add the rectangle to the plot
    ax.add_patch(rect)

    # Add caption as title
    plt.title(example['caption'])
    plt.axis('off')
    plt.tight_layout()
    plt.show()

def explore_dataset(dataset):
    """
    Basic exploration of the dataset

    Args:
        dataset: HuggingFace dataset
    """
    print(f"Dataset contains {len(dataset)} examples")
    print(f"Dataset features: {list(dataset.features.keys())}")

    # Print first example (excluding image to keep output clean)
    print("\nFirst example:")
    example = dataset[0]
    for key, value in example.items():
        if key != 'image':  # Skip showing the image data
            print(f"{key}: {value}")

    # Get some statistics
    print("\nDataset statistics:")
    print(f"Number of unique images: {len(set(dataset['file_name']))}")

    # Count number of examples by dataset
    datasets = {}
    for ex in dataset:
        dataset_name = ex['dataset']
        if dataset_name not in datasets:
            datasets[dataset_name] = 0
        datasets[dataset_name] += 1

    print("Examples per dataset:")
    for dataset_name, count in datasets.items():
        print(f"  {dataset_name}: {count}")

def image_availability_check(dataset):
    """
    Check how many examples have valid images

    Args:
        dataset: HuggingFace dataset
    """
    if 'image' not in dataset.features:
        print("Dataset does not contain image data")
        return

    valid_images = sum(1 for example in dataset if example['image'] is not None)
    print(f"Images available: {valid_images} out of {len(dataset)} examples ({valid_images/len(dataset)*100:.1f}%)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Example usage of the converted RefCOCOS dataset')
    parser.add_argument('--dataset_dir', type=str, default='hf_dataset',
                        help='Directory containing the HuggingFace dataset')
    parser.add_argument('--image_root', type=str, default='',
                        help='Root directory containing the images (only used if images not in dataset)')
    parser.add_argument('--example_index', type=int, default=0,
                        help='Index of the example to visualize')
    parser.add_argument('--visualize', action='store_true',
                        help='Visualize an example with its bounding box')

    args = parser.parse_args()

    # Load the dataset
    dataset = load_from_disk(args.dataset_dir)

    # Explore the dataset
    explore_dataset(dataset)

    # Check image availability
    image_availability_check(dataset)

    # Visualize an example if requested
    if args.visualize:
        visualize_example(dataset, args.example_index, args.image_root)
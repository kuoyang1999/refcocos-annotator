import json

def filter_images(input_file, output_file, max_instances=8):
    # Read the input JSON file
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Create a new list for filtered images
    filtered_images = []
    
    # Keep track of how many images were removed
    total_removed = 0
    
    # Process each image
    for image in data['images']:
        should_keep = True
        
        # Check each category in the image
        for category in image['categories_with_multiple_instances']:
            if category['count'] > max_instances:
                should_keep = False
                total_removed += 1
                break
        
        if should_keep:
            filtered_images.append(image)
    
    # Create new output data
    output_data = {
        'min_instances': data['min_instances'],
        'total_images_found': len(filtered_images),
        'images': filtered_images
    }
    
    # Write the filtered data to a new file
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Processing complete:")
    print(f"Original number of images: {len(data['images'])}")
    print(f"Number of images removed: {total_removed}")
    print(f"Number of images remaining: {len(filtered_images)}")

if __name__ == "__main__":
    input_file = "data/test_images_multiple_instances_converted.json"
    output_file = "data/test_images_multiple_instances_filtered.json"
    filter_images(input_file, output_file) 
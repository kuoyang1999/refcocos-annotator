#!/usr/bin/env python3
import json
import os

# Paths to the input files
file1_path = 'data-coco-multiple-instances.json'
file2_path = 'refcocos_test.json'
# Path to the output file
output_path = 'combined_data.json'

# Read the first file
with open(file1_path, 'r') as f1:
    data1 = json.load(f1)
    print(f"Loaded {len(data1)} items from {file1_path}")
    
    # Count empty cases in first file
    empty_cases_1 = sum(1 for item in data1 if item.get('categories', {}).get('empty_case', False))
    print(f"File 1 has {empty_cases_1} items with empty_case=True")

# Read the second file
with open(file2_path, 'r') as f2:
    data2 = json.load(f2)
    print(f"Loaded {len(data2)} items from {file2_path}")
    
    # Count empty cases in second file
    empty_cases_2 = sum(1 for item in data2 if item.get('categories', {}).get('empty_case', False))
    print(f"File 2 has {empty_cases_2} items with empty_case=True")

# Combine the data
combined_data = data1 + data2
print(f"Combined data contains {len(combined_data)} items")

# Count empty cases in combined data
total_empty_cases = empty_cases_1 + empty_cases_2
print(f"Combined data has {total_empty_cases} items with empty_case=True")

# Write the combined data to a new file
with open(output_path, 'w') as outfile:
    json.dump(combined_data, outfile, indent=2)

print(f"Successfully wrote combined data to {output_path}") 
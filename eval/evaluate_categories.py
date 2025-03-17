import json
import os
import argparse
from collections import defaultdict
import glob

def load_data(coco_json_path=None, results_json_path=None, coco_data=None):
    """
    Load data from the COCO JSON file and results JSON file

    coco_json_path: Path to the COCO JSON file (optional if coco_data is provided)
    results_json_path: Path to the results JSON file
    coco_data: Pre-loaded COCO data (optional)
    """
    # Load COCO data with category annotations if not provided
    if coco_data is None and coco_json_path is not None:
        with open(coco_json_path, 'r') as f:
            coco_data = json.load(f)

    # Load model prediction results
    results_data = []
    if results_json_path is not None:
        with open(results_json_path, 'r') as f:
            content = f.read()
            # Split the content by newlines to handle JSON-per-line format
            lines = content.strip().split('\n')

            # Skip the first two rows as they are metadata
            for line in lines[2:]:
                if line.strip():  # Skip empty lines
                    try:
                        results_data.append(json.loads(line))
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse line in {results_json_path}: {line[:50]}...")

        print(f"Loaded {len(results_data)} results from {results_json_path}")

        # Verify data length matches if we have coco_data
        if coco_data and len(coco_data) != len(results_data):
            print(f"Warning: Number of annotations ({len(coco_data)}) does not match number of results ({len(results_data)})")
            print("Will process only the overlapping entries")

    return coco_data, results_data

def calculate_accuracy_metrics(coco_data, results_data):
    """
    Calculate various accuracy metrics based on category annotations
    """
    # Initialize counters
    total_samples = min(len(coco_data), len(results_data))
    total_correct = 0

    # Category-specific counters
    metrics = {
        'overall': {'correct': 0, 'total': 0},
        'hops': {
            '2': {'correct': 0, 'total': 0},
            '3': {'correct': 0, 'total': 0},
            '4': {'correct': 0, 'total': 0}
        },
        'empty_case': {
            'true': {'correct': 0, 'total': 0},
            'false': {'correct': 0, 'total': 0}
        },
        'type': {
            'spatial': {'correct': 0, 'total': 0},
            'exclude': {'correct': 0, 'total': 0},
            'verb': {'correct': 0, 'total': 0},
            'attr': {'correct': 0, 'total': 0}
        },
        'occluded': {
            'true': {'correct': 0, 'total': 0},
            'false': {'correct': 0, 'total': 0}
        },
        'distractors': {
            '3': {'correct': 0, 'total': 0},
            '4': {'correct': 0, 'total': 0},
            '5+': {'correct': 0, 'total': 0}
        }
    }

    # Process each entry
    for i in range(total_samples):
        coco_entry = coco_data[i]
        result_entry = results_data[i]

        # Skip entries without categories
        if 'categories' not in coco_entry:
            continue

        # Get categories
        categories = coco_entry['categories']

        # Get hops value
        hops = categories.get('hops')

        # Skip entries where hops = 1
        if hops == "1":
            continue

        # Get prediction correctness
        is_correct = result_entry.get('correct', 0) == 1

        # Update overall metrics
        metrics['overall']['total'] += 1
        if is_correct:
            metrics['overall']['correct'] += 1

        # Update hops metrics (only for hops 2, 3, 4)
        if hops and hops != "1":
            metrics['hops'][hops]['total'] += 1
            if is_correct:
                metrics['hops'][hops]['correct'] += 1

        # Update empty_case metrics
        empty_case = categories.get('empty_case', False)
        empty_case_key = 'true' if empty_case else 'false'
        metrics['empty_case'][empty_case_key]['total'] += 1
        if is_correct:
            metrics['empty_case'][empty_case_key]['correct'] += 1

        # Update type metrics (can be multiple)
        types = categories.get('type', [])
        for type_val in types:
            metrics['type'][type_val]['total'] += 1
            if is_correct:
                metrics['type'][type_val]['correct'] += 1

        # Update occluded metrics
        occluded = categories.get('occluded', False)
        occluded_key = 'true' if occluded else 'false'
        metrics['occluded'][occluded_key]['total'] += 1
        if is_correct:
            metrics['occluded'][occluded_key]['correct'] += 1

        # Update distractors metrics
        distractors = categories.get('distractors')
        if distractors:
            metrics['distractors'][distractors]['total'] += 1
            if is_correct:
                metrics['distractors'][distractors]['correct'] += 1

    return metrics

def print_metrics(metrics, model_name=""):
    """
    Print accuracy metrics in a readable format
    """
    header = f"===== ACCURACY METRICS FOR {model_name} =====" if model_name else "===== ACCURACY METRICS ====="
    print(f"\n{header}\n")

    # 1. Calculate and print hops accuracy - only for hops 2, 3, 4
    print("1. Accuracy by Hops:")
    for hops in ['2', '3', '4']:  # Removed '1' from this list
        hops_data = metrics['hops'][hops]
        acc = (hops_data['correct'] / hops_data['total']) * 100 if hops_data['total'] > 0 else 0
        print(f"   Hops = {hops}: {acc:.1f}% ({hops_data['correct']}/{hops_data['total']})")

    # 2. Calculate and print occluded accuracy
    occluded_data = metrics['occluded']['true']
    occluded_acc = (occluded_data['correct'] / occluded_data['total']) * 100 if occluded_data['total'] > 0 else 0
    print(f"\n2. Accuracy for Occluded = true: {occluded_acc:.1f}% ({occluded_data['correct']}/{occluded_data['total']})")

    # 3. Calculate and print empty_case accuracy
    print("\n3. Accuracy by Empty Case:")
    for case in ['true', 'false']:
        case_data = metrics['empty_case'][case]
        acc = (case_data['correct'] / case_data['total']) * 100 if case_data['total'] > 0 else 0
        print(f"   Empty Case = {case}: {acc:.1f}% ({case_data['correct']}/{case_data['total']})")

    # 4. Calculate and print type accuracy
    print("\n4. Accuracy by Type:")
    for type_val in ['spatial', 'exclude', 'verb', 'attr']:
        type_data = metrics['type'][type_val]
        acc = (type_data['correct'] / type_data['total']) * 100 if type_data['total'] > 0 else 0
        print(f"   Type = {type_val}: {acc:.1f}% ({type_data['correct']}/{type_data['total']})")

    # 5. Calculate and print distractors accuracy
    print("\n5. Accuracy by Distractors:")
    for distractors in ['3', '4', '5+']:
        distractors_data = metrics['distractors'][distractors]
        acc = (distractors_data['correct'] / distractors_data['total']) * 100 if distractors_data['total'] > 0 else 0
        print(f"   Distractors = {distractors}: {acc:.1f}% ({distractors_data['correct']}/{distractors_data['total']})")

    # 6. Calculate and print overall accuracy
    overall = metrics['overall']
    overall_acc = (overall['correct'] / overall['total']) * 100 if overall['total'] > 0 else 0
    print(f"\n6. Overall Accuracy: {overall_acc:.1f}% ({overall['correct']}/{overall['total']})")

def calculate_percentage(data):
    """Helper function to calculate percentage and return a dict with percentage, correct and total"""
    if data['total'] == 0:
        return {'percentage': 0, 'correct': 0, 'total': 0}

    # Round to 1 decimal place
    percentage = round((data['correct'] / data['total']) * 100, 1)

    return {
        'percentage': percentage,
        'correct': data['correct'],
        'total': data['total']
    }

def process_result_file(coco_data, results_path):
    """Process a single result file and return metrics"""
    # Extract model directory name (e.g. "v1_3b", "base_7b") from the path
    # Expected path format: ./results/results/MODEL_DIR/results/filename.json
    parts = results_path.split(os.sep)

    # Extract the model directory name
    model_dir = None
    for i in range(len(parts)):
        if i > 0 and parts[i-1] == "results" and parts[i] in ["v1_3b", "v1_7b", "base_3b", "base_7b",
                                                               "sft_3b", "sft_7b", "vanilla_3b", "vanilla_7b"]:
            model_dir = parts[i]
            break

    if not model_dir:
        # Alternative approach: extract from path pattern
        path = os.path.normpath(results_path)
        # Look for patterns like /results/v1_3b/
        for model_type in ["v1_3b", "v1_7b", "base_3b", "base_7b", "sft_3b", "sft_7b", "vanilla_3b", "vanilla_7b"]:
            if f"/results/{model_type}/" in path.replace("\\", "/"):
                model_dir = model_type
                break

    if not model_dir:
        # Fallback to just filename if we can't find the model directory
        model_dir = os.path.splitext(os.path.basename(results_path))[0]

    # Load results data
    _, results_data = load_data(results_json_path=results_path, coco_data=coco_data)

    # Skip if no valid results
    if not results_data:
        print(f"No valid results found in {results_path}")
        return None, None

    # Calculate metrics
    metrics = calculate_accuracy_metrics(coco_data, results_data)

    # Print metrics for this model - include full path for debugging
    print_metrics(metrics, f"{model_dir} ({os.path.basename(results_path)})")

    # Convert metrics to exportable format in the requested order
    export_metrics = {
        'hops': {k: calculate_percentage(v) for k, v in metrics['hops'].items()},
        'occluded': {k: calculate_percentage(v) for k, v in metrics['occluded'].items()},
        'empty_case': {k: calculate_percentage(v) for k, v in metrics['empty_case'].items()},
        'type': {k: calculate_percentage(v) for k, v in metrics['type'].items()},
        'distractors': {k: calculate_percentage(v) for k, v in metrics['distractors'].items()},
        'overall': calculate_percentage(metrics['overall'])
    }

    return model_dir, export_metrics

def find_result_files(base_dir):
    """
    Recursively find all JSON result files in subdirectories
    """
    all_files = []

    # Walk through all subdirectories
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".json"):
                all_files.append(os.path.join(root, file))

    return all_files

def main():
    parser = argparse.ArgumentParser(description='Calculate accuracy metrics based on categories for multiple result files')
    parser.add_argument('--coco', default='data-coco.json', help='Path to the COCO JSON file with category annotations')
    parser.add_argument('--results-dir', default='./results/results', help='Directory containing result JSON files')
    parser.add_argument('--output', default='all_accuracy_metrics.json', help='Path to save the metrics JSON file')

    args = parser.parse_args()

    # Check if results directory exists
    if not os.path.isdir(args.results_dir):
        print(f"Error: Results directory '{args.results_dir}' not found.")
        return

    # Load COCO data once
    print(f"Loading annotations from {args.coco}...")
    with open(args.coco, 'r') as f:
        coco_data = json.load(f)
    print(f"Loaded {len(coco_data)} annotations")

    # Find all JSON files in the results directory and subdirectories
    result_files = find_result_files(args.results_dir)

    if not result_files:
        print(f"No JSON files found in {args.results_dir} or its subdirectories")
        return

    print(f"Found {len(result_files)} result files to process")

    # Process each result file and collect metrics
    all_metrics = {}
    for results_path in sorted(result_files):
        try:
            print(f"Processing: {results_path}")
            model_name, metrics = process_result_file(coco_data, results_path)
            if model_name and metrics:
                all_metrics[model_name] = metrics
        except Exception as e:
            print(f"Error processing {results_path}: {e}")

    # Export all metrics to a single JSON file
    with open(args.output, 'w') as f:
        json.dump(all_metrics, f, indent=2)

    print(f"\nAll metrics exported to {args.output}")

if __name__ == "__main__":
    main()
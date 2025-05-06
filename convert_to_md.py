import json
import os

def convert_json_to_md(json_file_path, output_md_path):
    # Read the JSON file
    with open(json_file_path, 'r') as f:
        data = json.load(f)

    # Create the output directory if it doesn't exist
    output_dir = os.path.dirname(output_md_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Generate markdown content
    md_content = "# RefCOCOS Dataset\n\n"

    for item in data:
        # Get caption (if it exists and is not empty)
        caption = item.get("normal_caption", "")
        caption_text = f"**Caption:** {caption}\n\n" if caption else "**Caption:** *(empty)*\n\n"

        # Get empty case status
        empty_case = item.get("categories", {}).get("empty_case", None)
        empty_case_text = f"**Empty Case:** {empty_case}\n\n" if empty_case is not None else ""

        # Get and validate image path
        original_image_path = item.get("image", "")
        image_link = ""
        if original_image_path:
            # Check path relative to script location (assuming 'images' symlink exists)
            script_relative_image_path = os.path.join("images", original_image_path)
            if os.path.exists(script_relative_image_path):
                # Path for markdown file (relative to 'results/' directory)
                md_image_path = os.path.join("..", script_relative_image_path)
                image_link = f"![Image]({md_image_path})\n\n"
            else:
                image_link = f"**Image:** *Not found at {script_relative_image_path}*\n\n"
        else:
            image_link = "**Image:** *Not specified*\n\n"

        # Add separator line
        separator = "---\n\n"

        # Combine elements for this item
        md_content += caption_text + empty_case_text + image_link + separator

    # Write to markdown file
    with open(output_md_path, 'w') as f:
        f.write(md_content)

    print(f"Conversion complete. Markdown file saved to: {output_md_path}")

if __name__ == "__main__":
    # json_file_path = "results/refcocos_test_cleaned.json"
    # output_md_path = "results/refcocos_test_cleaned.md"

    json_file_path = "results/refcocos_test.json"
    output_md_path = "results/refcocos_test.md"
    convert_json_to_md(json_file_path, output_md_path)
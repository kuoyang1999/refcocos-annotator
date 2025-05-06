import pandas as pd
import os
from pathlib import Path
import fiftyone as fo
import fiftyone.zoo as foz

def download_images_from_csv(csv_path, download_folder, num_processes=5):
    """Reads a CSV file, extracts ImageIDs, and downloads them."""
    print(f"Reading image IDs from {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
        # Ensure the column name is correct, case-insensitive check
        image_id_col = next((col for col in df.columns if col.lower() == 'imageid'), None)
        if image_id_col is None:
            print("Error: Could not find 'ImageID' column in the CSV.")
            return
        image_ids = df[image_id_col].unique()
    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_path}")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    print(f"Found {len(image_ids)} unique image IDs.")

    # Create the download folder if it doesn't exist
    dl_path = Path(download_folder)
    dl_path.mkdir(parents=True, exist_ok=True)
    print(f"Ensured download directory exists: {download_folder}")

    # Download images using fiftyone
    print(f"\nStarting download of {len(image_ids)} images...")
    try:
        # Create a dataset with the specified image IDs
        dataset = foz.load_zoo_dataset(
            "open-images-v7",
            split="test",
            label_types=[],  # Don't download any labels
            image_ids=list(image_ids),
            dataset_dir=str(dl_path)
        )
        print("Download process completed.")
    except Exception as e:
        print(f"Error during download: {e}")

if __name__ == '__main__':
    # Define the path to the CSV file and the target download directory
    csv_file_path = 'test-images-with-rotation.csv'
    # Define target directory relative to the script location or project root
    image_download_dir = 'open_image_v7'
    
    print("--- Open Images Test Set Downloader ---")
    download_images_from_csv(csv_file_path, image_download_dir, num_processes=5)
    print("---------------------------------------")
    print("Script finished. Check console for download progress/errors.") 
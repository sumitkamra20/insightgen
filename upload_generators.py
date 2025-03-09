#!/usr/bin/env python3
"""
Upload Generator YAML files to Google Cloud Storage

This script uploads all generator YAML files from the local 'generators' directory
to a specified Google Cloud Storage bucket.

Usage:
    python upload_generators.py --bucket=your-bucket-name

Requirements:
    - google-cloud-storage
    - Application Default Credentials configured
"""

import os
import argparse
from pathlib import Path
from google.cloud import storage

def upload_generators(bucket_name, local_dir="generators", remote_prefix="generators"):
    """
    Upload all YAML files from the local directory to GCS bucket.

    Args:
        bucket_name (str): Name of the GCS bucket
        local_dir (str): Local directory containing YAML files
        remote_prefix (str): Prefix for the remote path in the bucket
    """
    # Create a storage client
    storage_client = storage.Client()

    # Get the bucket
    bucket = storage_client.bucket(bucket_name)

    # Get the local directory
    local_path = Path(local_dir)

    if not local_path.exists():
        print(f"Error: Local directory '{local_dir}' does not exist")
        return

    # Upload all YAML files
    for file_path in local_path.glob("*.yaml"):
        # Destination path in the bucket
        remote_path = f"{remote_prefix}/{file_path.name}"

        # Create a blob
        blob = bucket.blob(remote_path)

        # Upload the file
        blob.upload_from_filename(str(file_path))

        print(f"Uploaded {file_path} to gs://{bucket_name}/{remote_path}")

def main():
    parser = argparse.ArgumentParser(description="Upload generator YAML files to GCS")
    parser.add_argument("--bucket", required=True, help="Name of the GCS bucket")
    parser.add_argument("--local-dir", default="generators", help="Local directory containing YAML files")
    parser.add_argument("--remote-prefix", default="generators", help="Prefix for the remote path in the bucket")

    args = parser.parse_args()

    upload_generators(args.bucket, args.local_dir, args.remote_prefix)

    print("Upload completed successfully!")

if __name__ == "__main__":
    main()

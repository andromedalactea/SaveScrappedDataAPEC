# Import standard libraries
import os
from typing import List, Dict

# Import third-party libraries
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Retrieve environment variables
BLOB_CONTAINER_ENDPOINT = os.getenv("BLOB_CONTAINER_ENDPOINT")
BLOB_SAS_TOKEN = os.getenv("BLOB_SAS_TOKEN")


def upload_file_to_blob(file_path: str, blob_name: str, metadata: Dict[str, str]) -> Dict[str, str]:
    """
    Uploads a single file to Azure Blob Storage with metadata.

    Args:
        file_path: Path to the file on the local system.
        blob_name: Desired name for the file in the Blob Storage.
        metadata: Metadata to attach to the blob.

    Returns:
        A dictionary containing upload status and the blob's URL.
    """
    # Construct the full URL for the Blob with SAS token
    url = f"{BLOB_CONTAINER_ENDPOINT}/{blob_name}?{BLOB_SAS_TOKEN}"

    # Read the file data
    with open(file_path, "rb") as f:
        file_data = f.read()

    # Prepare headers
    headers = {
        "x-ms-blob-type": "BlockBlob"
    }

    if metadata:
        # Append metadata as additional headers (key: x-ms-meta-{custom_key})
        for key, value in metadata.items():
            headers[f"x-ms-meta-{key}"] = value

    # Send the PUT request to Azure
    response = requests.put(url, headers=headers, data=file_data)

    # Analyze the response and return status
    if response.status_code == 201:
        return {
            "status": "success",
            "blob_url": url.split("?")[0],
            "message": f"File '{blob_name}' uploaded successfully!"
        }
    else:
        return {
            "status": "failure",
            "blob_url": None,
            "error": response.text,
            "http_status": response.status_code
        }


def upload_files_to_blob(files: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Uploads multiple files to Azure Blob Storage.

    Args:
        files: A list of file dictionaries containing 'path', 'name', and 'metadata'.

    Returns:
        A list of dictionaries indicating the upload status of each file.
    """
    results = []
    for file in files:
        file_path = file.get("path")
        blob_name = file.get("name")
        metadata = file.get("metadata", {})

        # Upload file and append the result to the results list
        results.append(upload_file_to_blob(file_path, blob_name, metadata))

    return results
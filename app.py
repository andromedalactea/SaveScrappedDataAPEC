# Import FastAPI and Pydantic for request handling
from fastapi import FastAPI, UploadFile, Form
from pydantic import BaseModel
from typing import List, Dict
from scripts.azure_blob import upload_files_to_blob

# Initialize the FastAPI app
app = FastAPI()


# Define the structure of metadata for each file
class FileMetadata(BaseModel):
    url_extracted: str  # URL where the file was scraped
    additional_info: Dict[str, str] = {}  # Optional additional metadata


# Define the structure of the request body
class FileUploadRequest(BaseModel):
    files: List[FileMetadata]  # A list of files with metadata


@app.post("/upload-files/")
async def upload_files(files: List[UploadFile], metadata: List[FileMetadata]):
    """
    Uploads one or more files to Azure Blob Storage, including their metadata.
    
    Args:
        files: A list of files uploaded via multipart form-data.
        metadata: A list of metadata corresponding to each file.
    
    Returns:
        A response indicating the status of each file upload.
    """
    if len(files) != len(metadata):
        return {"error": "Number of files and metadata entries must match."}

    upload_data = []
    for index, file in enumerate(files):
        # Save the uploaded file temporarily
        temp_file_path = f"/tmp/{file.filename}"
        with open(temp_file_path, "wb") as f:
            f.write(await file.read())

        # Prepare data for the upload process
        upload_data.append({
            "path": temp_file_path,
            "name": file.filename,
            "metadata": metadata[index].dict()
        })

    # Upload files to Azure Blob Storage
    result = upload_files_to_blob(upload_data)

    # Return the results
    return {"results": result}

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
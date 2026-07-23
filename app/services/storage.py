import os
import shutil
from fastapi import UploadFile
from app.config import settings

class StorageService:
    def __init__(self):
        # Ensure local uploads directory exists
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    def save_file(self, file: UploadFile, filename: str) -> str:
        # Save file locally
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # Return path of uploaded file. In the future, this will return the AWS S3 URL.
        return f"/uploads/{filename}"

    def delete_file(self, filename: str):
        # Delete local file
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

storage_service = StorageService()

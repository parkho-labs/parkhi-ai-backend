import os
import tempfile
import shutil
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
import uuid


class FileHandler:
    """Service for handling file uploads, validation, and temporary storage."""

    def __init__(self):
        # File size limits in bytes
        self.file_limits = {
            "pdf": 10 * 1024 * 1024,   # 10MB
            "docx": 5 * 1024 * 1024,   # 5MB
            "doc": 5 * 1024 * 1024,    # 5MB
        }

        # Allowed file extensions
        self.allowed_extensions = {".pdf", ".docx", ".doc"}

        # Create temp directory for uploaded files
        self.temp_dir = tempfile.mkdtemp(prefix="ai_video_tutor_")

    def validate_file(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded file for size and type.

        Args:
            file: FastAPI UploadFile object

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file.filename:
            return False, "No filename provided"

        # Check file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in self.allowed_extensions:
            return False, f"Unsupported file type: {file_ext}. Allowed: {', '.join(self.allowed_extensions)}"

        # Get file type for size check
        file_type = file_ext[1:]  # Remove the dot

        # Check file size
        if hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
            # Get file size
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Seek back to beginning

            max_size = self.file_limits.get(file_type)
            if max_size and file_size > max_size:
                return False, f"File too large: {file_size} bytes (max: {max_size} bytes)"

        return True, None

    async def save_temp_file(self, file: UploadFile) -> str:
        """
        Save uploaded file to temporary location.

        Args:
            file: FastAPI UploadFile object

        Returns:
            Path to saved temporary file

        Raises:
            HTTPException: If file validation fails or save error occurs
        """
        # Validate file
        is_valid, error_msg = self.validate_file(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        try:
            # Generate unique filename
            file_ext = os.path.splitext(file.filename)[1].lower()
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            temp_file_path = os.path.join(self.temp_dir, unique_filename)

            # Save file
            with open(temp_file_path, "wb") as temp_file:
                shutil.copyfileobj(file.file, temp_file)

            return temp_file_path

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    def cleanup_file(self, file_path: str) -> bool:
        """
        Delete temporary file.

        Args:
            file_path: Path to file to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False

    def cleanup_temp_dir(self):
        """Clean up entire temporary directory."""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    def get_file_info(self, file_path: str) -> dict:
        """
        Get file information.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file information
        """
        try:
            if not os.path.exists(file_path):
                return {}

            stat = os.stat(file_path)
            return {
                "filename": os.path.basename(file_path),
                "size": stat.st_size,
                "extension": os.path.splitext(file_path)[1].lower(),
                "exists": True
            }
        except Exception:
            return {"exists": False}

    def __del__(self):
        """Cleanup on destruction."""
        self.cleanup_temp_dir()
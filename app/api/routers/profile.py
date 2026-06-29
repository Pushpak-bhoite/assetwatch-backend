from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.images import imagekit
from app.core.db import User, get_db
import shutil
import os
import tempfile
from app.users import current_active_user

router = APIRouter(prefix="/users", tags=["Profile"])

# Allowed image types and max size (5MB)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def validate_image(file: UploadFile) -> None:
    """Validate uploaded image file type and size."""
    # Check content type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    
    # Check file size by reading content
    file.file.seek(0, 2)  # Move to end of file
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB"
        )


@router.post("/profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload or update user profile image.
    
    - Validates file type (jpeg, png, gif, webp only)
    - Validates file size (max 5MB)
    - Uploads to ImageKit under /profiles folder
    - Updates user's profile_image_url
    """
    # Validate the image
    validate_image(file)
    
    temp_file_path = None
    try:
        # Create temp file for upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)
        
        # Upload to ImageKit
        response = imagekit.files.upload(
            file=open(temp_file_path, "rb"),
            file_name=f"profile_{user.id}_{file.filename}",
            folder="/profiles",
            tags=["profile", "avatar"]
        )
        
        # Update user's profile image URL
        user.profile_image_url = response.url
        await db.commit()
        await db.refresh(user)
        
        return {
            "success": True,
            "message": "Profile image uploaded successfully",
            "profile_image_url": response.url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print('Error uploading profile image:', e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        file.file.close()


@router.get("/profile-image")
async def get_profile_image(
    user: User = Depends(current_active_user)
):
    """
    Get current user's profile image URL.
    
    Returns the profile image URL or null if not set.
    """
    return {
        "profile_image_url": user.profile_image_url
    }


@router.delete("/profile-image")
async def delete_profile_image(
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user's profile image.
    
    Note: This only removes the URL from database.
    ImageKit files are not deleted (can be managed via ImageKit dashboard).
    """
    if not user.profile_image_url:
        raise HTTPException(status_code=404, detail="No profile image to delete")
    
    try:
        user.profile_image_url = None
        await db.commit()
        
        return {
            "success": True,
            "message": "Profile image removed successfully"
        }
    except Exception as e:
        print('Error deleting profile image:', e)
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

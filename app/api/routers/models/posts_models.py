"""
AssetWatch Pydantic Schemas

This module defines all request/response schemas for the API.
Based on Wanaware's form fields and data structures.

Schema Categories:
- Post schemas (kept for backwards compatibility)
- User schemas (fastapi-users integration)
- Asset schemas (create, update, response)
- Monitor schemas (performance and availability)
- Metric schemas (performance and availability data)
- Summary/Dashboard schemas (aggregated data)
"""

from pydantic import BaseModel, Field
from datetime import date
from fastapi_users import schemas
from typing import Literal, Optional
import uuid


# ==================== POST SCHEMAS (kept for backwards compatibility) ====================

class PostCreate(BaseModel):
    """Schema for creating a blog post"""
    title: str
    content: str
    caption: str


class PostResponse(BaseModel):
    """Schema for post response"""
    id: int
    title: str
    content: str
    caption: str

    class Config: 
        from_attributes = True # this is for returning id along with data when user makes post request

class FilePost(BaseModel):
    """Schema for file post response"""
    id: int
    caption: str
    file_url: str
    file_name: str
    created_At: date
    
    class Config: 
        from_attributes = True 


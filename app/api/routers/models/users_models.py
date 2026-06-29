
# ==================== USER SCHEMAS ====================

from typing import Optional
from fastapi_users import schemas
import uuid

class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema for reading user data"""
    name: str
    organization_type: str
    parent_organization_id: Optional[uuid.UUID] = None



class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a user"""
    name: str  # Required: used as organization name
    organization_type: str = "customer"  # Default to customer for self-registration


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating a user"""
    name: Optional[str] = None


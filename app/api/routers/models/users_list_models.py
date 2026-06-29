"""
Schemas for Users List API
"""

from pydantic import BaseModel
from typing import Optional


class UserListItem(BaseModel):
    """Schema for user list item response"""
    id: str
    email: str
    name: str
    organization_type: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    parent_organization_id: Optional[str] = None

    class Config:
        from_attributes = True


class PaginatedUsersResponse(BaseModel):
    """Schema for paginated users list response"""
    data: list[UserListItem]
    total: int
    page: int
    limit: int
    total_pages: int

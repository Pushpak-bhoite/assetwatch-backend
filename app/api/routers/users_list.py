"""
Users List API Router

Provides paginated list of users with sorting and filtering support.
Designed for AG Grid server-side row model integration.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, asc, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Literal
from datetime import datetime
import uuid

from app.api.dependencies import check_permission
from app.core.db import User, get_db
from app.users import current_active_user
from app.api.routers.models.users_list_models import UserListItem, PaginatedUsersResponse, UserInviteRequest, UserInviteResponse
from app.core.email_service import email_service

router = APIRouter(prefix="/users", tags=["users-list"])


# ==================== ENDPOINTS ====================

@router.get("/list",
            response_model=PaginatedUsersResponse,
            dependencies=[Depends(check_permission("read", "asset"))]
            )
async def list_users(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    sort_by: str = Query("name", description="Field to sort by"),
    order: Literal["asc", "desc"] = Query("asc", description="Sort order"),
    search: Optional[str] = Query(None, description="Search term for name or email"),
    organization_type: Optional[str] = Query(None, description="Filter by organization type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    List users with pagination, sorting, and filtering.
    
    This endpoint is designed for AG Grid server-side row model.
    
    - **page**: Page number (1-indexed)
    - **limit**: Items per page (default 10, max 100)
    - **sort_by**: Field to sort by (name, email, organization_type, is_active)
    - **order**: Sort order (asc, desc)
    - **search**: Search term for name or email
    - **organization_type**: Filter by organization type
    - **is_active**: Filter by active status
    """
    
    # Map sortable fields to actual columns
    sortable_fields = {
        "name": User.name,
        "email": User.email,
        "organization_type": User.organization_type,
        "is_active": User.is_active,
        "is_verified": User.is_verified,
        "is_superuser": User.is_superuser,
    }
    
    # Base query
    query = select(User)
    count_query = select(func.count(User.id))
    
    # Apply organization hierarchy filter based on current user's role
    # - assetwatch: can see all users (customers, resellers, reseller_customers, and other admins)
    # - reseller: can see their own reseller_customers (parent_organization_id = their id)
    # - customer/reseller_customer: can only see themselves
    if current_user.organization_type == "assetwatch":
        # AssetWatch admins see ALL users
        pass  # No filter needed
    elif current_user.organization_type == "reseller":
        # Resellers see their own reseller_customers
        query = query.where(User.parent_organization_id == current_user.id)
        count_query = count_query.where(User.parent_organization_id == current_user.id)
    else:
        # Customers and reseller_customers can only see themselves
        query = query.where(User.id == current_user.id)
        count_query = count_query.where(User.id == current_user.id)
    
    # Apply search filter
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (User.name.ilike(search_filter)) | (User.email.ilike(search_filter))
        )
        count_query = count_query.where(
            (User.name.ilike(search_filter)) | (User.email.ilike(search_filter))
        )
    
    # Apply organization_type filter
    if organization_type:
        query = query.where(User.organization_type == organization_type)
        count_query = count_query.where(User.organization_type == organization_type)
    
    # Apply is_active filter
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)
    
    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply sorting
    sort_column = sortable_fields.get(sort_by, User.name)
    if order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    # Calculate offset from page number (internal logic, not exposed to frontend)
    offset = (page - 1) * limit
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    # Execute query
    result = await session.execute(query)
    users = result.scalars().all()
    
    # Calculate total pages
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    
    # Transform users to response format
    user_list = [
        UserListItem(
            id=str(user.id),
            email=user.email,
            name=user.name,
            organization_type=user.organization_type,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            parent_organization_id=str(user.parent_organization_id) if user.parent_organization_id else None,
        )
        for user in users
    ]
    
    return PaginatedUsersResponse(
        data=user_list,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.post("/invite",
             response_model=UserInviteResponse,
             dependencies=[Depends(check_permission("create", "asset"))]
             )
async def invite_user(
    invite_data: UserInviteRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Send an invitation email to a new user.
    
    The invited user will receive an email with a link to register.
    
    - **email**: Email address to send the invitation to
    - **organization_type**: Role the invitee will have (customer, reseller, reseller_customer)
    - **message**: Optional personal message to include in the email
    """
    
    # Validate organization_type
    valid_types = ["customer", "reseller", "reseller_customer"]
    if invite_data.organization_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid organization type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Check if user already exists
    existing_user = await session.execute(
        select(User).where(User.email == invite_data.email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="A user with this email address already exists"
        )
    
    # Send invitation email
    email_sent = await email_service.send_invitation_email(
        to_email=invite_data.email,
        inviter_name=current_user.name or current_user.email,
        organization_type=invite_data.organization_type,
        personal_message=invite_data.message
    )
    
    if not email_sent:
        # Even if email fails, we return success but with a note
        # This is because the email service might not be configured in dev
        return UserInviteResponse(
            success=True,
            message="Invitation created, but email could not be sent. Please check email configuration.",
            email=invite_data.email
        )
    
    return UserInviteResponse(
        success=True,
        message="Invitation sent successfully",
        email=invite_data.email
    )

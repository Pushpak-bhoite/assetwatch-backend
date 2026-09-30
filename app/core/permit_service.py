"""
Permit.io Integration Service

This module handles all interactions with Permit.io for authorization.
It provides functions to:
- Sync users and organizations to Permit.io
- Check permissions for actions
- Manage role assignments

Permit.io Concepts:
- User: A person in your system (synced from your DB)
- Tenant: An organization/workspace (maps to our Organization)
- Role: A set of permissions (assetwatch, reseller, customer, reseller_customer)
- Resource: Something you want to protect (organization, asset, monitor)
- Action: What can be done (create, read, update, delete)

Setup Required in Permit.io Dashboard:
1. Create Resources: organization, asset, monitor (with CRUD actions)
2. Create Roles: assetwatch, reseller, customer, reseller_customer
3. Set permissions for each role on each resource
"""

import os
from typing import Optional

from permit import Permit

# =============================================================================
# PERMIT.IO CLIENT INITIALIZATION
# =============================================================================

# Initialize Permit.io client with API key from environment
# The API key connects to your Permit.io project
# Get your API key from: https://app.permit.io -> Settings -> API Keys
permit = Permit(
    # Permit.io's cloud PDP (Policy Decision Point)
    pdp="https://cloudpdp.api.permit.io",
    # API key from environment variable
    token=os.environ.get("PERMIT_IO_KEY", "")
)


# =============================================================================
# USER SYNC FUNCTIONS
# =============================================================================

async def sync_user_to_permit(
    user_id: str,
    email: str,
    organization_id: Optional[str] = None,
    organization_type: Optional[str] = None
) -> bool:
    """
    Sync a user from our database to Permit.io.
    
    This should be called:
    - When a new user registers
    - When user's organization changes
    - When user's role changes
    
    Args:
        user_id: UUID of the user (from our DB)
        email: User's email address
        organization_id: UUID of user's organization (used as tenant)
        organization_type: Type determines the role (assetwatch/reseller/customer/reseller_customer)
    
    Returns:
        True if sync successful, False otherwise
        
    Example:
        await sync_user_to_permit(
            user_id="d972bb13-4d63-4ba6-99d9-cfe7e3e7ae7f",
            email="bran@example.com",
            organization_id="org-123",
            organization_type="customer"
        )
    """
    try:
        # Step 1: Create or update user in Permit.io
        # The 'key' is our user_id - this links Permit.io user to our DB user
        await permit.api.users.sync({
            "key": user_id,
            "email": email,
            # You can add more attributes here for ABAC (Attribute-Based Access Control)
            "attributes": {
                "organization_id": organization_id,
                "organization_type": organization_type
            }
        })
        
        # Step 2: If user has an organization, assign them to that tenant with appropriate role
        if organization_id and organization_type:
            # First, ensure the tenant (organization) exists
            await sync_organization_to_permit(organization_id, organization_type)
            
            # Assign user to tenant with role based on organization type
            # The role name matches organization_type for simplicity
            await permit.api.users.assign_role({
                "user": user_id,
                "role": organization_type,  # assetwatch, reseller, customer, or reseller_customer
                "tenant": organization_id
            })
        
        print(f"✅ User {email} synced to Permit.io with role {organization_type}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to sync user to Permit.io: {e}")
        return False


async def sync_organization_to_permit(
    organization_id: str,
    organization_type: str,
    organization_name: Optional[str] = None
) -> bool:
    """
    Sync an organization as a Tenant in Permit.io.
    
    In Permit.io, a Tenant represents an isolated workspace/organization.
    Each organization in our system becomes a tenant in Permit.io.
    
    Args:
        organization_id: UUID of the organization
        organization_type: Type of organization (for attributes)
        organization_name: Human-readable name
        
    Returns:
        True if sync successful, False otherwise
    """
    try:
        await permit.api.tenants.create({
            "key": organization_id,
            "name": organization_name or f"Organization {organization_id}",
            "attributes": {
                "type": organization_type
            }
        })
        print(f"✅ Organization {organization_id} synced to Permit.io as tenant")
        return True
        
    except Exception as e:
        # Tenant might already exist, which is fine
        if "already exists" in str(e).lower():
            print(f"ℹ️ Organization {organization_id} already exists in Permit.io")
            return True
        print(f"❌ Failed to sync organization to Permit.io: {e}")
        return False


async def remove_user_from_permit(user_id: str) -> bool:
    """
    Remove a user from Permit.io when they're deleted from our system.
    
    Args:
        user_id: UUID of the user to remove
        
    Returns:
        True if removal successful, False otherwise
    """
    try:
        await permit.api.users.delete(user_id)
        print(f"✅ User {user_id} removed from Permit.io")
        return True
    except Exception as e:
        print(f"❌ Failed to remove user from Permit.io: {e}")
        return False

    
# =============================================================================
# PERMISSION CHECK FUNCTIONS
# =============================================================================

async def check_permitio_permission(
    user_id: str,
    action: str,
    resource: str,
    tenant_id: Optional[str] = None,
    resource_attributes: Optional[dict] = None
) -> bool:
    """
    Check if a user is permitted to perform an action on a resource.
    
    This is the core authorization function. Call this before any protected operation.
    
    Args:
        user_id: UUID of the user making the request
        action: The action being performed (create, read, update, delete)
        resource: The resource type (organization, asset, monitor)
        tenant_id: The organization/tenant context (optional for global resources)
        resource_attributes: Additional attributes for ABAC decisions
        
    Returns:
        True if action is permitted, False otherwise
        
    Example:
        # Check if user can create an asset
        allowed = await check_permitio_permission(
            user_id="user-123",
            action="create",
            resource="asset",
            tenant_id="org-456"
        )
        if not allowed:
            raise HTTPException(status_code=403, detail="Permission denied")
    """
    try:
        # Build the resource dict for Permit.io
        resource_dict = {"type": resource}
        if tenant_id:
            resource_dict["tenant"] = tenant_id
        if resource_attributes:
            resource_dict["attributes"] = resource_attributes
        # Ask Permit.io if this action is allowed
        permitted = await permit.check(
            user_id,
            action,
            resource_dict
        )
        print("resource_dict-->", resource_dict)
        print("permitted--->", permitted)
        
        print(f"🔐 Permission check: user={user_id}, action={action}, resource={resource}, tenant={tenant_id} → {'✅ ALLOWED' if permitted else '❌ DENIED'}")
        return permitted
        
    except Exception as e:
        print(f"❌ Permission check failed: {e}")
        # Fail closed - deny access if check fails
        return False


async def check_organization_permission(
    user_id: str,
    action: str,
    target_organization_id: str,
    user_organization_id: str,
    user_organization_type: str
) -> bool:
    """
    Check if a user can perform an action on a specific organization.
    
    This handles the hierarchical permission logic:
    - assetwatch: Can do anything to any organization
    - reseller: Can CRUD their own reseller_customers, read/update self
    - customer/reseller_customer: Can only read/update self
    
    Args:
        user_id: UUID of the user making the request
        action: The action (create, read, update, delete)
        target_organization_id: The organization being acted upon
        user_organization_id: The user's own organization
        user_organization_type: The user's organization type
        
    Returns:
        True if permitted, False otherwise
    """
    # First, check basic Permit.io permission
    basic_permission = await check_permitio_permission(
        user_id=user_id,
        action=action,
        resource="organization",
        tenant_id=user_organization_id
    )
    
    if not basic_permission:
        return False
    
    # Additional business logic based on organization hierarchy
    
    # AssetWatch can do anything
    if user_organization_type == "assetwatch":
        return True
    
    # Users can always read/update their own organization
    if target_organization_id == user_organization_id:
        return action in ["read", "update"]
    
    # Resellers can manage their children (reseller_customers)
    if user_organization_type == "reseller":
        # This would need to check if target_organization is a child
        # For now, we'll handle this with resource attributes
        return await check_permitio_permission(
            user_id=user_id,
            action=action,
            resource="organization",
            tenant_id=user_organization_id,
            resource_attributes={"target_org_id": target_organization_id}
        )
    
    # Customers can only access their own organization
    return False


# =============================================================================
# ROLE MANAGEMENT FUNCTIONS
# =============================================================================

async def assign_role(
    user_id: str,
    role: str,
    tenant_id: str
) -> bool:
    """
    Assign a role to a user within a tenant/organization.
    
    Args:
        user_id: UUID of the user
        role: Role name (assetwatch, reseller, customer, reseller_customer)
        tenant_id: Organization ID (tenant)
        
    Returns:
        True if assignment successful, False otherwise
    """
    try:
        await permit.api.users.assign_role({
            "user": user_id,
            "role": role,
            "tenant": tenant_id
        })
        print(f"✅ Assigned role '{role}' to user {user_id} in tenant {tenant_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to assign role: {e}")
        return False


async def remove_role(
    user_id: str,
    role: str,
    tenant_id: str
) -> bool:
    """
    Remove a role from a user within a tenant/organization.
    
    Args:
        user_id: UUID of the user
        role: Role name to remove
        tenant_id: Organization ID (tenant)
        
    Returns:
        True if removal successful, False otherwise
    """
    try:
        await permit.api.users.unassign_role(
            user=user_id,
            role=role,
            tenant=tenant_id
        )
        print(f"✅ Removed role '{role}' from user {user_id} in tenant {tenant_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to remove role: {e}")
        return False
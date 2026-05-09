"""
Setup script to create/check the assetwatch super admin.
User IS the org — user.id = org_id, user.email = org_email, user.name = org_name.

Usage:
    python scripts/setup_initial_org.py                         # check status + create db
    python scripts/setup_initial_org.py --assign-user <email>   # promote user + create db
"""

import asyncio, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.core.db import User, async_session_maker, create_db_and_tables
from app.core.permit_service import sync_organization_to_permit, sync_user_to_permit
from sqlalchemy import select


def _print_user(label: str, user):
    print(f"\n  {label}")
    print(f"  ID:    {user.id}")
    print(f"  Email: {user.email}")
    print(f"  Name:  {user.name}")
    print(f"  Type:  {user.organization_type}\n")


async def _get_user_by(session, **kwargs):
    """Generic user lookup. Pass email=... or organization_type=..."""
    key, value = next(iter(kwargs.items()))
    result = await session.execute(
        select(User).where(getattr(User, key) == value)
    )
    return result.scalars().first()


async def check_status():
    """Check if an assetwatch admin exists."""
    await create_db_and_tables()
    async with async_session_maker() as session:
        user = await _get_user_by(session, organization_type="assetwatch")
        if user:
            _print_user("✅ AssetWatch admin found:", user)
        else:
            print("\n  ⚠️  No assetwatch admin. Register a user then run --assign-user\n")
        return user


async def assign_user(email: str):
    """Promote a registered user to assetwatch and sync to Permit.io."""
    await create_db_and_tables()
    async with async_session_maker() as session:
        user = await _get_user_by(session, email=email)
        if not user:
            print(f"\n  ❌ User '{email}' not found. Register first.\n")
            return None

        # Promote in DB
        user.organization_type = "assetwatch"
        user.name = user.name or "AssetWatch"
        user.is_superuser = True  # this will enable admin to edit other users via fast api auth
        await session.commit()
        await session.refresh(user)
        _print_user("✅ Promoted to assetwatch:", user)

        # Sync tenant + user + role to Permit.io
        uid = str(user.id)
        await sync_organization_to_permit(uid, "assetwatch", user.name)
        await sync_user_to_permit(uid, user.email, uid, "assetwatch")
        print("  ✅ Permit.io synced\n")
        return user


async def main():
    if not os.environ.get("PERMIT_IO_KEY"):
        print("  ⚠️  PERMIT_IO_KEY not set — Permit.io sync will fail\n")

    if len(sys.argv) > 2 and sys.argv[1] == "--assign-user":
        await assign_user(sys.argv[2])
    else:
        await check_status()


if __name__ == "__main__":
    asyncio.run(main())

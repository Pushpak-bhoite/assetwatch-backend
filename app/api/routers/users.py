
from fastapi import APIRouter, Depends, HTTPException
from app.users import auth_backend, current_active_user, fastapi_users
from app.api.routers.models.users_models import UserRead, UserCreate, UserUpdate
from app.api.routers.models.posts_models import PostCreate, PostResponse

router = APIRouter()

# connect diff auth endpoints that we need to our fast API users endpoints. 
router.include_router(fastapi_users.get_auth_router(auth_backend), prefix='/auth/jwt', tags=["auth"])
router.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix='/auth', tags=["auth"])
router.include_router(fastapi_users.get_reset_password_router(), prefix='/auth', tags=["auth"])
router.include_router(fastapi_users.get_verify_router(UserRead), prefix='/auth', tags=["auth"])
router.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix='/users', tags=["users"])


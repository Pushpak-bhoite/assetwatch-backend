from fastapi import FastAPI, HTTPException, Depends, File, Form, UploadFile 
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.images import imagekit
from app.api.routers.models.posts_models import PostCreate, PostResponse
from app.api.routers.models.users_models import UserRead, UserCreate, UserUpdate
from app.core.db import Post, FilePost, User, create_db_and_tables, get_db
from sqlalchemy import select 
from app.users import auth_backend, current_active_user, fastapi_users
from app.api.main import api_router
from app.core.config import settings
from scripts.setup_initial_org import create_superuser_if_not_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 50)
    print(f"FRONTEND_HOST: {settings.FRONTEND_HOST}")
    print(f"CORS Origins: {settings.all_cors_origins}")
    print(f"ENVIRONMENT: {settings.ENVIRONMENT}")
    print("=" * 50)
    await create_db_and_tables()
    await create_superuser_if_not_exists()
    yield

app = FastAPI(lifespan=lifespan,
            docs_url="/api/docs",  #these extra 2 lines are for updating faastapi's docs with base endpoint /api since defauld start with just / 
            openapi_url="/api/openapi.json"
            )

# Configure CORS - allow frontend to make requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.all_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/users", tags=["All users"])
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    result = await db.execute(select(User))
    users = result.scalars().all()
    
    return users
    
app.include_router(api_router, prefix=settings.API_BASE)
        
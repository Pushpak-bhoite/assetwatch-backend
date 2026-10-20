from fastapi import APIRouter
from app.routes.items import router

api_router = APIRouter()

api_router.include_router(router)
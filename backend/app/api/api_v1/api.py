from fastapi import APIRouter
from app.api.api_v1.endpoints import auth, chat, admin, locations

api_router = APIRouter()

api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])

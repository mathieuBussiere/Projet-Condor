from fastapi import APIRouter, HTTPException

from src.api.v1.endpoints import export
from src.api.v1.endpoints import path

api_router = APIRouter()

# Register the sub-routers
@api_router.get("/health")
def health_check():
    return {"ping"}


api_router.include_router(path.router, prefix="/path", tags=["path"])

api_router.include_router(export.router, prefix="/export", tags=["export"])
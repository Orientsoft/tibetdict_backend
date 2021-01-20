from fastapi import APIRouter
from applications.user import router as user_router

router = APIRouter()

router.include_router(user_router)


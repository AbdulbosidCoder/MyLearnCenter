from fastapi import APIRouter

from app.api import content, users

router = APIRouter(prefix="/api")
router.include_router(users.router)
router.include_router(content.router)

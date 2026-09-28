from fastapi import APIRouter

from app.api import ai, content, materials, quiz, users

router = APIRouter(prefix="/api")
router.include_router(users.router)
router.include_router(content.router)
router.include_router(materials.router)
router.include_router(quiz.router)
router.include_router(ai.router)

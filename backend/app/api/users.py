from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app import gamification
from app.deps import ADMIN, CurrentUser, Session
from app.models import Role, User
from app.schemas import LeaderboardOut, RoleIn, StatsOut, UserOut

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.get("/me/stats", response_model=StatsOut)
async def my_stats(session: Session, user: CurrentUser):
    return await gamification.stats(session, user)


@router.get("/leaderboard", response_model=LeaderboardOut)
async def leaderboard(session: Session, user: CurrentUser):
    return await gamification.leaderboard(session, user)


@router.get("/users", response_model=list[UserOut], dependencies=[ADMIN])
async def list_users(session: Session):
    return (await session.scalars(select(User).order_by(User.created_at))).all()


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def set_role(user_id: int, body: RoleIn, session: Session, admin: User = ADMIN):
    # There is exactly one administrator (set by ADMIN_TG_ID), so the admin role is never handed out here.
    if body.role == Role.admin:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The admin role cannot be assigned")
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot change your own role")
    user.role = body.role
    await session.commit()
    return user

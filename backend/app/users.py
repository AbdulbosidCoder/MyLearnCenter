from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Role, User


async def upsert_user(session: AsyncSession, telegram_id: int, first_name: str, username: str | None) -> User:
    """Create the user on first contact (from the bot or the Mini App) and refresh their name."""
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id, role=Role.student)
        session.add(user)
    user.first_name = first_name
    user.username = username
    if telegram_id == get_settings().admin_tg_id:
        user.role = Role.admin
    await session.commit()
    return user

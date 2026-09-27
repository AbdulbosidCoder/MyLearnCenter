from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import Role, User
from app.telegram_auth import InvalidInitData, validate_init_data
from app.users import upsert_user

Session = Annotated[AsyncSession, Depends(get_session)]


async def current_user(
    session: Session,
    authorization: Annotated[str | None, Header()] = None,
    x_dev_user: Annotated[int | None, Header()] = None,
) -> User:
    settings = get_settings()
    if settings.dev_mode and x_dev_user is not None:
        return await upsert_user(session, x_dev_user, f"Dev {x_dev_user}", None)

    if not authorization or not authorization.startswith("tma "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Open the app from Telegram")
    try:
        tg_user = validate_init_data(authorization[4:], settings.bot_token, settings.init_data_ttl)
    except InvalidInitData as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return await upsert_user(session, tg_user.id, tg_user.first_name, tg_user.username)


CurrentUser = Annotated[User, Depends(current_user)]


def require_role(*roles: Role):
    async def check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed for your role")
        return user

    return Depends(check)


# Teachers and the admin edit content; only the admin manages people.
EDITOR = require_role(Role.admin, Role.teacher)
ADMIN = require_role(Role.admin)

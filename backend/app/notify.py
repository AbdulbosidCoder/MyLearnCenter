"""Messages from the Telegram bot, sent by the API when something happens.

Sending never blocks or breaks a request: messages go out in a background task and errors are
only logged (a student may have blocked the bot, or the bot token may be missing in development).
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Role, User

log = logging.getLogger(__name__)

_tasks: set[asyncio.Task] = set()
_bot: Bot | None = None
PAUSE = 0.05  # stay under Telegram's 30 messages per second


def _open_app() -> InlineKeyboardMarkup:
    url = get_settings().webapp_url
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📚 Открыть", web_app=WebAppInfo(url=url))]])


async def _send(telegram_id: int, text: str) -> None:
    global _bot
    token = get_settings().bot_token
    if not token:
        return
    if _bot is None:
        _bot = Bot(token)
    await _bot.send_message(telegram_id, text, reply_markup=_open_app())


async def _send_all(telegram_ids: list[int], text: str) -> None:
    for telegram_id in telegram_ids:
        try:
            await _send(telegram_id, text)
        except Exception as exc:  # blocked bot, wrong token, network: never fatal
            log.warning("Bot message to %s failed: %s", telegram_id, exc)
        await asyncio.sleep(PAUSE)


def send(telegram_ids: list[int], text: str) -> None:
    """Queues a message to these users and returns at once."""
    if not telegram_ids:
        return
    task = asyncio.create_task(_send_all(telegram_ids, text))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def telegram_ids(session: AsyncSession, *roles: Role) -> list[int]:
    return list(await session.scalars(select(User.telegram_id).where(User.role.in_(roles))))

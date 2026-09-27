"""Telegram bot: greets users, registers them and opens the Mini App.

Run with: python -m app.bot
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, Message, WebAppInfo

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.models import Role
from app.progress import class_report, student_report
from app.users import upsert_user

dp = Dispatcher()

ROLE_NAMES = {Role.admin: "администратор", Role.teacher: "преподаватель", Role.student: "студент"}


def open_app_keyboard() -> InlineKeyboardMarkup:
    url = get_settings().webapp_url
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📚 Открыть уроки", web_app=WebAppInfo(url=url))]]
    )


@dp.message(CommandStart())
async def start(message: Message) -> None:
    tg = message.from_user
    async with SessionLocal() as session:
        user = await upsert_user(session, tg.id, tg.first_name, tg.username)
    await message.answer(
        f"Привет, {tg.first_name}! Это MyLearnCenter — Data Science шаг за шагом.\n"
        f"Ваша роль: {ROLE_NAMES[Role(user.role)]}.\n"
        "Команда /progress покажет прогресс по тестам.",
        reply_markup=open_app_keyboard(),
    )


@dp.message(Command("progress"))
async def progress(message: Message) -> None:
    tg = message.from_user
    async with SessionLocal() as session:
        user = await upsert_user(session, tg.id, tg.first_name, tg.username)
        if user.role in (Role.admin, Role.teacher):
            text = await class_report(session)
        else:
            text = await student_report(session, user)
    await message.answer(text, reply_markup=open_app_keyboard())


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    await init_db()
    bot = Bot(settings.bot_token)
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Открыть уроки"),
            BotCommand(command="progress", description="Прогресс: сданные тесты"),
        ]
    )
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text="Уроки", web_app=WebAppInfo(url=settings.webapp_url))
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

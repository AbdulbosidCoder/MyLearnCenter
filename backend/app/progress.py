"""Which lessons a student may open.

Themes are all open. Inside a theme, lessons go in order: a lesson with a test blocks the next
lessons until the student passes that test. A lesson without a test never blocks.
Teachers and the admin are never blocked.
"""

from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lesson, Module, Question, Role, TestAttempt, User


class LessonState(StrEnum):
    done = "done"  # the lesson's test is passed
    open = "open"
    locked = "locked"  # an earlier lesson's test is not passed yet


async def passed_lessons(session: AsyncSession, user_id: int, lesson_ids: list[int]) -> set[int]:
    return set(
        await session.scalars(
            select(TestAttempt.lesson_id)
            .where(TestAttempt.user_id == user_id, TestAttempt.passed, TestAttempt.lesson_id.in_(lesson_ids))
            .distinct()
        )
    )


async def lesson_states(session: AsyncSession, user: User, lessons: list[Lesson]) -> dict[int, LessonState]:
    """States for the visible lessons of one theme, given in their order."""
    ids = [lesson.id for lesson in lessons]
    with_test = set(await session.scalars(select(Question.lesson_id).where(Question.lesson_id.in_(ids)).distinct()))
    passed = await passed_lessons(session, user.id, ids)
    can_skip = user.role in (Role.admin, Role.teacher)

    states: dict[int, LessonState] = {}
    blocked = False
    for lesson in lessons:
        if lesson.id in passed:
            states[lesson.id] = LessonState.done
        else:
            states[lesson.id] = LessonState.locked if blocked and not can_skip else LessonState.open
        if lesson.id in with_test and lesson.id not in passed:
            blocked = True
    return states


async def is_locked(session: AsyncSession, user: User, lesson: Lesson) -> bool:
    lessons = list(
        await session.scalars(
            select(Lesson)
            .where(Lesson.module_id == lesson.module_id, Lesson.is_draft.is_(False))
            .order_by(Lesson.position, Lesson.id)
        )
    )
    if lesson.id not in {sib.id for sib in lessons}:
        return False
    return (await lesson_states(session, user, lessons))[lesson.id] == LessonState.locked


# --- Progress report for the bot's /progress command -----------------------------------------

MAX_MESSAGE = 4000  # Telegram allows 4096 characters in one message


async def _themes(session: AsyncSession) -> list[tuple[Module, list[Lesson], set[int]]]:
    """Published themes with their lessons in order and the ids of lessons that have a test."""
    lessons = list(
        await session.scalars(
            select(Lesson).where(Lesson.is_draft.is_(False)).order_by(Lesson.module_id, Lesson.position, Lesson.id)
        )
    )
    with_test = set(await session.scalars(select(Question.lesson_id).distinct()))
    modules = list(await session.scalars(select(Module).order_by(Module.position, Module.id)))
    themes = []
    for module in modules:
        own = [lesson for lesson in lessons if lesson.module_id == module.id]
        if own:
            themes.append((module, own, {lesson.id for lesson in own if lesson.id in with_test}))
    return themes


async def student_report(session: AsyncSession, user: User) -> str:
    lines = ["📊 Ваш прогресс"]
    for module, lessons, tested in await _themes(session):
        states = await lesson_states(session, user, lessons)
        done = sum(states[lesson_id] == LessonState.done for lesson_id in tested)
        if tested and done == len(tested):
            lines.append(f"\n✅ {module.title}: все тесты сданы ({done} из {len(tested)})")
            continue
        lines.append(f"\n📘 {module.title}: сдано тестов {done} из {len(tested)}")
        current = next((lesson for lesson in lessons if states[lesson.id] == LessonState.open), None)
        if current is not None:
            lines.append(f"   Дальше: «{current.title}»")
    if len(lines) == 1:
        lines.append("Пока нет опубликованных тем.")
    return _fit("\n".join(lines))


async def class_report(session: AsyncSession) -> str:
    """For teachers: who passed how many tests in each theme."""
    students = list(await session.scalars(select(User).where(User.role == Role.student).order_by(User.first_name)))
    passed = await session.execute(select(TestAttempt.user_id, TestAttempt.lesson_id).where(TestAttempt.passed).distinct())
    by_student: dict[int, set[int]] = {}
    for user_id, lesson_id in passed:
        by_student.setdefault(user_id, set()).add(lesson_id)

    lines = [f"👥 Прогресс студентов ({len(students)})"]
    idle = {s.id for s in students if not by_student.get(s.id)}
    for module, _, tested in await _themes(session):
        if not tested:
            continue
        rows = []
        for s in students:
            done = len(by_student.get(s.id, set()) & tested)
            if done:
                mark = "✅" if done == len(tested) else "▫️"
                rows.append(f"{mark} {_name(s)}: {done} из {len(tested)}")
        lines.append(f"\n📘 {module.title}")
        lines.extend(rows or ["   пока никто не сдал тесты"])
    if idle:
        lines.append(f"\nЕщё не сдали ни одного теста: {len(idle)}")
    return _fit("\n".join(lines))


def _name(user: User) -> str:
    return user.first_name or (f"@{user.username}" if user.username else f"id {user.telegram_id}")


def _fit(text: str) -> str:
    return text if len(text) <= MAX_MESSAGE else text[: MAX_MESSAGE - 20].rsplit("\n", 1)[0] + "\n…"

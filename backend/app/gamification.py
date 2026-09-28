"""Experience points, day streak, daily quests and the weekly rating.

Everything is computed from test attempts, so there is nothing extra to store:
- the first passed attempt of a lesson gives XP_PASS points, plus XP_PERFECT if it had no mistakes;
- a day counts for the streak when the student finished at least one test that day;
- days follow the learning centre's time zone (settings.timezone).
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Role, TestAttempt, User

XP_PASS = 10
XP_PERFECT = 5
WEEK_DAYS = 7


@dataclass
class Quest:
    key: str
    title: str
    value: int
    goal: int


def _day(moment: datetime) -> date:
    if moment.tzinfo is None:  # SQLite returns naive UTC
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(ZoneInfo(get_settings().timezone)).date()


def today() -> date:
    return _day(datetime.now(timezone.utc))


async def _attempts(session: AsyncSession, user_ids: list[int] | None = None) -> list[TestAttempt]:
    query = select(TestAttempt).order_by(TestAttempt.created_at, TestAttempt.id)
    if user_ids is not None:
        query = query.where(TestAttempt.user_id.in_(user_ids))
    return list(await session.scalars(query))


def xp_events(attempts: list[TestAttempt]) -> list[tuple[int, date, int]]:
    """(user_id, day, points) for every attempt that earned XP: the first pass of each lesson."""
    seen: set[tuple[int, int]] = set()
    events = []
    for a in attempts:
        if not a.passed or (a.user_id, a.lesson_id) in seen:
            continue
        seen.add((a.user_id, a.lesson_id))
        points = XP_PASS + (XP_PERFECT if a.correct_count == a.total else 0)
        events.append((a.user_id, _day(a.created_at), points))
    return events


def streak(days: set[date], now: date) -> int:
    """Days in a row with a finished test, ending today (or yesterday, so the streak survives until tonight)."""
    day = now if now in days else now - timedelta(days=1)
    count = 0
    while day in days:
        count += 1
        day -= timedelta(days=1)
    return count


async def stats(session: AsyncSession, user: User) -> dict:
    attempts = await _attempts(session, [user.id])
    events = xp_events(attempts)
    now = today()
    today_attempts = [a for a in attempts if _day(a.created_at) == now]
    xp_today = sum(points for _, day, points in events if day == now)
    quests = [
        Quest("xp", "Получите 20 очков опыта", min(xp_today, 20), 20),
        Quest("test", "Сдайте 1 тест", min(sum(a.passed for a in today_attempts), 1), 1),
        Quest("perfect", "Пройдите тест без ошибок", min(sum(a.correct_count == a.total for a in today_attempts), 1), 1),
    ]
    return {
        "xp_total": sum(points for *_, points in events),
        "xp_today": xp_today,
        "streak": streak({_day(a.created_at) for a in attempts}, now),
        "tests_passed": len(events),
        "quests": [q.__dict__ for q in quests],
    }


async def leaderboard(session: AsyncSession, user: User, limit: int = 10) -> dict:
    """Students ranked by XP earned in the last seven days."""
    students = list(await session.scalars(select(User).where(User.role == Role.student)))
    since = today() - timedelta(days=WEEK_DAYS - 1)
    week: dict[int, int] = {s.id: 0 for s in students}
    for user_id, day, points in xp_events(await _attempts(session, list(week))):
        if day >= since:
            week[user_id] += points
    ranked = sorted(students, key=lambda s: (-week[s.id], s.first_name.lower(), s.id))
    rows = [
        {"place": place, "name": s.first_name or s.username or "Студент", "xp": week[s.id], "is_me": s.id == user.id}
        for place, s in enumerate(ranked, start=1)
    ]
    mine = next((row for row in rows if row["is_me"]), None)
    return {"rows": rows[:limit], "me": mine, "total": len(rows)}

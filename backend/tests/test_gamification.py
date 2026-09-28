from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, update

from app import gamification
from app.db import SessionLocal
from app.models import TestAttempt as Attempt
from app.models import User
from tests.conftest import ADMIN_ID, auth
from tests.test_progress import pass_test, seeded_theme
from tests.test_quiz import add_questions


def test_streak_counts_days_in_a_row():
    d = date(2026, 9, 28)
    assert gamification.streak(set(), d) == 0
    assert gamification.streak({d, d - timedelta(days=1), d - timedelta(days=3)}, d) == 2
    # Nothing yet today: yesterday's streak still stands until the day is over.
    assert gamification.streak({d - timedelta(days=1), d - timedelta(days=2)}, d) == 2


async def test_xp_quests_and_rating(client):
    module_id, lessons = await seeded_theme(client)
    first = await add_questions(client, lessons[0])
    second = await add_questions(client, lessons[1])

    stats = (await client.get("/api/me/stats", headers=auth(500))).json()
    assert (stats["xp_total"], stats["streak"], stats["quests"][0]["value"]) == (0, 0, 0)

    await pass_test(client, lessons[0], first)
    await pass_test(client, lessons[0], first)  # a second pass of the same lesson earns nothing
    wrong = {str(q["id"]): [] for q in second}
    await client.post(f"/api/lessons/{lessons[1]}/quiz", json={"answers": wrong}, headers=auth(500))

    stats = (await client.get("/api/me/stats", headers=auth(500))).json()
    assert stats["xp_total"] == stats["xp_today"] == 15  # 10 for passing + 5 without mistakes
    assert stats["streak"] == 1 and stats["tests_passed"] == 1
    assert [(q["key"], q["value"], q["goal"]) for q in stats["quests"]] == [("xp", 15, 20), ("test", 1, 1), ("perfect", 1, 1)]

    # Another student passes one test; attempts older than a week do not count for the rating.
    await pass_test(client, lessons[0], first, user=501)
    await pass_test(client, lessons[0], first, user=502)
    async with SessionLocal() as session:
        old = datetime.now(timezone.utc) - timedelta(days=10)
        user_502 = select(User.id).where(User.telegram_id == 502).scalar_subquery()
        await session.execute(update(Attempt).where(Attempt.user_id == user_502).values(created_at=old))
        await session.commit()

    board = (await client.get("/api/leaderboard", headers=auth(501))).json()
    assert [(r["place"], r["xp"]) for r in board["rows"]] == [(1, 15), (2, 15), (3, 0)]
    assert board["me"]["is_me"] and board["me"]["xp"] == 15 and board["total"] == 3

    admin_board = (await client.get("/api/leaderboard", headers=auth(ADMIN_ID))).json()
    assert admin_board["me"] is None  # teachers and the admin are not ranked


async def test_path_has_every_theme_with_states(client):
    module_id, lessons = await seeded_theme(client)
    await add_questions(client, lessons[0])
    path = (await client.get("/api/path", headers=auth(500))).json()
    theme = next(m for m in path if m["id"] == module_id)
    assert [(l["state"], l["has_test"]) for l in theme["lessons"][:2]] == [("open", True), ("locked", False)]
    assert all(m["lessons"] for m in path)

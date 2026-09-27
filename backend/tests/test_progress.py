from sqlalchemy import select

from app import progress
from app.db import SessionLocal
from app.models import User
from tests.conftest import ADMIN_ID, auth
from tests.test_quiz import add_questions

STUDENT = 500


async def seeded_theme(client) -> tuple[int, list[int]]:
    modules = (await client.get("/api/modules", headers=auth(ADMIN_ID))).json()
    module = (await client.get(f"/api/modules/{modules[0]['id']}", headers=auth(ADMIN_ID))).json()
    return module["id"], [lesson["id"] for lesson in module["lessons"]]


async def pass_test(client, lesson_id: int, questions: list[dict], user: int = STUDENT) -> dict:
    answers = {str(q["id"]): q["correct"] for q in questions}
    r = await client.post(f"/api/lessons/{lesson_id}/quiz", json={"answers": answers}, headers=auth(user))
    assert r.status_code == 200, r.text
    return r.json()


async def states(client, module_id: int, user: int = STUDENT) -> list[str]:
    module = (await client.get(f"/api/modules/{module_id}", headers=auth(user))).json()
    return [lesson["state"] for lesson in module["lessons"]]


async def test_next_lesson_opens_after_the_test(client, outbox):
    module_id, (first, second, *rest) = await seeded_theme(client)
    questions = await add_questions(client, first)
    await add_questions(client, (rest or [second])[-1])  # a later test, so passing the first does not finish the theme
    assert await states(client, module_id) == ["open"] + ["locked"] * (1 + len(rest))

    lesson = (await client.get(f"/api/lessons/{first}", headers=auth(STUDENT))).json()
    assert lesson["next_lesson_id"] == second and lesson["next_unlocked"] is False
    r = await client.get(f"/api/lessons/{second}", headers=auth(STUDENT))
    assert r.status_code == 403 and r.json()["detail"] == "Сначала сдайте тест предыдущего урока"
    assert (await client.get(f"/api/lessons/{second}/quiz", headers=auth(STUDENT))).status_code == 403

    # Teachers and the admin are never blocked.
    assert (await client.get(f"/api/lessons/{second}", headers=auth(ADMIN_ID))).status_code == 200
    assert set(await states(client, module_id, ADMIN_ID)) == {"open"}

    # A failed attempt changes nothing and sends nothing.
    wrong = {str(q["id"]): [] for q in questions}
    await client.post(f"/api/lessons/{first}/quiz", json={"answers": wrong}, headers=auth(STUDENT))
    assert await states(client, module_id) == ["open"] + ["locked"] * (1 + len(rest))
    assert await outbox.flush() == []

    assert (await pass_test(client, first, questions))["passed"] is True
    assert (await pass_test(client, first, questions))["next_lesson_id"] == second
    # Lessons without a test don't block, so everything after the first is open now.
    assert await states(client, module_id) == ["done"] + ["open"] * (1 + len(rest))
    lesson = (await client.get(f"/api/lessons/{first}", headers=auth(STUDENT))).json()
    assert lesson["state"] == "done" and lesson["next_unlocked"] is True

    await outbox.flush()
    [student_msg] = outbox.to(STUDENT)
    assert "сдан" in student_msg and "Открыт следующий урок" in student_msg
    [teacher_msg] = outbox.to(ADMIN_ID)
    assert teacher_msg.startswith("🎓 Тест урока") and "3 из 3" in teacher_msg

    # Passing again does not notify twice.
    outbox.clear()
    await pass_test(client, first, questions)
    assert await outbox.flush() == []


async def test_last_test_finishes_the_theme(client, outbox):
    module_id, lessons = await seeded_theme(client)
    tests = {lesson_id: await add_questions(client, lesson_id) for lesson_id in (lessons[0], lessons[-1])}
    await pass_test(client, lessons[0], tests[lessons[0]])
    await outbox.flush()
    outbox.clear()

    await pass_test(client, lessons[-1], tests[lessons[-1]])
    await outbox.flush()
    assert "пройдена полностью" in outbox.to(STUDENT)[0]
    assert "Вся тема" in outbox.to(ADMIN_ID)[0]


async def test_progress_reports(client):
    module_id, lessons = await seeded_theme(client)
    questions = await add_questions(client, lessons[0])
    await add_questions(client, lessons[1])
    await pass_test(client, lessons[0], questions)
    await client.get("/api/me", headers=auth(501))  # a second student who has not started

    async with SessionLocal() as session:
        student = await session.scalar(select(User).where(User.telegram_id == STUDENT))
        mine = await progress.student_report(session, student)
        everyone = await progress.class_report(session)

    assert "сдано тестов 1 из 2" in mine
    assert "Дальше:" in mine
    assert ": 1 из 2" in everyone
    assert "Ещё не сдали ни одного теста: 1" in everyone

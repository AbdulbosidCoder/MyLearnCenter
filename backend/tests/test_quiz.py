from tests.conftest import ADMIN_ID, auth


async def first_lesson_id(client) -> int:
    modules = (await client.get("/api/modules", headers=auth(ADMIN_ID))).json()
    module = (await client.get(f"/api/modules/{modules[0]['id']}", headers=auth(ADMIN_ID))).json()
    return module["lessons"][0]["id"]


async def add_questions(client, lesson_id: int) -> list[dict]:
    questions = [
        {"prompt": "2 + 2?", "options": ["3", "4", "5"], "correct": [1], "explanation": "Two and two is four."},
        {"kind": "multiple", "prompt": "Even numbers?", "options": ["1", "2", "4"], "correct": [1, 2]},
        {"prompt": "Mean of 2, 4, 6?", "options": ["4", "6"], "correct": [0]},
    ]
    created = []
    for i, q in enumerate(questions):
        r = await client.post(f"/api/lessons/{lesson_id}/questions", json={**q, "position": i}, headers=auth(ADMIN_ID))
        assert r.status_code == 201, r.text
        created.append(r.json())
    return created


async def test_student_takes_a_test_without_seeing_answers(client):
    lesson_id = await first_lesson_id(client)
    q1, q2, q3 = await add_questions(client, lesson_id)

    quiz = (await client.get(f"/api/lessons/{lesson_id}/quiz", headers=auth(500))).json()
    assert quiz["pass_score"] == 0.7
    assert [q["prompt"] for q in quiz["questions"]] == ["2 + 2?", "Even numbers?", "Mean of 2, 4, 6?"]
    assert all("correct" not in q and "explanation" not in q for q in quiz["questions"])
    lesson = (await client.get(f"/api/lessons/{lesson_id}", headers=auth(500))).json()
    assert lesson["question_count"] == 3

    # 2 of 3 is below 70%.
    answers = {str(q1["id"]): [1], str(q2["id"]): [2], str(q3["id"]): [0]}
    r = (await client.post(f"/api/lessons/{lesson_id}/quiz", json={"answers": answers}, headers=auth(500))).json()
    assert (r["correct_count"], r["total"], r["passed"]) == (2, 3, False)
    assert r["results"][0]["explanation"] == "Two and two is four."
    assert r["results"][1] == {"question_id": q2["id"], "is_correct": False, "correct": [1, 2], "explanation": ""}

    answers[str(q2["id"])] = [2, 1]
    r = (await client.post(f"/api/lessons/{lesson_id}/quiz", json={"answers": answers}, headers=auth(500))).json()
    assert r["passed"] is True


async def test_bad_questions_and_roles(client):
    lesson_id = await first_lesson_id(client)
    bad = [
        {"prompt": "x", "options": ["a", "b"], "correct": [2]},
        {"prompt": "x", "options": ["a", "b"], "correct": [0, 1]},  # single with two answers
        {"prompt": "x", "options": ["a"], "correct": [0]},
    ]
    for q in bad:
        assert (await client.post(f"/api/lessons/{lesson_id}/questions", json=q, headers=auth(ADMIN_ID))).status_code == 422
    good = {"prompt": "x", "options": ["a", "b"], "correct": [0]}
    assert (await client.post(f"/api/lessons/{lesson_id}/questions", json=good, headers=auth(500))).status_code == 403

    created = (await add_questions(client, lesson_id))[0]
    assert (await client.delete(f"/api/questions/{created['id']}", headers=auth(ADMIN_ID))).status_code == 204
    quiz = (await client.get(f"/api/lessons/{lesson_id}/quiz", headers=auth(ADMIN_ID))).json()
    assert len(quiz["questions"]) == 2


async def test_lesson_without_test(client):
    lesson_id = await first_lesson_id(client)
    r = await client.post(f"/api/lessons/{lesson_id}/quiz", json={"answers": {}}, headers=auth(500))
    assert r.status_code == 404

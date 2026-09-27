from tests.conftest import ADMIN_ID, auth


async def test_requires_telegram_auth(client):
    assert (await client.get("/api/modules")).status_code == 401
    bad = {"Authorization": "tma hash=deadbeef&auth_date=1"}
    assert (await client.get("/api/modules", headers=bad)).status_code == 401


async def test_first_login_roles(client):
    me = (await client.get("/api/me", headers=auth(ADMIN_ID))).json()
    assert me["role"] == "admin"
    me = (await client.get("/api/me", headers=auth(500))).json()
    assert me["role"] == "student"


async def test_student_reads_themes_and_lessons(client):
    modules = (await client.get("/api/modules", headers=auth(500))).json()
    assert [m["title"] for m in modules][:2] == ["Введение в Data Science", "Статистика"]
    assert modules[0]["lesson_count"] == 2

    module = (await client.get(f"/api/modules/{modules[0]['id']}", headers=auth(500))).json()
    first, second = module["lessons"]

    lesson = (await client.get(f"/api/lessons/{first['id']}", headers=auth(500))).json()
    assert lesson["blocks"][0]["type"] == "text"
    assert lesson["prev_lesson_id"] is None
    assert lesson["next_lesson_id"] == second["id"]


async def test_student_cannot_edit(client):
    r = await client.post("/api/modules", json={"title": "X"}, headers=auth(500))
    assert r.status_code == 403
    assert (await client.get("/api/users", headers=auth(500))).status_code == 403


async def test_admin_makes_teacher_who_builds_a_lesson(client):
    await client.get("/api/me", headers=auth(ADMIN_ID))
    teacher = (await client.get("/api/me", headers=auth(700))).json()

    r = await client.patch(f"/api/users/{teacher['id']}/role", json={"role": "teacher"}, headers=auth(ADMIN_ID))
    assert r.status_code == 200 and r.json()["role"] == "teacher"

    module = (await client.post("/api/modules", json={"title": "Pandas"}, headers=auth(700))).json()
    lesson = (
        await client.post(f"/api/modules/{module['id']}/lessons", json={"title": "DataFrame"}, headers=auth(700))
    ).json()
    gif = {"type": "gif", "content": "https://example.com/df.gif", "caption": "Таблица"}
    r = await client.post(f"/api/lessons/{lesson['id']}/blocks", json=gif, headers=auth(700))
    assert r.status_code == 201

    detail = (await client.get(f"/api/lessons/{lesson['id']}", headers=auth(500))).json()
    assert detail["blocks"][0]["caption"] == "Таблица"

    assert (await client.delete(f"/api/modules/{module['id']}", headers=auth(700))).status_code == 204
    assert (await client.get(f"/api/lessons/{lesson['id']}", headers=auth(500))).status_code == 404


async def test_admin_role_cannot_be_given_or_self_changed(client):
    admin = (await client.get("/api/me", headers=auth(ADMIN_ID))).json()
    student = (await client.get("/api/me", headers=auth(500))).json()
    r = await client.patch(f"/api/users/{student['id']}/role", json={"role": "admin"}, headers=auth(ADMIN_ID))
    assert r.status_code == 400
    r = await client.patch(f"/api/users/{admin['id']}/role", json={"role": "student"}, headers=auth(ADMIN_ID))
    assert r.status_code == 400


async def test_viz_blocks_are_checked(client):
    lesson_id = 1
    widgets = (await client.get("/api/widgets", headers=auth(ADMIN_ID))).json()
    assert {"gradient-descent-3d", "kmeans-2d"} <= {w["name"] for w in widgets}

    good = {"type": "viz", "content": '{"widget": "kmeans-2d", "params": {"k": 4}}'}
    assert (await client.post(f"/api/lessons/{lesson_id}/blocks", json=good, headers=auth(ADMIN_ID))).status_code == 201
    for content in ["not json", '{"widget": "pie-chart"}', '{"widget": "kmeans-2d", "params": 5}']:
        bad = {"type": "viz", "content": content}
        r = await client.post(f"/api/lessons/{lesson_id}/blocks", json=bad, headers=auth(ADMIN_ID))
        assert r.status_code == 422, content

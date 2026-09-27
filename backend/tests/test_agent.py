import asyncio

import pytest
from sqlalchemy import text

from app import agent
from app.config import get_settings
from app.db import engine, init_db
from tests.conftest import ADMIN_ID, auth

MATERIAL = "# Mean\n\nThe mean is the sum divided by the count.\n\n" + "More about the mean. " * 60 + (
    "\n\n# Variance\n\nVariance is the spread of the data.\n\n" + "More about variance. " * 60
)


def fake_claude(refuse_second_part: bool = False):
    """Answers like Claude: lessons for each part, then a plan that reverses and deduplicates them."""

    async def ask(prompt: str, schema: dict):
        if schema is agent.PLAN_SCHEMA:
            return {"title": "Statistics basics", "description": "Centre and spread.", "order": [2, 1, 2, 99]}
        if refuse_second_part and "part 2 of" in prompt:
            return None
        topic = "Mean" if "Mean" in prompt else "Variance"
        return {
            "lessons": [
                {
                    "title": f"What is {topic.lower()}",
                    "level": 1 if topic == "Mean" else 2,
                    "cards": [{"heading": topic, "text": "Explained."}, {"heading": "Recap", "text": "Short."}],
                    "visualization": "normal-distribution-2d" if topic == "Variance" else "none",
                    "questions": [
                        {"kind": "single", "prompt": f"{topic}?", "options": ["a", "b", "c"], "correct": [1], "explanation": "b."},
                        # Broken: index out of range, so the agent drops it.
                        {"kind": "single", "prompt": "Bad", "options": ["a", "b"], "correct": [5], "explanation": ""},
                    ],
                }
            ]
        }

    return ask


@pytest.fixture
def ai_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "test-key")


async def upload(client) -> dict:
    r = await client.post(
        "/api/materials", files={"file": ("stats.md", MATERIAL.encode())}, headers=auth(ADMIN_ID)
    )
    assert r.status_code == 201
    return r.json()


async def run_agent(client, material_id: int) -> dict:
    r = await client.post(f"/api/materials/{material_id}/generate", headers=auth(ADMIN_ID))
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "generating"
    await asyncio.gather(*agent._running)
    return (await client.get(f"/api/materials/{material_id}", headers=auth(ADMIN_ID))).json()


async def test_agent_builds_a_draft_theme_that_teacher_publishes(client, ai_key, monkeypatch):
    monkeypatch.setattr(agent, "ask_claude", fake_claude())
    material = await upload(client)
    assert material["chunk_count"] == 2

    done = await run_agent(client, material["id"])
    assert done["status"] == "draft_ready" and done["chunks_done"] == 2 and done["error"] == ""
    module_id = done["module_id"]

    # The teacher sees the draft in the planned order, with levels.
    module = (await client.get(f"/api/modules/{module_id}", headers=auth(ADMIN_ID))).json()
    assert module["title"] == "Statistics basics"
    assert [(l["title"], l["level"], l["is_draft"]) for l in module["lessons"]] == [
        ("What is variance", 2, True),
        ("What is mean", 1, True),
    ]
    lesson = (await client.get(f"/api/lessons/{module['lessons'][0]['id']}", headers=auth(ADMIN_ID))).json()
    assert [b["type"] for b in lesson["blocks"]] == ["text", "viz", "text"]
    assert lesson["blocks"][1]["content"] == '{"widget": "normal-distribution-2d", "params": {"mean": 0, "sd": 1}}'
    assert lesson["blocks"][2]["content"] == "### Recap\n\nShort."
    assert lesson["question_count"] == 1
    quiz = (await client.get(f"/api/lessons/{lesson['id']}/quiz", headers=auth(ADMIN_ID))).json()
    assert quiz["questions"][0]["correct"] == [1] and quiz["questions"][0]["prompt"] == "Variance?"
    assert (await client.get(f"/api/lessons/{lesson['id']}/quiz", headers=auth(500))).status_code == 404

    # Students see nothing until the teacher publishes.
    titles = [m["title"] for m in (await client.get("/api/modules", headers=auth(500))).json()]
    assert "Statistics basics" not in titles
    assert (await client.get(f"/api/lessons/{lesson['id']}", headers=auth(500))).status_code == 404

    r = await client.post(f"/api/modules/{module_id}/publish", headers=auth(ADMIN_ID))
    assert r.status_code == 200 and r.json()["lesson_count"] == 2
    student_view = (await client.get(f"/api/modules/{module_id}", headers=auth(500))).json()
    assert len(student_view["lessons"]) == 2


async def test_agent_adds_to_chosen_theme_and_reports_skipped_parts(client, ai_key, monkeypatch):
    monkeypatch.setattr(agent, "ask_claude", fake_claude(refuse_second_part=True))
    modules = (await client.get("/api/modules", headers=auth(ADMIN_ID))).json()
    stats = next(m for m in modules if m["title"] == "Статистика")
    r = await client.post(
        "/api/materials",
        files={"file": ("stats.md", MATERIAL.encode())},
        data={"module_id": str(stats["id"])},
        headers=auth(ADMIN_ID),
    )
    done = await run_agent(client, r.json()["id"])
    assert done["status"] == "draft_ready" and done["module_id"] == stats["id"]
    assert "1" in done["error"]

    # Existing lessons stay visible to students; the new draft is hidden from them.
    student = (await client.get(f"/api/modules/{stats['id']}", headers=auth(500))).json()
    teacher = (await client.get(f"/api/modules/{stats['id']}", headers=auth(ADMIN_ID))).json()
    assert len(teacher["lessons"]) == len(student["lessons"]) + 1
    assert teacher["draft_count"] == 1


async def test_agent_failure_is_shown(client, ai_key, monkeypatch):
    async def broken(prompt, schema):
        raise agent.AgentError("Неверный ключ ANTHROPIC_API_KEY.")

    monkeypatch.setattr(agent, "ask_claude", broken)
    material = await upload(client)
    done = await run_agent(client, material["id"])
    assert done["status"] == "failed" and "ключ" in done["error"]


async def test_generate_needs_api_key_and_editor(client):
    material = await upload(client)
    r = await client.post(f"/api/materials/{material['id']}/generate", headers=auth(ADMIN_ID))
    assert r.status_code == 503 and "ANTHROPIC_API_KEY" in r.json()["detail"]
    r = await client.post(f"/api/materials/{material['id']}/generate", headers=auth(500))
    assert r.status_code == 403


async def test_old_database_gets_new_columns():
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE lesson_blocks"))
        await conn.execute(text("DROP TABLE lessons"))
        await conn.execute(
            text("CREATE TABLE lessons (id INTEGER PRIMARY KEY, module_id INTEGER, title VARCHAR(200), position INTEGER)")
        )
        await conn.execute(text("INSERT INTO lessons VALUES (1, 1, 'Old lesson', 0)"))
    await init_db()
    async with engine.connect() as conn:
        row = (await conn.execute(text("SELECT level, is_draft FROM lessons WHERE id = 1"))).one()
    assert tuple(row) == (1, 0)


async def test_teacher_rewrites_a_card_with_ai(client, ai_key, monkeypatch):
    prompts = []

    async def ask(prompt, schema):
        prompts.append(prompt)
        return {"text": "### Mean\n\nSimpler words."}

    monkeypatch.setattr(agent, "ask_claude", ask)
    lesson = (await client.get("/api/lessons/1", headers=auth(ADMIN_ID))).json()
    block_id = lesson["blocks"][0]["id"]

    r = await client.post(f"/api/blocks/{block_id}/rewrite", json={"mode": "simpler"}, headers=auth(ADMIN_ID))
    assert r.status_code == 200 and r.json() == {"text": "### Mean\n\nSimpler words."}
    assert "simpler" in prompts[0] and lesson["title"] in prompts[0]
    # Nothing is saved until the teacher accepts.
    again = (await client.get("/api/lessons/1", headers=auth(ADMIN_ID))).json()
    assert again["blocks"][0]["content"] == lesson["blocks"][0]["content"]

    r = await client.post(
        f"/api/blocks/{block_id}/rewrite", json={"mode": "custom", "instruction": "через футбол"}, headers=auth(ADMIN_ID)
    )
    assert r.status_code == 200 and "через футбол" in prompts[1]
    r = await client.post(f"/api/blocks/{block_id}/rewrite", json={"mode": "custom"}, headers=auth(ADMIN_ID))
    assert r.status_code == 422
    r = await client.post(f"/api/blocks/{block_id}/rewrite", json={"mode": "simpler"}, headers=auth(500))
    assert r.status_code == 403

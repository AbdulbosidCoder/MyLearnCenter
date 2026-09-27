"""The AI agent that turns an uploaded file into a theme of short lessons.

1. Each part of the file (see app/materials.py) goes to Claude separately, so a file of any size
   works: Claude writes 1–3 short lessons for that part, each with a level from 1 to 3.
2. One more request sees only the lesson titles and puts them into a theme: name, description,
   order, and which repeated lessons to drop.
3. The lessons are saved as drafts. Students see them only after a teacher publishes them.
"""

import asyncio
import json
import logging
from functools import lru_cache

import anthropic
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select, update

from app.config import get_settings
from app.db import SessionLocal
from app.models import BlockType, Lesson, LessonBlock, Module, SourceChunk, SourceDocument, SourceStatus

log = logging.getLogger(__name__)

# Parts sent to Claude at the same time; keeps a big book fast without hitting rate limits.
PARALLEL_REQUESTS = 3

# --- What Claude returns ------------------------------------------------------------------


class Card(BaseModel):
    heading: str
    text: str


class LessonDraft(BaseModel):
    title: str
    level: int = Field(ge=1, le=3)
    cards: list[Card] = Field(min_length=1)


class PartLessons(BaseModel):
    lessons: list[LessonDraft]


class ThemePlan(BaseModel):
    title: str
    description: str
    order: list[int]


def _schema(properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required or list(properties),
        "additionalProperties": False,
    }


PART_SCHEMA = _schema(
    {
        "lessons": {
            "type": "array",
            "items": _schema(
                {
                    "title": {"type": "string"},
                    "level": {"type": "integer", "enum": [1, 2, 3]},
                    "cards": {
                        "type": "array",
                        "items": _schema({"heading": {"type": "string"}, "text": {"type": "string"}}),
                    },
                }
            ),
        }
    }
)

PLAN_SCHEMA = _schema(
    {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "order": {"type": "array", "items": {"type": "integer"}},
    }
)

SYSTEM = """You are a teacher who turns textbook material into short, clear lessons for a learning app \
for Data Science and Computer Science students, in the style of Brilliant and Duolingo.

Write in the same language as the material. Keep every fact from the material correct; do not invent \
facts, numbers or formulas that are not supported by it."""

PART_PROMPT = """Here is part {n} of {total} of the material "{doc_title}" (section: "{heading}").

<material>
{text}
</material>

Turn this part into 1 to 3 short lessons. Each lesson teaches one idea and takes 3 to 5 minutes.

- title: a short, concrete lesson name.
- level: 1 = basics (a first-time learner follows it), 2 = practice (needs the basics), \
3 = hard (proofs, tricky cases, advanced use).
- cards: 2 to 5 cards the student reads one after another. Each card is at most 120 words of \
Markdown: plain words first, then an example with real numbers or code when it helps. Formulas go \
in LaTeX between $...$. The last card is a short recap of the main idea.

If this part has no teachable content (a table of contents, references, a preface), return an \
empty list of lessons."""

PLAN_PROMPT = """These draft lessons were written from the material "{doc_title}", in the order of the material:

{lessons}

Build a theme from them:
- title: a short theme name.
- description: one sentence about what the student learns.
- order: the lesson numbers in the order a student should take them. Keep the order of the \
material unless a lesson clearly needs another one first. Leave out a lesson only when it repeats \
another one almost exactly."""


# --- Talking to Claude --------------------------------------------------------------------


class AgentError(Exception):
    """A failure the teacher should see; the message is in Russian."""


@lru_cache
def _client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=get_settings().anthropic_api_key)


async def ask_claude(prompt: str, schema: dict) -> dict | None:
    """One structured request. Returns None when Claude declines to answer this piece."""
    settings = get_settings()
    try:
        response = await _client().beta.messages.create(
            model=settings.ai_model,
            max_tokens=16000,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
            # If a safety classifier declines, the API retries on a fallback model in the same call.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as exc:
        raise AgentError("Неверный ключ ANTHROPIC_API_KEY.") from exc
    except anthropic.PermissionDeniedError as exc:
        raise AgentError("Ключ Claude API не имеет доступа к этой модели.") from exc
    except anthropic.NotFoundError as exc:
        raise AgentError(f"Модель {settings.ai_model} не найдена. Проверьте AI_MODEL.") from exc
    except anthropic.RateLimitError as exc:
        raise AgentError("Превышен лимит запросов к Claude API. Попробуйте позже.") from exc
    except anthropic.APIStatusError as exc:
        raise AgentError(f"Claude API ответил ошибкой {exc.status_code}. Попробуйте позже.") from exc
    except anthropic.APIConnectionError as exc:
        raise AgentError("Нет связи с Claude API.") from exc

    if response.stop_reason in ("refusal", "max_tokens"):
        return None
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


async def lessons_for_part(doc_title: str, chunk: SourceChunk, total: int) -> list[LessonDraft]:
    prompt = PART_PROMPT.format(
        n=chunk.position + 1, total=total, doc_title=doc_title, heading=chunk.heading, text=chunk.text
    )
    data = await ask_claude(prompt, PART_SCHEMA)
    if data is None:
        return []
    try:
        return PartLessons.model_validate(data).lessons
    except ValidationError:
        return []


async def plan_theme(doc_title: str, drafts: list[LessonDraft]) -> ThemePlan:
    listing = "\n".join(
        f"{i}. [level {d.level}] {d.title}: {d.cards[0].text[:150]}" for i, d in enumerate(drafts, start=1)
    )
    data = await ask_claude(PLAN_PROMPT.format(doc_title=doc_title, lessons=listing), PLAN_SCHEMA)
    fallback = ThemePlan(title=doc_title, description="", order=list(range(1, len(drafts) + 1)))
    if data is None:
        return fallback
    try:
        plan = ThemePlan.model_validate(data)
    except ValidationError:
        return fallback
    # Keep only valid, unique lesson numbers; never lose the whole theme to a bad plan.
    seen: set[int] = set()
    plan.order = [i for i in plan.order if 1 <= i <= len(drafts) and not (i in seen or seen.add(i))]
    if not plan.order:
        plan.order = fallback.order
    return plan


# --- The job -------------------------------------------------------------------------------

_running: set[asyncio.Task] = set()


def start_generation(document_id: int) -> None:
    task = asyncio.create_task(generate_course(document_id))
    _running.add(task)
    task.add_done_callback(_running.discard)


async def _set(document_id: int, **values) -> None:
    async with SessionLocal() as session:
        await session.execute(update(SourceDocument).where(SourceDocument.id == document_id).values(**values))
        await session.commit()


async def generate_course(document_id: int) -> None:
    try:
        await _generate(document_id)
    except AgentError as exc:
        await _set(document_id, status=SourceStatus.failed, error=str(exc))
    except Exception:
        log.exception("AI agent failed on material %s", document_id)
        await _set(document_id, status=SourceStatus.failed, error="Внутренняя ошибка агента. Подробности в логах сервера.")


async def _generate(document_id: int) -> None:
    async with SessionLocal() as session:
        doc = await session.get(SourceDocument, document_id)
        chunks = (
            await session.scalars(
                select(SourceChunk).where(SourceChunk.document_id == document_id).order_by(SourceChunk.position)
            )
        ).all()
        doc_title, target_module_id = doc.title, doc.module_id

    limit = asyncio.Semaphore(PARALLEL_REQUESTS)
    done = 0

    async def one(chunk: SourceChunk) -> list[LessonDraft]:
        nonlocal done
        async with limit:
            drafts = await lessons_for_part(doc_title, chunk, len(chunks))
        done += 1
        await _set(document_id, chunks_done=done)
        return drafts

    per_part = await asyncio.gather(*(one(c) for c in chunks))
    drafts = [d for part in per_part for d in part]
    if not drafts:
        raise AgentError("ИИ не нашёл в файле материала для уроков.")
    skipped = sum(1 for part in per_part if not part)

    plan = await plan_theme(doc_title, drafts)

    async with SessionLocal() as session:
        if target_module_id is not None and await session.get(Module, target_module_id) is not None:
            module_id = target_module_id
        else:
            last = await session.scalar(select(func.max(Module.position))) or 0
            module = Module(title=plan.title[:200], description=plan.description, position=last + 1)
            session.add(module)
            await session.flush()
            module_id = module.id

        start = await session.scalar(select(func.count(Lesson.id)).where(Lesson.module_id == module_id)) or 0
        for offset, number in enumerate(plan.order):
            draft = drafts[number - 1]
            session.add(
                Lesson(
                    module_id=module_id,
                    title=draft.title[:200],
                    position=start + offset,
                    level=draft.level,
                    is_draft=True,
                    blocks=[
                        LessonBlock(type=BlockType.text, content=f"### {card.heading}\n\n{card.text}", position=i)
                        for i, card in enumerate(draft.cards)
                    ],
                )
            )
        doc = await session.get(SourceDocument, document_id)
        doc.module_id = module_id
        doc.status = SourceStatus.draft_ready
        doc.error = f"Частей без материала для уроков: {skipped}." if skipped else ""
        await session.commit()


async def fail_interrupted_jobs() -> None:
    """A restart kills running jobs; mark them so the teacher can start again."""
    async with SessionLocal() as session:
        await session.execute(
            update(SourceDocument)
            .where(SourceDocument.status == SourceStatus.generating)
            .values(status=SourceStatus.failed, error="Сервер перезапустился во время работы. Запустите заново.")
        )
        await session.commit()

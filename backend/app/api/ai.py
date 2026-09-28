"""The AI helper: answers a question about the course, optionally with a picture.

The picture is read on this server (app/vision.py); the question and what was read are matched
against the knowledge base (app/rag.py) and the current lesson, and Claude writes the answer.
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app import agent, rag, vision
from app.config import get_settings
from app.deps import CurrentUser, Session
from app.models import BlockType, KnowledgeItem, Lesson, LessonBlock, Module, Role, SourceDocument, SourceImage, User
from app.progress import is_locked
from app.schemas import AiStatus, AskOut, Source

router = APIRouter(tags=["ai"])

MAX_IMAGE_MB = 10
PIECES = 5
MAX_PIECE_CHARS = 1500

HELPER_SYSTEM = """You are a friendly tutor inside a learning app for Data Science and Computer Science.

Answer in the language of the student's question (Uzbek, Russian or English). Explain simply and \\
precisely: plain words first, then a short example with real numbers or code when it helps. Use \\
Markdown; formulas go in LaTeX between $...$. Keep it under 250 words unless the student asks for more.

Base the answer on the course material given below; when you add general knowledge beyond it, keep \\
it correct and say so. If the question is about a picture, use what was read from it. If you are not \\
sure, say so instead of guessing. If the student asks for the answers to a test, help them think it \\
through instead of giving the answer letter."""

HELPER_PROMPT = """{lesson}{picture}Course material that may help:
<material>
{pieces}
</material>

Student's question: {question}"""


@router.get("/ai/status", response_model=AiStatus)
async def ai_status(_: CurrentUser):
    return AiStatus(
        claude=bool(get_settings().anthropic_api_key),
        ocr_languages=await run_in_threadpool(vision.ocr_languages),
        captions=vision.captions_available(),
        embeddings=rag.embeddings_available(),
    )


async def _allowed_documents(session: Session, user: User, lesson: Lesson | None) -> list[int]:
    """Students search only materials whose theme is published; the lesson's theme comes first."""
    stmt = select(SourceDocument.id)
    if user.role not in (Role.admin, Role.teacher):
        published = select(Lesson.module_id).where(Lesson.is_draft.is_(False))
        stmt = stmt.where(SourceDocument.module_id.in_(published))
    if lesson is not None:
        in_theme = list(await session.scalars(stmt.where(SourceDocument.module_id == lesson.module_id)))
        if in_theme:
            return in_theme
    return list(await session.scalars(stmt))


async def _lesson(session: Session, user: User, lesson_id: int) -> Lesson:
    lesson = await session.get(Lesson, lesson_id)
    editor = user.role in (Role.admin, Role.teacher)
    if lesson is None or (lesson.is_draft and not editor):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    if await is_locked(session, user, lesson):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Сначала сдайте тест предыдущего урока")
    return lesson


@router.post("/ai/ask", response_model=AskOut)
async def ask(
    session: Session,
    user: CurrentUser,
    question: Annotated[str, Form(max_length=2000)] = "",
    lesson_id: Annotated[int | None, Form()] = None,
    image: Annotated[UploadFile | None, File()] = None,
):
    if not get_settings().anthropic_api_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "ИИ не настроен: добавьте ANTHROPIC_API_KEY в backend/.env")
    question = question.strip()
    if not question and image is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Напишите вопрос или приложите картинку.")

    image_text = ""
    if image is not None:
        data = await image.read(MAX_IMAGE_MB * 1024 * 1024 + 1)
        if len(data) > MAX_IMAGE_MB * 1024 * 1024:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"Картинка больше {MAX_IMAGE_MB} МБ")
        if not (image.content_type or "").startswith("image/"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Приложите картинку: PNG, JPG или WebP.")
        read = await run_in_threadpool(vision.read_image, data)
        image_text = read.describe() if (read.caption or read.ocr_text) else ""
        if not image_text:
            image_text = "Картинку прочитать не удалось: на сервере нет моделей для изображений."
    question = question or "Объясни, что на этой картинке, и как это связано с курсом."

    lesson = await _lesson(session, user, lesson_id) if lesson_id is not None else None
    lesson_block = ""
    if lesson is not None:
        module = await session.get(Module, lesson.module_id)
        texts = await session.scalars(
            select(LessonBlock.content)
            .where(LessonBlock.lesson_id == lesson.id, LessonBlock.type == BlockType.text)
            .order_by(LessonBlock.position)
        )
        body = "\n\n".join(texts)[:6000]
        lesson_block = f'The student is on the lesson "{lesson.title}" of the theme "{module.title}":\n<lesson>\n{body}\n</lesson>\n\n'

    documents = await _allowed_documents(session, user, lesson)
    found = await rag.search(session, f"{question}\n{image_text}", document_ids=documents, k=PIECES)
    pieces = "\n\n".join(f"[{item.title}]\n{item.text[:MAX_PIECE_CHARS]}" for item, _ in found) or "(nothing found)"
    picture = f"The student attached a picture. Read on the server:\n<picture>\n{image_text}\n</picture>\n\n" if image_text else ""

    try:
        answer = await agent.ask_text(
            HELPER_SYSTEM,
            HELPER_PROMPT.format(lesson=lesson_block, picture=picture, pieces=pieces, question=question),
        )
    except agent.AgentError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return AskOut(
        answer=answer or "ИИ не смог ответить на этот вопрос. Попробуйте сформулировать его иначе.",
        image_text=image_text,
        sources=[await _source(session, item) for item, _ in found],
    )


async def _source(session: Session, item: KnowledgeItem) -> Source:
    image = await session.get(SourceImage, item.image_id) if item.image_id else None
    return Source(title=item.title, image_url=image.url if image else None)

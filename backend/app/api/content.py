from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from app import agent, notify
from app.config import get_settings
from app.deps import EDITOR, CurrentUser, Session
from app.models import BlockType, Lesson, LessonBlock, Module, Question, Role, User
from app.progress import LessonState, lesson_states
from app.schemas import (
    BlockIn,
    BlockOut,
    BlockPatch,
    LessonDetail,
    LessonIn,
    LessonPatch,
    LessonShort,
    ModuleDetail,
    ModuleIn,
    ModuleOut,
    ModulePatch,
    RewriteIn,
    RewriteMode,
    RewriteOut,
    WidgetOut,
)
from app.widgets import WIDGETS

router = APIRouter(tags=["content"])


async def _get_or_404(session: Session, model, obj_id: int):
    obj = await session.get(model, obj_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} not found")
    return obj


def _apply(obj, patch) -> None:
    for key, value in patch.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)


# --- Modules (themes) ---------------------------------------------------------


def _is_editor(user: User) -> bool:
    return user.role in (Role.admin, Role.teacher)


@router.get("/modules", response_model=list[ModuleOut])
async def list_modules(session: Session, user: CurrentUser):
    counts = (
        select(
            Lesson.module_id,
            func.count(Lesson.id).label("total"),
            func.count(Lesson.id).filter(Lesson.is_draft).label("drafts"),
        )
        .group_by(Lesson.module_id)
        .subquery()
    )
    rows = await session.execute(
        select(Module, func.coalesce(counts.c.total, 0), func.coalesce(counts.c.drafts, 0))
        .outerjoin(counts, counts.c.module_id == Module.id)
        .order_by(Module.position, Module.id)
    )
    result = []
    for module, total, drafts in rows:
        published = total - drafts
        if not _is_editor(user):
            # A theme the AI agent has only drafted is not ready for students yet.
            if drafts and not published:
                continue
            drafts = 0
        result.append(ModuleOut.model_validate(module).model_copy(update={"lesson_count": published, "draft_count": drafts}))
    return result


@router.get("/path", response_model=list[ModuleDetail])
async def learning_path(session: Session, user: CurrentUser):
    """All themes with their lessons, for the path on the home screen."""
    modules = await session.scalars(
        select(Module).order_by(Module.position, Module.id).options(selectinload(Module.lessons))
    )
    path = [await _module_detail(session, user, module) for module in modules]
    return [m for m in path if m.lessons] if not _is_editor(user) else path


@router.get("/modules/{module_id}", response_model=ModuleDetail)
async def get_module(module_id: int, session: Session, user: CurrentUser):
    module = await session.scalar(
        select(Module).where(Module.id == module_id).options(selectinload(Module.lessons))
    )
    if module is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
    return await _module_detail(session, user, module)


async def _module_detail(session: Session, user: User, module: Module) -> ModuleDetail:
    lessons = [lesson for lesson in module.lessons if _is_editor(user) or not lesson.is_draft]
    states = await lesson_states(session, user, lessons)
    ids = [lesson.id for lesson in lessons]
    with_test = set(await session.scalars(select(Question.lesson_id).where(Question.lesson_id.in_(ids)).distinct()))
    return ModuleDetail(
        id=module.id,
        title=module.title,
        description=module.description,
        position=module.position,
        lesson_count=sum(1 for lesson in lessons if not lesson.is_draft),
        draft_count=sum(1 for lesson in lessons if lesson.is_draft),
        lessons=[
            LessonShort.model_validate(lesson).model_copy(
                update={"state": states[lesson.id], "has_test": lesson.id in with_test}
            )
            for lesson in lessons
        ],
    )


@router.post("/modules", response_model=ModuleOut, status_code=201, dependencies=[EDITOR])
async def create_module(body: ModuleIn, session: Session):
    module = Module(**body.model_dump())
    session.add(module)
    await session.commit()
    return module


@router.patch("/modules/{module_id}", response_model=ModuleOut, dependencies=[EDITOR])
async def update_module(module_id: int, body: ModulePatch, session: Session):
    module = await _get_or_404(session, Module, module_id)
    _apply(module, body)
    await session.commit()
    return module


@router.post("/modules/{module_id}/publish", response_model=ModuleOut, dependencies=[EDITOR])
async def publish_module(module_id: int, session: Session):
    """Makes every draft lesson of the theme visible to students."""
    module = await _get_or_404(session, Module, module_id)
    new = await session.scalar(select(func.count(Lesson.id)).where(Lesson.module_id == module_id, Lesson.is_draft))
    await session.execute(update(Lesson).where(Lesson.module_id == module_id).values(is_draft=False))
    await session.commit()
    total = await session.scalar(select(func.count(Lesson.id)).where(Lesson.module_id == module_id))
    if new:
        text = f"📘 Новые уроки в теме «{module.title}»: {new}. Заходите учиться!"
        notify.send(await notify.telegram_ids(session, Role.student), text)
    return ModuleOut.model_validate(module).model_copy(update={"lesson_count": total})


@router.delete("/modules/{module_id}", status_code=204, dependencies=[EDITOR])
async def delete_module(module_id: int, session: Session):
    await session.delete(await _get_or_404(session, Module, module_id))
    await session.commit()
    return Response(status_code=204)


# --- Lessons --------------------------------------------------------------------


@router.get("/lessons/{lesson_id}", response_model=LessonDetail)
async def get_lesson(lesson_id: int, session: Session, user: CurrentUser):
    lesson = await session.scalar(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(
            selectinload(Lesson.blocks),
            selectinload(Lesson.questions),
            selectinload(Lesson.module).selectinload(Module.lessons),
        )
    )
    if lesson is None or (lesson.is_draft and not _is_editor(user)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    visible = [sib for sib in lesson.module.lessons if _is_editor(user) or not sib.is_draft]
    states = await lesson_states(session, user, visible)
    if states[lesson.id] == LessonState.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Сначала сдайте тест предыдущего урока")
    siblings = [sib.id for sib in visible]
    i = siblings.index(lesson.id)
    next_id = siblings[i + 1] if i + 1 < len(siblings) else None
    return LessonDetail(
        id=lesson.id,
        module_id=lesson.module_id,
        module_title=lesson.module.title,
        title=lesson.title,
        position=lesson.position,
        level=lesson.level,
        is_draft=lesson.is_draft,
        question_count=len(lesson.questions),
        state=states[lesson.id],
        blocks=[BlockOut.model_validate(b) for b in lesson.blocks],
        prev_lesson_id=siblings[i - 1] if i > 0 else None,
        next_lesson_id=next_id,
        next_unlocked=next_id is None or states[next_id] != LessonState.locked,
    )


@router.post("/modules/{module_id}/lessons", response_model=LessonShort, status_code=201, dependencies=[EDITOR])
async def create_lesson(module_id: int, body: LessonIn, session: Session):
    await _get_or_404(session, Module, module_id)
    lesson = Lesson(module_id=module_id, **body.model_dump())
    session.add(lesson)
    await session.commit()
    return lesson


@router.patch("/lessons/{lesson_id}", response_model=LessonShort, dependencies=[EDITOR])
async def update_lesson(lesson_id: int, body: LessonPatch, session: Session):
    lesson = await _get_or_404(session, Lesson, lesson_id)
    _apply(lesson, body)
    await session.commit()
    return lesson


@router.delete("/lessons/{lesson_id}", status_code=204, dependencies=[EDITOR])
async def delete_lesson(lesson_id: int, session: Session):
    await session.delete(await _get_or_404(session, Lesson, lesson_id))
    await session.commit()
    return Response(status_code=204)


# --- Lesson blocks (theory, GIF, image, video) ------------------------------------


@router.post("/lessons/{lesson_id}/blocks", response_model=BlockOut, status_code=201, dependencies=[EDITOR])
async def create_block(lesson_id: int, body: BlockIn, session: Session):
    await _get_or_404(session, Lesson, lesson_id)
    block = LessonBlock(lesson_id=lesson_id, **body.model_dump())
    session.add(block)
    await session.commit()
    return block


@router.patch("/blocks/{block_id}", response_model=BlockOut, dependencies=[EDITOR])
async def update_block(block_id: int, body: BlockPatch, session: Session):
    block = await _get_or_404(session, LessonBlock, block_id)
    _apply(block, body)
    await session.commit()
    return block


@router.delete("/blocks/{block_id}", status_code=204, dependencies=[EDITOR])
async def delete_block(block_id: int, session: Session):
    await session.delete(await _get_or_404(session, LessonBlock, block_id))
    await session.commit()
    return Response(status_code=204)


@router.post("/blocks/{block_id}/rewrite", response_model=RewriteOut, dependencies=[EDITOR])
async def rewrite_block(block_id: int, body: RewriteIn, session: Session):
    """Asks the AI for a new version of a theory card. Nothing is saved: the teacher accepts it with PATCH."""
    if not get_settings().anthropic_api_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "ИИ не настроен: добавьте ANTHROPIC_API_KEY в backend/.env")
    block = await _get_or_404(session, LessonBlock, block_id)
    if block.type != BlockType.text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ИИ переписывает только текстовые карточки")
    if body.mode == RewriteMode.custom and not body.instruction.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Напишите, что изменить")
    lesson = await session.get(Lesson, block.lesson_id)
    try:
        text = await agent.rewrite_card(lesson.title, block.content, body.mode, body.instruction)
    except agent.AgentError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return RewriteOut(text=text)


@router.get("/widgets", response_model=list[WidgetOut], dependencies=[EDITOR])
async def list_widgets():
    return [WidgetOut(name=name, title=w["title"], params=w["params"]) for name, w in WIDGETS.items()]

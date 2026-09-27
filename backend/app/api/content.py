from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.deps import EDITOR, CurrentUser, Session
from app.models import Lesson, LessonBlock, Module
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
)

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


@router.get("/modules", response_model=list[ModuleOut])
async def list_modules(session: Session, _: CurrentUser):
    counts = (
        select(Lesson.module_id, func.count(Lesson.id).label("n")).group_by(Lesson.module_id).subquery()
    )
    rows = await session.execute(
        select(Module, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.module_id == Module.id)
        .order_by(Module.position, Module.id)
    )
    return [ModuleOut.model_validate(m).model_copy(update={"lesson_count": n}) for m, n in rows]


@router.get("/modules/{module_id}", response_model=ModuleDetail)
async def get_module(module_id: int, session: Session, _: CurrentUser):
    module = await session.scalar(
        select(Module).where(Module.id == module_id).options(selectinload(Module.lessons))
    )
    if module is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
    return ModuleDetail(
        id=module.id,
        title=module.title,
        description=module.description,
        position=module.position,
        lesson_count=len(module.lessons),
        lessons=[LessonShort.model_validate(lesson) for lesson in module.lessons],
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


@router.delete("/modules/{module_id}", status_code=204, dependencies=[EDITOR])
async def delete_module(module_id: int, session: Session):
    await session.delete(await _get_or_404(session, Module, module_id))
    await session.commit()
    return Response(status_code=204)


# --- Lessons --------------------------------------------------------------------


@router.get("/lessons/{lesson_id}", response_model=LessonDetail)
async def get_lesson(lesson_id: int, session: Session, _: CurrentUser):
    lesson = await session.scalar(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(selectinload(Lesson.blocks), selectinload(Lesson.module).selectinload(Module.lessons))
    )
    if lesson is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    siblings = [sib.id for sib in lesson.module.lessons]
    i = siblings.index(lesson.id)
    return LessonDetail(
        id=lesson.id,
        module_id=lesson.module_id,
        module_title=lesson.module.title,
        title=lesson.title,
        position=lesson.position,
        blocks=[BlockOut.model_validate(b) for b in lesson.blocks],
        prev_lesson_id=siblings[i - 1] if i > 0 else None,
        next_lesson_id=siblings[i + 1] if i + 1 < len(siblings) else None,
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

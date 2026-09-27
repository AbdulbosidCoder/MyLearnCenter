from pathlib import PurePath
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.deps import EDITOR, Session
from app.materials import MaterialError, parse_material
from app.models import Module, SourceChunk, SourceDocument, User
from app.schemas import ChunkOut, MaterialDetail, MaterialOut

router = APIRouter(tags=["materials"])


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    data = bytearray()
    while chunk := await file.read(1024 * 1024):
        data += chunk
        if len(data) > limit:
            raise HTTPException(
                status.HTTP_413_CONTENT_TOO_LARGE, f"Файл больше {limit // (1024 * 1024)} МБ"
            )
    return bytes(data)


@router.post("/materials", response_model=MaterialOut, status_code=201)
async def upload_material(
    session: Session,
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form(max_length=200)] = "",
    module_id: Annotated[int | None, Form()] = None,
    user: User = EDITOR,
):
    filename = file.filename or "file"
    data = await _read_limited(file, get_settings().max_upload_mb * 1024 * 1024)
    if module_id is not None and await session.get(Module, module_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
    try:
        # PDF parsing is CPU work; keep it off the event loop.
        kind, chunks = await run_in_threadpool(parse_material, filename, data)
    except MaterialError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    doc = SourceDocument(
        title=title.strip() or PurePath(filename).stem[:200],
        filename=filename[:255],
        kind=kind,
        char_count=sum(len(c.text) for c in chunks),
        module_id=module_id,
        uploaded_by=user.id,
        chunks=[
            SourceChunk(position=i, heading=c.heading, text=c.text, char_count=len(c.text))
            for i, c in enumerate(chunks)
        ],
    )
    session.add(doc)
    await session.commit()
    return MaterialOut.model_validate(doc).model_copy(update={"chunk_count": len(chunks)})


@router.get("/materials", response_model=list[MaterialOut], dependencies=[EDITOR])
async def list_materials(session: Session):
    counts = (
        select(SourceChunk.document_id, func.count(SourceChunk.id).label("n"))
        .group_by(SourceChunk.document_id)
        .subquery()
    )
    rows = await session.execute(
        select(SourceDocument, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.document_id == SourceDocument.id)
        .order_by(SourceDocument.created_at.desc(), SourceDocument.id.desc())
    )
    return [MaterialOut.model_validate(d).model_copy(update={"chunk_count": n}) for d, n in rows]


@router.get("/materials/{material_id}", response_model=MaterialDetail, dependencies=[EDITOR])
async def get_material(material_id: int, session: Session):
    doc = await session.scalar(
        select(SourceDocument).where(SourceDocument.id == material_id).options(selectinload(SourceDocument.chunks))
    )
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Material not found")
    return MaterialDetail(
        **MaterialOut.model_validate(doc).model_dump(exclude={"chunk_count"}),
        chunk_count=len(doc.chunks),
        chunks=[ChunkOut.model_validate(c) for c in doc.chunks],
    )


@router.delete("/materials/{material_id}", status_code=204, dependencies=[EDITOR])
async def delete_material(material_id: int, session: Session):
    doc = await session.get(SourceDocument, material_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Material not found")
    await session.delete(doc)
    await session.commit()
    return Response(status_code=204)

import shutil
from pathlib import PurePath
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from app import rag
from app.agent import start_generation
from app.config import get_settings
from app.deps import EDITOR, Session
from app.materials import MaterialError, read_material
from app.models import IndexStatus, Module, SourceChunk, SourceDocument, SourceImage, SourceStatus, User
from app.schemas import ChunkOut, ImageOut, MaterialDetail, MaterialOut

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
        parsed = await run_in_threadpool(read_material, filename, data)
    except MaterialError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    doc = SourceDocument(
        title=title.strip() or PurePath(filename).stem[:200],
        filename=filename[:255],
        kind=parsed.kind,
        char_count=sum(len(c.text) for c in parsed.chunks),
        module_id=module_id,
        uploaded_by=user.id,
        index_status=IndexStatus.pending,
        chunks=[
            SourceChunk(position=i, heading=c.heading, text=c.text, char_count=len(c.text))
            for i, c in enumerate(parsed.chunks)
        ],
    )
    session.add(doc)
    await session.flush()
    session.add_all(await run_in_threadpool(rag.save_images, doc.id, parsed.images))
    await session.commit()
    # Pictures are read and the knowledge base is filled in the background.
    rag.start_indexing(doc.id)
    return _out(doc, len(parsed.chunks), len(parsed.images))


def _out(doc: SourceDocument, chunk_count: int, image_count: int) -> MaterialOut:
    return MaterialOut.model_validate(doc).model_copy(update={"chunk_count": chunk_count, "image_count": image_count})


@router.get("/materials", response_model=list[MaterialOut], dependencies=[EDITOR])
async def list_materials(session: Session):
    counts = (
        select(SourceChunk.document_id, func.count(SourceChunk.id).label("n"))
        .group_by(SourceChunk.document_id)
        .subquery()
    )
    pictures = (
        select(SourceImage.document_id, func.count(SourceImage.id).label("n"))
        .group_by(SourceImage.document_id)
        .subquery()
    )
    rows = await session.execute(
        select(SourceDocument, func.coalesce(counts.c.n, 0), func.coalesce(pictures.c.n, 0))
        .outerjoin(counts, counts.c.document_id == SourceDocument.id)
        .outerjoin(pictures, pictures.c.document_id == SourceDocument.id)
        .order_by(SourceDocument.created_at.desc(), SourceDocument.id.desc())
    )
    return [_out(d, n, m) for d, n, m in rows]


@router.get("/materials/{material_id}", response_model=MaterialDetail, dependencies=[EDITOR])
async def get_material(material_id: int, session: Session):
    doc = await session.scalar(
        select(SourceDocument)
        .where(SourceDocument.id == material_id)
        .options(selectinload(SourceDocument.chunks), selectinload(SourceDocument.images))
    )
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Material not found")
    return MaterialDetail(
        **MaterialOut.model_validate(doc).model_dump(exclude={"chunk_count", "image_count"}),
        chunk_count=len(doc.chunks),
        image_count=len(doc.images),
        chunks=[ChunkOut.model_validate(c) for c in doc.chunks],
        images=[ImageOut.model_validate(i) for i in doc.images],
    )


@router.post("/materials/{material_id}/index", response_model=MaterialOut, status_code=202, dependencies=[EDITOR])
async def reindex_material(material_id: int, session: Session):
    """Reads the pictures and rebuilds the knowledge base again, e.g. after installing the vision models."""
    doc = await session.get(SourceDocument, material_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Material not found")
    if doc.index_status == IndexStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "ИИ уже изучает этот материал")
    doc.index_status, doc.images_done = IndexStatus.pending, 0
    await session.commit()
    rag.start_indexing(doc.id)
    return MaterialOut.model_validate(doc)


@router.post("/materials/{material_id}/generate", response_model=MaterialOut, status_code=202, dependencies=[EDITOR])
async def generate_lessons(material_id: int, session: Session):
    """Starts the AI agent in the background; the page polls the material for progress."""
    if not get_settings().anthropic_api_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "ИИ не настроен: добавьте ANTHROPIC_API_KEY в backend/.env"
        )
    doc = await session.get(SourceDocument, material_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Material not found")
    if doc.status == SourceStatus.generating:
        raise HTTPException(status.HTTP_409_CONFLICT, "ИИ уже работает с этим материалом")
    if doc.index_status == IndexStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "ИИ ещё изучает рисунки. Подождите немного.")
    chunk_count = await session.scalar(select(func.count(SourceChunk.id)).where(SourceChunk.document_id == doc.id))
    doc.status, doc.chunks_done, doc.error = SourceStatus.generating, 0, ""
    await session.commit()
    start_generation(doc.id)
    return MaterialOut.model_validate(doc).model_copy(update={"chunk_count": chunk_count})


@router.delete("/materials/{material_id}", status_code=204, dependencies=[EDITOR])
async def delete_material(material_id: int, session: Session):
    doc = await session.get(SourceDocument, material_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Material not found")
    await session.delete(doc)
    await session.commit()
    shutil.rmtree(rag.media_root() / "materials" / str(material_id), ignore_errors=True)
    return Response(status_code=204)

"""The knowledge base: every part of an uploaded file and every picture in it, searchable by meaning.

After an upload, `start_indexing` reads the pictures (app/vision.py), saves them under
settings.media_dir and stores one KnowledgeItem per text part and per picture, with a vector from
the local embedding model multilingual-e5-small (Uzbek, Russian and English in one space).
`search` then finds the pieces closest to a question. Without sentence-transformers installed
the search falls back to matching words, so the app still works on a small server.
"""

import asyncio
import logging
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from sqlalchemy import delete, select
from starlette.concurrency import run_in_threadpool

from app import vision
from app.config import get_settings
from app.db import SessionLocal
from app.materials import FIGURE, FIGURE_RE, Image, Paragraph, figure_numbers, split_into_chunks
from app.models import IndexStatus, KnowledgeItem, SourceChunk, SourceDocument, SourceImage

log = logging.getLogger(__name__)

_running: set[asyncio.Task] = set()


# --- Embeddings ---------------------------------------------------------------------------


@lru_cache
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(get_settings().embedding_model, device="cpu")


def embeddings_available() -> bool:
    if not get_settings().embedding_model:
        return False
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return False
    return True


def embed(texts: list[str], query: bool = False) -> list[list[float]] | None:
    """Normalised vectors, or None when the model is not available. Blocking."""
    if not texts or not embeddings_available():
        return None
    # e5 models expect these prefixes on questions and on stored passages.
    prefix = "query: " if query else "passage: "
    try:
        vectors = _model().encode([prefix + t for t in texts], normalize_embeddings=True, batch_size=16)
    except Exception as exc:
        log.warning("Embedding failed: %s", exc)
        return None
    return [[round(float(x), 6) for x in v] for v in vectors]


# --- Indexing an uploaded file ----------------------------------------------------------------


def media_root() -> Path:
    return Path(get_settings().media_dir).resolve()


def save_images(document_id: int, images: list[Image]) -> list[SourceImage]:
    folder = media_root() / "materials" / str(document_id)
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for image in images:
        name = f"{image.number}.{image.ext or 'png'}"
        (folder / name).write_bytes(image.data)
        rows.append(SourceImage(document_id=document_id, number=image.number, path=f"materials/{document_id}/{name}"))
    return rows


async def resume_indexing() -> None:
    """A restart stops running jobs; start them again."""
    async with SessionLocal() as session:
        pending = await session.scalars(
            select(SourceDocument.id).where(SourceDocument.index_status == IndexStatus.pending)
        )
        for document_id in pending:
            start_indexing(document_id)


def start_indexing(document_id: int) -> None:
    task = asyncio.create_task(index_document(document_id))
    _running.add(task)
    task.add_done_callback(_running.discard)


async def index_document(document_id: int) -> None:
    try:
        await _index(document_id)
    except Exception:
        log.exception("Indexing material %s failed", document_id)
        async with SessionLocal() as session:
            doc = await session.get(SourceDocument, document_id)
            if doc is not None:
                doc.index_status = IndexStatus.failed
                await session.commit()


async def _index(document_id: int) -> None:
    async with SessionLocal() as session:
        images = list(await session.scalars(select(SourceImage).where(SourceImage.document_id == document_id)))
        paths = {img.id: media_root() / img.path for img in images}

    # 1. Read every picture, one at a time: the models are heavy and the server is shared.
    for done, image in enumerate(images, start=1):
        data = paths[image.id].read_bytes() if paths[image.id].is_file() else b""
        result = await run_in_threadpool(vision.read_image, data) if data else vision.ImageText()
        async with SessionLocal() as session:
            row = await session.get(SourceImage, image.id)
            row.caption, row.ocr_text = result.caption[:4000], result.ocr_text[:20000]
            doc = await session.get(SourceDocument, document_id)
            doc.images_done = done
            await session.commit()

    async with SessionLocal() as session:
        doc = await session.get(SourceDocument, document_id)
        images = list(await session.scalars(select(SourceImage).where(SourceImage.document_id == document_id)))
        chunks = list(
            await session.scalars(
                select(SourceChunk).where(SourceChunk.document_id == document_id).order_by(SourceChunk.position)
            )
        )
        # 2. A scan has only pictures: its text is what OCR read, so the parts are rebuilt from it.
        if _is_scan(chunks, images):
            await _rebuild_chunks_from_ocr(session, doc, chunks, images)
            chunks = list(
                await session.scalars(
                    select(SourceChunk).where(SourceChunk.document_id == document_id).order_by(SourceChunk.position)
                )
            )

        # 3. One searchable item per part and per picture.
        items = [
            KnowledgeItem(document_id=document_id, title=f"{doc.title}: {c.heading}"[:300], text=c.text) for c in chunks
        ]
        items += [
            KnowledgeItem(
                document_id=document_id,
                image_id=img.id,
                title=f"{doc.title}: рисунок {img.number}"[:300],
                text=vision.ImageText(img.caption, img.ocr_text).describe(),
            )
            for img in images
        ]
        vectors = await run_in_threadpool(embed, [f"{i.title}\n{i.text}" for i in items])
        for item, vector in zip(items, vectors or [None] * len(items)):
            item.embedding = vector
        await session.execute(delete(KnowledgeItem).where(KnowledgeItem.document_id == document_id))
        session.add_all(items)
        doc.index_status = IndexStatus.ready
        await session.commit()


def _is_scan(chunks: list[SourceChunk], images: list[SourceImage]) -> bool:
    own_text = sum(len(FIGURE_RE.sub("", c.text).strip()) for c in chunks)
    read_text = sum(len(img.ocr_text) for img in images)
    return bool(images) and read_text > 200 and own_text < read_text * 0.2


async def _rebuild_chunks_from_ocr(session, doc: SourceDocument, chunks, images) -> None:
    by_number = {img.number: img for img in images}
    paragraphs: list[Paragraph] = []
    for chunk in chunks:
        for n in figure_numbers(chunk.text):
            img = by_number.get(n)
            if img is not None and img.ocr_text:
                paragraphs += [Paragraph(p) for p in re.split(r"\n\s*\n", img.ocr_text) if p.strip()]
            paragraphs.append(Paragraph(FIGURE.format(n=n)))
    new = split_into_chunks(paragraphs)
    for chunk in chunks:
        await session.delete(chunk)
    await session.flush()
    for i, c in enumerate(new):
        session.add(SourceChunk(document_id=doc.id, position=i, heading=c.heading, text=c.text, char_count=len(c.text)))
    doc.char_count = sum(len(c.text) for c in new)


# --- Search -----------------------------------------------------------------------------------

_WORD = re.compile(r"\w{3,}", re.UNICODE)


def _words(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def _keyword_scores(query: str, items: list[KnowledgeItem]) -> list[float]:
    """TF-IDF-like overlap, used when there is no embedding model."""
    docs = [Counter(_words(f"{i.title} {i.text}")) for i in items]
    df = Counter(w for d in docs for w in d)
    q = set(_words(query))
    n = len(items)
    return [
        sum((1 + math.log(d[w])) * math.log(1 + n / df[w]) for w in q if w in d) / math.sqrt(1 + sum(d.values()) / 200)
        for d in docs
    ]


async def search(session, query: str, document_ids: list[int] | None = None, k: int = 5, exclude: set[int] | None = None):
    """The k items closest to the query, best first, as (item, score)."""
    stmt = select(KnowledgeItem)
    if document_ids is not None:
        if not document_ids:
            return []
        stmt = stmt.where(KnowledgeItem.document_id.in_(document_ids))
    items = [i for i in await session.scalars(stmt) if not exclude or i.id not in exclude]
    if not items:
        return []
    vectors = [i.embedding for i in items]
    query_vector = await run_in_threadpool(embed, [query], True) if all(vectors) else None
    if query_vector:
        qv = query_vector[0]
        scores = [sum(a * b for a, b in zip(qv, v)) for v in vectors]
    else:
        scores = _keyword_scores(query, items)
    ranked = sorted(zip(items, scores), key=lambda pair: -pair[1])
    return [(item, score) for item, score in ranked[:k] if score > 0]

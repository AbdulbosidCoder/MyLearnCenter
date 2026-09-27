"""Turns an uploaded file (PDF, Word, text) into short parts the AI agent can read one at a time.

Nothing here calls the AI: we only extract the text and cut it along headings and paragraphs,
so a 300-page book becomes a list of parts of a few thousand characters each.
"""

import io
import re
from dataclasses import dataclass
from pathlib import PurePath

from app.models import SourceKind

# A part aims for about TARGET characters (roughly one short lesson of source text)
# and never goes over MAX_CHARS. A heading starts a new part once the current one has MIN_CHARS.
TARGET_CHARS = 3000
MAX_CHARS = 6000
MIN_CHARS = 600

EXTENSIONS = {
    ".pdf": SourceKind.pdf,
    ".docx": SourceKind.docx,
    ".txt": SourceKind.text,
    ".md": SourceKind.text,
    ".markdown": SourceKind.text,
}


class MaterialError(ValueError):
    """The file cannot be used; the message is shown to the teacher as is."""


@dataclass
class Paragraph:
    text: str
    is_heading: bool = False


@dataclass
class Chunk:
    heading: str
    text: str


def detect_kind(filename: str) -> SourceKind:
    ext = PurePath(filename).suffix.lower()
    if ext == ".doc":
        raise MaterialError("Старый формат .doc не поддерживается. Сохраните файл в Word как .docx.")
    if ext not in EXTENSIONS:
        raise MaterialError("Поддерживаются файлы PDF, Word (.docx) и текст (.txt, .md).")
    return EXTENSIONS[ext]


# --- Extraction -----------------------------------------------------------------------

_NUMBERED_HEADING = re.compile(r"^(\d+(\.\d+)*[.)]?|глава|chapter|раздел|section|bob|mavzu)\s+\S", re.IGNORECASE)


def _looks_like_heading(line: str) -> bool:
    """PDF has no heading styles, so short title-like lines are treated as headings."""
    line = line.strip()
    if not line or len(line) > 90 or line[-1] in ".,;:!?":
        return False
    if _NUMBERED_HEADING.match(line):
        return True
    letters = [c for c in line if c.isalpha()]
    return len(letters) >= 4 and all(c.isupper() for c in letters)


def _split_plain(text: str, markdown: bool) -> list[Paragraph]:
    """Blank lines separate paragraphs; '#' lines (Markdown) or title-like lines are headings."""
    paragraphs: list[Paragraph] = []
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            paragraphs.append(Paragraph(" ".join(buffer)))
            buffer.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
        elif markdown and line.startswith("#"):
            flush()
            paragraphs.append(Paragraph(line.lstrip("#").strip(), is_heading=True))
        elif not markdown and not buffer and _looks_like_heading(line):
            paragraphs.append(Paragraph(line, is_heading=True))
        else:
            buffer.append(line)
    flush()
    return [p for p in paragraphs if p.text]


def _decode(data: bytes) -> str:
    # Russian and Uzbek texts from Windows often come in cp1251 rather than UTF-8.
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _extract_pdf(data: bytes) -> list[Paragraph]:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise MaterialError("PDF защищён паролем. Снимите защиту и загрузите снова.")
        pages = [page.extract_text() or "" for page in reader.pages]
    except PdfReadError as exc:
        raise MaterialError("Не удалось прочитать PDF: файл повреждён.") from exc
    return _split_plain("\n\n".join(pages), markdown=False)


def _extract_docx(data: bytes) -> list[Paragraph]:
    from docx import Document

    try:
        doc = Document(io.BytesIO(data))
    except Exception as exc:  # python-docx raises several unrelated types for broken files
        raise MaterialError("Не удалось прочитать файл Word: он повреждён или это не .docx.") from exc

    paragraphs: list[Paragraph] = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        style = (p.style.name if p.style is not None else "").lower()
        is_heading = style.startswith(("heading", "title", "заголовок", "название"))
        paragraphs.append(Paragraph(text, is_heading=is_heading))
    for table in doc.tables:
        rows = [" | ".join(cell.text.strip() for cell in row.cells) for row in table.rows]
        if rows:
            paragraphs.append(Paragraph("\n".join(rows)))
    return paragraphs


def extract_paragraphs(kind: SourceKind, filename: str, data: bytes) -> list[Paragraph]:
    if kind == SourceKind.pdf:
        paragraphs = _extract_pdf(data)
    elif kind == SourceKind.docx:
        paragraphs = _extract_docx(data)
    else:
        markdown = PurePath(filename).suffix.lower() in (".md", ".markdown")
        paragraphs = _split_plain(_decode(data), markdown=markdown)
    if not paragraphs:
        if kind == SourceKind.pdf:
            raise MaterialError("В PDF нет текста. Похоже, это скан: распознавание сканов добавим позже.")
        raise MaterialError("В файле нет текста.")
    return paragraphs


# --- Splitting into parts -------------------------------------------------------------

_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def _split_long(text: str) -> list[str]:
    """Cuts one oversized paragraph at sentence ends, or hard at MAX_CHARS as a last resort."""
    pieces: list[str] = []
    current = ""
    for sentence in _SENTENCE_END.split(text):
        while len(sentence) > MAX_CHARS:
            pieces.append(sentence[:MAX_CHARS])
            sentence = sentence[MAX_CHARS:]
        if current and len(current) + 1 + len(sentence) > TARGET_CHARS:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def split_into_chunks(paragraphs: list[Paragraph]) -> list[Chunk]:
    chunks: list[Chunk] = []
    heading = ""
    body: list[str] = []
    size = 0

    def flush() -> None:
        nonlocal body, size
        if body:
            chunks.append(Chunk(heading=heading, text="\n\n".join(body)))
        body, size = [], 0

    for p in paragraphs:
        if p.is_heading:
            if size >= MIN_CHARS:
                flush()
            if body:
                # A short section stays with the previous one; keep its heading visible in the text.
                body.append(p.text)
                size += len(p.text)
            else:
                heading = p.text
            continue
        for piece in _split_long(p.text) if len(p.text) > MAX_CHARS else [p.text]:
            if body and size + len(piece) > TARGET_CHARS:
                flush()
            body.append(piece)
            size += len(piece)
    flush()

    for chunk in chunks:
        if not chunk.heading:
            chunk.heading = chunk.text[:60].split("\n")[0]
        chunk.heading = chunk.heading[:300]
    return chunks


def parse_material(filename: str, data: bytes) -> tuple[SourceKind, list[Chunk]]:
    kind = detect_kind(filename)
    return kind, split_into_chunks(extract_paragraphs(kind, filename, data))

from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Role(StrEnum):
    admin = "admin"
    teacher = "teacher"
    student = "student"


class BlockType(StrEnum):
    text = "text"  # Markdown theory
    gif = "gif"  # URL of a GIF/WebP animation
    image = "image"  # URL of a picture
    video = "video"  # URL of a video
    viz = "viz"  # interactive 2D/3D visualization, JSON {"widget": ..., "params": ...} (app/widgets.py)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(128), default="")
    username: Mapped[str | None] = mapped_column(String(64))
    role: Mapped[Role] = mapped_column(String(16), default=Role.student)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Module(Base):
    """A theme of the course, e.g. "Statistics"."""

    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(Integer, default=0)

    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="module", cascade="all, delete-orphan", order_by="Lesson.position"
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0)
    # 1 basics, 2 practice, 3 hard.
    level: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    # Lessons the AI agent wrote stay hidden from students until a teacher publishes them.
    is_draft: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    module: Mapped[Module] = relationship(back_populates="lessons")
    blocks: Mapped[list["LessonBlock"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan", order_by="LessonBlock.position"
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan", order_by="Question.position"
    )


class LessonBlock(Base):
    __tablename__ = "lesson_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    type: Mapped[BlockType] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text, default="")
    caption: Mapped[str] = mapped_column(String(300), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)

    lesson: Mapped[Lesson] = relationship(back_populates="blocks")


class SourceKind(StrEnum):
    pdf = "pdf"
    docx = "docx"
    text = "text"  # .txt or .md
    image = "image"  # a single picture: a photo of a board, a scan, a diagram


class IndexStatus(StrEnum):
    pending = "pending"  # pictures are being read
    ready = "ready"
    failed = "failed"


class SourceStatus(StrEnum):
    parsed = "parsed"  # text extracted and split into parts
    generating = "generating"  # the AI agent is writing lessons
    draft_ready = "draft_ready"  # draft lessons are waiting for a teacher
    failed = "failed"


class SourceDocument(Base):
    """A file a teacher uploaded so the AI agent can turn it into lessons."""

    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(255))
    kind: Mapped[SourceKind] = mapped_column(String(16))
    status: Mapped[SourceStatus] = mapped_column(String(16), default=SourceStatus.parsed)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    # Progress of the AI agent and what went wrong, shown to the teacher.
    chunks_done: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error: Mapped[str] = mapped_column(Text, default="", server_default="")
    # Theme the lessons go to. Empty means the agent creates a new theme and stores it here.
    module_id: Mapped[int | None] = mapped_column(ForeignKey("modules.id", ondelete="SET NULL"))
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Reading the pictures (OCR and captions) and filling the knowledge base runs after the upload.
    index_status: Mapped[IndexStatus] = mapped_column(String(16), default=IndexStatus.pending, server_default="ready")
    images_done: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    chunks: Mapped[list["SourceChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="SourceChunk.position"
    )
    images: Mapped[list["SourceImage"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="SourceImage.number"
    )


class SourceChunk(Base):
    """One short part of an uploaded file, small enough for one AI request."""

    __tablename__ = "source_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str] = mapped_column(String(300), default="")
    text: Mapped[str] = mapped_column(Text)
    char_count: Mapped[int] = mapped_column(Integer)

    document: Mapped[SourceDocument] = relationship(back_populates="chunks")


class SourceImage(Base):
    """A picture from an uploaded file, with what the local vision models read from it."""

    __tablename__ = "source_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)  # the N of "[Рисунок N]" in the text
    path: Mapped[str] = mapped_column(String(300))  # under settings.media_dir
    caption: Mapped[str] = mapped_column(Text, default="")  # what is shown (Florence-2)
    ocr_text: Mapped[str] = mapped_column(Text, default="")  # text on the picture (Tesseract)

    document: Mapped[SourceDocument] = relationship(back_populates="images")

    @property
    def url(self) -> str:
        return f"/media/{self.path}"


class KnowledgeItem(Base):
    """One searchable piece of the knowledge base: a part of a file's text or a picture's description."""

    __tablename__ = "knowledge_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"), index=True)
    image_id: Mapped[int | None] = mapped_column(ForeignKey("source_images.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(300), default="")
    text: Mapped[str] = mapped_column(Text)
    # Normalised vector from the local embedding model; empty when the model is not installed.
    embedding: Mapped[list[float] | None] = mapped_column(JSON)


class QuestionKind(StrEnum):
    single = "single"  # exactly one correct option
    multiple = "multiple"  # one or more correct options, all must be picked


# Share of correct answers needed to pass a lesson test.
PASS_SCORE = 0.7


class Question(Base):
    """One question of a lesson's test."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[QuestionKind] = mapped_column(String(16), default=QuestionKind.single)
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSON)
    correct: Mapped[list[int]] = mapped_column(JSON)  # indexes into options
    # Shown after the answer: why the right option is right.
    explanation: Mapped[str] = mapped_column(Text, default="")

    lesson: Mapped[Lesson] = relationship(back_populates="questions")


class TestAttempt(Base):
    """A student's finished test; the next lesson unlocks from these once progress is added."""

    __tablename__ = "test_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    correct_count: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    passed: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

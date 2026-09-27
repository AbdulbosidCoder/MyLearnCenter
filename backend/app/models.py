from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, false, func
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

    chunks: Mapped[list["SourceChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="SourceChunk.position"
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

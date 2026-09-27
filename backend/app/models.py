from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
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

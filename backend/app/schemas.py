from pydantic import BaseModel, ConfigDict, Field

from app.models import BlockType, Role, SourceKind, SourceStatus


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserOut(ORM):
    id: int
    telegram_id: int
    first_name: str
    username: str | None
    role: Role


class RoleIn(BaseModel):
    role: Role


class ModuleIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    position: int = 0


class ModulePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    position: int | None = None


class ModuleOut(ORM):
    id: int
    title: str
    description: str
    position: int
    lesson_count: int = 0
    draft_count: int = 0


class LessonIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    position: int = 0
    level: int = Field(default=1, ge=1, le=3)
    is_draft: bool = False


class LessonPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    position: int | None = None
    level: int | None = Field(default=None, ge=1, le=3)
    is_draft: bool | None = None


class LessonShort(ORM):
    id: int
    title: str
    position: int
    level: int
    is_draft: bool


class ModuleDetail(ModuleOut):
    lessons: list[LessonShort]


class BlockIn(BaseModel):
    type: BlockType
    content: str = ""
    caption: str = Field(default="", max_length=300)
    position: int = 0


class BlockPatch(BaseModel):
    type: BlockType | None = None
    content: str | None = None
    caption: str | None = Field(default=None, max_length=300)
    position: int | None = None


class BlockOut(ORM):
    id: int
    type: BlockType
    content: str
    caption: str
    position: int


class LessonDetail(ORM):
    id: int
    module_id: int
    module_title: str
    title: str
    position: int
    level: int
    is_draft: bool
    blocks: list[BlockOut]
    prev_lesson_id: int | None
    next_lesson_id: int | None


class MaterialOut(ORM):
    id: int
    title: str
    filename: str
    kind: SourceKind
    status: SourceStatus
    char_count: int
    chunks_done: int
    error: str
    module_id: int | None
    chunk_count: int = 0


class ChunkOut(ORM):
    id: int
    position: int
    heading: str
    text: str
    char_count: int


class MaterialDetail(MaterialOut):
    chunks: list[ChunkOut]

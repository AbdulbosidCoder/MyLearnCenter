from pydantic import BaseModel, ConfigDict, Field

from app.models import BlockType, Role


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


class LessonIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    position: int = 0


class LessonPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    position: int | None = None


class LessonShort(ORM):
    id: int
    title: str
    position: int


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
    blocks: list[BlockOut]
    prev_lesson_id: int | None
    next_lesson_id: int | None

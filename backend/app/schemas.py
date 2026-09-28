from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import BlockType, QuestionKind, Role, SourceKind, SourceStatus
from app.progress import LessonState
from app.widgets import parse_viz


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
    # For the current user: done, open or locked (see app/progress.py).
    state: LessonState = LessonState.open
    has_test: bool = False


class ModuleDetail(ModuleOut):
    lessons: list[LessonShort]


class BlockIn(BaseModel):
    type: BlockType
    content: str = ""
    caption: str = Field(default="", max_length=300)
    position: int = 0

    @model_validator(mode="after")
    def _check_viz(self):
        if self.type == BlockType.viz:
            parse_viz(self.content)
        return self


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
    question_count: int
    state: LessonState
    blocks: list[BlockOut]
    prev_lesson_id: int | None
    next_lesson_id: int | None
    # False while this lesson's test is not passed and it blocks the next lesson.
    next_unlocked: bool


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


class QuestionIn(BaseModel):
    kind: QuestionKind = QuestionKind.single
    prompt: str = Field(min_length=1)
    options: list[str] = Field(min_length=2, max_length=8)
    correct: list[int] = Field(min_length=1)
    explanation: str = ""
    position: int = 0

    @model_validator(mode="after")
    def _check_answers(self):
        if any(not 0 <= i < len(self.options) for i in self.correct) or len(set(self.correct)) != len(self.correct):
            raise ValueError("correct must list distinct option indexes")
        if self.kind == QuestionKind.single and len(self.correct) != 1:
            raise ValueError("a single-choice question has exactly one correct option")
        return self


class QuestionOut(ORM):
    """What a student sees before answering: no correct options, no explanation."""

    id: int
    position: int
    kind: QuestionKind
    prompt: str
    options: list[str]


class QuestionFull(QuestionOut):
    correct: list[int]
    explanation: str


class QuizOut(BaseModel):
    lesson_id: int
    pass_score: float
    # Editors get QuestionFull (with answers), students get QuestionOut.
    questions: list[QuestionFull | QuestionOut]


class QuizSubmit(BaseModel):
    # question id -> picked option indexes
    answers: dict[int, list[int]]


class AnswerResult(BaseModel):
    question_id: int
    is_correct: bool
    correct: list[int]
    explanation: str


class QuizResult(BaseModel):
    correct_count: int
    total: int
    passed: bool
    results: list[AnswerResult]
    module_id: int
    # The lesson after this one, when the student may open it now.
    next_lesson_id: int | None = None


class RewriteMode(StrEnum):
    simpler = "simpler"
    example = "example"
    shorter = "shorter"
    custom = "custom"


class RewriteIn(BaseModel):
    mode: RewriteMode
    # The teacher's own request for mode "custom", e.g. "объясни через футбол".
    instruction: str = Field(default="", max_length=500)


class RewriteOut(BaseModel):
    text: str


class WidgetOut(BaseModel):
    name: str
    title: str
    params: dict


class QuestOut(BaseModel):
    key: str
    title: str
    value: int
    goal: int


class StatsOut(BaseModel):
    xp_total: int
    xp_today: int
    streak: int
    tests_passed: int
    quests: list[QuestOut]


class RatingRow(BaseModel):
    place: int
    name: str
    xp: int
    is_me: bool


class LeaderboardOut(BaseModel):
    rows: list[RatingRow]
    me: RatingRow | None
    total: int

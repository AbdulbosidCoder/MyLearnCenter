from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app import notify
from app.deps import EDITOR, CurrentUser, Session
from app.models import PASS_SCORE, Lesson, Module, Question, Role, TestAttempt, User
from app.progress import LessonState, is_locked, lesson_states, passed_lessons
from app.schemas import AnswerResult, QuestionFull, QuestionIn, QuestionOut, QuizOut, QuizResult, QuizSubmit

router = APIRouter(tags=["quiz"])


def _is_editor(user: User) -> bool:
    return user.role in (Role.admin, Role.teacher)


async def _lesson_for(session: Session, lesson_id: int, user: User) -> Lesson:
    lesson = await session.get(Lesson, lesson_id)
    if lesson is None or (lesson.is_draft and not _is_editor(user)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    if await is_locked(session, user, lesson):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Сначала сдайте тест предыдущего урока")
    return lesson


async def _questions(session: Session, lesson_id: int) -> list[Question]:
    return list(
        await session.scalars(
            select(Question).where(Question.lesson_id == lesson_id).order_by(Question.position, Question.id)
        )
    )


@router.get("/lessons/{lesson_id}/quiz", response_model=QuizOut)
async def get_quiz(lesson_id: int, session: Session, user: CurrentUser):
    await _lesson_for(session, lesson_id, user)
    shape = QuestionFull if _is_editor(user) else QuestionOut
    questions = [shape.model_validate(q) for q in await _questions(session, lesson_id)]
    return QuizOut(lesson_id=lesson_id, pass_score=PASS_SCORE, questions=questions)


@router.post("/lessons/{lesson_id}/quiz", response_model=QuizResult)
async def submit_quiz(lesson_id: int, body: QuizSubmit, session: Session, user: CurrentUser):
    lesson = await _lesson_for(session, lesson_id, user)
    questions = await _questions(session, lesson_id)
    if not questions:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This lesson has no test")

    results = []
    for q in questions:
        picked = sorted(set(body.answers.get(q.id, [])))
        results.append(
            AnswerResult(
                question_id=q.id,
                is_correct=picked == sorted(q.correct),
                correct=q.correct,
                explanation=q.explanation,
            )
        )
    correct_count = sum(r.is_correct for r in results)
    passed = correct_count >= PASS_SCORE * len(questions)
    first_pass = passed and not await passed_lessons(session, user.id, [lesson_id])
    session.add(
        TestAttempt(user_id=user.id, lesson_id=lesson_id, correct_count=correct_count, total=len(questions), passed=passed)
    )
    await session.commit()
    if first_pass and not _is_editor(user):
        await _announce_pass(session, user, lesson_id, f"{correct_count} из {len(questions)}")
    return QuizResult(
        correct_count=correct_count,
        total=len(questions),
        passed=passed,
        results=results,
        module_id=lesson.module_id,
        next_lesson_id=await _next_open(session, user, lesson),
    )


async def _next_open(session: Session, user: User, lesson: Lesson) -> int | None:
    lessons = list(
        await session.scalars(
            select(Lesson)
            .where(Lesson.module_id == lesson.module_id, Lesson.is_draft.is_(False))
            .order_by(Lesson.position, Lesson.id)
        )
    )
    ids = [sib.id for sib in lessons]
    if lesson.id not in ids or ids[-1] == lesson.id:
        return None
    following = ids[ids.index(lesson.id) + 1]
    states = await lesson_states(session, user, lessons)
    return None if states[following] == LessonState.locked else following


async def _announce_pass(session: Session, user: User, lesson_id: int, score: str) -> None:
    """Tells the student what opened next, and teachers who passed what."""
    lesson = await session.get(Lesson, lesson_id)
    module = await session.get(Module, lesson.module_id)
    lessons = list(
        await session.scalars(
            select(Lesson).where(Lesson.module_id == module.id, Lesson.is_draft.is_(False)).order_by(Lesson.position, Lesson.id)
        )
    )
    states = await lesson_states(session, user, lessons)
    with_test = set(
        await session.scalars(select(Question.lesson_id).where(Question.lesson_id.in_([sib.id for sib in lessons])))
    )
    theme_done = all(states[sib.id] == LessonState.done for sib in lessons if sib.id in with_test)
    ids = [sib.id for sib in lessons]
    following = lessons[ids.index(lesson_id) + 1] if ids.index(lesson_id) + 1 < len(ids) else None

    if theme_done:
        notify.send([user.telegram_id], f"🎉 Тема «{module.title}» пройдена полностью! Выберите следующую тему.")
    elif following is not None:
        notify.send([user.telegram_id], f"✅ Тест урока «{lesson.title}» сдан. Открыт следующий урок: «{following.title}».")

    teachers = await notify.telegram_ids(session, Role.admin, Role.teacher)
    text = f"🎓 Тест урока «{lesson.title}» ({module.title}) сдан: {user.first_name or 'студент'}, {score}."
    if theme_done:
        text += f"\nВся тема «{module.title}» пройдена."
    notify.send(teachers, text)


@router.post("/lessons/{lesson_id}/questions", response_model=QuestionFull, status_code=201, dependencies=[EDITOR])
async def create_question(lesson_id: int, body: QuestionIn, session: Session):
    if await session.get(Lesson, lesson_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    question = Question(lesson_id=lesson_id, **body.model_dump())
    session.add(question)
    await session.commit()
    return question


@router.delete("/questions/{question_id}", status_code=204, dependencies=[EDITOR])
async def delete_question(question_id: int, session: Session):
    question = await session.get(Question, question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    await session.delete(question)
    await session.commit()
    return Response(status_code=204)

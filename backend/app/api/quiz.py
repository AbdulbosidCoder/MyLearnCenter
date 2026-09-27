from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.deps import EDITOR, CurrentUser, Session
from app.models import PASS_SCORE, Lesson, Question, Role, TestAttempt, User
from app.schemas import AnswerResult, QuestionFull, QuestionIn, QuestionOut, QuizOut, QuizResult, QuizSubmit

router = APIRouter(tags=["quiz"])


def _is_editor(user: User) -> bool:
    return user.role in (Role.admin, Role.teacher)


async def _lesson_for(session: Session, lesson_id: int, user: User) -> Lesson:
    lesson = await session.get(Lesson, lesson_id)
    if lesson is None or (lesson.is_draft and not _is_editor(user)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
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
    await _lesson_for(session, lesson_id, user)
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
    session.add(
        TestAttempt(user_id=user.id, lesson_id=lesson_id, correct_count=correct_count, total=len(questions), passed=passed)
    )
    await session.commit()
    return QuizResult(correct_count=correct_count, total=len(questions), passed=passed, results=results)


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

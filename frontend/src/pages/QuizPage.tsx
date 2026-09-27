import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api, type Question, type QuizResult } from "../api";
import { BackButton } from "../components/BackButton";
import { Markdown } from "../components/Markdown";
import { ErrorBox, Loading } from "../components/Status";
import { canEdit, useLoad, useUser } from "../hooks";
import { confirmAction } from "../telegram";

export default function QuizPage() {
  const lessonId = Number(useParams().id);
  const user = useUser();
  const { data: quiz, error, reload } = useLoad(() => api.quiz(lessonId), [lessonId]);
  const [answers, setAnswers] = useState<Record<number, number[]>>({});
  const [result, setResult] = useState<QuizResult | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  if (error) return <ErrorBox message={error} />;
  if (!quiz) return <Loading />;

  function pick(q: Question, option: number) {
    if (result) return;
    setAnswers((prev) => {
      const current = prev[q.id] ?? [];
      if (q.kind === "single") return { ...prev, [q.id]: [option] };
      const next = current.includes(option) ? current.filter((o) => o !== option) : [...current, option];
      return { ...prev, [q.id]: next };
    });
  }

  async function submit() {
    setSubmitError(null);
    try {
      setResult(await api.submitQuiz(lessonId, answers));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setSubmitError((err as Error).message);
    }
  }

  function retry() {
    setAnswers({});
    setResult(null);
  }

  const answered = quiz.questions.filter((q) => (answers[q.id] ?? []).length > 0).length;

  return (
    <>
      <BackButton to={`/lessons/${lessonId}`} />
      <Link to={`/lessons/${lessonId}`} className="muted small">
        ← К уроку
      </Link>
      <h1>Тест по уроку</h1>

      {result && (
        <div className={`card result ${result.passed ? "passed" : "failed"}`}>
          <strong>{result.passed ? "🎉 Тест пройден!" : "Пока не получилось"}</strong>
          <span className="block">
            Верно {result.correct_count} из {result.total}. Нужно не меньше {Math.ceil(quiz.pass_score * result.total)}.
          </span>
          {!result.passed && <span className="muted small block">Посмотрите объяснения ниже и попробуйте ещё раз.</span>}
        </div>
      )}

      <ol className="list">
        {quiz.questions.map((q, i) => {
          const verdict = result?.results.find((r) => r.question_id === q.id);
          const shownCorrect = verdict?.correct ?? q.correct;
          const explanation = verdict?.explanation ?? q.explanation;
          return (
            <li key={q.id} className="card question">
              <div className="theory">
                <Markdown>{`**${i + 1}.** ${q.prompt}`}</Markdown>
              </div>
              {q.kind === "multiple" && <span className="muted small">Выберите все верные варианты.</span>}
              <div className="options">
                {q.options.map((option, o) => {
                  const picked = (answers[q.id] ?? []).includes(o);
                  const isCorrect = shownCorrect?.includes(o);
                  const state = verdict
                    ? isCorrect
                      ? "right"
                      : picked
                        ? "wrong"
                        : ""
                    : !result && q.correct && isCorrect
                      ? "right"
                      : "";
                  return (
                    <button key={o} type="button" className={`option ${picked ? "picked" : ""} ${state}`} onClick={() => pick(q, o)}>
                      <Markdown>{option}</Markdown>
                    </button>
                  );
                })}
              </div>
              {verdict && <strong className={verdict.is_correct ? "ok" : "error"}>{verdict.is_correct ? "Верно" : "Неверно"}</strong>}
              {(verdict || q.correct) && explanation && (
                <div className="muted small theory">
                  <Markdown>{explanation}</Markdown>
                </div>
              )}
              {canEdit(user) && (
                <button
                  className="danger small"
                  onClick={async () => {
                    if (await confirmAction("Удалить этот вопрос?")) {
                      await api.deleteQuestion(q.id);
                      reload();
                    }
                  }}
                >
                  Удалить вопрос
                </button>
              )}
            </li>
          );
        })}
      </ol>

      {submitError && <ErrorBox message={submitError} />}
      <nav className="pager">
        {result ? (
          <>
            <button className="button secondary" onClick={retry}>
              Пройти ещё раз
            </button>
            <Link className="button" to={`/lessons/${lessonId}`}>
              К уроку
            </Link>
          </>
        ) : (
          <button onClick={submit} disabled={answered < quiz.questions.length}>
            Проверить ({answered} из {quiz.questions.length})
          </button>
        )}
      </nav>
    </>
  );
}

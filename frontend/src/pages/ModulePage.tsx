import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, type LessonShort } from "../api";
import { BackButton } from "../components/BackButton";
import { ErrorBox, Loading } from "../components/Status";
import { canEdit, useLoad, useUser } from "../hooks";
import { confirmAction } from "../telegram";

export const LEVEL_NAMES: Record<number, string> = { 1: "Уровень 1 · основы", 2: "Уровень 2 · практика", 3: "Уровень 3 · сложно" };

export default function ModulePage() {
  const id = Number(useParams().id);
  const user = useUser();
  const navigate = useNavigate();
  const { data: module, error, reload } = useLoad(() => api.module(id), [id]);

  return (
    <>
      <BackButton to="/" />
      <Link to="/" className="muted small">
        ← Все темы
      </Link>
      {error && <ErrorBox message={error} />}
      {!module && !error && <Loading />}
      {module && (
        <>
          <h1>{module.title}</h1>
          {module.description && <p className="muted">{module.description}</p>}

          <ol className="list">
            {module.lessons.map((lesson, i) => (
              <li key={lesson.id} className={`card lesson-${lesson.state}`}>
                <LessonRow lesson={lesson} index={i} />
                {canEdit(user) && (
                  <button
                    className="danger small"
                    onClick={async () => {
                      if (await confirmAction(`Удалить урок «${lesson.title}»?`)) {
                        await api.deleteLesson(lesson.id);
                        reload();
                      }
                    }}
                  >
                    Удалить
                  </button>
                )}
              </li>
            ))}
          </ol>
          {module.lessons.length === 0 && <p className="muted">В этой теме пока нет уроков.</p>}

          {canEdit(user) && module.draft_count > 0 && (
            <div className="card agent-card">
              <strong>Черновиков: {module.draft_count}</strong>
              <span className="muted small">Их написал ИИ. Студенты не видят черновики, пока вы не опубликуете тему.</span>
              <button
                onClick={async () => {
                  if (await confirmAction(`Опубликовать ${module.draft_count} черновик(ов) для студентов?`)) {
                    await api.publishModule(module.id);
                    reload();
                  }
                }}
              >
                Опубликовать
              </button>
            </div>
          )}

          {canEdit(user) && <NewLessonForm moduleId={id} position={module.lessons.length} onCreated={reload} />}
          {canEdit(user) && (
            <button
              className="danger small"
              onClick={async () => {
                if (await confirmAction(`Удалить тему «${module.title}» со всеми уроками?`)) {
                  await api.deleteModule(module.id);
                  navigate("/");
                }
              }}
            >
              Удалить тему
            </button>
          )}
        </>
      )}
    </>
  );
}

function NewLessonForm({ moduleId, position, onCreated }: { moduleId: number; position: number; onCreated: () => void }) {
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api.createLesson(moduleId, { title, position });
      setTitle("");
      onCreated();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h3>Новый урок</h3>
      <input placeholder="Название урока" value={title} onChange={(e) => setTitle(e.target.value)} required />
      {error && <ErrorBox message={error} />}
      <button type="submit">Добавить урок</button>
    </form>
  );
}

function LessonRow({ lesson, index }: { lesson: LessonShort; index: number }) {
  const body = (
    <>
      <span className="num">{lesson.state === "done" ? "✓" : lesson.state === "locked" ? "🔒" : index + 1}</span>
      <span className="grow">
        {lesson.title}
        <span className="muted small block">
          {LEVEL_NAMES[lesson.level] ?? `Уровень ${lesson.level}`}
          {lesson.is_draft && " · черновик"}
          {lesson.state === "done" && " · тест сдан"}
          {lesson.state === "locked" && " · откроется после теста предыдущего урока"}
        </span>
      </span>
    </>
  );
  if (lesson.state === "locked") {
    return (
      <div className="row" aria-disabled="true">
        {body}
      </div>
    );
  }
  return (
    <Link to={`/lessons/${lesson.id}`} className="row">
      {body}
      <span className="muted">›</span>
    </Link>
  );
}

import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import { BackButton } from "../components/BackButton";
import { ErrorBox, Loading } from "../components/Status";
import { canEdit, useLoad, useUser } from "../hooks";
import { confirmAction } from "../telegram";

export default function ModulePage() {
  const id = Number(useParams().id);
  const user = useUser();
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
              <li key={lesson.id} className="card">
                <Link to={`/lessons/${lesson.id}`} className="row">
                  <span className="num">{i + 1}</span>
                  <span className="grow">{lesson.title}</span>
                  <span className="muted">›</span>
                </Link>
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

          {canEdit(user) && <NewLessonForm moduleId={id} position={module.lessons.length} onCreated={reload} />}
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

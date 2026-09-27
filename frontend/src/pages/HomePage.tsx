import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { ErrorBox, Loading } from "../components/Status";
import { canEdit, useLoad, useUser } from "../hooks";
import { confirmAction } from "../telegram";

const ROLE_NAMES = { admin: "Администратор", teacher: "Преподаватель", student: "Студент" };

export default function HomePage() {
  const user = useUser();
  const { data: modules, error, reload } = useLoad(api.modules, []);

  return (
    <>
      <header className="hero">
        <div>
          <h1>Привет, {user.first_name}!</h1>
          <p className="muted">Data Science шаг за шагом</p>
        </div>
        <span className={`badge role-${user.role}`}>{ROLE_NAMES[user.role]}</span>
      </header>

      {user.role === "admin" && (
        <Link to="/admin" className="card link-card">
          👥 Пользователи и роли
        </Link>
      )}

      <h2>Темы</h2>
      {error && <ErrorBox message={error} />}
      {!modules && !error && <Loading />}
      {modules?.length === 0 && <p className="muted">Тем пока нет.</p>}
      <ol className="list">
        {modules?.map((m, i) => (
          <li key={m.id} className="card">
            <Link to={`/modules/${m.id}`} className="row">
              <span className="num">{i + 1}</span>
              <span className="grow">
                <strong>{m.title}</strong>
                {m.description && <span className="muted small block">{m.description}</span>}
              </span>
              <span className="muted small">{m.lesson_count} ур.</span>
            </Link>
            {canEdit(user) && (
              <button
                className="danger small"
                onClick={async () => {
                  if (await confirmAction(`Удалить тему «${m.title}» со всеми уроками?`)) {
                    await api.deleteModule(m.id);
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

      {canEdit(user) && modules && <NewModuleForm position={modules.length} onCreated={reload} />}
    </>
  );
}

function NewModuleForm({ position, onCreated }: { position: number; onCreated: () => void }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api.createModule({ title, description, position });
      setTitle("");
      setDescription("");
      onCreated();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h3>Новая тема</h3>
      <input placeholder="Название" value={title} onChange={(e) => setTitle(e.target.value)} required />
      <textarea placeholder="Короткое описание" value={description} onChange={(e) => setDescription(e.target.value)} />
      {error && <ErrorBox message={error} />}
      <button type="submit">Добавить тему</button>
    </form>
  );
}

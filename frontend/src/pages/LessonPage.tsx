import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { api, type BlockType } from "../api";
import { BackButton } from "../components/BackButton";
import { AiRewrite } from "../components/AiRewrite";
import { BlockView } from "../components/BlockView";
import { ErrorBox, Loading } from "../components/Status";
import { canEdit, useLoad, useUser } from "../hooks";
import { confirmAction } from "../telegram";
import { LEVEL_NAMES } from "./ModulePage";

export default function LessonPage() {
  const id = Number(useParams().id);
  const user = useUser();
  const { data: lesson, error, reload } = useLoad(() => api.lesson(id), [id]);

  if (error) return <ErrorBox message={error} />;
  if (!lesson) return <Loading />;

  return (
    <>
      <BackButton to={`/modules/${lesson.module_id}`} />
      <Link to={`/modules/${lesson.module_id}`} className="muted small">
        ← {lesson.module_title}
      </Link>
      <h1>{lesson.title}</h1>
      <p className="muted small">
        {LEVEL_NAMES[lesson.level] ?? `Уровень ${lesson.level}`}
        {lesson.is_draft && " · черновик, студенты его пока не видят"}
      </p>

      {lesson.blocks.length === 0 && <p className="muted">В уроке пока нет материалов.</p>}
      {lesson.blocks.map((block) => (
        <section key={block.id} className="lesson-block">
          <BlockView block={block} />
          {canEdit(user) && block.type === "text" && <AiRewrite block={block} onSaved={reload} />}
          {canEdit(user) && (
            <button
              className="danger small"
              onClick={async () => {
                if (await confirmAction("Удалить этот блок?")) {
                  await api.deleteBlock(block.id);
                  reload();
                }
              }}
            >
              Удалить блок
            </button>
          )}
        </section>
      ))}

      {lesson.question_count > 0 && (
        <Link to={`/lessons/${lesson.id}/quiz`} className="card link-card quiz-link">
          <strong>{lesson.state === "done" ? "✅ Тест сдан" : "✍️ Тест по уроку"}</strong>
          <span className="muted small block">Вопросов: {lesson.question_count}. Для прохождения нужно 70% верных ответов.</span>
        </Link>
      )}

      {canEdit(user) && <NewBlockForm lessonId={id} position={lesson.blocks.length} onCreated={reload} />}

      <nav className="pager">
        {lesson.prev_lesson_id ? (
          <Link className="button secondary" to={`/lessons/${lesson.prev_lesson_id}`}>
            ← Назад
          </Link>
        ) : (
          <span />
        )}
        {lesson.next_lesson_id && lesson.next_unlocked ? (
          <Link className="button" to={`/lessons/${lesson.next_lesson_id}`}>
            Следующий урок →
          </Link>
        ) : lesson.next_lesson_id ? (
          <Link className="button" to={`/lessons/${lesson.id}/quiz`}>
            🔒 Сдайте тест, чтобы идти дальше
          </Link>
        ) : (
          <Link className="button" to={`/modules/${lesson.module_id}`}>
            Тема пройдена ✓
          </Link>
        )}
      </nav>
    </>
  );
}

const BLOCK_LABELS: Record<BlockType, string> = {
  text: "Теория (Markdown)",
  gif: "GIF-анимация (ссылка)",
  image: "Картинка (ссылка)",
  video: "Видео (ссылка)",
  viz: "Визуализация 2D/3D",
};

function NewBlockForm({ lessonId, position, onCreated }: { lessonId: number; position: number; onCreated: () => void }) {
  const [type, setType] = useState<BlockType>("text");
  const { data: widgets } = useLoad(api.widgets, []);
  const [content, setContent] = useState("");
  const [caption, setCaption] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api.createBlock(lessonId, { type, content, caption, position });
      setContent("");
      setCaption("");
      onCreated();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h3>Добавить блок</h3>
      <select
        value={type}
        onChange={(e) => {
          setType(e.target.value as BlockType);
          setContent("");
        }}
      >
        {Object.entries(BLOCK_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      {type === "text" ? (
        <textarea
          rows={6}
          placeholder="# Заголовок&#10;&#10;Текст теории…"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          required
        />
      ) : type === "viz" ? (
        <>
          <select value={content} onChange={(e) => setContent(e.target.value)} required>
            <option value="">Выберите визуализацию</option>
            {widgets?.map((w) => (
              <option key={w.name} value={JSON.stringify({ widget: w.name, params: w.params })}>
                {w.title}
              </option>
            ))}
          </select>
          <input placeholder="Подпись (необязательно)" value={caption} onChange={(e) => setCaption(e.target.value)} />
        </>
      ) : (
        <>
          <input type="url" placeholder="https://…" value={content} onChange={(e) => setContent(e.target.value)} required />
          <input placeholder="Подпись (необязательно)" value={caption} onChange={(e) => setCaption(e.target.value)} />
        </>
      )}
      {error && <ErrorBox message={error} />}
      <button type="submit">Добавить</button>
    </form>
  );
}

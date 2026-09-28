import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, type MaterialDetail } from "../api";
import { BackButton } from "../components/BackButton";
import { ErrorBox, Loading } from "../components/Status";
import { useLoad } from "../hooks";
import { confirmAction } from "../telegram";
import { formatChars } from "./MaterialsPage";

export default function MaterialPage() {
  const id = Number(useParams().id);
  const navigate = useNavigate();
  const { data: material, error, reload } = useLoad(() => api.material(id), [id]);

  // While the AI agent works, refresh every few seconds to move the progress bar.
  const generating = material?.status === "generating" || material?.index_status === "pending";
  useEffect(() => {
    if (!generating) return;
    const timer = setInterval(reload, 3000);
    return () => clearInterval(timer);
  }, [generating, reload]);

  return (
    <>
      <BackButton to="/materials" />
      <Link to="/materials" className="muted small">
        ← Материалы
      </Link>
      {error && <ErrorBox message={error} />}
      {!material && !error && <Loading />}
      {material && (
        <>
          <h1>{material.title}</h1>
          <p className="muted small">
            {material.filename} · частей: {material.chunk_count} · {formatChars(material.char_count)}
          </p>

          <AgentCard material={material} onStarted={reload} />

          {material.images.length > 0 && (
            <>
              <h2>Рисунки</h2>
              <p className="muted small">
                Их прочитали локальные модели: Florence-2 описывает, что изображено, Tesseract читает текст. Агент вставит
                подходящие рисунки в уроки.
              </p>
              <ul className="figures">
                {material.images.map((img) => (
                  <li key={img.id} className="card figure">
                    <img src={img.url} alt={`Рисунок ${img.number}`} loading="lazy" />
                    <div className="grow">
                      <strong>Рисунок {img.number}</strong>
                      {img.caption && <span className="small block">{img.caption}</span>}
                      {img.ocr_text && <span className="muted small block ocr">Текст: {img.ocr_text}</span>}
                      {!img.caption && !img.ocr_text && (
                        <span className="muted small block">
                          {material.index_status === "pending" ? "Читается…" : "Ничего не прочитано."}
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}

          <h2>Части файла</h2>
          <ol className="list">
            {material.chunks.map((c) => (
              <li key={c.id} className="card">
                <details>
                  <summary>
                    <strong>
                      {c.position + 1}. {c.heading}
                    </strong>
                    <span className="muted small"> · {formatChars(c.char_count)}</span>
                  </summary>
                  <p className="chunk-text">{c.text}</p>
                </details>
              </li>
            ))}
          </ol>

          <button
            className="danger small"
            onClick={async () => {
              if (await confirmAction(`Удалить материал «${material.title}»? Созданные уроки останутся.`)) {
                await api.deleteMaterial(material.id);
                navigate("/materials");
              }
            }}
          >
            Удалить материал
          </button>
        </>
      )}
    </>
  );
}

function AgentCard({ material, onStarted }: { material: MaterialDetail; onStarted: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      await api.generateLessons(material.id);
      onStarted();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (material.index_status === "pending") {
    return (
      <div className="card agent-card">
        <strong>🔎 ИИ изучает рисунки…</strong>
        <progress value={material.images_done} max={Math.max(material.image_count, 1)} />
        <span className="muted small">
          Прочитано рисунков: {material.images_done} из {material.image_count}. Потом материал попадёт в базу знаний, и
          можно будет создавать уроки.
        </span>
      </div>
    );
  }

  if (material.status === "generating") {
    return (
      <div className="card agent-card">
        <strong>🤖 ИИ пишет уроки…</strong>
        <progress value={material.chunks_done} max={material.chunk_count} />
        <span className="muted small">
          Прочитано частей: {material.chunks_done} из {material.chunk_count}. Можно закрыть страницу, работа продолжится.
        </span>
      </div>
    );
  }

  return (
    <div className="card agent-card">
      {material.status === "draft_ready" && material.module_id !== null && (
        <>
          <strong>✅ Черновик уроков готов</strong>
          <span className="muted small">Проверьте уроки и опубликуйте тему, тогда студенты их увидят.</span>
          {material.error && <span className="muted small">{material.error}</span>}
          <Link to={`/modules/${material.module_id}`} className="button">
            Открыть черновик
          </Link>
        </>
      )}
      {material.status === "failed" && <ErrorBox message={`ИИ не справился: ${material.error}`} />}
      {material.status === "parsed" && (
        <span className="muted small">
          ИИ прочитает каждую часть, разобьёт её на короткие уроки по 3–5 минут, выставит уровень 1–3 и соберёт тему.
          Уроки появятся черновиком: студенты увидят их только после публикации.
        </span>
      )}
      {error && <ErrorBox message={error} />}
      {material.status !== "draft_ready" && (
        <button onClick={start} disabled={busy}>
          {material.status === "failed" ? "🤖 Попробовать снова" : "🤖 Создать уроки с ИИ"}
        </button>
      )}
      {material.index_status === "failed" && (
        <ErrorBox message="Не удалось прочитать рисунки. Уроки можно создать и без них." />
      )}
      <button
        className="secondary small"
        onClick={async () => {
          await api.reindexMaterial(material.id);
          onStarted();
        }}
      >
        Прочитать рисунки заново
      </button>
    </div>
  );
}

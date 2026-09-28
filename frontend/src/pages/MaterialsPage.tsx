import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { api, type Material } from "../api";
import { BackButton } from "../components/BackButton";
import { ErrorBox, Loading } from "../components/Status";
import { canEdit, useLoad, useUser } from "../hooks";

const KIND_NAMES: Record<Material["kind"], string> = { pdf: "PDF", docx: "Word", text: "Текст", image: "Картинка" };
const STATUS_NAMES: Record<Material["status"], string> = {
  parsed: "",
  generating: "ИИ пишет уроки…",
  draft_ready: "черновик готов",
  failed: "ошибка ИИ",
};

export function formatChars(n: number): string {
  return n >= 1000 ? `${Math.round(n / 1000)} тыс. знаков` : `${n} знаков`;
}

export default function MaterialsPage() {
  const user = useUser();
  const { data: materials, error, reload } = useLoad(api.materials, []);

  if (!canEdit(user)) return <ErrorBox message="Эта страница только для преподавателей." />;

  return (
    <>
      <BackButton to="/" />
      <Link to="/" className="muted small">
        ← Главная
      </Link>
      <h1>Материалы для ИИ</h1>
      <p className="muted small">
        Загрузите тему файлом любого размера: PDF, Word, текст или картинку. Система достанет текст и рисунки,
        прочитает рисунки и сканы и разрежет всё на короткие части. Из них ИИ-агент соберёт уроки, уровни и тесты.
      </p>

      <ModelsCard />
      <UploadForm onUploaded={reload} />

      <h2>Загруженные файлы</h2>
      {error && <ErrorBox message={error} />}
      {!materials && !error && <Loading />}
      {materials?.length === 0 && <p className="muted">Пока ничего не загружено.</p>}
      <ul className="list">
        {materials?.map((m) => (
          <li key={m.id} className="card">
            <Link to={`/materials/${m.id}`} className="row">
              <span className="grow">
                <strong>{m.title}</strong>
                <span className="muted small block">
                  {KIND_NAMES[m.kind]} · частей: {m.chunk_count} · {formatChars(m.char_count)}
                  {m.image_count > 0 && ` · рисунков: ${m.image_count}`}
                  {m.index_status === "pending" && " · ИИ изучает рисунки…"}
                  {STATUS_NAMES[m.status] && ` · ${STATUS_NAMES[m.status]}`}
                </span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}

/** Which local models work on this server, so a teacher knows what the agent can read. */
function ModelsCard() {
  const { data: status } = useLoad(api.aiStatus, []);
  if (!status) return null;
  const rows = [
    { on: status.claude, name: "Claude", about: "пишет уроки и тесты" },
    { on: Boolean(status.ocr_languages), name: "Tesseract", about: `читает текст на рисунках и сканах${status.ocr_languages ? ` (${status.ocr_languages})` : ""}` },
    { on: status.captions, name: "Florence-2", about: "описывает графики, схемы и таблицы" },
    { on: status.embeddings, name: "multilingual-e5", about: "ищет нужные части материала по смыслу" },
  ];
  return (
    <div className="card models">
      {rows.map((r) => (
        <span key={r.name} className={r.on ? "on" : "off"}>
          {r.on ? "✓" : "✕"} <strong>{r.name}</strong> {r.about}
        </span>
      ))}
    </div>
  );
}

function UploadForm({ onUploaded }: { onUploaded: () => void }) {
  const { data: modules } = useLoad(api.modules, []);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [moduleId, setModuleId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inputKey, setInputKey] = useState(0);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await api.uploadMaterial(file, title, moduleId ? Number(moduleId) : null);
      setFile(null);
      setTitle("");
      setInputKey((k) => k + 1);
      onUploaded();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h3>Новый материал</h3>
      <input
        key={inputKey}
        type="file"
        accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        required
      />
      <input placeholder="Название (по умолчанию имя файла)" value={title} onChange={(e) => setTitle(e.target.value)} />
      <select value={moduleId} onChange={(e) => setModuleId(e.target.value)}>
        <option value="">Для новой темы</option>
        {modules?.map((m) => (
          <option key={m.id} value={m.id}>
            Для темы «{m.title}»
          </option>
        ))}
      </select>
      {error && <ErrorBox message={error} />}
      <button type="submit" disabled={!file || busy}>
        {busy ? "Читаю файл…" : "Загрузить"}
      </button>
    </form>
  );
}

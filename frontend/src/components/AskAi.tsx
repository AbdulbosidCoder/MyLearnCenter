import { useEffect, useState, type FormEvent } from "react";

import { api, type AskResult } from "../api";
import { Markdown } from "./Markdown";
import { ErrorBox } from "./Status";

/** A question to the AI helper, with an optional picture (a photo of a board, a chart, a task). */
export function AskAi({ lessonId = null, placeholder }: { lessonId?: number | null; placeholder?: string }) {
  const [question, setQuestion] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [inputKey, setInputKey] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskResult | null>(null);

  useEffect(() => {
    if (!image) return setPreview(null);
    const url = URL.createObjectURL(image);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [image]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setResult(await api.ask(question, lessonId, image));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function clearImage() {
    setImage(null);
    setInputKey((k) => k + 1);
  }

  return (
    <div className="ask">
      <form className="form ask-form" onSubmit={submit}>
        <textarea
          rows={3}
          placeholder={placeholder ?? "Спросите что угодно по курсу. Можно приложить фото доски, графика или задачи."}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        {preview && (
          <div className="ask-preview">
            <img src={preview} alt="Приложенная картинка" />
            <button type="button" className="secondary small" onClick={clearImage}>
              Убрать
            </button>
          </div>
        )}
        <div className="ask-actions">
          <label className="button secondary attach">
            🖼 Картинка
            <input
              key={inputKey}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(e) => setImage(e.target.files?.[0] ?? null)}
            />
          </label>
          <button type="submit" disabled={busy || (!question.trim() && !image)}>
            {busy ? "Думаю…" : "Спросить"}
          </button>
        </div>
      </form>
      {error && <ErrorBox message={error} />}
      {result && (
        <div className="answer">
          <div className="theory">
            <Markdown>{result.answer}</Markdown>
          </div>
          {result.image_text && (
            <details>
              <summary className="muted small">Что ИИ прочитал на картинке</summary>
              <p className="chunk-text">{result.image_text}</p>
            </details>
          )}
          {result.sources.length > 0 && (
            <div className="sources">
              <span className="muted small">Из материалов курса:</span>
              {result.sources.map((s, i) => (
                <span key={i} className="source">
                  {s.image_url && <img src={s.image_url} alt="" />}
                  {s.title}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

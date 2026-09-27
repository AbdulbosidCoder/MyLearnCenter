import { useState } from "react";

import { api, type Block, type RewriteMode } from "../api";
import { Markdown } from "./Markdown";
import { ErrorBox } from "./Status";

const ASKS: { mode: RewriteMode; label: string }[] = [
  { mode: "simpler", label: "Проще" },
  { mode: "example", label: "Добавить пример" },
  { mode: "shorter", label: "Короче" },
];

/** Buttons under a theory card: the AI proposes a new version, the teacher accepts or drops it. */
export function AiRewrite({ block, onSaved }: { block: Block; onSaved: () => void }) {
  const [proposal, setProposal] = useState<string | null>(null);
  const [custom, setCustom] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask(mode: RewriteMode, instruction = "") {
    setBusy(true);
    setError(null);
    try {
      setProposal((await api.rewriteBlock(block.id, mode, instruction)).text);
      setCustom(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function accept() {
    if (proposal === null) return;
    await api.updateBlock(block.id, { content: proposal });
    setProposal(null);
    onSaved();
  }

  if (proposal !== null) {
    return (
      <div className="ai-proposal">
        <span className="muted small">🤖 Вариант от ИИ:</span>
        <div className="theory">
          <Markdown>{proposal}</Markdown>
        </div>
        <div className="viz-buttons">
          <button className="small" onClick={accept}>
            Принять
          </button>
          <button className="small button secondary" onClick={() => setProposal(null)}>
            Оставить как было
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="ai-row">
      <span className="muted small">🤖 ИИ:</span>
      {ASKS.map((a) => (
        <button key={a.mode} className="small chip" disabled={busy} onClick={() => ask(a.mode)}>
          {a.label}
        </button>
      ))}
      <button className="small chip" disabled={busy} onClick={() => setCustom(custom === null ? "" : null)}>
        Своя просьба
      </button>
      {custom !== null && (
        <form
          className="ai-custom"
          onSubmit={(e) => {
            e.preventDefault();
            ask("custom", custom);
          }}
        >
          <input placeholder="Например: объясни через футбол" value={custom} onChange={(e) => setCustom(e.target.value)} required />
          <button type="submit" className="small" disabled={busy}>
            Отправить
          </button>
        </form>
      )}
      {busy && <span className="muted small block">ИИ пишет новый вариант…</span>}
      {error && <ErrorBox message={error} />}
    </div>
  );
}

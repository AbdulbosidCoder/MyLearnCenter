import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import { BackButton } from "../components/BackButton";
import { ErrorBox, Loading } from "../components/Status";
import { useLoad } from "../hooks";
import { confirmAction } from "../telegram";
import { formatChars } from "./MaterialsPage";

export default function MaterialPage() {
  const id = Number(useParams().id);
  const navigate = useNavigate();
  const { data: material, error } = useLoad(() => api.material(id), [id]);

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
          <p className="muted small">Так файл разделён на части. На следующем этапе ИИ-агент сделает из них уроки.</p>

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
              if (await confirmAction(`Удалить материал «${material.title}»?`)) {
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

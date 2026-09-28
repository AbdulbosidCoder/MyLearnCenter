import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { api, type LessonShort, type ModuleDetail } from "../api";
import { BookIcon, CheckIcon, ChestIcon, ListIcon, LockIcon, PencilIcon, StarIcon } from "../components/Icons";
import { Mascot } from "../components/Mascot";
import { ErrorBox, Loading } from "../components/Status";
import { canEdit, useLoad, useUser } from "../hooks";

// Each theme gets its own colour, in this order.
const SECTION_COLORS = ["green", "pink", "blue", "purple", "orange"];
// Horizontal shift of the nodes, in px: the path winds left and right like a road.
const WIND = [0, 44, 70, 44, 0, -44, -70, -44];

export default function HomePage() {
  const user = useUser();
  const { data: path, error, reload } = useLoad(api.path, []);

  // The lesson to start now: the first open lesson whose test is not passed, across all themes.
  const current = path?.flatMap((m) => m.lessons).find((l) => l.state === "open");

  return (
    <>
      {error && <ErrorBox message={error} />}
      {!path && !error && <Loading />}
      {path?.length === 0 && <p className="muted center">Тем пока нет.</p>}
      {path?.map((module, i) => (
        <Section key={module.id} module={module} index={i} currentId={current?.id} />
      ))}
      {canEdit(user) && path && <NewModuleForm position={path.length} onCreated={reload} />}
    </>
  );
}

function Section({ module, index, currentId }: { module: ModuleDetail; index: number; currentId?: number }) {
  const color = SECTION_COLORS[index % SECTION_COLORS.length];
  const reachable = module.lessons.some((l) => l.state !== "locked");
  const finished = module.lessons.length > 0 && module.lessons.every((l) => l.state === "done" || !l.has_test);
  // The character stands beside the path, on the side the road bends away from.
  const mascotAt = Math.min(2, module.lessons.length - 1);

  return (
    <section className="section">
      <header className={`section-banner ${color}`}>
        <div className="grow">
          <span className="section-label">Раздел {index + 1}</span>
          <h2>{module.title}</h2>
          {module.draft_count > 0 && <span className="small">Черновиков: {module.draft_count}</span>}
        </div>
        <Link to={`/modules/${module.id}`} className="section-button">
          <ListIcon size={22} />
          <span>Уроки</span>
        </Link>
      </header>

      <ol className={`path ${color}`}>
        {module.lessons.map((lesson, i) => (
          <li key={lesson.id} style={{ transform: `translateX(${WIND[i % WIND.length]}px)` }}>
            <Node lesson={lesson} current={lesson.id === currentId} />
            {i === mascotAt && (
              <div className={`path-mascot ${WIND[i % WIND.length] > 0 ? "left" : "right"}`}>
                <Mascot size={120} dim={!reachable} wave={lesson.id === currentId} />
              </div>
            )}
          </li>
        ))}
        {module.lessons.length > 0 && (
          <li style={{ transform: `translateX(${WIND[module.lessons.length % WIND.length]}px)` }}>
            <span className={`node chest${finished ? " open" : ""}`} title={finished ? "Тема пройдена" : "Сундук в конце темы"}>
              <ChestIcon size={42} />
            </span>
          </li>
        )}
      </ol>
    </section>
  );
}

function Node({ lesson, current }: { lesson: LessonShort; current: boolean }) {
  // Open the home screen at the lesson to do next, like a bookmark.
  const ref = useRef<HTMLAnchorElement>(null);
  useEffect(() => {
    if (current) ref.current?.scrollIntoView({ block: "center" });
  }, [current]);
  const Icon =
    lesson.state === "done" ? CheckIcon : lesson.state === "locked" ? LockIcon : current ? StarIcon : lesson.has_test ? PencilIcon : BookIcon;
  const body = (
    <>
      {current && <span className="start-bubble">Начать</span>}
      <span className="node-face">
        <Icon size={current ? 38 : 32} />
      </span>
    </>
  );
  const className = `node ${lesson.state}${current ? " current" : ""}${lesson.is_draft ? " draft" : ""}`;
  if (lesson.state === "locked") {
    return (
      <span className={className} title={`${lesson.title}: откроется после теста предыдущего урока`}>
        {body}
      </span>
    );
  }
  return (
    <Link ref={ref} to={`/lessons/${lesson.id}`} className={className} title={lesson.title} aria-label={lesson.title}>
      {body}
    </Link>
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

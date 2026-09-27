import { Link } from "react-router-dom";

import { api, type Role } from "../api";
import { BackButton } from "../components/BackButton";
import { ErrorBox, Loading } from "../components/Status";
import { useLoad, useUser } from "../hooks";

export default function AdminPage() {
  const me = useUser();
  const { data: users, error, reload } = useLoad(api.users, []);

  if (me.role !== "admin") return <ErrorBox message="Эта страница только для администратора." />;

  return (
    <>
      <BackButton to="/" />
      <Link to="/" className="muted small">
        ← Главная
      </Link>
      <h1>Пользователи</h1>
      <p className="muted small">Пользователь появляется здесь после того, как нажмёт /start в боте.</p>
      {error && <ErrorBox message={error} />}
      {!users && !error && <Loading />}
      <ul className="list">
        {users?.map((u) => (
          <li key={u.id} className="card row">
            <span className="grow">
              <strong>{u.first_name || "Без имени"}</strong>
              <span className="muted small block">{u.username ? `@${u.username}` : `id ${u.telegram_id}`}</span>
            </span>
            {u.role === "admin" ? (
              <span className="badge role-admin">Администратор</span>
            ) : (
              <select
                value={u.role}
                onChange={async (e) => {
                  await api.setRole(u.id, e.target.value as Role);
                  reload();
                }}
              >
                <option value="student">Студент</option>
                <option value="teacher">Преподаватель</option>
              </select>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}

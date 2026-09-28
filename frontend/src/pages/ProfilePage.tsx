import { api } from "../api";
import { BoltIcon, FlameIcon, TrophyIcon } from "../components/Icons";
import { Mascot } from "../components/Mascot";
import { ErrorBox, Loading } from "../components/Status";
import { useLoad, useUser } from "../hooks";

const ROLE_NAMES = { admin: "Администратор", teacher: "Преподаватель", student: "Студент" };

export default function ProfilePage() {
  const user = useUser();
  const { data: stats, error } = useLoad(api.stats, []);
  if (error) return <ErrorBox message={error} />;
  if (!stats) return <Loading />;
  return (
    <>
      <header className="profile">
        <Mascot size={96} wave />
        <div>
          <h1>{user.first_name}</h1>
          <p className="muted">
            {ROLE_NAMES[user.role]}
            {user.username && ` · @${user.username}`}
          </p>
        </div>
      </header>
      <h2>Статистика</h2>
      <div className="stat-grid">
        <div className="panel stat-tile">
          <FlameIcon size={30} />
          <strong>{stats.streak}</strong>
          <span className="muted small">дней подряд</span>
        </div>
        <div className="panel stat-tile">
          <BoltIcon size={30} />
          <strong>{stats.xp_total}</strong>
          <span className="muted small">очков опыта</span>
        </div>
        <div className="panel stat-tile">
          <TrophyIcon size={30} />
          <strong>{stats.tests_passed}</strong>
          <span className="muted small">тестов сдано</span>
        </div>
      </div>
    </>
  );
}

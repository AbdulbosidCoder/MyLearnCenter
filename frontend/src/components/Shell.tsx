import type { ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

import { api, type Leaderboard, type Quest, type Stats } from "../api";
import { canEdit, useLoad, useUser } from "../hooks";
import { BoltIcon, ClockIcon, FlameIcon, HomeIcon, RobotIcon, TargetIcon, TrophyIcon, UserIcon, UsersIcon } from "./Icons";

/** Page frame: menu on the left (a tab bar on phones), content in the middle, quests and rating on the right. */
export function Shell({ children }: { children: ReactNode }) {
  const user = useUser();
  const { pathname } = useLocation();
  // Reload on every page change, so points earned in a test show up right away.
  const { data: stats } = useLoad(api.stats, [pathname]);
  const { data: board } = useLoad(api.leaderboard, [pathname]);

  const items = [
    { to: "/", label: "Обучение", icon: HomeIcon, end: true },
    { to: "/leaderboard", label: "Рейтинг", icon: TrophyIcon },
    { to: "/quests", label: "Задания", icon: TargetIcon },
    { to: "/profile", label: "Профиль", icon: UserIcon },
    ...(canEdit(user) ? [{ to: "/materials", label: "ИИ-материалы", icon: RobotIcon }] : []),
    ...(user.role === "admin" ? [{ to: "/admin", label: "Пользователи", icon: UsersIcon }] : []),
  ];
  const wide = pathname === "/" || pathname === "/leaderboard" || pathname === "/quests" || pathname === "/profile";

  return (
    <div className="shell">
      <nav className="sidenav">
        <Link to="/" className="logo">
          mylearn<span>center</span>
        </Link>
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className="nav-item">
            <Icon size={30} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="content">
        <StatsBar stats={stats} className="stats-top" />
        <main className={wide ? "wide" : undefined}>{children}</main>
      </div>

      <aside className="rail">
        <StatsBar stats={stats} />
        <QuestsCard quests={stats?.quests} compact />
        <RatingCard board={board} compact />
      </aside>
    </div>
  );
}

export function StatsBar({ stats, className = "" }: { stats: Stats | null; className?: string }) {
  return (
    <div className={`stats-bar ${className}`}>
      <span className={`stat ${stats?.streak ? "fire" : "off"}`} title="Дней подряд">
        <FlameIcon size={26} /> {stats?.streak ?? 0}
      </span>
      <span className="stat xp" title="Очки опыта">
        <BoltIcon size={26} /> {stats?.xp_total ?? 0}
      </span>
    </div>
  );
}

const QUEST_ICONS = { xp: BoltIcon, test: ClockIcon, perfect: TargetIcon };

export function QuestsCard({ quests, compact = false }: { quests: Quest[] | undefined; compact?: boolean }) {
  return (
    <section className="panel">
      <header className="panel-head">
        <h3>Задания дня</h3>
        {compact && (
          <Link to="/quests" className="panel-link">
            Все
          </Link>
        )}
      </header>
      {quests?.map((q) => {
        const Icon = QUEST_ICONS[q.key];
        const done = q.value >= q.goal;
        return (
          <div key={q.key} className="quest">
            <Icon size={40} />
            <div className="grow">
              <strong>{q.title}</strong>
              <div className={`bar${done ? " done" : ""}`}>
                <span style={{ width: `${Math.round((q.value / q.goal) * 100)}%` }} />
                <em>
                  {q.value} / {q.goal}
                </em>
              </div>
            </div>
          </div>
        );
      })}
    </section>
  );
}

export function RatingCard({ board, compact = false }: { board: Leaderboard | null; compact?: boolean }) {
  const rows = compact ? board?.rows.slice(0, 5) : board?.rows;
  return (
    <section className="panel">
      <header className="panel-head">
        <h3>Рейтинг недели</h3>
        {compact && (
          <Link to="/leaderboard" className="panel-link">
            Все
          </Link>
        )}
      </header>
      {board?.me && (
        <p className="muted small">
          Вы на {board.me.place}-м месте из {board.total}. Очки за 7 дней: {board.me.xp}.
        </p>
      )}
      {board && board.rows.length === 0 && <p className="muted small">Студентов пока нет.</p>}
      <ol className="rating">
        {rows?.map((r) => (
          <li key={r.place} className={r.is_me ? "me" : undefined}>
            <span className={`place p${r.place}`}>{r.place}</span>
            <span className="avatar">{r.name.slice(0, 1).toUpperCase()}</span>
            <span className="grow">{r.name}</span>
            <span className="muted">{r.xp} XP</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

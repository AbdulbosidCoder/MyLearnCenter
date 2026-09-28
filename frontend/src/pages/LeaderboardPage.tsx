import { api } from "../api";
import { RatingCard } from "../components/Shell";
import { ErrorBox, Loading } from "../components/Status";
import { useLoad } from "../hooks";

export default function LeaderboardPage() {
  const { data: board, error } = useLoad(api.leaderboard, []);
  if (error) return <ErrorBox message={error} />;
  if (!board) return <Loading />;
  return (
    <>
      <h1>Рейтинг</h1>
      <p className="muted">Студенты по очкам опыта за последние 7 дней.</p>
      <RatingCard board={board} />
    </>
  );
}

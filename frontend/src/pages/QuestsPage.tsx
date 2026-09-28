import { api } from "../api";
import { QuestsCard } from "../components/Shell";
import { ErrorBox, Loading } from "../components/Status";
import { useLoad } from "../hooks";

export default function QuestsPage() {
  const { data: stats, error } = useLoad(api.stats, []);
  if (error) return <ErrorBox message={error} />;
  if (!stats) return <Loading />;
  return (
    <>
      <h1>Задания</h1>
      <p className="muted">Каждый день новые. Очки опыта дают тесты: 10 за сданный урок и ещё 5, если без ошибок.</p>
      <QuestsCard quests={stats.quests} />
    </>
  );
}

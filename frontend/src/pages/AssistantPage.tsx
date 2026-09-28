import { api } from "../api";
import { AskAi } from "../components/AskAi";
import { Mascot } from "../components/Mascot";
import { useLoad } from "../hooks";

export default function AssistantPage() {
  const { data: status } = useLoad(api.aiStatus, []);
  return (
    <>
      <header className="profile">
        <Mascot size={88} wave />
        <div>
          <h1>ИИ-помощник</h1>
          <p className="muted">Отвечает по материалам курса и понимает картинки: фото доски, графики, задачи.</p>
        </div>
      </header>
      {status && !status.claude && <p className="error">ИИ не настроен: нужен ANTHROPIC_API_KEY на сервере.</p>}
      <div className="card">
        <AskAi />
      </div>
    </>
  );
}

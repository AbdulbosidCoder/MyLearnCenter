import { Navigate, Route, Routes } from "react-router-dom";

import { api } from "./api";
import { ErrorBox, Loading } from "./components/Status";
import { UserContext, useLoad } from "./hooks";
import AdminPage from "./pages/AdminPage";
import AssistantPage from "./pages/AssistantPage";
import { Shell } from "./components/Shell";
import HomePage from "./pages/HomePage";
import LeaderboardPage from "./pages/LeaderboardPage";
import LessonPage from "./pages/LessonPage";
import MaterialPage from "./pages/MaterialPage";
import MaterialsPage from "./pages/MaterialsPage";
import ModulePage from "./pages/ModulePage";
import ProfilePage from "./pages/ProfilePage";
import QuestsPage from "./pages/QuestsPage";
import QuizPage from "./pages/QuizPage";

export default function App() {
  const { data: user, error } = useLoad(api.me, []);

  if (error) {
    return (
      <main>
        <ErrorBox message={`Не удалось войти: ${error}. Откройте приложение через Telegram-бота.`} />
      </main>
    );
  }
  if (!user) return <Loading />;

  return (
    <UserContext.Provider value={user}>
      <Shell>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/modules/:id" element={<ModulePage />} />
          <Route path="/lessons/:id" element={<LessonPage />} />
          <Route path="/lessons/:id/quiz" element={<QuizPage />} />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/quests" element={<QuestsPage />} />
          <Route path="/leaderboard" element={<LeaderboardPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/materials" element={<MaterialsPage />} />
          <Route path="/materials/:id" element={<MaterialPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Shell>
    </UserContext.Provider>
  );
}

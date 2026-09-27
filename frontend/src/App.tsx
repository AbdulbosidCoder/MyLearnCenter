import { Navigate, Route, Routes } from "react-router-dom";

import { api } from "./api";
import { ErrorBox, Loading } from "./components/Status";
import { UserContext, useLoad } from "./hooks";
import AdminPage from "./pages/AdminPage";
import HomePage from "./pages/HomePage";
import LessonPage from "./pages/LessonPage";
import MaterialPage from "./pages/MaterialPage";
import MaterialsPage from "./pages/MaterialsPage";
import ModulePage from "./pages/ModulePage";
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
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/modules/:id" element={<ModulePage />} />
          <Route path="/lessons/:id" element={<LessonPage />} />
          <Route path="/lessons/:id/quiz" element={<QuizPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/materials" element={<MaterialsPage />} />
          <Route path="/materials/:id" element={<MaterialPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </UserContext.Provider>
  );
}

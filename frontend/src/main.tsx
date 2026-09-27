import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter } from "react-router-dom";

import App from "./App";
import { initTelegram } from "./telegram";
import "./styles.css";

initTelegram();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* Hash routing keeps deep links working inside Telegram and on any static host. */}
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
);

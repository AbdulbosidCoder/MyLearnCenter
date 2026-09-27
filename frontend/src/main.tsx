import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter } from "react-router-dom";

import App from "./App";
import { initTelegram } from "./telegram";
import "./styles.css";

initTelegram();

// Telegram opens the Mini App with its launch data in the hash (#tgWebAppData=...).
// telegram-web-app.js has already read it, but HashRouter would treat it as a page path
// and render nothing, so start from the home page instead.
if (!window.location.hash.startsWith("#/")) {
  window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}#/`);
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* Hash routing keeps deep links working inside Telegram and on any static host. */}
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
);

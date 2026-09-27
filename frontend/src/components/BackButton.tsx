import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { tg } from "../telegram";

/** Shows Telegram's native back button while the page is open. */
export function BackButton({ to }: { to: string }) {
  const navigate = useNavigate();
  useEffect(() => {
    const back = tg?.BackButton;
    if (!back) return;
    const go = () => navigate(to);
    back.show();
    back.onClick(go);
    return () => {
      back.offClick(go);
      back.hide();
    };
  }, [navigate, to]);
  return null;
}

// Minimal typing for the parts of Telegram.WebApp we use.
interface TelegramWebApp {
  initData: string;
  colorScheme: "light" | "dark";
  ready(): void;
  expand(): void;
  showAlert(message: string): void;
  showConfirm(message: string, callback: (ok: boolean) => void): void;
  BackButton: { show(): void; hide(): void; onClick(cb: () => void): void; offClick(cb: () => void): void };
  HapticFeedback?: { impactOccurred(style: "light" | "medium" | "heavy"): void };
}

declare global {
  interface Window {
    Telegram?: { WebApp: TelegramWebApp };
  }
}

export const tg: TelegramWebApp | undefined = window.Telegram?.WebApp;

export function initTelegram() {
  tg?.ready();
  tg?.expand();
  // Inside Telegram follow its day/night setting; in a browser the CSS follows the system.
  if (tg?.initData) document.documentElement.dataset.theme = tg.colorScheme;
}

export function confirmAction(message: string): Promise<boolean> {
  if (tg?.initData) return new Promise((resolve) => tg.showConfirm(message, resolve));
  return Promise.resolve(window.confirm(message));
}

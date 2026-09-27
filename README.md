# MyLearnCenter

Telegram Mini App и Telegram-бот для изучения Data Science шаг за шагом: теория, GIF, тесты по каждой теме, 2D/3D-визуализации, уведомления и AI-помощник.

План развития: [docs/architecture.md](docs/architecture.md).

## Что уже есть (этап 1)

- **Бот** (`/start`): регистрирует пользователя, показывает его роль и кнопку «Открыть уроки», ставит кнопку меню Mini App.
- **Вход через Telegram**: Mini App отправляет `initData`, бэкенд проверяет подпись токеном бота. Паролей нет.
- **Роли**: один администратор (задаётся `ADMIN_TG_ID`), преподаватели и студенты. Администратор назначает преподавателей на странице «Пользователи».
- **Темы и уроки**: все видят темы, уроки и их блоки. Блок — это теория в Markdown, GIF, картинка или видео по ссылке.
- **Редактор**: преподаватель и администратор прямо в Mini App добавляют и удаляют темы, уроки и блоки.
- **Дневная и ночная тема**: цвета берутся из темы Telegram.
- При первом запуске создаются три демо-темы.

Следующие этапы: тесты и разблокировка уроков, задания и уведомления, визуализации, AI-помощник, геймификация.

## Структура

```
backend/    FastAPI + SQLAlchemy (API), aiogram (бот), pytest
frontend/   React + TypeScript + Vite (Mini App)
docs/       план развития
```

## Локальный запуск

1. Создайте бота у [@BotFather](https://t.me/BotFather) и узнайте свой Telegram id (например, у @userinfobot).
2. Бэкенд:

   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements-dev.txt
   cp .env.example .env   # впишите BOT_TOKEN, ADMIN_TG_ID, WEBAPP_URL
   uvicorn app.main:app --reload       # API на :8000
   python -m app.bot                   # бот, в отдельном терминале
   pytest                              # тесты
   ```

3. Mini App:

   ```bash
   cd frontend
   npm install
   npm run dev      # http://localhost:5173, запросы /api идут на :8000
   ```

   Чтобы открыть приложение в обычном браузере без Telegram, запустите API с `DEV_MODE=true`
   и создайте `frontend/.env` с `VITE_DEV_USER=<ваш telegram id>`. В продакшене `DEV_MODE` должен быть выключен.

## Запуск в Telegram

Telegram открывает Mini App только по HTTPS. Самый простой путь:

1. Выполните `npm run build` в `frontend/`. Собранное приложение раздаёт сам бэкенд, отдельный хостинг для фронта не нужен.
2. Разверните бэкенд на сервере с HTTPS (для проверки можно пробросить порт 8000 через ngrok или cloudflared).
3. Укажите этот адрес в `WEBAPP_URL` и перезапустите бота.

Через Docker: заполните `backend/.env` и выполните `docker compose up --build` (PostgreSQL, API и бот).

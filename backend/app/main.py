from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.config import get_settings
from app.db import SessionLocal, init_db
from app.seed import seed_demo_content

# The built Mini App (frontend/dist) is served by the same server, so one HTTPS host is enough.
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    if get_settings().seed_demo_content:
        async with SessionLocal() as session:
            await seed_demo_content(session)
    yield


app = FastAPI(title="MyLearnCenter", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if not FRONTEND_DIST.is_dir():

    @app.get("/", include_in_schema=False)
    async def frontend_not_built():
        # Without this the root URL answers {"detail":"Not Found"}, which looks like a broken tunnel.
        return HTMLResponse(
            "<h1>MyLearnCenter API работает</h1>"
            "<p>Mini App ещё не собран. Выполните <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code> "
            "и перезапустите API.</p>",
            status_code=503,
        )

else:
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        file = (FRONTEND_DIST / path).resolve()
        if path and file.is_file() and file.is_relative_to(FRONTEND_DIST):
            return FileResponse(file)
        return FileResponse(FRONTEND_DIST / "index.html")

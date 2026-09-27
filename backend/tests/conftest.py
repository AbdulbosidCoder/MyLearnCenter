import hashlib
import hmac
import json
import os
import tempfile
import time
from urllib.parse import urlencode

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["BOT_TOKEN"] = "123:test-token"
os.environ["ADMIN_TG_ID"] = "1"
os.environ["DEV_MODE"] = "false"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_demo_content  # noqa: E402

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = 1


def make_init_data(user_id: int, first_name: str = "Test", auth_date: int | None = None, token: str = BOT_TOKEN) -> str:
    """Sign initData the same way Telegram does."""
    fields = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAH",
        "user": json.dumps({"id": user_id, "first_name": first_name}),
    }
    dcs = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def auth(user_id: int) -> dict[str, str]:
    return {"Authorization": f"tma {make_init_data(user_id)}"}


@pytest.fixture(autouse=True)
async def fresh_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    async with SessionLocal() as session:
        await seed_demo_content(session)
    yield


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

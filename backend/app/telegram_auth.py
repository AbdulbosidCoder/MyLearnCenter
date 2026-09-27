"""Validation of Telegram Mini App initData.

See https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class InvalidInitData(Exception):
    pass


@dataclass
class TelegramUser:
    id: int
    first_name: str
    username: str | None


def validate_init_data(init_data: str, bot_token: str, ttl: int, now: float | None = None) -> TelegramUser:
    if not bot_token:
        raise InvalidInitData("bot token is not configured")
    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = fields.pop("hash", None)
    if not received_hash:
        raise InvalidInitData("hash is missing")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InvalidInitData("bad signature")

    try:
        auth_date = int(fields["auth_date"])
    except (KeyError, ValueError) as exc:
        raise InvalidInitData("auth_date is missing") from exc
    if (now if now is not None else time.time()) - auth_date > ttl:
        raise InvalidInitData("initData has expired")

    try:
        user = json.loads(fields["user"])
        return TelegramUser(id=int(user["id"]), first_name=user.get("first_name", ""), username=user.get("username"))
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidInitData("user is missing") from exc

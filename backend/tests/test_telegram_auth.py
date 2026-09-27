import time

import pytest

from app.telegram_auth import InvalidInitData, validate_init_data
from tests.conftest import BOT_TOKEN, make_init_data


def test_valid_init_data():
    user = validate_init_data(make_init_data(42, "Ali"), BOT_TOKEN, ttl=3600)
    assert user.id == 42
    assert user.first_name == "Ali"


def test_wrong_token_is_rejected():
    with pytest.raises(InvalidInitData):
        validate_init_data(make_init_data(42, token="999:other"), BOT_TOKEN, ttl=3600)


def test_tampered_data_is_rejected():
    data = make_init_data(42).replace("42", "43")
    with pytest.raises(InvalidInitData):
        validate_init_data(data, BOT_TOKEN, ttl=3600)


def test_expired_data_is_rejected():
    old = int(time.time()) - 7200
    with pytest.raises(InvalidInitData, match="expired"):
        validate_init_data(make_init_data(42, auth_date=old), BOT_TOKEN, ttl=3600)


def test_missing_hash_is_rejected():
    with pytest.raises(InvalidInitData):
        validate_init_data("auth_date=1&user=%7B%7D", BOT_TOKEN, ttl=3600)

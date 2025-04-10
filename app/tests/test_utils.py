from datetime import date, datetime
from typing import Callable

import pytest
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from utils import PeriodFrom, get_datetime_now, get_password_hash, pwd_context, verify_password


@pytest.mark.parametrize(
    "timezone",
    [
        "UTC",
        "Europe/Kyiv",
        "Asia/Tokyo",
        "America/New_York",
    ],
)
def test_get_datetime_now_valid(timezone: str) -> None:
    result = get_datetime_now(timezone)
    assert isinstance(result, datetime)

    expected = datetime.now(ZoneInfo(timezone)).replace(tzinfo=None)
    assert abs((expected - result).total_seconds()) < 1


@pytest.mark.parametrize("timezone", ["Mars/Phobos", "Invalid/Zone", "Kyiv", "Not/AZone"])
def test_get_datetime_now_invalid(timezone: str) -> None:
    with pytest.raises(ZoneInfoNotFoundError):
        get_datetime_now(timezone)


@pytest.mark.parametrize(
    "period, expected_fn",
    [
        (PeriodFrom.DAY, lambda now: now),
        (PeriodFrom.MONTH, lambda now: date(now.year, now.month, 1)),
        (PeriodFrom.YEAR, lambda now: date(now.year, 1, 1)),
    ],
)
def test_get_date_start(period: PeriodFrom, expected_fn: Callable[[date], date]) -> None:
    today = date.today()
    assert period.get_date_start() == expected_fn(today)


@pytest.mark.parametrize(
    "password",
    [
        "Simple123!",
        "Another$trong1",
        "weird_pass_321",
        "pass",
    ],
)
def test_get_password_hash(password: str) -> None:
    hash_ = get_password_hash(password)

    assert isinstance(hash_, str)
    assert hash_ != password
    assert pwd_context.verify(password, hash_)


@pytest.mark.parametrize("password", ["MyPass123!", "Another$ecret99", "pass"])
def test_verify_password_success(password: str) -> None:
    hashed = pwd_context.hash(password)
    assert verify_password(password, hashed) is True


@pytest.mark.parametrize(
    "plain, wrong",
    [
        ("MyPass123!", "WrongPass123!"),
        ("123456", "654321"),
        ("Secret", "secret"),
    ],
)
def test_verify_password_fail(plain: str, wrong: str) -> None:
    hashed = pwd_context.hash(plain)
    assert verify_password(wrong, hashed) is False

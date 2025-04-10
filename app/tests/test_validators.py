import pytest
from fastapi.exceptions import RequestValidationError

from validators import normalize_name, validate_password


@pytest.mark.parametrize("password", ["Abcdef1!", "StrongPass1@", "XyZ12345#", "TestPass99$"])
def test_validate_password_valid(password: str) -> None:
    assert validate_password(password) == password


@pytest.mark.parametrize(
    "password", ["short1!", "nouppercase1!", "NOLOWERCASE1!", "NoSpecial123", "NoDigit!@", "      ", ""]
)
def test_validate_password_invalid(password: str) -> None:
    with pytest.raises(RequestValidationError):
        validate_password(password)


@pytest.mark.parametrize(
    "input_name, expected",
    [
        ("john", "John"),
        ("alice", "Alice"),
        ("BOB", "Bob"),
        ("dEvElOpEr", "Developer"),
    ],
)
def test_normalize_name_valid(input_name: str, expected: str) -> None:
    assert normalize_name(input_name) == expected


@pytest.mark.parametrize(
    "input_name",
    [
        "john doe",
        " alice",
        "bob ",
        "multi word name",
        "a b",
    ],
)
def test_normalize_name_invalid(input_name: str) -> None:
    with pytest.raises(RequestValidationError):
        normalize_name(input_name)

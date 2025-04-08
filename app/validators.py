import re

from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError


def normalize_name(value: str) -> str:
    """Validate 'name' field."""
    if " " in value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {"type": "string_type", "loc": ["body", "name"], "msg": "Input should contain one word", "input": value}
            ],
        )
    return value.capitalize()


def validate_password(raw_password: str) -> str:
    """Validate raw password.

    Password must be at least 8 characters long
    and include at least one uppercase letter, one
    lowercase letter, one digit, and one special
    character.
    :param raw_password: Raw password.
    :return: Raw password if valid.
    """
    if not re.match(r"^(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[0-9])(?=.*?[#?!@$%^&*-]).{8,40}$", raw_password):
        raise RequestValidationError(
            errors=[
                {
                    "msg": "Password must be at least 8 characters long and include at least one uppercase "
                    "letter, one lowercase letter, one digit, and one special character."
                }
            ]
        )
    return raw_password

import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi.exceptions import RequestValidationError
from pydantic import AfterValidator


def normalize_name(value: str) -> str:
    """Validate 'name' field."""
    if " " in value:
        raise RequestValidationError(errors={"msg": "Input should contain one word"})
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
            errors={
                "msg": "Password must be at least 8 characters long and include at least one uppercase "
                "letter, one lowercase letter, one digit, and one special character."
            }
        )
    return raw_password


def validate_cash(value: Decimal) -> Decimal:
    """Adjust Decimal value to 4 places."""
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


CurrencyValue = Annotated[Decimal, AfterValidator(validate_cash)]

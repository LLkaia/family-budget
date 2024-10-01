from fastapi import HTTPException, status


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

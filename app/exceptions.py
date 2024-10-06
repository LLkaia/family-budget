from fastapi import HTTPException, status


class CredentialsException(HTTPException):
    """Exception for credentials errors."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"}
        )


class ItemNotExistsException(Exception):
    """Exception for not found item in DB."""


class ParameterMissingException(Exception):
    """Exception for missed parameters."""

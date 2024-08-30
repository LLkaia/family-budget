from fastapi import HTTPException, status


class CredentialsException(HTTPException):
    """Exception for credentials errors.

    Args:
        detail: Exception message
        status_code: HTTP status
        headers: Headers for response
    """

    def __init__(
        self,
        detail: str = "Could not validate credentials",
        status_code: int = status.HTTP_401_UNAUTHORIZED,
        headers: dict = {"WWW-Authenticate": "Bearer"},
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)

from fastapi import HTTPException, status


class CredentialsException(HTTPException):
    def __init__(
        self,
        detail="Could not validate credentials",
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Bearer"},
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)

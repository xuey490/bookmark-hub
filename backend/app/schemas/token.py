from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

MIN_TOKEN_LENGTH = 16
MAX_TOKEN_LENGTH = 128


class TokenUpdate(BaseModel):
    token: str = Field(min_length=MIN_TOKEN_LENGTH, max_length=MAX_TOKEN_LENGTH)

    @field_validator("token")
    @classmethod
    def _clean_token(cls, value: str) -> str:
        token = value.strip()
        if len(token) < MIN_TOKEN_LENGTH:
            raise ValueError(
                f"token must be at least {MIN_TOKEN_LENGTH} characters"
            )
        if any(character.isspace() for character in token):
            raise ValueError("token must not contain whitespace")
        if not token.isascii():
            raise ValueError("token must contain ASCII characters only")
        return token

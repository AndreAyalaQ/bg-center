import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.api.auth import issue_token, require_token
from app.config import Settings


def test_issue_token_rejects_an_empty_jwt_secret() -> None:
    settings = Settings(jwt_secret="")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        issue_token(settings)


def test_require_token_rejects_an_empty_jwt_secret() -> None:
    settings = Settings(jwt_secret="")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="whatever")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        require_token(credentials=credentials, settings=settings)


def test_issue_token_works_with_a_real_secret() -> None:
    settings = Settings(jwt_secret="test-secret")
    assert issue_token(settings)

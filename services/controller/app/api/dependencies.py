from __future__ import annotations

from typing import Generator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.db.session import SessionLocal
from app.services.auth import CurrentPrincipal, get_current_principal_from_token


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_current_principal(
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: Session = Depends(get_db_session),
) -> CurrentPrincipal:
    if not authorization:
        raise api_error(status_code=401, message="Authorization header is required.")
    return get_current_principal_from_token(session, authorization)

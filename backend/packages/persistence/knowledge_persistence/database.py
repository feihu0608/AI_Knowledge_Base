from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


class Database:
    def __init__(self, url: str, *, echo: bool = False) -> None:
        parsed = make_url(url)
        if parsed.drivername.startswith("sqlite") and parsed.database not in {None, "", ":memory:"}:
            Path(parsed.database).expanduser().parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, echo=echo, pool_pre_ping=True, connect_args=connect_args)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False, class_=Session)

    def session(self) -> Iterator[Session]:
        with self.session_factory() as session:
            yield session

import importlib.util
from pathlib import Path

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from knowledge_persistence.models import Tenant, User


SEED_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "seed_demo.py"
SPEC = importlib.util.spec_from_file_location("seed_demo", SEED_SCRIPT)
assert SPEC is not None and SPEC.loader is not None
seed_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(seed_module)
seed = seed_module.seed


def test_seed_demo_respects_foreign_keys_and_is_idempotent(tmp_path):
    database_path = tmp_path / "seed.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"

    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    event.listen(Engine, "connect", enable_foreign_keys)
    try:
        seed(database_url, "DemoOnly!2026", create_schema=True)
        seed(database_url, "DemoOnly!2026", create_schema=True)
    finally:
        event.remove(Engine, "connect", enable_foreign_keys)

    engine = create_engine(database_url)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Tenant)) == 2
        # Each fictional tenant has one administrator plus three organization
        # fixtures used by the organization management page.
        assert session.scalar(select(func.count()).select_from(User)) == 8

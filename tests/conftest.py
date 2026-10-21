import os
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
DB = os.environ.get("BOREAL_DB", str(ROOT / "boreal.duckdb"))


@pytest.fixture(scope="session")
def con():
    c = duckdb.connect(DB, read_only=True)
    yield c
    c.close()


def scalar(con, sql):
    return con.execute(sql).fetchone()[0]

from collections.abc import AsyncIterator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

engine = create_async_engine(get_settings().database_url)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _add_missing_columns(conn) -> None:
    """create_all never changes existing tables, so columns added later are appended here.

    Every column added after a table first shipped needs a server_default (or to be nullable).
    """
    inspector = inspect(conn)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            ddl = f"ALTER TABLE {table.name} ADD COLUMN {column.name} {column.type.compile(conn.dialect)}"
            if column.server_default is not None:
                default = column.server_default.arg
                if isinstance(default, str):
                    ddl += f" DEFAULT '{default}'"
                else:
                    ddl += f" DEFAULT {default.compile(dialect=conn.dialect)}"
            if not column.nullable:
                ddl += " NOT NULL"
            conn.execute(text(ddl))


async def init_db() -> None:
    # Tables are created directly; Alembic migrations come once the schema settles.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session

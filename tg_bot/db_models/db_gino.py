import logging

import sqlalchemy as sa
from typing import List
from gino import Gino
from sqlalchemy import Column, DateTime

from config import Config

db = Gino()

logger = logging.getLogger(__name__)


class BaseModel(db.Model):
    __abstract__ = True

    def __str__(self):
        model = self.__class__.__name__
        table: sa.Table = sa.inspect(self.__class__)
        primary_key_columns: List[sa.Column] = table.primary_key.columns
        values = {
            column.name: getattr(self, self._column_name_map[column.name])
            for column in primary_key_columns
        }
        values_str = " ".join(f"{name}={value!r}" for name, value in values.items())
        return f"<{model} {values_str}>"


class TimedBaseModel(BaseModel):
    __abstract__ = True

    created_at = Column(DateTime(True), server_default=db.func.now())
    updated_at = Column(DateTime(True),
                        default=db.func.now(),
                        onupdate=db.func.now(),
                        server_default=db.func.now())


async def connect_to_db(remove_data: bool = False):
    logger.info("Connecting to PostgreSQL...")
    postgres_uri = f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}/{Config.DB_NAME}"
    await db.set_bind(postgres_uri)

    if remove_data:
        await db.gino.drop_all()

    await db.gino.create_all()

from sqlalchemy import Column, sql, Integer, String, BigInteger, Boolean

from tg_bot.db_models.db_gino import TimedBaseModel

prefix = "amurbooking_bot_"


class MessageId(TimedBaseModel):
    __tablename__ = prefix + "messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tg_user_id = Column(BigInteger, nullable=False)
    telegram_id = Column(BigInteger, nullable=False)

    query: sql.Select


class Account(TimedBaseModel):
    __tablename__ = prefix + "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    verified = Column(Boolean)
    phone = Column(String, primary_key=True)
    password = Column(String)
    proxy = Column(String)
    auth_token = Column(String)
    is_work = Column(Boolean, default=False)

    query: sql.Select

# app/db.py

import databases
import ormar
import sqlalchemy
import datetime as dt

from pydantic import BaseModel

from .config import settings

database = databases.Database(settings.db_url)
metadata = sqlalchemy.MetaData()


class BaseMeta(ormar.ModelMeta):
    metadata = metadata
    database = database


class User(ormar.Model):
    class Meta(BaseMeta):
        tablename = "users"

    id: int = ormar.Integer(primary_key=True)
    email: str = ormar.String(max_length=128, unique=True, nullable=False)
    active: bool = ormar.Boolean(default=True, nullable=False)

class CompanyDB(ormar.Model):
    class Meta(BaseMeta):
        tablename = "company"

    id: int = ormar.Integer(primary_key=True)
    committee_id: str = ormar.String(max_length=128, unique=True, nullable=False)
    name: str = ormar.String(max_length=128, unique=True, nullable=False)
    industry: str = ormar.String(max_length=128, unique=False, nullable=False)
    starting_date: str = ormar.String(max_length=128, unique=False, nullable=False)
    metadata: str = ormar.String(max_length=128, unique=False, nullable=False)
    statement: bool = ormar.Boolean(nullable=False)
    broke_promise: bool = ormar.Boolean(nullable=False)
    created: dt.datetime = ormar.DateTime(nullable=False)
    last_updated: dt.datetime = ormar.DateTime(nullable=False)
    active: bool = ormar.Boolean(nullable=False, default=False)

class CompanyNameAPI(BaseModel):
    name: str

class CompanyAPI(BaseModel):
    committee_id: str
    name: str
    industry: str
    starting_date: str

engine = sqlalchemy.create_engine(settings.db_url)
metadata.create_all(engine)

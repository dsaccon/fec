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


class Transactions(ormar.Model):
    class Meta(BaseMeta):
        tablename = "transactions"

    id: int = ormar.Integer(primary_key=True)
    transaction_id: str = ormar.String(max_length=32, unique=True, nullable=False)
    committee_id: str = ormar.String(max_length=128, unique=False, nullable=False)
    company_name: str = ormar.String(max_length=128, unique=False, nullable=False)
    industry: str = ormar.String(max_length=128, unique=False, nullable=False)
    recipient_name: str = ormar.String(max_length=128, unique=False, nullable=False)
    recipient_state: str = ormar.String(max_length=128, unique=False, nullable=False)
    candidate_id: str = ormar.String(max_length=32, unique=False, nullable=False)
    description: str = ormar.String(max_length=128, unique=False, nullable=False)
    date: str = ormar.String(max_length=128, unique=False, nullable=False)
    amount: float = ormar.Float(unique=False, nullable=False)


class TransactionsLog(ormar.Model):
    class Meta(BaseMeta):
        tablename = "transactions_log"

    id: int = ormar.Integer(primary_key=True)
    timestamp: dt.datetime = ormar.DateTime(unique=False, nullable=False)
    data: str = ormar.Text(unique=False, nullable=False)


class Candidates(ormar.Model):
    class Meta(BaseMeta):
        tablename = "candidates"

    id: int = ormar.Integer(primary_key=True)
    committee_id: str = ormar.String(max_length=128, unique=False, nullable=False)
    first_name: str = ormar.String(max_length=128, unique=False, nullable=False)
    last_name: str = ormar.String(max_length=128, unique=False, nullable=False)
    district: str = ormar.String(max_length=128, unique=False, nullable=True)
    state: str = ormar.String(max_length=128, unique=False, nullable=False)
    active: bool = ormar.Boolean(unique=False, nullable=False, default=True)
    priority: bool = ormar.Boolean(unique=False, nullable=False, default=False)


class Adjustments(ormar.Model):
    class Meta(BaseMeta):
        tablename = "adjustments"

    id: int = ormar.Integer(primary_key=True)
    type: str = ormar.String(max_length=64, unique=False, nullable=False)
    value: str = ormar.String(max_length=128, unique=False, nullable=False)
    amount: float = ormar.Float(unique=False, nullable=False)


class CompanyDB(ormar.Model):
    class Meta(BaseMeta):
        tablename = "company"

    id: int = ormar.Integer(primary_key=True)
    committee_id: str = ormar.String(max_length=128, unique=True, nullable=False)
    name: str = ormar.String(max_length=256, unique=True, nullable=False)
    industry: str = ormar.String(max_length=128, unique=False, nullable=False)
    starting_date: str = ormar.String(max_length=128, unique=False, nullable=False)
    metadata: str = ormar.Text(unique=False, nullable=False)
    statement: bool = ormar.Boolean(unique=False, nullable=False)
    broke_promise: bool = ormar.Boolean(unique=False, nullable=False)
    created: dt.datetime = ormar.DateTime(unique=False, nullable=False)
    last_updated: dt.datetime = ormar.DateTime(unique=False, nullable=False)
    last_api_accessed: dt.datetime = ormar.DateTime(unique=False, nullable=False)
    active: bool = ormar.Boolean(unique=False, nullable=False, default=False)


class CompanyNameAPI(BaseModel):
    name: str


class CompanyIndustryAPI(BaseModel):
    industry: str


class CompanyRecipientAPI(BaseModel):
    recipient: str


class CompanyCommmitteeIdAPI(BaseModel):
    committee_id: str


class CompanyAPI(BaseModel):
    committee_id: str
    name: str
    industry: str
    starting_date: str
    metadata: str
    statement: bool
    broke_promise: bool


class CorporateDonationsAPI(BaseModel):
    date_start: str
    date_end: str
    statement: bool
    broke_promise: bool


engine = sqlalchemy.create_engine(settings.db_url)
try:
    metadata.create_all(engine, checkfirst=True)
except sqlalchemy.exc.IntegrityError as e:
    # Race condition on startup (api/agent both importing this module), known pg issue
    print(e)

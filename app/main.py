# app/main.py

from fastapi import FastAPI

import datetime as dt
import requests
import ormar

from app.db import database, Transactions, CompanyDB, CompanyNameAPI
from app.db import CompanyCommmitteeIdAPI, CompanyIndustryAPI, CompanyAPI
from app.http_api import SingletonAioHttp

from dotenv import dotenv_values

app = FastAPI(title="FEC data collection API")

API_KEY=dotenv_values('.env').get('API_KEY')


# Admin endpoints

@app.post("/company/add/")
async def company_add(company: CompanyAPI):
    now = dt.datetime.utcnow()
    comp = await CompanyDB.objects.create(
        committee_id=company.committee_id,
        name=company.name,
        industry=company.industry,
        starting_date=company.starting_date,
        metadata=company.metadata,
        statement=company.statement,
        broke_promise=company.broke_promise,
        created=now,
        last_updated=now,
        active=True)
    return company

@app.post("/company/edit/{_id}")
async def company_edit(company: CompanyAPI, _id: int):
    try:
        comp = await CompanyDB.objects.get(id=_id, active=True)
        comp.committee_id = company.committee_id
        comp.name = company.name
        comp.industry = company.industry
        comp.starting_date = company.starting_date
        comp.metadata = company.metadata
        comp.statement = company.statement
        comp.broke_promise = company.broke_promise
        comp.last_updated = dt.datetime.utcnow()
        return await comp.update()
    except ormar.exceptions.NoMatch:
        return False

@app.get("/company/delete/{_id}")
async def company_delete(_id: int):
    try:
        comp = await CompanyDB.objects.get(id=_id)
        comp.active = False
        return await comp.update()
    except ormar.exceptions.NoMatch:
        return False

@app.get("/company/view/{_id}")
async def company_view(_id: int):
    try:
        comp = await CompanyDB.objects.get(id=_id, active=True)
        comp.name = comp.name.encode('utf-8').decode('unicode-escape')
        comp.industry = comp.industry.encode('utf-8').decode('unicode-escape')
        comp.metadata = comp.metadata.encode('utf-8').decode('unicode-escape')
        return comp
    except ormar.exceptions.NoMatch:
        return False

@app.get("/company/get-all/")
async def company_view():
    companies = await CompanyDB.objects.all(active=True)
    for comp in companies:
        comp.name = comp.name.encode('utf-8').decode('unicode-escape')
        comp.industry = comp.industry.encode('utf-8').decode('unicode-escape')
        comp.metadata = comp.metadata.encode('utf-8').decode('unicode-escape')
    return companies

@app.post("/company/search/")
async def company_search(company: CompanyNameAPI):
    params = {
        'sort_hide_null': 'false',
        'q': company.name,
        'sort_nulls_last': 'false',
        'api_key': API_KEY,
        'sort': 'name',
        'sort_null_only': 'false',
    }
    url = f'https://api.open.fec.gov/v1/names/committees/'
    return await SingletonAioHttp.query_url(url, data=params)


# Frontend endpoints

@app.post("/data/donations-by-industry")
async def data_donations_by_industry(company: CompanyIndustryAPI):
    industry_transactions = await Transactions.objects.all(industry=company.industry)
    for tx in industry_transactions:
        tx.company_name = tx.company_name.encode('utf-8').decode('unicode-escape')
        tx.industry = tx.industry.encode('utf-8').decode('unicode-escape')
    return industry_transactions

@app.get("/data/all-transactions/")
async def data_all_transactions():
    transactions = await Transactions.objects.all()
    for tx in transactions:
        tx.company_name = tx.company_name.encode('utf-8').decode('unicode-escape')
        tx.industry = tx.industry.encode('utf-8').decode('unicode-escape')
    return transactions

@app.post("/data/company-detail")
async def data_company_detail(company: CompanyCommmitteeIdAPI):
    company_transactions = await Transactions.objects.all(committee_id=company.committee_id)
    return company_transactions


#

@app.on_event("startup")
async def startup():
    if not database.is_connected:
        await database.connect()
    SingletonAioHttp.get_aiohttp_client()


@app.on_event("shutdown")
async def shutdown():
    if database.is_connected:
        await database.disconnect()
    await SingletonAioHttp.close_aiohttp_client()

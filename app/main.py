# app/main.py

from fastapi import FastAPI

import datetime as dt
import requests
import ormar

from app.db import database, User, CompanyDB, CompanyNameAPI, CompanyAPI
from app.http import SingletonAioHttp

from dotenv import dotenv_values

app = FastAPI(title="FEC data collection API")

API_KEY=dotenv_values('.env').get('API_KEY')

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
        return await CompanyDB.objects.get(id=_id, active=True)
    except ormar.exceptions.NoMatch:
        return False

@app.get("/company/get-all/")
async def company_view():
    return await CompanyDB.objects.all(active=True)

@app.post("/company/search/")
async def company_search(company: CompanyNameAPI):
    url = f'https://api.open.fec.gov/v1/names/committees/?api_key={API_KEY}={company.name}'
    resp = await SingletonAioHttp.query_url(url)
    return requests.get(url).json()

##
#@app.post("/companies/get/")
#async def companies_get(company: CompanyAPI):
#    await asyncio.sleep(0)
#    return None
#
#@app.post("/data/donations-by-industry")
#async def companies_get(company: CompanyAPI):
#    await asyncio.sleep(0)
#    return None

#@app.post("/data/donations-by-industry")
#async def donations_by_industry():
#    # add company to table
#    pass
#
#@app.post("/data/all-transactions")
#async def all_transactions():
#    # add company to table
#    pass
#
#@app.post("/data/company-detail")
#async def company_detail():
#    # add company to table
#    pass
#
@app.on_event("startup")
async def startup():
    if not database.is_connected:
        await database.connect()
    SingletonAioHttp.get_aiohttp_client()
    # create a dummy entry
    await User.objects.get_or_create(email="test@test.com")


@app.on_event("shutdown")
async def shutdown():
    if database.is_connected:
        await database.disconnect()
    await SingletonAioHttp.close_aiohttp_client()

# app/main.py

from fastapi import FastAPI

import datetime as dt
import asyncio
import ormar

from app.db import database, Transactions, CompanyDB, CompanyNameAPI
from app.db import CompanyCommmitteeIdAPI, CompanyAPI
from app.db import CompanyIndustryAPI, CompanyRecipientAPI, CorporateDonationsAPI
from app.http_api import SingletonAioHttp

from dotenv import dotenv_values

app = FastAPI(title="FEC data collection API")

API_KEY=dotenv_values('.env').get('API_KEY')


# Admin endpoints

@app.post("/company/add/")
async def company_add(company: CompanyAPI):
    now = dt.datetime.utcnow()
    comp = await CompanyDB.objects.get(committee_id=company.committee_id, name=company.name)
    if comp.id is None:
        await CompanyDB.objects.update_or_create(
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
    else:
        await CompanyDB.objects.update_or_create(
            id=comp.id,
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

@app.get("/data/top-donations")
async def top_donations():
    ind_query = """SELECT industry, SUM (amount) FROM transactions GROUP BY industry ORDER BY SUM (amount) DESC"""
    rcp_query = """SELECT recipient_name, SUM (amount) FROM transactions GROUP BY recipient_name ORDER BY SUM (amount) DESC"""
    aio_tasks = [
        database.fetch_all(query=ind_query),
        database.fetch_all(query=rcp_query)
    ]
    top_industries, top_recipients = await asyncio.gather(*aio_tasks)
    top_industries = top_industries[:10]
    top_recipients = top_recipients[:10]
    top_industries = {ind.get('industry'): ind.get('sum') for ind in top_industries}
    top_recipients = {ind.get('recipient_name'): ind.get('sum') for ind in top_recipients}
    return {'by_industry': top_industries, 'by_recipient': top_recipients}


@app.post("/data/corporate-donations")
async def corporate_donations(params: CorporateDonationsAPI):
    companies = await CompanyDB.objects.all(active=True)
    for comp in companies:
        comp.name = comp.name.encode('utf-8').decode('unicode-escape')
        comp.industry = comp.industry.encode('utf-8').decode('unicode-escape')
        comp.metadata = comp.metadata.encode('utf-8').decode('unicode-escape')

    comp_query = (
        f"SELECT company_name, SUM (amount)\n"
        f"  FROM transactions\n"
        f"  GROUP BY company_name\n"
        f"  ORDER BY SUM (amount) DESC\n")
    companies_tot_contr = await database.fetch_all(query=comp_query)
    aio_tasks = []
    for company in companies_tot_contr:
        query = (
            f"SELECT recipient_name, company_name, SUM (amount)\n"
            f"  FROM transactions\n"
            f"  WHERE company_name = '{company.get('company_name')}'\n"
            f"  GROUP BY recipient_name, company_name\n"
            f"  ORDER BY SUM (amount) DESC\n")
        aio_tasks += [database.fetch_all(query=query)]
    companies_sorted_txs = await asyncio.gather(*aio_tasks)

    results = {}
    for company in companies_sorted_txs:
        statement = [
            comp.statement for comp in companies
            if comp.name == company[0].get('company_name')
        ][0]
        tot_contr = [
            comp.get('sum')
            for comp in companies_tot_contr
            if comp.get('company_name') == company[0].get('company_name')
        ][0]
        results[company[0].get('company_name')] = {
            'statement': statement,
            'total_contributions': tot_contr,
            'all_recipients': {
                recipient.get('recipient_name'): recipient.get('sum')
                for recipient in company
            }
        }
    return results


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

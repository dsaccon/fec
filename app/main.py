# app/main.py

from fastapi import FastAPI

import datetime as dt
import asyncio
import ormar

from app.db import database, Transactions, CompanyDB, Candidates
from app.db import CompanyCommmitteeIdAPI, CompanyAPI, CompanyNameAPI
from app.db import CompanyIndustryAPI, CompanyRecipientAPI, CorporateDonationsAPI
from app.http_api import SingletonAioHttp

from dotenv import dotenv_values

app = FastAPI(title="FEC data collection API")

API_KEY=dotenv_values('.env').get('API_KEY_0')


# Admin endpoints

@app.post("/company/add/")
async def company_add(company: CompanyAPI):
    now = dt.datetime.utcnow()
    comp = await CompanyDB.objects.all(committee_id=company.committee_id, name=company.name)
    if len(comp) == 0:
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
            last_api_accessed=dt.datetime(1970, 1, 1),
            active=True)
    elif len(comp) == 1:
        await CompanyDB.objects.update_or_create(
            id=comp[0].id,
            industry=company.industry,
            starting_date=company.starting_date,
            metadata=company.metadata,
            statement=company.statement,
            broke_promise=company.broke_promise,
            created=comp[0].created,
            last_updated=now,
            active=True)
    else:
        return {'msg': 'unknown state'}
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
    candidates = await Candidates.objects.all(active=True)
    candidates = {
        c.committee_id: {
            'first_name': c.first_name,
            'last_name': c.last_name,
            'district': c.district,
            'state': c.state,
            'active': c.active,
            'priority': c.priority,
        }
        for c in candidates
    }
    for comp in companies:
        comp.name = comp.name.encode('utf-8').decode('unicode-escape')
        comp.industry = comp.industry.encode('utf-8').decode('unicode-escape')
        comp.metadata = comp.metadata.encode('utf-8').decode('unicode-escape')

    get_company_from_tx = lambda tx: [
        comp for comp in companies if comp.name == tx[0].get('company_name')
    ][0]

    comp_query = (
        f"SELECT company_name, SUM (amount)\n"
        f"  FROM transactions\n"
        f"  GROUP BY company_name\n"
        f"  ORDER BY SUM (amount) DESC\n")
    companies_tot_contr = await database.fetch_all(query=comp_query)

    aio_tasks = []
    for company in companies_tot_contr:
        active = get_company_from_tx([company]).active
        if not active:
            continue
        query = (
            f"SELECT candidate_id, company_name, SUM (amount)\n"
            f"  FROM transactions\n"
            f"  WHERE company_name = '{company.get('company_name')}'\n"
            f"  GROUP BY candidate_id, company_name\n"
            f"  ORDER BY SUM (amount) DESC\n")
        aio_tasks += [database.fetch_all(query=query)]
    sorted_txs = await asyncio.gather(*aio_tasks)
    for tx in sorted_txs:
        i_insert = -1
        for i, rcpt in enumerate(tx):
            if candidates[rcpt.get('candidate_id')]['priority']:
                item = tx.pop(i)
                i_insert += 1
                tx.insert(i_insert, item)

    results = {}
    for tx in sorted_txs:
        statement = get_company_from_tx(tx).statement
        tot_contr = [
            comp.get('sum')
            for comp in companies_tot_contr
            if comp.get('company_name') == tx[0].get('company_name')
        ][0]
        comp_committee_id = [
            c.committee_id for c in companies
            if c.name == tx[0].get('company_name')
        ][0]
        results[comp_committee_id] = {
            'statement': statement,
            'company_name': tx[0].get('company_name'),
            'total_contributions': tot_contr,
            'all_recipients': {
                rcpt.get('candidate_id'): {
                    'contributions': rcpt.get('sum'),
                    'first_name': candidates[rcpt.get('candidate_id')]['first_name'],
                    'last_name': candidates[rcpt.get('candidate_id')]['last_name'],
                    'district': candidates[rcpt.get('candidate_id')]['district'],
                    'state': candidates[rcpt.get('candidate_id')]['state'],
                    'active': candidates[rcpt.get('candidate_id')]['active'],
                }
                for rcpt in tx
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

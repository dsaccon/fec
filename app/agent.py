import os
import datetime as dt
import asyncio
import logging
import uvloop
from dotenv import dotenv_values, load_dotenv
import requests

from app.db import database, CompanyDB, Transactions
from app.http_api import SingletonAioHttp

load_dotenv()
API_KEY = os.environ.get('API_KEY')

url = 'https://api.open.fec.gov/v1/schedules/schedule_b/'


def get_params(committee_id):
    return {
        'sort_hide_null': 'false',
        'committee_id': committee_id,
        'per_page': 20,
        'api_key': API_KEY,
        'sort': '-disbursement_date',
        'sort_null_only': 'false'
    }

async def get_companies():
    return await CompanyDB.objects.all(active=True)

async def api_get_transactions(company):
    params = get_params(company)
    transactions = await SingletonAioHttp.query_url(url, data=params)
    return transactions.get('results')

async def db_get_transactions(company):
    transactions = await Transactions.objects.all(committee_id=company)
    return [tx.transaction_id for tx in transactions]

async def update_company_transactions(committee_id):
    transactions = await api_get_transactions(committee_id)
    if transactions is None:
        return
    db_transactions = await db_get_transactions(committee_id)
    api_transactions = {tx['transaction_id'] for tx in transactions}
    new_transactions = api_transactions - set(db_transactions)
    for txid in new_transactions:
        tx = [t for t in transactions if t['transaction_id'] == txid][0]
        txid = tx['transaction_id']
        cdid = tx['candidate_id']
        dscr = tx['disbursement_description']
        date = tx['disbursement_date']
        if txid is None:
            continue
            txid = ''
        if cdid is None:
            cdid = ''
        if date is None:
            date = ''
        if dscr is None:
            dscr = ''
        await Transactions.objects.create(
            transaction_id=txid,
            committee_id=tx['committee_id'],
            company_name=tx['committee']['name'],
            recipient_name=tx['recipient_name'],
            recipient_state=tx['recipient_state'],
            candidate_id=cdid,
            description=dscr,
            date=date,
            amount=tx['disbursement_amount']
        )
    if new_transactions:
        logging.info(f'New transactions added for {committee_id}: {new_transactions}')

async def startup():
    if not database.is_connected:
        await database.connect()
    SingletonAioHttp.get_aiohttp_client()

async def shutdown():
    if database.is_connected:
        await database.disconnect()
    await SingletonAioHttp.close_aiohttp_client()

async def main():
    await startup()

    while True:
        logging.info(dt.datetime.utcnow())
        companies = await get_companies()
        aio_tasks = []
        for cid in [c.committee_id for c in companies]: 
            aio_tasks += [update_company_transactions(cid)]
        await asyncio.gather(*aio_tasks)
        await asyncio.sleep(60)

    await shutdown()

if __name__ == '__main__':
    logfile = 'app/logs/agent.log'
    logging.basicConfig(filename=logfile, level=logging.INFO)
    uvloop.install()
    asyncio.run(main())
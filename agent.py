import os
import asyncio
import uvloop
from dotenv import dotenv_values, load_dotenv
import requests

from app.db import database, CompanyDB, Transactions
from app.http import SingletonAioHttp

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
    return await SingletonAioHttp.query_url(url, data=params)

async def db_get_transactions(company):
    transactions = await Transactions.objects.all(committee_id=company)
    return [tx.transaction_id for tx in transactions]

async def update_company_transactions(transactions):
    db_transactions = await db_get_transactions(transactions[0]['committee_id'])
    api_transactions = {tx['transaction_id'] for tx in transactions}
    new_transactions = api_transactions - set(db_transactions)
    for txid in new_transactions:
        tx = [t for t in transactions if t['transaction_id'] == txid][0]
        await Transactions.objects.create(
            transaction_id=tx['transaction_id'],
            committee_id=tx['committee_id'],
            company_name=tx['committee']['name'],
            recipient_name=tx['recipient_name'],
            recipient_state=tx['recipient_state'],
            description=tx['disbursement_description'],
            date=tx['disbursement_date'],
            amount=tx['disbursement_amount']
        )

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

    companies = await get_companies()
    companies_ids = [c.committee_id for c in companies]
    transactions = await api_get_transactions(companies_ids[0])
    await update_company_transactions(transactions['results'])
    quit()

    resp = await SingletonAioHttp.query_url(url, data=params)
#    url = f"https://www.fec.gov/data/committee/{'C00542365'}/?tab=spending#total-disbursements"
#    resp = await SingletonAioHttp.query_url(url)
    import json
    print(resp)
    print(json.dumps(resp, indent=4))
#    for r in resp['results']:
#        print(r['candidate_last_name'])
    await shutdown()

if __name__ == '__main__':
    uvloop.install()
    asyncio.run(main())

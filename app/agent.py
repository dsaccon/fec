import os
import json
import datetime as dt
import asyncio
import logging
import uvloop
from dotenv import dotenv_values, load_dotenv
import requests
from itertools import cycle

from app.db import database, CompanyDB, Transactions, TransactionsLog, Candidates
from app.http_api import SingletonAioHttp

load_dotenv()

url = 'https://api.open.fec.gov/v1/schedules/schedule_b/'

def get_api_keys():
    API_KEYS = []
    while True:
        if not os.environ.get(f'API_KEY_{len(API_KEYS)}') is None:
            API_KEYS.append(os.environ.get(f'API_KEY_{len(API_KEYS)}'))
        else:
            break
    return API_KEYS

API_KEYS_iter = cycle(get_api_keys())

# Company Transactions related
def get_api_params(committee_id: str, last_indexes: dict, tx_period: str, start: str=''):
    params = {
        'sort_hide_null': 'false',
        'committee_id': committee_id,
        'two_year_transaction_period': tx_period,
        'per_page': 100,
        'api_key': next(API_KEYS_iter),
        'sort': '-disbursement_date',
        'sort_null_only': 'false'
    }
    params.update(last_indexes)
    if start:
        params.update({'min_date': start})
    return params

async def get_companies():
    return await CompanyDB.objects.all(active=True)

async def api_get_transactions(company: CompanyDB):
    committee_id = company.committee_id
    _start = [int(d) for d in company.starting_date.split('-')]
    _start = dt.datetime(year=_start[0], month=_start[1], day=_start[2])
    if company.last_api_accessed > _start:
        clai = company.last_api_accessed
        start = f'{clai.year}-{clai.month}-{clai.day}'
    else:
        start = company.starting_date
    last_indexes = {}
    tx_period = dt.datetime.utcnow().year + dt.datetime.utcnow().year%2 
    tx_periods = (tx_period,)
    if (tx_period - int(start[:4])) > 2:
        i = 1
        while True:
            tx_periods += (tx_period - 2*i,)
            i += 1
            if tx_period - 2*i < int(start[:4]) + dt.datetime.utcnow().year%2:
                break
    transactions = []
    for tx_per in tx_periods:
        while True:
            now = int(dt.datetime.utcnow().timestamp()) ### tmp
            params = get_api_params(committee_id, last_indexes, tx_per, start)
            txs = await SingletonAioHttp.query_url(url, data=params)
            if 'results' in txs and len(txs['results']) > 0:
                print(now, '0:', committee_id, len(txs['results'])) ### tmp
                transactions += txs.get('results')
                last_indexes = txs.get('pagination')['last_indexes']
            elif 'error' in txs and txs['error']['code'] == 'OVER_RATE_LIMIT':
                await asyncio.sleep(0.5)
                print('rate limit error:', committee_id) ### tmp
            elif 'error' in txs:
                await asyncio.sleep(0.5)
                print('error:', txs['error']['code'], committee_id) ### tmp
            else:
                try:
                    print(now, '1:', committee_id, len(txs['results']))
                except:
                    print(now, '1(exception:', txs)
                break
    print(now, '2:', committee_id, len(transactions)) ### tmp
    return transactions

async def db_get_transactions(committee_id: str):
    transactions = await Transactions.objects.all(committee_id=committee_id)
    return [tx.transaction_id for tx in transactions]

async def update_company_transactions(company: CompanyDB):
    now = dt.datetime.utcnow()
    kwargs = {'last_api_accessed': now}
    transactions = await api_get_transactions(company)
    if transactions is None:
        await CompanyDB.objects.filter(committee_id=company.committee_id).update(**kwargs)
        return
    db_transactions = await db_get_transactions(company.committee_id)
    api_transactions = {tx['transaction_id'] for tx in transactions}
    new_transactions = api_transactions - set(db_transactions)
    aio_tx_objs = []
    added_transactions = []
    for txid in new_transactions:
        tx = [t for t in transactions if t['transaction_id'] == txid][0]
        candidate = await Candidates.objects.filter(committee_id=tx['recipient_committee_id']).all()
        txid = tx['transaction_id']
        cdid = tx['recipient_committee_id']
        dscr = tx['disbursement_description']
        date = tx['disbursement_date']
        if txid is None:
            continue
        if cdid is None:
            continue
        if date is None:
            date = ''
        if dscr is None:
            dscr = ''
        if len(candidate) == 0:
            pass
        elif len(candidate) == 1:
            aio_tx_objs.append(Transactions.objects.create(
                transaction_id=txid,
                committee_id=tx['committee_id'],
                company_name=company.name,
                industry=company.industry,
                recipient_name=f'{candidate[0].first_name} {candidate[0].last_name}',
                recipient_state=candidate[0].state,
                candidate_id=cdid,
                description=dscr,
                date=date,
                amount=tx['disbursement_amount']))
            added_transactions.append(txid)
        else:
            raise ValueError
        aio_tx_objs.append(TransactionsLog.objects.create(
            timestamp=now,
            data=json.dumps(tx)))
    await asyncio.gather(*aio_tx_objs)
    if added_transactions:
        kwargs.update({'last_updated': now})
        logging.info(f'New transactions added for {company.committee_id}: {added_transactions}')

    await CompanyDB.objects.filter(committee_id=company.committee_id).update(**kwargs)


async def main():
    await startup()

    while True:
        logging.info(dt.datetime.utcnow())
        companies = await get_companies()
        aio_tasks = []
        for company in companies:
            aio_tasks += [update_company_transactions(company)]
        await asyncio.gather(*aio_tasks)
        await asyncio.sleep(60)

    await shutdown()

#
async def startup():
    if not database.is_connected:
        await database.connect()
    SingletonAioHttp.get_aiohttp_client()

async def shutdown():
    if database.is_connected:
        await database.disconnect()
    await SingletonAioHttp.close_aiohttp_client()


if __name__ == '__main__':
    logfile = 'app/logs/agent.log'
    logging.basicConfig(filename=logfile, level=logging.INFO)
    uvloop.install()
    asyncio.run(main())

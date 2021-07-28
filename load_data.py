import os
import csv
import json
import subprocess
import asyncio
import asyncpg
import psycopg2
import requests
import databases
import datetime as dt
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get('API_KEY')

def get_ip():
    cmd = ('sudo', 'docker', 'inspect', 'fec_db_1')
    txt = json.loads(subprocess.check_output(cmd).decode('utf-8'))
    ip_addr = txt[0]['NetworkSettings']['Networks']['fec_default']['IPAddress']
    return ip_addr

def build_query_candidates():
    objectors = []
    with open('objectors.csv') as f:
        csv_reader = csv.reader(f, delimiter=',')
        for row in csv_reader:
            objectors.append(row)

    query = "INSERT INTO candidates (committee_id, first_name, last_name, district, state, active, priority)\n"
    query += "VALUES\n"
    for o in objectors[1:]:
        query += f"('{o[0]}','{o[1]}','{o[2]}',NULL,'{o[4]}',True, False),\n"
    query = query[:-2] + ';'
    return query

async def run_candidates_async():
    conn = await asyncpg.connect(
        user='fec_db',
        password='fec_db',
        database='fec_db',
        host=get_ip())
    await conn.execute(build_query_candidates())

def build_query_companies():
    companies = []
    with open('companies.csv') as f:
        csv_reader = csv.reader(f, delimiter=',')
        for row in csv_reader:
            companies.append(row)
    now = dt.datetime.utcnow()
    query = "INSERT INTO company (committee_id, name, industry, starting_date, metadata, statement, broke_promise, created, last_updated, last_api_accessed, active)\n"
    query += "VALUES\n"
    for c in companies[1:]:
        name = c[0].replace("'", "''")
        query += f"('{c[2]}','{name}','tbd','2021-01-01','',False,False,'{now}','{now}','{dt.datetime(1970,1,1)}',True),\n"
    query = query[:-2] + ';'
    return query

async def run_companies_async():
    conn = await asyncpg.connect(
        user='fec_db',
        password='fec_db',
        database='fec_db',
        host=get_ip())
    await conn.execute(build_query_companies())

def run_sync():
    try:
        conn = psycopg2.connect(
            user='fec_db',
            password='fec_db',
            host=get_ip(),
            port=5432,
            database='fec_db')

        cursor = conn.cursor()

        objectors = []
        with open('objectors.csv') as f:
            csv_reader = csv.reader(f, delimiter=',')
            for row in csv_reader:
                objectors.append(row)

        query = "INSERT INTO candidates (committee_id, first_name, last_name, district, state, active)\n"
        query += "VALUES\n"
        for o in objectors[1:]:
            #query += f"('{o[0]}','{o[1]}','{o[2]}',NULL,'{o[4]}',True),\n"
            _query = query + f"('{o[0]}','{o[1]}','{o[2]}',NULL,'{o[4]}',True),\n"
            _query = _query[:-2] + ';'
            print(_query)
            cursor.execute(_query)
            print('')
    #    query = query[:-2]
    #    query += ';'
    #    print(query)
    #    query = "SELECT * FROM candidates"
    #    print(query)
    #    cursor.execute(query)
    #    x = cursor.fetchall()
    #    print('--', x)
    #    print('done')
    except Exception as e:
        print(e)
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("PostgreSQL connection is closed")

def add_companies():
    url = 'http://ec2-35-81-83-141.us-west-2.compute.amazonaws.com:8008/company/add'
    companies = [
        {
            "committee_id": "C00121368",
            "name": "exxon",
            "industry": "energy",
            "starting_date": "2021-01-01",
            "metadata": "eee",
            "statement": False,
            "broke_promise": False
        },
        {
            "committee_id": "C00142711",
            "name": "boeing",
            "industry": "aerospace",
            "starting_date": "2021-01-15",
            "metadata": "aa",
            "statement": False,
            "broke_promise": False
        },
        {
            "committee_id": "C00303024",
            "name": "lockheed martin",
            "industry": "aerospace",
            "starting_date": "2021-02-15",
            "metadata": "bb",
            "statement": False,
            "broke_promise": False
        },
        {
            "committee_id": "C00227546",
            "name": "microsoft",
            "industry": "software",
            "starting_date": "2021-01-16",
            "metadata": "bbcc",
            "statement": False,
            "broke_promise": False
        },
        {
            "committee_id": "C00204099",
            "name": "john deere",
            "industry": "agriculture",
            "starting_date": "2021-02-16",
            "metadata": "gggeee",
            "statement": False,
            "broke_promise": False
        },
        {
            "committee_id": "C00096156",
            "name": "honeywell",
            "industry": "industrial",
            "starting_date": "2021-05-15",
            "metadata": "hhh",
            "statement": False,
            "broke_promise": False
        },
        {
            "committee_id": "C00024869",
            "name": "ge",
            "industry": "industrial",
            "starting_date": "2021-02-01",
            "metadata": "eee",
            "statement": False,
            "broke_promise": False
        },
        {
            "committee_id": "C00350744",
            "name": "goldman sachs",
            "industry": "financial",
            "starting_date": "2021-01-03",
            "metadata": "eee",
            "statement": False,
            "broke_promise": False
        },
        {   
            "committee_id": "C00300707",
            "name": "accenture",
            "industry": "consulting",
            "starting_date": "2021-03-03",
            "metadata": "ttt",
            "statement": False,
            "broke_promise": False
        },
        {
            "committee_id": "C00104802",
            "name": "delta airlines",
            "industry": "airlines",
            "starting_date": "2021-01-01",
            "metadata": "ttt",
            "statement": False,
            "broke_promise": False
        }
    ]
    for comp in companies:
        r = requests.post(url, data=json.dumps(comp))

def get_api_params(committee_id: str, last_indexes: dict, tx_period: str, start: str=''):
    params = {
        'sort_hide_null': 'false',
        'committee_id': committee_id,
        'two_year_transaction_period': tx_period,
        'per_page': 100,
        'api_key': API_KEY,
        'sort': '-disbursement_date',
        'sort_null_only': 'false'
    }
    params.update(last_indexes)
    if start:
        params.update({'min_date': start})
    return params

def get_txs():
    url = 'https://api.open.fec.gov/v1/schedules/schedule_b/'
    last_indexes = {}
    params = get_api_params('C00142711', last_indexes, 2022, '2021-01-15')
    print(params)
    result = requests.get(url, params=params)
    print(result, len(result.json()['results']))
    print('--')
    #
    last_indexes = result.json()['pagination']['last_indexes']
    params = get_api_params('C00142711', last_indexes, 2022, '2021-01-15')
    print(params)
    result = requests.get(url, params=params)
    print(result, len(result.json()['results']))

if __name__ == '__main__':
#    get_txs()
    asyncio.run(run_candidates_async())
    asyncio.run(run_companies_async())
#    add_companies()

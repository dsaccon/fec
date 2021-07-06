import json
import asyncio
from socket import AF_INET
from typing import Optional, Any

import aiohttp

SIZE_POOL_AIOHTTP = 100


class SingletonAioHttp:
    sem: Optional[asyncio.Semaphore] = None
    aiohttp_client: Optional[aiohttp.ClientSession] = None

    @classmethod
    def get_aiohttp_client(cls) -> aiohttp.ClientSession:
        if cls.aiohttp_client is None:
            timeout = aiohttp.ClientTimeout(total=2)
            connector = aiohttp.TCPConnector(family=AF_INET, limit_per_host=SIZE_POOL_AIOHTTP)
            cls.aiohttp_client = aiohttp.ClientSession(timeout=timeout, connector=connector)

        return cls.aiohttp_client

    @classmethod
    async def close_aiohttp_client(cls) -> None:
        if cls.aiohttp_client:
            await cls.aiohttp_client.close()
            cls.aiohttp_client = None

    @classmethod
    async def query_url(cls, url: str, method: str='get', data: dict=None) -> Any:
        client = cls.get_aiohttp_client()
        meth = getattr(client, method)
        if data is None:
            data = {}
        try:
            async with meth(url, params=data) as response:
                if response.status != 200:
                    return {"ERROR OCCURED" + str(await response.text())}
                json_result = await response.json()
        except Exception as e:
            return {"ERROR": e}
        return json_result

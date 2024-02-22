import asyncio
import json
import random

import aiohttp
from aiohttp_socks import ProxyConnector
from loguru import logger
from eth_utils import to_wei
from info.other_info import proxies, keys
from wallet.wallet_utils import get_wallet_private_key


async def sleep_indicator(secs, info):
    logger.info(f'{info} - жду {secs} секунд')
    await asyncio.sleep(secs)


def format_amount(amount):
    return to_wei(amount, 'ether')


async def eth_price():
    try:
        proxy_ = random.choice(proxies) if proxies else None
        if proxy_:
            proxy = f'http://{proxy_}'
        else:
            proxy = proxy_
        url = f'https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd'
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy) as response:
                if response.status == 200:
                    text = json.loads(await response.text())
                    eth_price_ = text['ethereum']['usd']
                    return eth_price_
                else:
                    await asyncio.sleep(1)
                    return await eth_price()

    except Exception as e:
        logger.error(e)
        await asyncio.sleep(1)
        return await eth_price()


async def proxy_checker(proxy):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://jsonip.com/', proxy=proxy) as response:
                if response.status == 200:
                    logger.success(f'Proxy is valid - {proxy}')
                    return True
                else:
                    logger.error(f'Proxy is not valid - {proxy}')
                    return False
    except Exception as e:
        logger.error(e)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://github.com/', proxy=proxy) as response:
                    if response.status == 200:
                        logger.success(f'Proxy is valid - {proxy}')
                        return True
                    else:
                        logger.error(f'Proxy is not valid - {proxy}')
                        return False
        except Exception as e:
            logger.error(e)
            logger.error(f'Proxy is not valid - {proxy}')
            return False


async def validate_proxy(proxy):
    proxy_ = proxy if proxy else random.choice(proxies) if proxies else None
    proxy_url = f'http://{proxy_}' if proxy_ else None
    if proxy_url:
        status_proxy = await proxy_checker(proxy_url)
        if not status_proxy:
            logger.info(f'Пробую еще раз с новой прокси...')
            new_proxy = random.choice(proxies) if proxies else None
            if not new_proxy:
                logger.error('Не вставлены прокси для замены в файл proxies.txt!...')
                return False
            return 'new'
        return proxy_url
    else:
        return 'not proxy'


async def setup_proxy(proxy):
    get_proxy = await validate_proxy(proxy)
    if get_proxy == 'new':
        return await setup_proxy(proxy)
    if not get_proxy:
        return
    if get_proxy == 'not proxy':
        get_proxy = None

    return get_proxy


def get_random(from_, to):
    return random.randint(from_, to)


def get_session(proxy=None):
    session = aiohttp.ClientSession(connector=ProxyConnector.from_url(proxy, limit_per_host=0))
    return session


def connect_keys():
    key_pairs = []
    for n, key in enumerate(keys):
        pair = key.split(';')
        if len(pair) == 2:
            key_pairs.append(f'{n + 1};{pair[0]};{pair[1]}')
        else:
            key_pairs.append(f'{n + 1};{pair[0]};')
    return key_pairs


def get_batches():
    keys_info = connect_keys()
    if proxies:
        proxies_ = proxies
        while len(proxies) < len(keys_info):
            for i in range(len(proxies_)):
                proxies.append(proxies_[i])
                if len(proxies) == len(keys_info):
                    break
        keys_ = zip(keys_info, proxies)
        return [f"{key};{proxy}" for key, proxy in keys_]
    else:
        return [f'{key};' for key in keys_info]

def get_data_wallets(key):
    data_wallet = key.split()
    if len(data_wallet) == 12:
        return 'seeds'
    elif len(data_wallet) == 1:
        return 'private_keys'
    else:
        logger.error('НЕПРАВИЛЬНО ВСТАВЛЕНЫ ДАННЫЕ ОТ КОШЕЛЬКОВ В keys.txt...')
        return


async def check_key(key: str):
    if get_data_wallets(key) == 'seeds':
        return await get_wallet_private_key(key)
    else:
        if key.startswith('0x'):
            return key
        else:
            return hex(int(key))
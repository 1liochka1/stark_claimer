import asyncio
import json as js
import sys

import aiohttp
from loguru import logger
from starknet_py.net.account.account import Account
from abi.abi import starknet_token_abi
from core.other_utils import format_amount
from core.utils import Starknet_account, get_contract
from info.tokens import starknet_tokens_addresses
from twocaptcha import TwoCaptcha
from config import _2captcha

sys.setrecursionlimit(5000)

def check_status_tx(status, tx_url):
    if status.value in ['ACCEPTED_ON_L2']:
        logger.success(f'Транзакция подтвердилась {tx_url} ...')
        return True
    else:
        logger.error(f'Ошибка транзакции {tx_url} ...')
        return False

async def solve_captcha():
    try:
        solver = TwoCaptcha(_2captcha)
        result = solver.recaptcha(sitekey='6Ldj1WopAAAAAGl194Fj6q-HWfYPNBPDXn-ndFRq',
                                  url='https://provisions.starknet.io/',
                                  version='v3', enterprise=1)
        g_response = result['code']
        return g_response
    except Exception as e:
        logger.error(e)
        await asyncio.sleep(1)
        return await solve_captcha()

async def send_request(url, method, *, params=None, json=None, headers=None, proxy=None):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, params=params, json=json,
                                       proxy=proxy) as response:
                if response.status == 200:
                    return js.loads(await response.text())
                await asyncio.sleep(1)
                logger.error(f'Ошибка при отправке запроса {url}: {await response.text()}...')
                return
    except Exception as e:
        logger.error(f'Ошибка - {e}...')
        return

async def get_proof(captcha, address=0x00f195f8d6108b5de4eb46dcc0e3303f575b93b32a95aebc15fb16c9c914c728, proxy='http://user65924:k8wpzf@23.247.247.221:9783'):
    try:
        headers = {
            'authority': 'provisions.starknet.io',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
            'referer': 'https://provisions.starknet.io/',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-recaptcha-token': captcha,
        }
        params = {
            'identity': address,
        }
        async with aiohttp.ClientSession() as session:
            async with session.request('GET', 'https://provisions.starknet.io/api/starknet/claim', headers=headers, params=params,
                                       proxy=proxy) as response:
                print(await response.text())
                if response.status == 403:
                    return 'again'
                if response.status == 200:
                    return js.loads(await response.text())
    except Exception as e:
        logger.error(f'{address} - {e}')
        return
class Claimer:
    def __init__(self):
        self.account: Account = None
        self.info = ''
        self.proxy = ''
        self.address_to = ''

    @classmethod
    async def create(cls, account: Starknet_account):
        self = Claimer()
        self.account = await account.get_account()
        self.proxy = account.proxy
        self.info = account.acc_info
        self.address_to = account.address_to
        return self

    async def claim(self, captcha):
        headers = {
            'authority': 'provisions.starknet.io',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://provisions.starknet.io',
            'referer': 'https://provisions.starknet.io/',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "YaBrowser";v="24.1", "Yowser";v="2.5"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 YaBrowser/24.1.0.0 Safari/537.36',
            'x-recaptcha-token': captcha,
        }

        json_data = {
            'identity': hex(self.account.address),
            'recipient': hex(self.account.address),
        }
        async with aiohttp.ClientSession() as session:
            async with session.request('POST', 'https://provisions.starknet.io/api/starknet/claim', headers=headers, json=json_data,
                                       proxy=self.proxy) as response:
                if response.status == 200:
                    logger.success(f'{self.info} - успешно заклеймил')
                return await self.create_transfer_call(self.address_to)

    async def create_transfer_call(self, address_to):
        while True:
            amount = await self.account.get_balance(starknet_tokens_addresses['stark'])
            if amount == 0:
                logger.debug(f'{self.info} - баланс еще не пополнен')
                await asyncio.sleep(15)
                continue
            try:
                contract = await get_contract(starknet_tokens_addresses['stark'], starknet_token_abi, self.account.client)
                call = contract.functions['transfer'].prepare(int(address_to, 16), format_amount(amount))
                tx = await self.account.execute([call], auto_estimate=True)
                status = await self.account.client.wait_for_tx(tx.transaction_hash)
                tx_url = f'https://starkscan.co/tx/{hex(tx.transaction_hash)}'
                if check_status_tx(status.finality_status, tx_url):
                    logger.success(f'{self.info} - успешно заклеймил и отправил {amount / 10 ** 18} STRK - {tx_url}')
                    return True
            except Exception as e:
                logger.error(e)
                await asyncio.sleep(1)
                continue



import asyncio
import json
import json as js
import sys

import aiohttp
from loguru import logger
from starknet_py.net.account.account import Account
from abi.abi import starknet_token_abi, claim_abi
from core.other_utils import format_amount
from core.utils import Starknet_account, get_contract
from info.starknet_info import claim_address
from info.tokens import starknet_tokens_addresses

sys.setrecursionlimit(5000)

def check_status_tx(status, tx_url):
    if status.value in ['ACCEPTED_ON_L2']:
        logger.success(f'Транзакция подтвердилась {tx_url} ...')
        return True
    else:
        logger.error(f'Ошибка транзакции {tx_url} ...')
        return False



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

    async def get_proof(self, address):
        with open('addresses_proofs.json', 'r') as f:
            data = json.load(f)

        if address in data:
            return data[address]

    async def claim(self, amount, index, proof):
        try:
            contract = await get_contract(claim_address, claim_abi, self.account.client, 1)
            claim_call = contract.functions['claim'].prepare({"identity":self.account.address,
                                                        "balance": format_amount(amount),
                                                        "index": index,
                                                        "merkle_path": [int(i, 16) for i in proof] })
            contract_strk = await get_contract(starknet_tokens_addresses['stark'], starknet_token_abi, self.account.client)
            call = contract_strk.functions['transfer'].prepare(int(self.address_to, 16), format_amount(amount))
            tx = await self.account.execute([claim_call, call], auto_estimate=True)
            status = await self.account.client.wait_for_tx(tx.transaction_hash)
            tx_url = f'https://starkscan.co/tx/{hex(tx.transaction_hash)}'
            if check_status_tx(status.finality_status, tx_url):
                logger.success(f'{self.info} - успешно заклеймил и отправил {amount / 10 ** 18} STRK - {tx_url}')
                return True
        except Exception as e:
            logger.error(e)
            await asyncio.sleep(1)
            return

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
                    logger.success(f'{self.info} - успешно заклеймил и отправил {amount} STRK - {tx_url}')
                    return True
            except Exception as e:
                logger.error(e)
                await asyncio.sleep(1)
                continue



import asyncio
import functools

from aiohttp.client_exceptions import ClientConnectorError
from loguru import logger
from python_socks._errors import ProxyError, ProxyTimeoutError, ProxyConnectionError
from starknet_py.contract import Contract
from starknet_py.net.account.account import Account, _parse_calls_v2, _execute_payload_serializer_v2, \
    _execute_payload_serializer, _merge_calls
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.models import StarknetChainId, Invoke
from starknet_py.utils.iterable import ensure_iterable

from config import rpc
from core.other_utils import get_session
from info.tokens import (starknet_tokens_addresses)
from wallet.wallet_utils import get_wallet_address
from wallet.starknet_utils import get_keypair


class Starknet_account:
    def __init__(self, key, id: int, address_to=None, proxy=None):
        self.proxy_ = proxy if proxy else None
        self.session = get_session(proxy) if proxy else None
        self.client = self.setup_client()
        self._address = ''
        self._address_to = address_to
        self.key = key
        self.id = id
        self.wallet_type = ''

    @property
    def acc_info(self):
        return f'{self.id}) {self.address}:{self.wallet_type}'

    @property
    def proxy(self):
        return self.proxy_

    @property
    def address(self):
        return self._address

    @property
    def address_to(self):
        return self._address_to

    async def close(self):
        if self.session:
            await self.session.close()

    def setup_client(self):
        return FullNodeClient(rpc, session=self.session)

    async def get_account(self):
        self._address, self.wallet_type = await get_wallet_address(self.key, self.client)
        address = self._address[2:]
        while len(str(address)) < 64:
            address = "0" + address
        self._address = '0x' + address
        return Account(
            address=self._address,
            client=self.client,
            key_pair=await get_keypair(self.key),
            chain=StarknetChainId.MAINNET
        )


async def get_fee(calls, account: Account):
    try:
        if await account.cairo_version == 1:
            parsed_calls = _parse_calls_v2(ensure_iterable(calls))
            wrapped_calldata = _execute_payload_serializer_v2.serialize(
                {"calls": parsed_calls}
            )
        else:
            call_descriptions, calldata = _merge_calls(ensure_iterable(calls))
            wrapped_calldata = _execute_payload_serializer.serialize(
                {"call_array": call_descriptions, "calldata": calldata}
            )

        max_fee = await account._get_max_fee(Invoke(
            calldata=wrapped_calldata,
            signature=[],
            max_fee=0,
            version=1,
            nonce=await account.get_nonce(),
            sender_address=account.address,
        ), auto_estimate=True)
        return max_fee
    except Exception as e:
        logger.error(f'{hex(account.address)} - {e}')
        return

def tx_exceptor(info, address=None):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (ProxyError, ProxyTimeoutError, ProxyConnectionError):
                logger.error('Отъебнуло прокси, пробую еще раз...')
                await asyncio.sleep(1)
                return await resend(info, func, address=address, *args, **kwargs)
            except ClientConnectorError as e:
                logger.error(e)
                if e.ssl is None:
                    return await resend(info, func, address=address, *args, **kwargs)
                else:
                    return False
            except Exception as e:
                if 'The server encountered a temporary error and could not complete your request' in str(
                        e) or 'Cannot connect to host' in str(e) or 'Too Many Requests' in str(e):
                    logger.error('Ошибка подключения к рпц старкнета, пробую еще раз...')
                    await asyncio.sleep(5)
                    return await resend(info, func, address=address, *args, **kwargs)
                elif 'Account balance must be greater or equal' in str(e):
                    logger.error('Нет баланса эфира...')
                    await asyncio.sleep(1)
                    return 'balance'
                elif 'Insufficient max fee: max_fee' in str(e):
                    logger.error(f'{info} - газ повысился и транза не может быть отправлена, пробую ещё раз...')
                    await asyncio.sleep(1)
                    return await resend(info, func, address=address, *args, **kwargs)
                elif "Couldn't connect to proxy" in str(e):
                    logger.error('Отъебнуло прокси, пробую еще раз...')
                    await asyncio.sleep(1)
                    return await resend(info, func, address=address, *args, **kwargs)
                logger.error(f"{info} - ошибка : {e}")
                return False

        return wrapper

    return decorator


async def resend(info, func, *args, address=None, **kwargs):
    @tx_exceptor(info, address)
    async def resend_():
        return await func(*args, **kwargs)

    return await resend_()


@tx_exceptor('get balance')
async def get_balance(account: Account, token=None, token_address=None):
    balance = await account.get_balance(starknet_tokens_addresses[token] if token else token_address,
                                        StarknetChainId.MAINNET)
    return balance


async def get_contract(address, abi, client, version=0) -> Contract:
    return Contract(address, abi, client, cairo_version=version)

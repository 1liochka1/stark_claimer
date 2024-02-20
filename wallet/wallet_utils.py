import asyncio
import hashlib

import bip32
import bip39
from aiohttp import ClientConnectorError
from hdwallet import (HDWallet, BIP44HDWallet)
from hdwallet.cryptocurrencies import EthereumMainnet
from loguru import logger
from python_socks import ProxyError, ProxyTimeoutError, ProxyConnectionError
from starknet_py.constants import EC_ORDER
from starknet_py.hash.address import compute_address
from starknet_py.net.client_errors import ClientError
from starknet_py.net.full_node_client import FullNodeClient

from config import wallet_type, rpcs
from info.starknet_info import (ARGENT_CLASS_HASH, ARGENT_OLD_CLASH_HASH, ARGENT_PROXY_CLASS_HASH)
from info.starknet_info import (BRAAVOS_CLASS_HASH, BRAAVOS_PROXY_CLASS_HASH)
from info.starknet_info import base_path
from wallet.starknet_utils import (create_constructor_call_data, get_starknet_keypair_public_key)


async def mod(a, b):
    result = a % b
    return result if result >= 0 else b + result


async def ensure_bytes(seed):
    if isinstance(seed, str):
        if seed.startswith('0x'):
            seed = seed[2:]
        return bytes.fromhex(seed)
    elif isinstance(seed, bytes):
        return seed
    else:
        logger.error("Seed must be a string or bytes")
        return


async def sha256_num(data):
    if isinstance(data, str):
        data = data.encode()
    h = hashlib.sha256(data)
    return int.from_bytes(h.digest(), byteorder='big')


async def number_to_var_bytes_be(n):
    hex_string = format(n, 'x')
    if len(hex_string) % 2 != 0:
        hex_string = '0' + hex_string
    return bytes.fromhex(hex_string)


async def grind_key(seed):
    _seed = await ensure_bytes(seed)
    if not _seed:
        return
    sha256mask = 2 ** 256
    limit = sha256mask - await mod(sha256mask, EC_ORDER)
    for i in range(100001):
        key = await sha256_num(_seed + await number_to_var_bytes_be(i))
        if key < limit:
            return hex(await mod(key, EC_ORDER))

    logger.error('grindKey is broken: tried 100k vals')
    return


async def get_private_argent_(seed):
    signer = BIP44HDWallet(cryptocurrency=EthereumMainnet).from_mnemonic(seed)
    master_node = HDWallet(cryptocurrency=EthereumMainnet).from_seed(signer.private_key())
    child_node = master_node.from_path(base_path)
    return await grind_key(child_node.private_key())


async def get_private_braavos_(mnemonic):
    seed = bip39.phrase_to_seed(mnemonic)
    hd_key = bip32.BIP32.from_seed(seed)
    derived = hd_key.get_privkey_from_path(base_path)
    key = '0x' + derived.hex()
    return await grind_key(key)


async def get_address(key, account_class_hash, proxy_class_hash):
    public_key = await get_starknet_keypair_public_key(key)
    address = compute_address(
        salt=public_key,
        class_hash=account_class_hash if account_class_hash == ARGENT_CLASS_HASH else proxy_class_hash,
        constructor_calldata=await create_constructor_call_data(account_class_hash, public_key),
        deployer_address=0,
    )
    return hex(address)


async def get_braavos_address(key):
    return await get_address(key, BRAAVOS_CLASS_HASH, BRAAVOS_PROXY_CLASS_HASH)


async def get_argent_address(key):
    return await get_address(key, ARGENT_CLASS_HASH, ARGENT_PROXY_CLASS_HASH)


async def get_old_argent_address(key):
    return await get_address(key, ARGENT_OLD_CLASH_HASH, ARGENT_PROXY_CLASS_HASH)


async def get_private_braavos(seed):
    return await get_private_braavos_(seed)


async def get_private_argent(seed):
    return await get_private_argent_(seed)


async def check_class_hash(address, client):
    class_hash = await client.get_class_hash_at(address)
    if class_hash:
        return True
    else:
        return False


async def check_and_get_argent_address(key, client=FullNodeClient(rpcs['stark'])):
    try:
        address = await get_argent_address(key)
        class_hash = await check_class_hash(address, client)
        if class_hash:
            return address
    except ClientError as e:
        if 'is not deployed' in str(e) or 'Contract not found' in str(e):
            try:
                address = await get_old_argent_address(key)
                class_hash = await check_class_hash(address, client)
                if class_hash:
                    return address
            except ClientError as e:
                if 'is not deployed' in str(e) or 'Contract not found' in str(e):
                    logger.error(
                        f'{key[:6]}...{key[60:]} - Не нашел версию для данного ключа, возможно он не был задеплоен...')
                    return False
                else:
                    return await check_and_get_argent_address(key, client)
        else:
            logger.error(e)
            return await check_and_get_argent_address(key, client)
    except ClientConnectorError as e:
        logger.error(e)
        if ClientConnectorError.ssl == 'default':
            return await get_wallet_address(key, client)
        else:
            return False
    except (ProxyError, ProxyTimeoutError, ProxyConnectionError):
        logger.error('Отъебнуло прокси, пробую еще раз...')
        await asyncio.sleep(1)
        return await get_wallet_address(key, client)
    except Exception as e:
        if 'Cannot connect to host' in str(e):
            return await check_and_get_argent_address(key, client)
        logger.error(e)
        return False


async def get_wallet_address(key, client=FullNodeClient(rpcs['stark'])):
    try:
        address = await get_argent_address(key)
        class_hash = await check_class_hash(address, client)
        if class_hash:
            return address, 'argent'
    except ClientError as e:
        if 'is not deployed' in str(e) or 'Contract not found' in str(e):
            try:
                address = await get_old_argent_address(key)
                class_hash = await check_class_hash(address, client)
                if class_hash:
                    return address, 'argent'
            except ClientConnectorError as e:
                logger.error(e)
                if ClientConnectorError.ssl == 'default':
                    return await get_wallet_address(key, client)
                else:
                    return False
            except ClientError as e:
                try:
                    address = await get_braavos_address(key)
                    class_hash = await check_class_hash(address, client)
                    if class_hash:
                        return address, 'braavos'
                except ClientConnectorError as e:
                    logger.error(e)
                    if ClientConnectorError.ssl == 'default':
                        return await get_wallet_address(key, client)
                    else:
                        return False
                except ClientError as e:
                    if 'is not deployed' in str(e) or 'Contract not found' in str(e):
                        logger.error(
                            f'{key[:6]}...{key[60:]} - Не нашел версию для данного ключа, возможно он не был задеплоен...')
                        return False
                    elif "Couldn't connect to proxy" in str(e):
                        return await get_wallet_address(key, client)
                    else:
                        return await get_wallet_address(key, client)
        else:
            logger.error(e)
            return await get_wallet_address(key, client)
    except ClientConnectorError as e:
        logger.error(e)
        if ClientConnectorError.ssl == 'default':
            return await get_wallet_address(key, client)
        else:
            return False
    except (ProxyError, ProxyTimeoutError, ProxyConnectionError):
        logger.error('Отъебнуло прокси, пробую еще раз...')
        await asyncio.sleep(1)
        return await get_wallet_address(key, client)
    except Exception as e:
        if 'Cannot connect to host' in str(e) or "Couldn't connect to proxy" in str(e):
            return await get_wallet_address(key, client)
        logger.error(e)
        return False

async def _get_wallet_address(key, client=FullNodeClient(rpcs['stark'])):
    address = await get_wallet_address(key, client)
    if not address:
        return


async def get_wallet_address_not_deployed(key):
    if wallet_type == 'braavos':
        return await get_braavos_address(key)
    else:
        return await get_argent_address(key)


async def get_wallet_private_key(seed):
    if wallet_type == 'braavos':
        return await get_private_braavos(seed)
    else:
        return await get_private_argent(seed)


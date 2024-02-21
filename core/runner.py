from core.other_utils import check_key, setup_proxy
from core.tasks import Claimer
from core.utils import Starknet_account
from loguru import logger
from config import rpc


async def start(id, key, proxy=None, address_to=None, task=''):
    if not rpc:
        logger.error('НЕ ВСТАВЛЕНА РПЦ ОТ СТАРКА В КОНФИГЕ...')
        return
    key = await check_key(key)
    proxy = await setup_proxy(proxy)
    starknet_account = Starknet_account(key, id, address_to, proxy)
    claimer = await Claimer.create(starknet_account)
    if task == 'claim':
        proof = await claimer.get_proof(starknet_account.address)
        if not proof:
            logger.error(f'{starknet_account.acc_info} - нечего клеймить')
            await starknet_account.close()
            return
        amount, index, merkle = int(proof['amount']), int(proof[ "merkle_index"]), proof["merkle_path"]
        logger.debug(f'{starknet_account.acc_info} - начинаю клейм')
        await claimer.claim(amount, index, merkle)
    elif task == 'strk':
        await claimer.transfer_strk()
    else:
        await claimer.transfer_eth()

    await starknet_account.close()
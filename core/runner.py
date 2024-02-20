from core.other_utils import check_key, setup_proxy
from core.tasks import Claimer, get_proof
from core.utils import Starknet_account
from loguru import logger



async def start(id, key, captcha, proxy=None, address_to=None, task=''):
    key = await check_key(key)
    proxy = await setup_proxy(proxy)
    starknet_account = Starknet_account(key, id,address_to, proxy)
    claimer = await Claimer.create(starknet_account)
    if task == 'claim':
        proof = await get_proof(captcha, starknet_account.address, proxy)
        if not proof:
            await starknet_account.close()
            return
        if proof["claim"] == None:
            logger.debug(f'{starknet_account.acc_info} - начинаю клейм')
            await claimer.claim(captcha)
        else:
            logger.debug(f'{starknet_account.acc_info} - уже заклеймлено')
            await claimer.create_transfer_call(address_to)
    else:
        await claimer.create_transfer_call(address_to)

    await starknet_account.close()
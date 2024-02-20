from starknet_py.net.account.account import Account

from .utils import tx_exceptor
from loguru import logger
from info.starknet_info import scans

success_statuses = ['ACCEPTED_ON_L2']


async def check_status_tx(status, tx_url):
    if status.value in success_statuses:
        logger.success(f'Транзакция подтвердилась {tx_url} ...')
        return True
    else:
        logger.error(f'Ошибка транзакции {tx_url} ...')
        return False


async def tx_sender(calls, account: Account, info, tx_info):
    @tx_exceptor(info, hex(account.address))
    async def tx_sender_():
        tx = await account.execute(calls=calls, auto_estimate=True)
        status = await account.client.wait_for_tx(tx.transaction_hash)
        tx_url = f'{scans["stark"]}{hex(tx.transaction_hash)}'
        if await check_status_tx(status.finality_status, tx_url):
            logger.success(
                f'{info} - успешно {tx_info} {tx_url} ...')
            return True
        else:
            logger.error(f'{info} - транзакция не успешна, пробую еще раз...')
            return await tx_sender(calls, account, info, tx_info)

    return await tx_sender_()



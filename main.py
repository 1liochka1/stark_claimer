import asyncio

import questionary
from loguru import logger
from questionary import Choice

from core.other_utils import get_batches
from core.runner import start
from core.tasks import solve_captcha, get_proof


async def get_valid_captcha():
    for i in range(100):
        logger.debug('getting captcha')
        captcha = await solve_captcha()
        if await get_proof(captcha) != 'again':
            return captcha
async def main(module):
    # captcha = await get_valid_captcha()
    captcha = 'AVGAUYyhDkLXS8EnfH3FIzhV96wy21ZoB6bMAJtieWxVP2kaZiwg7KfTLraM_Iwzd-SuNx8tlBhDlJQylQRZrWZmZYtR6y8VFLpyeoS7kpqZZ7SA7kwL2Q6D16_vP1ByDF8o6rYz-_9dFSous7HWEMjOHZaKZfS20_-PQNugk-91V9k4ScN86fEPpnboog:U=09e2d8a540000000'
    tasks = []
    for i in get_batches():
        id, key, address_to,  proxy = i.split(';')
        tasks.append(start(id, key, captcha, proxy=proxy, address_to=address_to, task=module))

    await asyncio.gather(*tasks)


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        m = questionary.select(
            "Выберите модули для работы...",
            choices=[
                Choice(" 1) КЛЕЙМ", 'claim'),
                Choice(" 2) ТРАНСФЕР", 'tr'),
            ],
            qmark="",
            pointer="⟹",
        ).ask()
        loop.run_until_complete(main(m))
    except KeyboardInterrupt:
        logger.debug('Мануально завершаю работу')
        loop.close()
    except RuntimeError:
        pass
    logger.debug('Завершил работу')

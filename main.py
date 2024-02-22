import asyncio
import json
import os
import sys

import questionary
from loguru import logger
from questionary import Choice

from core.other_utils import get_batches, check_key
from core.runner import start
from core.utils import Starknet_account

async def get_proofs(batches):
    addresses = []
    addresses_proofs = {}
    for addr in batches:
        _, key, _, _ = addr.split(";")
        key = await check_key(key)
        starknet_account = Starknet_account(key, 0)
        await starknet_account.get_account()
        addresses.append(starknet_account.address)
    file_list = os.listdir('eligible')
    for file_name in file_list:
        file_path = os.path.join('eligible', file_name)
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            data = data["eligibles"]
            for addr in addresses:
                for addr_ in data:
                    if addr_["identity"] == addr:
                        addresses_proofs[addr] = addr_

    with open('addresses_proofs.json', 'w') as f:
        json.dump(addresses_proofs, f)



async def main(module):
    batches = get_batches()
    await get_proofs(batches)

    for batch in [batches[i:i + 50] for i in
                  range(0, len(batches), 50)]:
        tasks = []
        for i in batch:
            id, key, address_to, proxy = i.split(';')
            tasks.append(start(id, key, proxy=proxy, address_to=address_to, task=module))

        await asyncio.gather(*tasks)


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        m = questionary.select(
            "Выберите модули для работы...",
            choices=[
                Choice(" 1) КЛЕЙМ", 'claim'),
                Choice(" 2) ТРАНСФЕР ВСЕГО STRK", 'strk'),
                Choice(" 3) ТРАНСФЕР ВСЕГО ETH", 'eth'),
                Choice(" 4) ВЫХОД", 'e'),
            ],
            qmark="",
            pointer="⟹",
        ).ask()
        if m == 'e':
            sys.exit()
        loop.run_until_complete(main(m))
    except KeyboardInterrupt:
        logger.debug('Мануально завершаю работу')
        loop.close()
    except RuntimeError:
        pass
    logger.debug('Завершил работу')

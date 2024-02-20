import asyncio

import questionary
import requests
from anticaptchaofficial.recaptchav3enterpriseproxyless import recaptchaV3EnterpriseProxyless
from loguru import logger
from questionary import Choice

from core.other_utils import get_batches
from core.runner import start


async def get_valid_captcha():
    for i in range(100):
        logger.debug('пробую получить капчу ключ')
        solver = recaptchaV3EnterpriseProxyless()
        solver.set_key("20861ca91b0278cd4ca1bd3b80c4b6ba")
        solver.set_website_url("https://provisions.starknet.io/")
        solver.set_website_key("6Ldj1WopAAAAAGl194Fj6q-HWfYPNBPDXn-ndFRq")
        solver.set_min_score(1)
        solver.set_soft_id(0)
        g_response = solver.solve_and_return_solution()
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
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'x-recaptcha-token': g_response,
        }
        params = {
            'identity': '0x00f195f8d6108b5de4eb46dcc0e3303f575b93b32a95aebc15fb16c9c914c728',
        }
        p = {
            'http': 'http://user65924:k8wpzf@23.247.247.221:9783',
            'https': 'http://user65924:k8wpzf@23.247.247.221:9783'
        }

        response = requests.get(
            'https://provisions.starknet.io/api/starknet/get_eligibility',
            params=params,
            headers=headers, proxies=p
        )
        if 'reason' in response.text:
            return g_response


async def main(module):
    captcha = await get_valid_captcha()
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

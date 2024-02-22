from starknet_py.hash import selector
from starknet_py.net.signer.stark_curve_signer import KeyPair

from info.starknet_info import ARGENT_CLASS_HASH, ARGENT_OLD_CLASH_HASH, ARGENT_OLD_NOV_22_CLASS_HASH


async def get_keypair(key):
    return KeyPair.from_private_key(int(key[2:], 16))


async def get_starknet_keypair_public_key(key):
    return (await get_keypair(key)).public_key


async def create_call_data(account_class_hash, public_key):
    return [public_key, 0] if account_class_hash in (ARGENT_CLASS_HASH, ARGENT_OLD_CLASH_HASH, ARGENT_OLD_NOV_22_CLASS_HASH) else [public_key]


async def create_constructor_call_data(account_class_hash, public_key):
    account_initialize_call_data = await create_call_data(account_class_hash, public_key)
    if account_class_hash == ARGENT_CLASS_HASH:
        return account_initialize_call_data
    return [
        account_class_hash,
        selector.get_selector_from_name(
            "initialize" if account_class_hash in (ARGENT_OLD_CLASH_HASH, ARGENT_OLD_NOV_22_CLASS_HASH) else "initializer"),
        len(account_initialize_call_data),
        *account_initialize_call_data,
    ]







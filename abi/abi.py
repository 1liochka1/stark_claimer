
import json
import os
import pathlib


def get_path(file):
    BASE_DIR = pathlib.Path(__file__).resolve().parent
    your_path = os.path.join(BASE_DIR)
    path = os.path.join(your_path, file)
    return path


def get_file(file_name):
    file_name = f'{file_name}.json'
    path = get_path(file_name)
    with open(path, 'r') as f:
        return json.load(f)


starknet_token_abi = get_file('starknet_token_abi')
claim_abi = get_file('claim')
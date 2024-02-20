import os
import pathlib

def get_path(file):
    BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
    your_path = os.path.join(BASE_DIR, 'wallets_data')
    path = os.path.join(your_path, file)
    return path

with open(get_path('keys.txt'), "r") as f:
    keys = [row.strip() for row in f]

with open(get_path('proxies.txt'), "r") as f:
    proxies = [row.strip() for row in f]


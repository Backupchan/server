#!/usr/bin/python3

import secrets
import json
import os
import argparse
import sys

APIKEY_FILE = "apikey.json"

def generate():
    return "bakch-" + secrets.token_hex(32)

def save(key):
    with open(APIKEY_FILE, "w") as file:
        json.dump({"key": key}, file)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", "-o", action="store_true", help="Allow overwriting the API key file.")
    args = parser.parse_args()
    
    if os.path.exists(APIKEY_FILE) and not args.overwrite:
        print("API key file already exists. Pass --overwrite to allow overwriting.", file=sys.stderr)
    
    key = generate()
    save(key)
    print(f"Your new API key is:\n\n {key}\n\nMake sure to keep it safe.")

if __name__ == "__main__":
    main()
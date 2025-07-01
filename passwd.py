#!/usr/bin/python3

from werkzeug.security import generate_password_hash
import json

password = input("Enter new password: ")
passwd_hash = generate_password_hash(password)
with open("./auth.json", "w", encoding="utf-8") as auth_json:
    json.dump({"passwd_hash": passwd_hash}, auth_json)
print("Your password has been saved.")

from os import path
import pandas as pd
from cryptography.fernet import Fernet, InvalidToken

import sqlite3

def generate():
    key = Fernet.generate_key()
    with open(path.expanduser('~\\Documents') + '\\universal.key',"wb") as key_files:
        key_files.write(key)

def check_key():
    if path.isfile(path.expanduser('~\\Documents') + '\\universal.key'):
        pass
    else:
        generate()

def loadKey():
    key = open(path.expanduser('~\\Documents') + '\\universal.key',"rb").read()
    return key

def encrypt_df(df, columns):
    key = loadKey()
    f= Fernet(key)
    for column in columns:
        # Encrypt each column supplied
        df[column] = df[column].apply(lambda x: f.encrypt(str(x).encode()).decode())
    return df


def decrypt_df(df, columns):
    key = loadKey()
    f= Fernet(key)
    for column in columns:
        print(column)
        df[column] = df[column].apply(lambda x: str(f.decrypt(x).decode()))
    return df
    
def decrypt_value(encrypted_value):
    key = loadKey()
    f = Fernet(key)
    decrypted_text = f.decrypt(encrypted_value).decode()
    return decrypted_text

def encrypt_value(value):
    key = loadKey()
    f = Fernet(key)
    if isinstance(value, int) or isinstance(value,float):
        value = str(value)
    encrypted_text = f.encrypt(value.encode())
    return encrypted_text


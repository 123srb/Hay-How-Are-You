from os import path
from cryptography.fernet import Fernet

def generate():
    key = Fernet.generate_key()
    with open(path.expanduser('~\\Documents') + '\\universal.key',"wb") as key_files:
        key_files.write(key)

def loadKey():
    key = open(path.expanduser('~\\Documents') + '\\universal.key',"rb").read()
    return key

def Encrypt(secret):
    key = loadKey()
    encodeSecret = secret.encode()
    fer  = Fernet(key)
    return fer.encrypt(encodeSecret)

def Decrypt(encryptSecret):
    key = loadKey()
    fer  = Fernet(key)
    decryptSecret = fer.decrypt(encryptSecret)
    return decryptSecret.decode()

def encrpyt_df(df):
    key = loadKey()
    f = Fernet(key)
    df1 = df.applymap(lambda x: bytes(x[2:-1],'utf-8'))
    df2 = df1.applymap(lambda x: f.decrypt(x))
    df_decrp = df2.applymap(lambda x: x.decode('utf-8'))
    return df_decrp

def decrypt_df(df):
    key = loadKey()
    f = Fernet(key)
    df = df.apply(lambda x: x.astype(str)) # preprocess
    df_encp = df.applymap(lambda x: f.encrypt(x.encode('utf-8')))
    return df_encp
    
def decrypt_item(item):
    key = loadKey()
    f = Fernet(key)
    decryptSecret = f.decrypt(item)
    return item.decode()

def encrypt_item(item):
    key = loadKey()
    encodeSecret = item.encode()
    f = Fernet(key)
    return f.encrypt(encodeSecret)
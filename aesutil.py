import base64
import hashlib

from Cryptodome.Cipher import AES

BLOCK_SIZE = 16


def sha256(text):
    m = hashlib.sha256()
    m.update(text.encode())
    return m.digest()


def md5(text):
    m = hashlib.md5()
    m.update(text.encode())
    return m.digest()


def pkcs7_padding(s):
    s_len = len(s.encode('utf-8'))
    s = s + (BLOCK_SIZE - s_len % BLOCK_SIZE) * chr(BLOCK_SIZE - s_len % BLOCK_SIZE)
    return bytes(s, 'utf-8')


def pkcs7_trimming(s):
    return s[0:-s[-1]]


def encrypt(raw, key_string, iv_string):
    key = sha256(key_string)
    iv = md5(iv_string)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return base64.b64encode(cipher.encrypt(pkcs7_padding(raw)))


def decrypt(data, key_string, iv_string):
    try:
        ct = base64.b64decode(data)
        key = sha256(key_string)
        iv = md5(iv_string)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return pkcs7_trimming(cipher.decrypt(ct))
    except:
        return b''


if __name__ == '__main__':
    e = encrypt('Sid', 'key', 'key')
    print(e)

    data = decrypt(e, 'key', 'key')
    print(data)

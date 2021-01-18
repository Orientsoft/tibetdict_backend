import hashlib


def sha_key(key=None):
    sha = hashlib.sha1()
    sha.update(key.encode('utf-8'))
    return sha.hexdigest()

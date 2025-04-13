'''
公共方法
'''


# 密码加密
def pwd_to_sha256(password):
    import hashlib
    sha = hashlib.sha256()
    sha.update(password.encode('utf-8'))
    sha.update('接着奏乐接着舞'.encode('gbk'))
    return sha.hexdigest()
from passlib.hash import scrypt

senha = '123456'
hash_senha = scrypt.hash(senha)
print(f"Hash gerado: {hash_senha}")

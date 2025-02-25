from werkzeug.security import generate_password_hash

senha = 'admin123'
hash_senha = generate_password_hash(senha)
print(f"Hash gerado: {hash_senha}")

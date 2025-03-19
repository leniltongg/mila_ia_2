from dotenv import load_dotenv
import os

print("Verificando variáveis de ambiente:")
print("1. Antes de carregar .env:")
print(f"OPENAI_API_KEY = {os.getenv('OPENAI_API_KEY')}")

print("\n2. Carregando .env...")
load_dotenv(verbose=True)

print("\n3. Depois de carregar .env:")
print(f"OPENAI_API_KEY = {os.getenv('OPENAI_API_KEY')}")

# Tentar ler o arquivo diretamente
print("\n4. Tentando ler o arquivo .env diretamente:")
try:
    with open('.env', 'r') as f:
        print(f.read())
except Exception as e:
    print(f"Erro ao ler arquivo: {e}")

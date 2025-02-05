import os
import secrets
import subprocess
import sys

def generate_secret_key():
    """Gera uma chave secreta segura"""
    return secrets.token_hex(32)

def update_env_file():
    """Atualiza o arquivo .env com valores seguros"""
    if not os.path.exists('.env'):
        print("Arquivo .env não encontrado. Criando novo arquivo...")
    
    env_content = f"""# Configurações sensíveis - NÃO COMITAR ESTE ARQUIVO
SECRET_KEY={generate_secret_key()}
OPENAI_API_KEY=seu-api-key-aqui
DATABASE_PATH=mila.db

# Configurações de segurança
MAX_LOGIN_ATTEMPTS=5
LOGIN_ATTEMPT_TIMEOUT=300  # 5 minutos
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("Arquivo .env atualizado com nova chave secreta.")
    print("IMPORTANTE: Atualize OPENAI_API_KEY no arquivo .env com sua chave real!")

def setup_virtual_env():
    """Configura o ambiente virtual"""
    if not os.path.exists('venv'):
        print("Criando ambiente virtual...")
        subprocess.run([sys.executable, '-m', 'venv', 'venv'])
    
    # Ativa o ambiente virtual
    if sys.platform == 'win32':
        activate_script = os.path.join('venv', 'Scripts', 'activate')
    else:
        activate_script = os.path.join('venv', 'bin', 'activate')
    
    print(f"Para ativar o ambiente virtual, execute:")
    if sys.platform == 'win32':
        print(f".\\venv\\Scripts\\activate")
    else:
        print("source venv/bin/activate")

def install_requirements():
    """Instala as dependências do projeto"""
    pip_cmd = os.path.join('venv', 'Scripts' if sys.platform == 'win32' else 'bin', 'pip')
    print("Instalando dependências...")
    subprocess.run([pip_cmd, 'install', '-r', 'requirements.txt'])

def create_directories():
    """Cria diretórios necessários"""
    directories = ['uploads', 'logs', 'instance']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Diretório {directory} criado.")

def main():
    print("Iniciando setup do projeto Mila_IA...")
    
    # Cria diretórios necessários
    create_directories()
    
    # Configura ambiente virtual
    setup_virtual_env()
    
    # Atualiza arquivo .env
    update_env_file()
    
    # Instala dependências
    install_requirements()
    
    print("\nSetup concluído!")
    print("\nPróximos passos:")
    print("1. Ative o ambiente virtual usando o comando mostrado acima")
    print("2. Atualize a OPENAI_API_KEY no arquivo .env")
    print("3. Execute 'flask run' para iniciar a aplicação")

if __name__ == '__main__':
    main()

import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'chave-secreta-temporaria')
    UPLOAD_FOLDER = 'uploads'  # pasta onde os PDFs serão temporariamente salvos
    DATABASE = 'educacional.db'
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'mila.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_ATTEMPT_TIMEOUT = 300  # 5 minutos

    @staticmethod
    def init_app(app):
        # Certifique-se que a pasta de uploads existe
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

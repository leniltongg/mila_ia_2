from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, current_user
from werkzeug.urls import url_parse
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from auth import auth
from database import get_db, close_db, init_db
import logging
from logging.handlers import RotatingFileHandler
import os
from security_middleware import init_security_middleware
from datetime import timedelta
from validators import validate_email, validate_form_data, generate_form_token
from decorators import rate_limit, log_activity
from flask import url_for
from werkzeug.security import check_password_hash
from models import User

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configuração do proxy
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

    # Configuração de logs
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler(
            'logs/mila.log', maxBytes=10240, backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Mila startup')

    with app.app_context():
        # Inicializa o banco de dados
        init_db()
        app.teardown_appcontext(close_db)

        # Inicializa middleware de segurança
        init_security_middleware(app)

        # Configurações de segurança adicionais
        app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            PERMANENT_SESSION_LIFETIME=timedelta(minutes=30)
        )

        # Configuração do Login Manager
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'Por favor, faça login para acessar esta página.'
        login_manager.login_message_category = 'info'

        @login_manager.user_loader
        def load_user(user_id):
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                SELECT id, nome, tipo_usuario_id, escola_id, serie_id, turma_id, email, codigo_ibge
                FROM usuarios
                WHERE id = ?
            """, (user_id,))
            user_data = cursor.fetchone()
            
            if user_data:
                return User(
                    id=user_data['id'],
                    nome=user_data['nome'],
                    tipo_usuario_id=user_data['tipo_usuario_id'],
                    escola_id=user_data['escola_id'],
                    serie_id=user_data['serie_id'],
                    turma_id=user_data['turma_id'],
                    email=user_data['email'],
                    codigo_ibge=user_data['codigo_ibge']
                )
            return None

        # Registro dos blueprints
        app.register_blueprint(auth)

        # Página inicial
        @app.route('/')
        def index():
            return render_template('index.html')

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)

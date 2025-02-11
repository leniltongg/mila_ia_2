from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import current_app, request, abort
from flask_login import current_user
import time
from datetime import datetime
import logging

# Configuração do logging
logging.basicConfig(
    filename='security.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Dicionário para armazenar tentativas de login
login_attempts = {}

def hash_password(password):
    """Gera um hash seguro da senha"""
    return generate_password_hash(password, method='pbkdf2:sha256:260000')

def check_password(password, hashed_password):
    """Verifica se a senha está correta"""
    return check_password_hash(hashed_password, password)  # Usa o check_password_hash do Werkzeug

def check_login_attempts(email):
    """Verifica tentativas de login para prevenir brute force"""
    current_time = time.time()
    user_attempts = login_attempts.get(email, {"attempts": 0, "last_attempt": 0})
    
    # Reseta as tentativas após o timeout
    if current_time - user_attempts["last_attempt"] > current_app.config['LOGIN_ATTEMPT_TIMEOUT']:
        user_attempts = {"attempts": 0, "last_attempt": current_time}
    
    if user_attempts["attempts"] >= current_app.config['MAX_LOGIN_ATTEMPTS']:
        return False
    
    user_attempts["attempts"] += 1
    user_attempts["last_attempt"] = current_time
    login_attempts[email] = user_attempts
    return True

def reset_login_attempts(email):
    """Reseta as tentativas de login após um login bem-sucedido"""
    if email in login_attempts:
        del login_attempts[email]

def admin_required(f):
    """Decorator para rotas que requerem privilégios de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.tipo_usuario_id != "Administrador":
            logging.warning(f'Tentativa de acesso não autorizado à rota administrativa por {current_user.email if current_user.is_authenticated else "usuário não autenticado"}')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def log_security_event(event_type, user_id=None, details=None):
    """Registra eventos de segurança"""
    event = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'ip_address': request.remote_addr,
        'details': details
    }
    logging.info(f"Security Event: {event}")

def sanitize_input(text):
    """Sanitiza input do usuário para prevenir XSS"""
    if not text:
        return text
    # Remove caracteres potencialmente perigosos
    return str(text).replace('<', '&lt;').replace('>', '&gt;')

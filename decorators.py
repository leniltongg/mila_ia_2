from functools import wraps
from flask import request, abort, current_app
from flask_login import current_user
import time
from datetime import datetime, timedelta

def rate_limit(max_requests=5, window=60):
    """
    Limita o número de requisições por usuário
    max_requests: número máximo de requisições permitidas
    window: janela de tempo em segundos
    """
    def decorator(f):
        # Dicionário para armazenar as requisições
        requests = {}
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Identifica o usuário/IP
            user_id = current_user.get_id() if current_user.is_authenticated else request.remote_addr
            
            # Obtém o timestamp atual
            now = time.time()
            
            # Inicializa ou limpa requisições antigas
            if user_id not in requests:
                requests[user_id] = []
            requests[user_id] = [req for req in requests[user_id] if req > now - window]
            
            # Verifica se excedeu o limite
            if len(requests[user_id]) >= max_requests:
                abort(429)  # Too Many Requests
                
            # Adiciona nova requisição
            requests[user_id].append(now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(*roles):
    """Requer que o usuário tenha um dos papéis especificados"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)  # Unauthorized
            if current_user.tipo_usuario_id not in roles:
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_request_data(expected_fields):
    """Valida dados da requisição"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.form if request.method == 'POST' else request.args
            
            # Verifica campos obrigatórios
            for field in expected_fields:
                if field not in data:
                    abort(400, description=f"Campo obrigatório ausente: {field}")
                    
                value = str(data[field]).strip()
                if not value:
                    abort(400, description=f"Campo obrigatório vazio: {field}")
                    
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_activity(activity_type):
    """Registra atividade do usuário"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from database import get_db
            
            # Executa a função
            result = f(*args, **kwargs)
            
            # Registra a atividade
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    activity_type TEXT,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                INSERT INTO activity_log (user_id, activity_type, details, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            """, (
                current_user.id if current_user.is_authenticated else None,
                activity_type,
                str(request.form if request.method == 'POST' else request.args),
                request.remote_addr,
                request.user_agent.string
            ))
            
            db.commit()
            return result
        return decorated_function
    return decorator

def check_content_hash():
    """Verifica se o conteúdo não foi modificado"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method == 'POST':
                content_hash = request.form.get('_content_hash')
                if not content_hash:
                    abort(400, description="Hash de conteúdo ausente")
                    
                # Recalcula o hash dos campos
                form_data = {k: v for k, v in request.form.items() if not k.startswith('_')}
                calculated_hash = calculate_content_hash(form_data)
                
                if content_hash != calculated_hash:
                    abort(400, description="Conteúdo modificado")
                    
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_fresh_login(max_age=30):
    """Requer login recente para ações sensíveis"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
                
            # Verifica quando foi o último login
            last_login = getattr(current_user, 'last_login', None)
            if not last_login or datetime.utcnow() - last_login > timedelta(minutes=max_age):
                abort(401, description="Por favor, faça login novamente")
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Requer que o usuário seja um administrador (tipo 1)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # Unauthorized
        if current_user.tipo_usuario_id != 1:  # 1 é o tipo de usuário administrador
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

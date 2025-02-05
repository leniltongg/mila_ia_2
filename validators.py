import re
from functools import wraps
from flask import request, abort, current_app
from flask_login import current_user
import hashlib
import hmac
from datetime import datetime, timedelta

def validate_form_data(data, expected_fields):
    """Valida os dados do formulário contra manipulação"""
    # Verifica campos obrigatórios
    for field in expected_fields:
        if field not in data:
            return False, f"Campo obrigatório ausente: {field}"
        
        # Sanitiza e valida o valor
        value = str(data[field]).strip()
        if not value and field in expected_fields:
            return False, f"Campo obrigatório vazio: {field}"
            
        # Verifica tamanho máximo
        if len(value) > 1000:  # Limite genérico
            return False, f"Campo muito longo: {field}"
            
        # Verifica caracteres perigosos
        if re.search(r'[<>]', value):
            return False, f"Caracteres inválidos em: {field}"
    
    return True, "Dados válidos"

def generate_form_token():
    """Gera um token único para o formulário"""
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M')
    token = hmac.new(
        current_app.config['SECRET_KEY'].encode(),
        f"{current_user.get_id()}{timestamp}".encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{timestamp}.{token}"

def validate_form_token(token):
    """Valida o token do formulário"""
    try:
        timestamp, hash_value = token.split('.')
        expected_token = hmac.new(
            current_app.config['SECRET_KEY'].encode(),
            f"{current_user.get_id()}{timestamp}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Verifica se o token é válido
        if not hmac.compare_digest(hash_value, expected_token):
            return False
            
        # Verifica se o token não expirou (30 minutos)
        token_time = datetime.strptime(timestamp, '%Y%m%d%H%M')
        if datetime.utcnow() - token_time > timedelta(minutes=30):
            return False
            
        return True
    except:
        return False

def require_form_token(f):
    """Decorator para requerer token válido em formulários"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.form.get('_token')
        if not token or not validate_form_token(token):
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

# Validadores específicos
def validate_email(email):
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_cpf(cpf):
    """Valida CPF"""
    if not cpf:
        return True  # CPF é opcional
        
    # Remove caracteres não numéricos
    cpf = ''.join(filter(str.isdigit, cpf))
    
    # Verifica tamanho
    if len(cpf) != 11:
        return False
        
    # Verifica se todos os dígitos são iguais
    if len(set(cpf)) == 1:
        return False
        
    # Valida dígitos verificadores
    for i in range(9, 11):
        value = sum((int(cpf[num]) * ((i+1) - num) for num in range(0, i)))
        digit = ((value * 10) % 11) % 10
        if digit != int(cpf[i]):
            return False
    return True

def validate_data_nascimento(data):
    """Valida data de nascimento"""
    try:
        if not data:
            return True  # Data é opcional
            
        data_obj = datetime.strptime(data, '%Y-%m-%d')
        hoje = datetime.now()
        
        # Verifica se a data não é futura
        if data_obj > hoje:
            return False
            
        # Verifica se a pessoa não tem mais de 120 anos
        if hoje - data_obj > timedelta(days=365*120):
            return False
            
        return True
    except:
        return False

def sanitize_string(value, max_length=100):
    """Sanitiza uma string"""
    if not value:
        return ""
        
    # Remove caracteres perigosos
    value = re.sub(r'[<>]', '', str(value))
    
    # Limita o tamanho
    return value[:max_length]

def validate_password_strength(password):
    """Valida força da senha"""
    if len(password) < 8:
        return False, "Senha deve ter pelo menos 8 caracteres"
        
    if not re.search(r'[A-Z]', password):
        return False, "Senha deve conter pelo menos uma letra maiúscula"
        
    if not re.search(r'[a-z]', password):
        return False, "Senha deve conter pelo menos uma letra minúscula"
        
    if not re.search(r'[0-9]', password):
        return False, "Senha deve conter pelo menos um número"
        
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Senha deve conter pelo menos um caractere especial"
        
    return True, "Senha válida"

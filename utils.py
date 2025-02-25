from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def verificar_permissao(*tipos_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Admin (tipo 6) tem acesso a tudo
            if current_user.tipo_usuario_id == 6:
                return f(*args, **kwargs)
            
            # Verifica se o usuário tem um dos tipos permitidos
            if current_user.tipo_usuario_id not in tipos_permitidos:
                flash("Acesso não autorizado.", "danger")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

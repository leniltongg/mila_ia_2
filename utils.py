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

def get_nome_mes(mes_id):
    """Retorna o nome do mês correspondente ao número fornecido."""
    meses = {
        1: 'Janeiro',
        2: 'Fevereiro',
        3: 'Março',
        4: 'Abril',
        5: 'Maio',
        6: 'Junho',
        7: 'Julho',
        8: 'Agosto',
        9: 'Setembro',
        10: 'Outubro',
        11: 'Novembro',
        12: 'Dezembro'
    }
    return meses.get(mes_id, '-')

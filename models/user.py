from flask_login import UserMixin
from flask import g

def get_db():
    """Conecta ao banco de dados."""
    if 'db' not in g:
        g.db = sqlite3.connect('educacional.db')
        g.db.row_factory = sqlite3.Row
    return g.db

class User(UserMixin):
    def __init__(self, id, nome=None, tipo_usuario_id=None, escola_id=None, Ano_escolar_id=None, turma_id=None, email=None, codigo_ibge=None):
        self.id = id
        self.nome = nome
        self.tipo_usuario_id = tipo_usuario_id
        self.escola_id = escola_id
        self.Ano_escolar_id = Ano_escolar_id
        self.turma_id = turma_id
        self.email = email
        self.codigo_ibge = codigo_ibge
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return str(self.id)

    @staticmethod
    def get(user_id):
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            SELECT id, nome, tipo_usuario_id, escola_id, Ano_escolar_id, turma_id, email, codigo_ibge 
            FROM usuarios 
            WHERE id = ?
        ''', (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            return User(
                id=user_data[0],
                nome=user_data[1],
                tipo_usuario_id=user_data[2],
                escola_id=user_data[3],
                Ano_escolar_id=user_data[4],
                turma_id=user_data[5],
                email=user_data[6],
                codigo_ibge=user_data[7]
            )
        return None

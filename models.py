from flask_login import UserMixin
from security import hash_password
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Constantes para tipos de usuário
TIPO_USUARIO_ADMIN = 1
TIPO_USUARIO_SECRETARIA = 2
TIPO_USUARIO_PROFESSOR = 3
TIPO_USUARIO_ALUNO = 4
TIPO_USUARIO_SECRETARIA_EDUCACAO = 5

# Tabelas de relacionamento
professor_disciplina = db.Table('professor_disciplina',
    db.Column('professor_id', db.Integer, db.ForeignKey('usuarios.id'), primary_key=True),
    db.Column('disciplina_id', db.Integer, db.ForeignKey('disciplinas.id'), primary_key=True)
)

professor_turma_escola = db.Table('professor_turma_escola',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('professor_id', db.Integer, db.ForeignKey('usuarios.id'), nullable=False),
    db.Column('escola_id', db.Integer, db.ForeignKey('escolas.id'), nullable=False),
    db.Column('turma_id', db.Integer, db.ForeignKey('turmas.id'), nullable=False),
    db.Column('tipo_ensino_id', db.Integer, nullable=False),
    db.Column('serie_id', db.Integer, db.ForeignKey('series.id'), nullable=False)
)

# Modelo para Cidades
class Cidade(db.Model):
    __tablename__ = 'cidades'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    codigo_ibge = db.Column(db.String(7), unique=True, nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    escolas = db.relationship('Escola', back_populates='cidade')
    usuarios = db.relationship('User', back_populates='cidade')

    def __repr__(self):
        return f'<Cidade {self.nome}>'

class User(UserMixin, db.Model):
    __tablename__ = 'usuarios'  # Nome da tabela no banco de dados
    
    id = db.Column(db.Integer, primary_key=True)
    tipo_registro = db.Column(db.String)
    codigo_inep_escola = db.Column(db.String)
    cpf = db.Column(db.String)
    email = db.Column(db.String)
    _senha = db.Column('senha', db.String)  # Campo senha do banco de dados
    nome = db.Column(db.String)
    data_nascimento = db.Column(db.String)
    mae = db.Column(db.String)
    pai = db.Column(db.String)
    sexo = db.Column(db.Integer)
    codigo_ibge = db.Column(db.String)
    cep = db.Column(db.String)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'))
    tipo_ensino_id = db.Column(db.Integer)
    serie_id = db.Column(db.Integer)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'))
    tipo_usuario_id = db.Column(db.Integer)  # 1=admin, 2=secretaria, 3=professor, 4=aluno
    cidade_id = db.Column(db.Integer, db.ForeignKey('cidades.id'))  # Adicionando chave estrangeira para cidade
    ultimo_login = db.Column(db.Float)
    tentativas_login = db.Column(db.Integer)
    data_atualizacao_senha = db.Column(db.Float)
    bloqueado = db.Column(db.Integer)
    token_reset_senha = db.Column(db.String)
    token_expiracao = db.Column(db.Float)

    def __init__(self, id, tipo_usuario_id=None):
        self.id = id
        self.tipo_usuario_id = tipo_usuario_id
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return str(self.id)

    @property
    def senha(self):
        return self._senha

    @senha.setter
    def senha(self, senha):
        self._senha = hash_password(senha)

    @property
    def is_admin(self):
        return self.tipo_usuario_id == TIPO_USUARIO_ADMIN

    @property
    def is_secretaria(self):
        return self.tipo_usuario_id == TIPO_USUARIO_SECRETARIA

    def has_role(self, *roles):
        return self.tipo_usuario_id in roles

    @property
    def tipo(self):
        """Retorna o tipo de usuário em formato string."""
        tipos = {1: 'admin', 2: 'secretaria', 3: 'professor', 4: 'aluno'}
        return tipos.get(self.tipo_usuario_id, 'desconhecido')

    cidade = db.relationship('Cidade', back_populates='usuarios')
    escola_vinculada = db.relationship('Escola', back_populates='professores')
    turma = db.relationship('Turma', backref='alunos')
    disciplinas = db.relationship('Disciplina', secondary=professor_disciplina, lazy='subquery',
        backref=db.backref('professores', lazy=True))
    turmas_lecionadas = db.relationship('Turma', secondary=professor_turma_escola, lazy='subquery',
        backref=db.backref('professores', lazy=True))

# Modelo para Escolas
class Escola(db.Model):
    __tablename__ = 'escolas'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    codigo_inep = db.Column(db.String(8), unique=True, nullable=False)
    
    # Endereço
    cep = db.Column(db.String(8))
    logradouro = db.Column(db.String(200))
    numero = db.Column(db.String(10))
    complemento = db.Column(db.String(100))
    bairro = db.Column(db.String(100))
    cidade_id = db.Column(db.Integer, db.ForeignKey('cidades.id'), nullable=False)
    cidade = db.relationship('Cidade', back_populates='escolas')
    
    # Tipos de Ensino
    tem_fundamental_1 = db.Column(db.Boolean, default=False)  # 1º ao 5º ano
    tem_fundamental_2 = db.Column(db.Boolean, default=False)  # 6º ao 9º ano
    tem_medio = db.Column(db.Boolean, default=False)  # Ensino Médio
    tem_eja = db.Column(db.Boolean, default=False)  # Educação de Jovens e Adultos
    tem_tecnico = db.Column(db.Boolean, default=False)  # Ensino Técnico
    
    # Relacionamentos
    professores = db.relationship('User', back_populates='escola_vinculada', lazy=True,
                                foreign_keys='User.escola_id')

    def __repr__(self):
        return f'<Escola {self.nome}>'

# Modelo para Disciplinas
class Disciplina(db.Model):
    __tablename__ = 'disciplinas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)

    def __repr__(self):
        return f'<Disciplina {self.nome}>'

# Modelo para Series
class Serie(db.Model):
    __tablename__ = 'series'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    nivel_ensino = db.Column(db.String(20), nullable=False)  # fundamental_1, fundamental_2, medio, eja, tecnico
    ordem = db.Column(db.Integer, nullable=False)  # Para ordenar as séries corretamente (1º ano = 1, 2º ano = 2, etc)
    
    def __repr__(self):
        return f'<Serie {self.nome}>'

# Modelo para Turmas
class Turma(db.Model):
    __tablename__ = 'turmas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    serie_id = db.Column(db.Integer, db.ForeignKey('series.id'), nullable=False)
    serie = db.relationship('Serie', backref='turmas')
    turno = db.Column(db.String(20), nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'), nullable=False)

    def __repr__(self):
        return f'<Turma {self.nome}>'

def init_db():
    """Initialize the database tables."""
    db.create_all()

def migrate_users_from_sqlite():
    """Migrate users from old SQLite schema to new SQLAlchemy models."""
    import sqlite3
    import os

    # Connect to old database
    old_db = sqlite3.connect('educacional.db')
    cursor = old_db.cursor()
    
    # Get all users from old schema
    cursor.execute("""
        SELECT id, nome, tipo_usuario_id, escola_id, serie_id, turma_id, email, senha, codigo_ibge, cpf
        FROM usuarios
        WHERE email IS NOT NULL AND email != ''
    """)
    users = cursor.fetchall()
    
    # Migrate each user to new schema
    for user_data in users:
        try:
            user = User(
                id=user_data[0],
                nome=user_data[1] or '',  # Handle NULL values
                tipo_usuario_id=user_data[2] or TIPO_USUARIO_ALUNO,  # Default to student if NULL
                escola_id=user_data[3],  # Allow NULL
                serie_id=user_data[4],   # Allow NULL
                turma_id=user_data[5],   # Allow NULL
                email=user_data[6],
                codigo_ibge=int(user_data[8]) if user_data[8] and user_data[8].isdigit() else None,
                cpf=user_data[9]
            )
            user.senha = user_data[7] or ''  # Set password hash directly, empty string if NULL
            db.session.add(user)
        except Exception as e:
            print(f"Error migrating user {user_data[0]}: {str(e)}")
            continue
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

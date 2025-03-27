from flask_login import UserMixin
from extensions import db
from datetime import datetime
import json


# Constantes para tipos de usuário
TIPO_USUARIO_ADMIN = 1
TIPO_USUARIO_SECRETARIA = 2
TIPO_USUARIO_PROFESSOR = 3
TIPO_USUARIO_ALUNO = 4
TIPO_USUARIO_SECRETARIA_EDUCACAO = 5

class Usuarios(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    senha = db.Column(db.String(255), nullable=True)
    tipo_usuario_id = db.Column(db.Integer, nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'), nullable=True)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=True)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=True)
    codigo_ibge = db.Column(db.String(10), nullable=True)
    cep_usuario = db.Column(db.String(10), nullable=True)
    cpf = db.Column(db.String(11), unique=True, nullable=True)
    data_nascimento = db.Column(db.String(10), nullable=True)
    mae = db.Column(db.String(200), nullable=True)
    pai = db.Column(db.String(200), nullable=True)
    sexo = db.Column(db.Integer, nullable=True)
    cidade_id = db.Column(db.Integer, db.ForeignKey('cidades.id'), nullable=False)
    tipo_ensino_id = db.Column(db.Integer, db.ForeignKey('tipos_ensino.id'), nullable=True)
    codigo_inep_escola = db.Column(db.String(8), nullable=True)
    turno = db.Column(db.String(20), nullable=True)
    matricula_aluno = db.Column(db.String(50), nullable=True)
    codigo_inep_aluno = db.Column(db.String(20), nullable=True)
    cor = db.Column(db.String(20), nullable=True)
    turma_institucional = db.Column(db.String(255), nullable=True)

    def get_id(self):
        return str(self.id)

class Escolas(db.Model):
    __tablename__ = 'escolas'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    codigo_inep = db.Column(db.String(8), unique=True, nullable=False)
    nome_da_escola = db.Column(db.String(100), nullable=False)
    cep_escola = db.Column(db.String(8), nullable=False)
    codigo_ibge = db.Column(db.String(7), nullable=False)
    endereco = db.Column(db.String(100), nullable=False)
    numero = db.Column(db.String(10), nullable=False)
    complemento = db.Column(db.String(50), nullable=True)
    bairro = db.Column(db.String(50), nullable=False)
    ddd = db.Column(db.String(2), nullable=False)
    telefone = db.Column(db.String(9), nullable=False)
    telefone_2 = db.Column(db.String(9), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    ensino_fundamental = db.Column(db.Boolean, nullable=False, default=True)
    DEP_ADMINISTRATIVA = db.Column(db.String(100), nullable=True)
    DC_LOCALIZACAO = db.Column(db.String(50), nullable=True)

class Turmas(db.Model):
    __tablename__ = 'turmas'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    codigo_inep = db.Column(db.String(8), nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'), nullable=False)
    tipo_ensino_id = db.Column(db.Integer, db.ForeignKey('tipos_ensino.id'), nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    turma_institucional = db.Column(db.String(255), nullable=False)
    turma = db.Column(db.String(100), nullable=False)
    turno = db.Column(db.String(20), nullable=True)

class TiposEnsino(db.Model):
    __tablename__ = 'tipos_ensino'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)

class Ano_escolar(db.Model):
    __tablename__ = 'Ano_escolar'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    tipo_ensino_id = db.Column(db.Integer, db.ForeignKey('tipos_ensino.id'), nullable=False)

class ProfessorTurmaEscola(db.Model):
    __tablename__ = 'professor_turma_escola'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False)
    tipo_ensino_id = db.Column(db.Integer, db.ForeignKey('tipos_ensino.id'), nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    
    # Relacionamentos
    turma = db.relationship('Turmas', backref='professor_turmas')

class Assuntos(db.Model):
    __tablename__ = 'assuntos'
    __table_args__ = (
        db.UniqueConstraint('nome', 'disciplina_id', 'ano_escolar_id', 'professor_id'),
        {'extend_existing': True}
    )
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'), nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)

class Disciplinas(db.Model):
    __tablename__ = 'disciplinas'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)

    def __repr__(self):
        return f'<Disciplina {self.nome}>'

class SimuladosGerados(db.Model):
    __tablename__ = 'simulados_gerados'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    mes_id = db.Column(db.Integer, db.ForeignKey('meses.id'), nullable=False)
    status = db.Column(db.String(20), nullable=True, default='gerado')
    data_envio = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'), nullable=True)
    codigo_ibge = db.Column(db.String(10), nullable=True)
    pontuacao_total = db.Column(db.Numeric(5,1), nullable=False, default=10.0)  # Novo campo

    # Relacionamentos
    questoes = db.relationship('BancoQuestoes', secondary='simulado_questoes',
                             backref=db.backref('simulados_gerados', lazy='dynamic'),
                             lazy='joined')
    disciplina = db.relationship('Disciplinas', backref='simulados')

class MESES(db.Model):
    __tablename__ = 'meses'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)

class TiposUsuarios(db.Model):
    __tablename__ = 'tipos_usuarios'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)

class BancoQuestoes(db.Model):
    __tablename__ = 'banco_questoes'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    questao = db.Column(db.Text, nullable=False)
    alternativa_a = db.Column(db.Text, nullable=False)
    alternativa_b = db.Column(db.Text, nullable=False)
    alternativa_c = db.Column(db.Text, nullable=False)
    alternativa_d = db.Column(db.Text, nullable=False)
    alternativa_e = db.Column(db.Text, nullable=True)
    questao_correta = db.Column(db.String(1), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'), nullable=False)
    assunto = db.Column(db.Text, nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=True)
    mes_id = db.Column(db.Integer, db.ForeignKey('meses.id'), nullable=True)
    data_criacao = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())
    codigo_ibge = db.Column(db.String(7), nullable=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    # Relacionamentos
    disciplina = db.relationship('Disciplinas', backref='questoes')
    Ano_escolar = db.relationship('Ano_escolar', backref='questoes')
    usuario = db.relationship('Usuarios', backref='questoes')

class ImagemQuestao(db.Model):
    __tablename__ = 'imagens_questoes'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'))
    assunto = db.Column(db.String(100))
    descricao = db.Column(db.Text)
    data_upload = db.Column(db.DateTime, default=db.func.current_timestamp())
    tipo = db.Column(db.String(50))  # enunciado, alternativa, etc
    
    # Relacionamentos
    disciplina = db.relationship('Disciplinas', backref='imagens')

class SimuladosGeradosProfessor(db.Model):
    __tablename__ = 'simulados_gerados_professor'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'), nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())
    mes_id = db.Column(db.Integer, db.ForeignKey('meses.id'), nullable=True)
    status = db.Column(db.String(20), nullable=True, default='gerado')

class SimuladoQuestoes(db.Model):
    __tablename__ = 'simulado_questoes'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_gerados.id'), nullable=False)
    questao_id = db.Column(db.Integer, db.ForeignKey('banco_questoes.id'), nullable=True)
    pontuacao = db.Column(db.Float, nullable=False, default=1.0)
    
    # Relacionamentos
    simulado = db.relationship('SimuladosGerados', backref='questoes_simulado')
    questao = db.relationship('BancoQuestoes', backref='simulados_questoes')

class SimuladoQuestoesProfessor(db.Model):
    __tablename__ = 'simulado_questoes_professor'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_gerados_professor.id'), nullable=False)
    questao_id = db.Column(db.Integer, db.ForeignKey('banco_questoes.id'), nullable=False)

class SimuladosEnviados(db.Model):
    __tablename__ = 'simulados_enviados'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_gerados_professor.id'), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False)
    data_envio = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())
    status = db.Column(db.String(20), nullable=True, default='enviado')
    data_limite = db.Column(db.DateTime, nullable=True)

class AlunoSimulado(db.Model):
    __tablename__ = 'aluno_simulado'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_enviados.id'), nullable=False)
    status = db.Column(db.String(20), nullable=True, default='não respondido')
    data_resposta = db.Column(db.DateTime, nullable=True)

class DesempenhoSimulado(db.Model):
    __tablename__ = 'desempenho_simulado'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_enviados.id'), nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'), nullable=False)
    codigo_ibge = db.Column(db.String(10), nullable=False)
    respostas_aluno = db.Column(db.JSON, nullable=False)
    respostas_corretas = db.Column(db.JSON, nullable=False)
    desempenho = db.Column(db.Numeric(5, 2), nullable=False)
    pontuacao = db.Column(db.Numeric(5, 2), nullable=False)
    data_resposta = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=True)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    tipo_usuario_id = db.Column(db.Integer, db.ForeignKey('tipos_usuarios.id'), nullable=False)

class Cidades(db.Model):
    __tablename__ = 'cidades'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    codigo_ibge = db.Column(db.Integer, nullable=False, unique=True)
    nome = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(2), nullable=False)
    codigo_inep = db.Column(db.Integer, nullable=True)

class EscolaTiposEnsino(db.Model):
    __tablename__ = 'escola_tipos_ensino'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'), nullable=False)
    tipo_ensino_id = db.Column(db.Integer, db.ForeignKey('tipos_ensino.id'), nullable=False)

class RespostasSimulado(db.Model):
    __tablename__ = 'respostas_simulado'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_gerados.id'), nullable=False)
    questao_id = db.Column(db.Integer, db.ForeignKey('banco_questoes.id'), nullable=False)
    resposta = db.Column(db.String(1), nullable=False)
    data_resposta = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())

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
        SELECT id, nome, tipo_usuario_id, escola_id, ano_escolar_id, turma_id, email, senha, codigo_ibge, cpf
        FROM usuarios
        WHERE email IS NOT NULL AND email != ''
    """)
    users = cursor.fetchall()
    
    # Migrate each user to new schema
    for user_data in users:
        try:
            user = Usuarios(
                id=user_data[0],
                nome=user_data[1] or '',
                tipo_usuario_id=user_data[2] or TIPO_USUARIO_ALUNO,
                escola_id=user_data[3],
                ano_escolar_id=user_data[4],
                turma_id=user_data[5],
                email=user_data[6],
                senha=user_data[7] or '',
                codigo_ibge=user_data[8],
                cpf=user_data[9]
            )
            db.session.add(user)
        except Exception as e:
            print(f"Error migrating user {user_data[0]}: {str(e)}")

    try:
        db.session.commit()
        print("Migration completed successfully")
    except Exception as e:
        db.session.rollback()
        print(f"Error committing changes: {str(e)}")
    finally:
        cursor.close()
        old_db.close()

class User:
    def __init__(self, user_data):
        self.id = user_data.id
        self.nome = user_data.nome
        self.tipo_usuario_id = user_data.tipo_usuario_id
        self.escola_id = user_data.escola_id
        self.ano_escolar_id = user_data.ano_escolar_id
        self.turma_id = user_data.turma_id
        self.email = user_data.email
        self.codigo_ibge = user_data.codigo_ibge
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return str(self.id)

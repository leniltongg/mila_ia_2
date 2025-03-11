from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
from flask_login import UserMixin, LoginManager

load_dotenv()

app = Flask(__name__)

# Configurações básicas do Flask
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave-secreta-temporaria')

# Codificando a senha para URL
password = quote_plus('31952814Gg@')
# String de conexão MySQL usando pymysql
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://mila_user:{password}@127.0.0.1/mila_educacional'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class TiposUsuarios(db.Model):
    __tablename__ = 'tipos_usuarios'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)

class TiposEnsino(db.Model):
    __tablename__ = 'tipos_ensino'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)

class MESES(db.Model):
    __tablename__ = 'meses'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)

class Cidades(db.Model):
    __tablename__ = 'cidades'
    id = db.Column(db.Integer, primary_key=True)
    codigo_ibge = db.Column(db.Integer, nullable=False, unique=True)
    nome = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(2), nullable=False)
    codigo_inep = db.Column(db.Integer, nullable=True)

class Disciplinas(db.Model):
    __tablename__ = 'disciplinas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)

class Ano_escolar(db.Model):
    __tablename__ = 'Ano_escolar'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo_ensino_id = db.Column(db.Integer, db.ForeignKey('tipos_ensino.id'), nullable=False)

class Escolas(db.Model):
    __tablename__ = 'escolas'
    id = db.Column(db.Integer, primary_key=True)
    tipo_de_registro = db.Column(db.String(2), nullable=False)
    codigo_inep = db.Column(db.String(8), nullable=True)
    nome_da_escola = db.Column(db.String(200), nullable=True)
    cep = db.Column(db.String(10), nullable=True)
    codigo_ibge = db.Column(db.String(10), nullable=True)
    endereco = db.Column(db.String(200), nullable=True)
    numero = db.Column(db.String(10), nullable=True)
    complemento = db.Column(db.String(100), nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    ddd = db.Column(db.String(2), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    telefone_2 = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    ensino_fundamental = db.Column(db.Integer, nullable=True)

class Turmas(db.Model):
    __tablename__ = 'turmas'
    id = db.Column(db.Integer, primary_key=True)
    tipo_de_registro = db.Column(db.String(2), nullable=False, default='20')
    codigo_inep = db.Column(db.String(8), nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'), nullable=False)
    tipo_ensino_id = db.Column(db.Integer, db.ForeignKey('tipos_ensino.id'), nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    turma = db.Column(db.String(100), nullable=False)

class Usuarios(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    tipo_registro = db.Column(db.String(2), nullable=False, default='00')
    codigo_inep_escola = db.Column(db.String(8), nullable=True)
    cpf = db.Column(db.String(11), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    senha = db.Column(db.String(255), nullable=True)
    nome = db.Column(db.String(200), nullable=False)
    data_nascimento = db.Column(db.String(10), nullable=True)
    mae = db.Column(db.String(200), nullable=True)
    pai = db.Column(db.String(200), nullable=True)
    sexo = db.Column(db.Integer, nullable=True)
    codigo_ibge = db.Column(db.String(10), nullable=True)
    cep = db.Column(db.String(10), nullable=True)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'), nullable=True)
    tipo_ensino_id = db.Column(db.Integer, db.ForeignKey('tipos_ensino.id'), nullable=True)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=True)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=True)
    tipo_usuario_id = db.Column(db.Integer, db.ForeignKey('tipos_usuarios.id'), nullable=False, default=4)
    cidade_id = db.Column(db.Integer, db.ForeignKey('cidades.id'), nullable=False, default=4)

class EscolaTiposEnsino(db.Model):
    __tablename__ = 'escola_tipos_ensino'
    id = db.Column(db.Integer, primary_key=True)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'), nullable=False)
    tipo_ensino_id = db.Column(db.Integer, db.ForeignKey('tipos_ensino.id'), nullable=False)

class ProfessorTurmaEscola(db.Model):
    __tablename__ = 'professor_turma_escola'
    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False)
    tipo_ensino_id = db.Column(db.Integer, db.ForeignKey('tipos_ensino.id'), nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)

class Assuntos(db.Model):
    __tablename__ = 'assuntos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'), nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('nome', 'disciplina_id', 'ano_escolar_id', 'professor_id'),)

class BancoQuestoes(db.Model):
    __tablename__ = 'banco_questoes'
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
    codigo_ibge = db.Column(db.String(10), nullable=True)

class SimuladosGerados(db.Model):
    __tablename__ = 'simulados_gerados'
    id = db.Column(db.Integer, primary_key=True)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    mes_id = db.Column(db.Integer, db.ForeignKey('meses.id'), nullable=False)
    status = db.Column(db.String(20), nullable=True, default='gerado')
    data_envio = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'), nullable=True)
    codigo_ibge = db.Column(db.String(10), nullable=True)  # Adicione esta linha


class SimuladosGeradosProfessor(db.Model):
    __tablename__ = 'simulados_gerados_professor'
    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'), nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())
    mes_id = db.Column(db.Integer, db.ForeignKey('meses.id'), nullable=True)
    status = db.Column(db.String(20), nullable=True, default='gerado')

class SimuladoQuestoes(db.Model):
    __tablename__ = 'simulado_questoes'
    id = db.Column(db.Integer, primary_key=True)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_gerados.id'), nullable=False)
    questao_id = db.Column(db.Integer, db.ForeignKey('banco_questoes.id'), nullable=True)  # Permitindo NULL temporariamente

class SimuladoQuestoesProfessor(db.Model):
    __tablename__ = 'simulado_questoes_professor'
    id = db.Column(db.Integer, primary_key=True)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_gerados_professor.id'), nullable=False)
    questao_id = db.Column(db.Integer, db.ForeignKey('banco_questoes.id'), nullable=False)

class SimuladosEnviados(db.Model):
    __tablename__ = 'simulados_enviados'
    id = db.Column(db.Integer, primary_key=True)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_gerados_professor.id'), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False)
    data_envio = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())
    status = db.Column(db.String(20), nullable=True, default='enviado')
    data_limite = db.Column(db.DateTime, nullable=True)

class AlunoSimulado(db.Model):
    __tablename__ = 'aluno_simulado'
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_enviados.id'), nullable=False)
    status = db.Column(db.String(20), nullable=True, default='não respondido')
    data_resposta = db.Column(db.DateTime, nullable=True)

class DesempenhoSimulado(db.Model):
    __tablename__ = 'desempenho_simulado'
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_enviados.id'), nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'), nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    codigo_ibge = db.Column(db.Integer, nullable=False)
    respostas_aluno = db.Column(db.JSON, nullable=False)
    respostas_corretas = db.Column(db.JSON, nullable=False)
    desempenho = db.Column(db.Numeric(5, 2), nullable=False)
    data_resposta = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())
    tipo_usuario_id = db.Column(db.Integer, nullable=False, default=5)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=True)

# Configuração do Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data.id
        self.nome = user_data.nome
        self.tipo_usuario_id = user_data.tipo_usuario_id
        self.escola_id = user_data.escola_id
        self.ano_escolar_id = user_data.ano_escolar_id
        self.turma_id = user_data.turma_id
        self.email = user_data.email
        self.codigo_ibge = user_data.codigo_ibge

@login_manager.user_loader
def load_user(user_id):
    user_data = Usuarios.query.get(int(user_id))
    if user_data:
        return User(user_data)
    return None

# Rotas básicas para teste
@app.route('/')
def index():
    return 'Sistema funcionando com MySQL!'

@app.route('/test_db')
def test_db():
    try:
        # Tenta fazer uma consulta simples
        usuarios = Usuarios.query.limit(1).all()
        return f'Conexão com banco de dados OK! Encontrado {len(usuarios)} usuário(s).'
    except Exception as e:
        return f'Erro ao conectar com o banco de dados: {str(e)}'

if __name__ == '__main__':
    app.run(debug=True)

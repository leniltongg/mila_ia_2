from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, make_response, send_file, send_from_directory
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from urllib.parse import quote_plus
from datetime import datetime, timedelta
import openai
import os
import json
import PyPDF2
import pdfplumber
import tempfile
import pandas as pd
import base64
from dotenv import load_dotenv
from extensions import db
from routes.relatorios import relatorios_bp
import uuid
from flask_session import Session
from io import StringIO
import unicodedata
import re
import time
import requests

# Carrega variáveis do arquivo .env
load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Adicionar filtros personalizados ao Jinja2
app.jinja_env.filters['chr'] = chr

# Configurações básicas do Flask
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave-secreta-temporaria')

# Codificando a senha para URL
password = quote_plus('31952814Gg@')
# String de conexão MySQL usando pymysql
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://mila_user:{password}@127.0.0.1/mila_educacional'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'  # pasta onde os PDFs serão temporariamente salvos

# Configuração do Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = tempfile.gettempdir()
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
Session(app)



# Certifique-se que a pasta existe
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Configure a chave de API da OpenAI
openai.api_key="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"

# Inicializa o SQLAlchemy
db.init_app(app)


# Cria o contexto da aplicação
app.app_context().push()

# Agora podemos importar os modelos depois de inicializar o db
from models import (
    Usuarios, Escolas, Turmas, Ano_escolar, ProfessorTurmaEscola, 
    Assuntos, Disciplinas, SimuladosGerados, TiposUsuarios, TiposEnsino,
    MESES, Cidades, BancoQuestoes, SimuladosGeradosProfessor,
    SimuladoQuestoes, SimuladoQuestoesProfessor, SimuladosEnviados,
    AlunoSimulado, DesempenhoSimulado, EscolaTiposEnsino, ImagemQuestao
)
from routes import conteudo_bp, professores_bp, alunos_bp, simulados_bp, secretaria_educacao_bp
from routes.administrador import administrador_bp

migrate = Migrate(app, db)

# Registra os blueprints
app.register_blueprint(alunos_bp)
app.register_blueprint(professores_bp)
app.register_blueprint(simulados_bp)
app.register_blueprint(secretaria_educacao_bp)
app.register_blueprint(conteudo_bp)
app.register_blueprint(administrador_bp)
app.register_blueprint(relatorios_bp, url_prefix='/secretaria_educacao')

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Classe User para Flask-Login
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

@login_manager.user_loader
def load_user(user_id):
    # Usando a nova API do SQLAlchemy 2.0
    user_data = db.session.get(Usuarios, int(user_id))
    if user_data:
        return User(user_data)
    return None

# Rotas de autenticação
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        login_identifier = request.form['email']  # Pode ser email ou CPF
        senha = request.form['senha']

        user_data = Usuarios.query.filter(
            (Usuarios.email == login_identifier) | (Usuarios.cpf == login_identifier)
        ).first()

        if user_data:
            if check_password_hash(user_data.senha, senha):
                user = User(user_data)
                login_user(user)

                next_page = request.args.get('next') or {
                    1: 'portal_administrador',
                    2: 'portal_administracao',
                    3: 'professores.portal_professores',
                    4: 'alunos_bp.portal_alunos',  # Alterado para usar o endpoint do blueprint
                    5: 'secretaria_educacao.portal_secretaria_educacao',
                    6: 'administrador.portal_administrador2'
                }.get(user_data.tipo_usuario_id, 'login')

                return redirect(url_for(next_page))
            else:
                error = "Senha incorreta. Por favor, tente novamente."
        else:
            error = "Usuário não encontrado. Por favor, verifique seu email ou CPF."

    return render_template('login.html', error=error)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# @app.route("/redefinir_senha/<token>", methods=['GET', 'POST'])
# def redefinir_senha(token):
#     try:
#         token_data = base64.b64decode(token).decode('utf-8')
#         user_id = int(token_data.split(':')[0])
#         timestamp = float(token_data.split(':')[1])
        
#         # Verifica se o token expirou (24 horas)
#         if datetime.now().timestamp() - timestamp > 24 * 3600:
#             flash('O link de redefinição de senha expirou. Por favor, solicite um novo.', 'error')
#             return redirect(url_for('login'))
        
#         user = Usuarios.query.get(user_id)
#         if not user:
#             flash('Link inválido', 'error')
#             return redirect(url_for('login'))
        
#         if request.method == 'POST':
#             senha = request.form['senha']
#             confirmar_senha = request.form['confirmar_senha']
            
#             if senha != confirmar_senha:
#                 flash('As senhas não coincidem', 'error')
#                 return render_template('redefinir_senha.html')
            
#             user.senha = generate_password_hash(senha)
#             db.session.commit()
            
#             flash('Senha alterada com sucesso!', 'success')
#             return redirect(url_for('login'))
        
#         return render_template('redefinir_senha.html')
    
#     except Exception as e:
#         flash('Ocorreu um erro ao redefinir a senha', 'error')
#         return redirect(url_for('login'))

@app.route("/recuperar_senha", methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form['email']
        user = Usuarios.query.filter_by(email=email).first()
        
        if user:
            # Gera um token único baseado no ID do usuário e timestamp
            timestamp = datetime.now().timestamp()
            token = base64.b64encode(f"{user.id}:{timestamp}".encode()).decode()
            
            # Aqui você deve implementar o envio do email com o link de redefinição
            reset_link = url_for('redefinir_senha', token=token, _external=True)
            
            # Por enquanto, apenas mostra o link
            flash(f'Link de redefinição de senha: {reset_link}', 'info')
            return redirect(url_for('login'))
        else:
            flash('Email não encontrado', 'error')
    
    return render_template('recuperar_senha.html')

@app.route('/alterar-senha', methods=['GET', 'POST'])
@login_required
def alterar_senha():
    error = None
    success = None

    if request.method == 'POST':
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')

        if nova_senha != confirmar_senha:
            error = "As novas senhas não coincidem. Por favor, tente novamente."
        else:
            # Obter a senha atual do banco de dados
            usuario = Usuarios.query.get(current_user.id)

            # Validar a senha atual
            if not check_password_hash(usuario.senha, senha_atual):
                error = "A senha atual está incorreta. Por favor, tente novamente."
            else:
                # Gerar hash da nova senha
                nova_senha_hash = generate_password_hash(nova_senha)

                # Atualizar a senha no banco de dados
                usuario.senha = nova_senha_hash
                db.session.commit()
                success = "Senha alterada com sucesso!"

    return render_template('alterar_senha.html', error=error, success=success)

@app.route("/redefinir_senha/<token>", methods=['GET', 'POST'])
def redefinir_senha(token):
    try:
        # Decodificar o token
        token_data = base64.b64decode(token).decode('utf-8')
        user_id = int(token_data.split(':')[0])
        timestamp = float(token_data.split(':')[1])
        
        # Verifica se o token expirou (24 horas)
        if datetime.now().timestamp() - timestamp > 24 * 3600:
            flash('O link de redefinição de senha expirou. Por favor, solicite um novo.', 'error')
            return redirect(url_for('login'))
        
        # Buscar o usuário
        user = Usuarios.query.get(user_id)
        if not user:
            flash('Link inválido', 'error')
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            senha = request.form['senha']
            confirmar_senha = request.form['confirmar_senha']
            
            if senha != confirmar_senha:
                flash('As senhas não coincidem', 'error')
                return render_template('redefinir_senha.html', token=token)
            
            # Atualizar a senha
            user.senha = generate_password_hash(senha)
            db.session.commit()
            
            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('login'))
        
        # GET request - mostrar o formulário
        return render_template('redefinir_senha.html', token=token)
    
    except Exception as e:
        print(f"Erro ao redefinir senha: {e}")  # Log do erro
        flash('Ocorreu um erro ao redefinir a senha', 'error')
        return redirect(url_for('login'))

@app.route("/get_tipos_usuarios")
def get_tipos_usuarios():
    tipos = TiposUsuarios.query.all()
    return jsonify([{
        'id': tipo.id,
        'descricao': tipo.descricao
    } for tipo in tipos])


def save_temp_data(data, prefix='temp'):
    temp_id = str(uuid.uuid4())
    temp_file = os.path.join(tempfile.gettempdir(), f"{prefix}_{temp_id}.json")
    with open(temp_file, 'w') as f:
        json.dump(data, f)
    return temp_id

def get_temp_data(temp_id, prefix='temp'):
    temp_file = os.path.join(tempfile.gettempdir(), f"{prefix}_{temp_id}.json")
    try:
        with open(temp_file, 'r') as f:
            data = json.load(f)
        os.remove(temp_file)  # Remove o arquivo após a leitura
        return data
    except FileNotFoundError:
        return None

# Função para validar os dados do CSV
def validate_escolas(data):
    required_columns = [
        'nome', 'cep', 'estado', 'cidade', 'bairro', 'endereco', 'numero',
        'telefone', 'cnpj', 'diretor', 'codigo_ibge', 'ensino_infantil', 
        'aee', 'fundamental_i', 'fundamental_ii', 'ensino_medio'
    ]

    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        print(f"Faltam as seguintes colunas no arquivo CSV: {', '.join(missing_columns)}")
        return False

    for index, row in data.iterrows():
        if row.isnull().any():
            print(f"Erro: Valores ausentes na linha {index + 1}")
            return False

    return True

@app.route('/cadastrar_escolas_massa', methods=['POST'])
def cadastrar_escolas_massa():
    if 'file' not in request.files:
        flash("Nenhum arquivo enviado", "error")
        return redirect(request.url)

    file = request.files["file"]
    if file.filename == "":
        flash("Nenhum arquivo selecionado", "error")
        return redirect(request.url)

    if file:
        try:
            # Ler o arquivo CSV
            content = file.read().decode('utf-8')
            df = pd.read_csv(StringIO(content))

            # Validar os dados
            if not validate_escolas(df):
                flash("Erro na validação dos dados. Verifique o arquivo e tente novamente.", "error")
                return redirect(request.url)

            # Armazenar os dados em arquivo temporário
            temp_id = save_temp_data(df.to_dict('records'), 'escolas')
            session['escolas_temp_id'] = temp_id
            
            return redirect(url_for('confirmar_cadastro_escolas_massa'))

        except Exception as e:
            flash(f"Erro ao processar o arquivo: {str(e)}", "error")
            return redirect(request.url)

    return render_template("cadastrar_escolas_massa.html")

@app.route("/confirmar_cadastro_escolas_massa", methods=["GET", "POST"])
@login_required
def confirmar_cadastro_escolas_massa():
    if current_user.tipo_usuario_id != 1:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    temp_id = session.get('escolas_temp_id')
    if not temp_id:
        flash("Nenhum dado de escola para confirmar", "error")
        return redirect(url_for('cadastrar_escolas_massa'))

    escolas_data = get_temp_data(temp_id, 'escolas')
    if not escolas_data:
        flash("Dados temporários expirados. Por favor, faça o upload novamente.", "error")
        return redirect(url_for('cadastrar_escolas_massa'))

    if request.method == "POST":
        try:
            for escola in escolas_data:
                nova_escola = Escolas(
                    nome_da_escola=escola['nome'],
                    cep=escola['cep'],
                    codigo_ibge=escola['codigo_ibge'],
                    endereco=escola['endereco'],
                    numero=escola['numero'],
                    bairro=escola['bairro'],
                    telefone=escola['telefone'],
                    ensino_fundamental=escola.get('fundamental_i', 0) or escola.get('fundamental_ii', 0)
                )
                db.session.add(nova_escola)

            db.session.commit()
            session.pop('escolas_temp_id', None)  # Remove o ID temporário da sessão
            flash("Escolas cadastradas com sucesso!", "success")
            return redirect(url_for('portal_administrador'))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao cadastrar escolas: {str(e)}", "error")
            return redirect(url_for('cadastrar_escolas_massa'))

    return render_template(
        "confirmar_cadastro_escolas_massa.html",
        escolas=escolas_data
    )

@app.route('/cadastrar_turmas_massa', methods=['POST'])
def cadastrar_turmas_massa():
    if 'file' not in request.files:
        flash("Nenhum arquivo enviado", "error")
        return redirect(request.url)

    file = request.files["file"]
    if file.filename == "":
        flash("Nenhum arquivo selecionado", "error")
        return redirect(request.url)

    if file:
        try:
            # Ler o arquivo CSV
            content = file.read().decode('utf-8')
            df = pd.read_csv(StringIO(content))

            # Validar os dados
            required_columns = ['nome', 'escola_id', 'ano_escolar_id']
            if not all(col in df.columns for col in required_columns):
                flash("Arquivo não contém todas as colunas necessárias", "error")
                return redirect(request.url)

            # Armazenar os dados em arquivo temporário
            temp_id = save_temp_data(df.to_dict('records'), 'turmas')
            session['turmas_temp_id'] = temp_id
            
            return redirect(url_for('confirmar_cadastro_turmas'))

        except Exception as e:
            flash(f"Erro ao processar o arquivo: {str(e)}", "error")
            return redirect(request.url)

    return render_template("cadastrar_turmas_massa.html")

@app.route("/confirmar_cadastro_turmas", methods=["GET", "POST"])
@login_required
def confirmar_cadastro_turmas():
    if current_user.tipo_usuario_id != 1:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    temp_id = session.get('turmas_temp_id')
    if not temp_id:
        flash("Nenhum dado de turma para confirmar", "error")
        return redirect(url_for('cadastrar_turmas_massa'))

    turmas_data = get_temp_data(temp_id, 'turmas')
    if not turmas_data:
        flash("Dados temporários expirados. Por favor, faça o upload novamente.", "error")
        return redirect(url_for('cadastrar_turmas_massa'))

    if request.method == "POST":
        try:
            for turma in turmas_data:
                nova_turma = Turmas(
                    nome=turma['nome'],
                    escola_id=turma['escola_id'],
                    ano_escolar_id=turma['ano_escolar_id']
                )
                db.session.add(nova_turma)

            db.session.commit()
            session.pop('turmas_temp_id', None)  # Remove o ID temporário da sessão
            flash("Turmas cadastradas com sucesso!", "success")
            return redirect(url_for('portal_administrador'))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao cadastrar turmas: {str(e)}", "error")
            return redirect(url_for('cadastrar_turmas_massa'))

    return render_template(
        "confirmar_cadastro_turmas.html",
        turmas=turmas_data
    )

@app.route('/cadastrar_usuarios_massa', methods=['POST'])
def cadastrar_usuarios_massa():
    if 'file' not in request.files:
        flash("Nenhum arquivo enviado", "error")
        return redirect(request.url)

    file = request.files["file"]
    if file.filename == "":
        flash("Nenhum arquivo selecionado", "error")
        return redirect(request.url)

    if file:
        try:
            # Ler o arquivo CSV
            content = file.read().decode('utf-8')
            df = pd.read_csv(StringIO(content))

            # Validar os dados
            required_columns = ['nome', 'email', 'tipo_usuario_id', 'escola_id', 'codigo_ibge']
            if not all(col in df.columns for col in required_columns):
                flash("Arquivo não contém todas as colunas necessárias", "error")
                return redirect(request.url)

            # Armazenar os dados em arquivo temporário
            temp_id = save_temp_data(df.to_dict('records'), 'usuarios')
            session['usuarios_temp_id'] = temp_id
            
            return redirect(url_for('confirmar_cadastro_usuarios'))

        except Exception as e:
            flash(f"Erro ao processar o arquivo: {str(e)}", "error")
            return redirect(request.url)

    return render_template("cadastrar_usuarios_massa.html")

@app.route("/confirmar_cadastro_usuarios", methods=["GET", "POST"])
@login_required
def confirmar_cadastro_usuarios():
    if current_user.tipo_usuario_id != 1:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    temp_id = session.get('usuarios_temp_id')
    if not temp_id:
        flash("Nenhum dado de usuário para confirmar", "error")
        return redirect(url_for('cadastrar_usuarios_massa'))

    usuarios_data = get_temp_data(temp_id, 'usuarios')
    if not usuarios_data:
        flash("Dados temporários expirados. Por favor, faça o upload novamente.", "error")
        return redirect(url_for('cadastrar_usuarios_massa'))

    if request.method == "POST":
        try:
            for usuario in usuarios_data:
                senha_padrao = generate_password_hash('123456')
                novo_usuario = Usuarios(
                    nome=usuario['nome'],
                    email=usuario['email'],
                    senha=senha_padrao,
                    tipo_usuario_id=usuario['tipo_usuario_id'],
                    escola_id=usuario['escola_id'],
                    turma_id=usuario.get('turma_id'),
                    tipo_ensino_id=usuario.get('tipo_ensino_id'),
                    ano_escolar_id=usuario.get('ano_escolar_id'),
                    codigo_ibge=usuario['codigo_ibge'],
                    cep=usuario.get('cep')
                )
                db.session.add(novo_usuario)

            db.session.commit()
            session.pop('usuarios_temp_id', None)  # Remove o ID temporário da sessão
            flash("Usuários cadastrados com sucesso!", "success")
            return redirect(url_for('portal_administrador'))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao cadastrar usuários: {str(e)}", "error")
            return redirect(url_for('cadastrar_usuarios_massa'))

    return render_template(
        "confirmar_cadastro_usuarios.html",
        usuarios=usuarios_data
    )

# Rotas básicas
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    user = current_user
    if user.tipo_usuario_id == 1:  # Administrador
        return redirect(url_for('portal_administrador'))
    elif user.tipo_usuario_id == 2:  # Administração
        return redirect(url_for('portal_administracao'))
    elif user.tipo_usuario_id == 3:  # Professor
        return redirect(url_for('professores.portal_professores'))
    elif user.tipo_usuario_id == 4:  # Aluno
        return redirect(url_for('alunos_bp.portal_alunos'))
    elif user.tipo_usuario_id == 5:  # Secretaria de Educação
        return redirect(url_for('secretaria_educacao.portal_secretaria_educacao'))
    else:
        return redirect(url_for('login'))

@app.route("/debug_usuarios")
def debug_usuarios():
    usuarios = Usuarios.query.all()
    return jsonify([usuario.id for usuario in usuarios])

@app.route("/atualizar_senhas", methods=["GET"])
def atualizar_senhas():
    usuarios = Usuarios.query.all()

    for usuario in usuarios:
        senha = usuario.senha

        # Verificar se a senha já está em hash (hashes começam com 'pbkdf2:')
        if not senha.startswith("pbkdf2:sha256:"):
            # Gerar hash da senha
            senha_hash = generate_password_hash(senha)
            usuario.senha = senha_hash
            db.session.commit()

    return "Todas as senhas foram convertidas para hash com sucesso!"

@app.route("/importar_assuntos", methods=["GET", "POST"])
@login_required
def importar_assuntos():
    if current_user.tipo_usuario_id != 1:  # Apenas administradores podem importar
        return redirect(url_for("home"))

    if request.method == "POST":
        if "file" not in request.files:
            flash("Nenhum arquivo enviado.", "error")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("Nenhum arquivo selecionado.", "error")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            # Processar o CSV
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                registros_importados = 0

                for row in reader:
                    try:
                        assunto = Assunto(
                            disciplina=row['disciplina'],
                            assunto=row['assunto'],
                            ano_escolar_id=row['ano_escolar_id'],
                            turma_id=None,
                            escola_id=None,
                            professor_id=None
                        )
                        db.session.add(assunto)
                        registros_importados += 1
                    except Exception as e:
                        print(f"Erro ao inserir linha: {e}")
                        db.session.rollback()
                        raise

                db.session.commit()
                flash(f"Importação concluída com sucesso! {registros_importados} registros adicionados.", "success")
                return redirect(url_for('portal_administrador'))

            os.remove(filepath)  # Remove o arquivo após processamento
        else:
            flash("Tipo de arquivo não permitido.", "error")
            return redirect(request.url)

    return render_template('importar_assuntos.html')

@app.route("/portal_administrador/cadastrar_turma", methods=["GET", "POST"])
@login_required
def cadastrar_turma():
    if current_user.tipo_usuario_id != 1:  # Apenas administradores podem cadastrar
        return redirect(url_for("home"))

    # Buscar escolas cadastradas para o menu suspenso
    escolas = Escolas.query.all()

    if request.method == "POST":
        # Obter os valores do formulário
        escola_id = request.form.get("escola_id", "").strip()
        tipo_ensino_id = request.form.get("tipo_ensino_id", "").strip()
        ano_escolar_id = request.form.get("ano_escolar_id", "").strip()
        turma_nome = request.form.get("turma", "").strip()

        # Printar os valores recebidos para depuração
        print(f"escola_id: {escola_id}")
        print(f"tipo_ensino_id: {tipo_ensino_id}")
        print(f"ano_escolar_id: {ano_escolar_id}")
        print(f"turma_nome: {turma_nome}")

        # Validar campos obrigatórios
        if not all([escola_id, tipo_ensino_id, ano_escolar_id, turma_nome]):
            print("Erro: Campos obrigatórios não preenchidos!")
            return render_template(
                "cadastrar_turma.html",
                escolas=escolas,
                error="Todos os campos são obrigatórios!"
            )

        try:
            # Criar nova turma
            nova_turma = Turmas(
                escola_id=int(escola_id),
                tipo_ensino_id=int(tipo_ensino_id),
                ano_escolar_id=int(ano_escolar_id),
                turma=turma_nome
            )
            db.session.add(nova_turma)
            db.session.commit()

            print("Turma cadastrada com sucesso!")
            return render_template(
                "cadastrar_turma.html",
                escolas=escolas,
                success="Turma cadastrada com sucesso!"
            )
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao cadastrar turma: {e}")
            return render_template(
                "cadastrar_turma.html",
                escolas=escolas,
                error="Erro ao cadastrar turma. Por favor, tente novamente!"
            )

    return render_template("cadastrar_turma.html", escolas=escolas)



@app.route("/get_tipo_ensino", methods=["GET"])
@login_required
def get_tipo_ensino():
    escola_id = request.args.get("escola_id")
    if not escola_id:
        return jsonify([])

    # Buscar os tipos de ensino associados à escola
    tipos_ensino = TiposEnsino.query.join(
        EscolaTiposEnsino,
        EscolaTiposEnsino.tipo_ensino_id == TiposEnsino.id
    ).filter(
        EscolaTiposEnsino.escola_id == escola_id
    ).all()

    if not tipos_ensino:
        app.logger.info(f"Nenhum tipo de ensino encontrado para a escola {escola_id}.")
        return jsonify([])

    app.logger.info(f"Tipos de ensino encontrados: {tipos_ensino}")
    return jsonify([{"id": tipo.id, "nome": tipo.nome} for tipo in tipos_ensino])

@app.route("/get_Ano_escolar", methods=["GET"])
@login_required
def get_Ano_escolar():
    tipo_ensino_id = request.args.get("tipo_ensino_id")
    codigo_ibge = current_user.codigo_ibge

    if not tipo_ensino_id:
        return jsonify([])

    # Buscar séries pelo tipo de ensino
    Ano_escolar = Ano_escolar.query.filter_by(tipo_ensino_id=tipo_ensino_id).all()

    return jsonify([{"id": s.id, "nome": s.nome} for s in Ano_escolar])

@app.route("/get_turmas", methods=["GET"])
@login_required
def get_turmas():
    escola_id = request.args.get("escola_id")
    tipo_ensino_id = request.args.get("tipo_ensino_id")
    ano_escolar_id = request.args.get("ano_escolar_id")

    app.logger.info(f"Parâmetros recebidos: escola_id={escola_id}, tipo_ensino_id={tipo_ensino_id}, ano_escolar_id={ano_escolar_id}")

    if not all([escola_id, tipo_ensino_id, ano_escolar_id]):
        app.logger.warning("Parâmetros insuficientes fornecidos para /get_turmas.")
        return jsonify([])

    # Buscar turmas com os filtros
    turmas = Turmas.query.join(
        Ano_escolar, Turmas.ano_escolar_id == Ano_escolar.id
    ).filter(
        Turmas.escola_id == escola_id,
        Turmas.tipo_ensino_id == tipo_ensino_id,
        Turmas.ano_escolar_id == ano_escolar_id
    ).all()

    app.logger.info(f"Turmas encontradas: {turmas}")

    # Retorna série e turma
    return jsonify([{
        "id": turma.id,
        "Ano_escolar": turma.Ano_escolar.nome,
        "turma": turma.turma
    } for turma in turmas])

@app.route('/buscar_alunos', methods=['GET'])
@login_required
def buscar_alunos():
    turma_id = request.args.get("turma_id")
    
    if not turma_id:
        return jsonify([])

    # Buscar alunos da turma
    alunos = Usuarios.query.filter_by(
        turma_id=turma_id,
        tipo_usuario_id=4  # tipo aluno
    ).all()

    return jsonify([{"id": aluno.id, "nome": aluno.nome} for aluno in alunos])

@app.route("/portal_administrador/cadastrar_usuario", methods=["GET", "POST"])
@login_required
def cadastrar_usuario():
    print("Entrou na rota de cadastro de usuário!")
    
    if current_user.tipo_usuario_id != 1:  # Apenas administradores podem cadastrar
        print("Usuário não é administrador, redirecionando...")
        return redirect(url_for("home"))

    # Buscar escolas disponíveis
    escolas = Escolas.query.all()

    if request.method == "POST":
        print("Formulário de cadastro recebido!")

        # Capturando os dados do formulário
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")
        tipo_usuario_id = request.form.get("tipo_usuario_id")
        codigo_ibge = request.form.get("codigo_ibge")
        cep = request.form.get("cep")

        # Capturando múltiplas turmas para professores
        escolas_ids = request.form.getlist("escola_id[]")
        tipos_ensino_ids = request.form.getlist("tipo_ensino[]")
        ano_escolar_ids = request.form.getlist("Ano_escolar[]")
        turmas_ids = request.form.getlist("turma_id[]")

        print(f"Recebidos: Nome={nome}, Email={email}, Tipo={tipo_usuario_id}, Turmas={turmas_ids}")

        # Validar campos obrigatórios
        if not all([nome, email, senha, tipo_usuario_id, codigo_ibge, cep]):
            print("Erro: Campos obrigatórios não preenchidos.")
            flash("Todos os campos são obrigatórios!", "error")
            return render_template("cadastrar_usuario.html", escolas=escolas)

        # Validação específica para professores e alunos
        if tipo_usuario_id == "4":  # Aluno
            if not all([escolas_ids[0], turmas_ids[0], tipos_ensino_ids[0], ano_escolar_ids[0]]):
                flash("Escola, Tipo de Ensino, Ano Escolar e Turma são obrigatórios para Alunos!", "error")
                return render_template("cadastrar_usuario.html", escolas=escolas)

        if tipo_usuario_id == "3":  # Professor
            if not all([escolas_ids, turmas_ids, tipos_ensino_ids, ano_escolar_ids]):
                flash("Escola, Tipo de Ensino, Ano Escolar e Turma são obrigatórios para Professores!", "error")
                return render_template("cadastrar_usuario.html", escolas=escolas)

        try:
            senha_hash = generate_password_hash(senha)

            if tipo_usuario_id != "3":  # Não é professor
                novo_usuario = Usuarios(
                    nome=nome,
                    email=email,
                    senha=senha_hash,
                    tipo_usuario_id=tipo_usuario_id,
                    escola_id=escolas_ids[0],
                    turma_id=turmas_ids[0],
                    tipo_ensino_id=tipos_ensino_ids[0],
                    ano_escolar_id=ano_escolar_ids[0],
                    codigo_ibge=codigo_ibge,
                    cep=cep
                )
                db.session.add(novo_usuario)
                db.session.commit()
                print(f"Usuário {nome} cadastrado com sucesso!")
                flash("Usuário cadastrado com sucesso!", "success")
            else:  # Professor
                # Criar o professor
                novo_professor = Usuarios(
                    nome=nome,
                    email=email,
                    senha=senha_hash,
                    tipo_usuario_id=tipo_usuario_id,
                    codigo_ibge=codigo_ibge,
                    cep=cep
                )
                db.session.add(novo_professor)
                db.session.commit()
                print(f"Professor {nome} cadastrado com ID {novo_professor.id}")

                # Associar turmas ao professor
                for escola_id, tipo_ensino_id, ano_escolar_id, turma_id in zip(escolas_ids, tipos_ensino_ids, ano_escolar_ids, turmas_ids):
                    prof_turma = ProfessorTurmaEscola(
                        professor_id=novo_professor.id,
                        escola_id=escola_id,
                        turma_id=turma_id,
                        tipo_ensino_id=tipo_ensino_id,
                        ano_escolar_id=ano_escolar_id
                    )
                    db.session.add(prof_turma)
                db.session.commit()
                print(f"Turmas do professor {nome} cadastradas com sucesso!")
                flash("Professor cadastrado com sucesso com todas as turmas!", "success")

            return redirect(url_for("portal_administrador"))

        except Exception as e:
            db.session.rollback()
            print(f"Erro ao cadastrar usuário: {e}")
            flash(f"Erro ao cadastrar usuário: {e}", "error")

    return render_template("cadastrar_usuario.html", escolas=escolas)

@app.route("/portal_administrador/cadastrar_escola", methods=["GET", "POST"])
@login_required
def cadastrar_escola():
    if current_user.tipo_usuario_id != 1:  # Apenas administradores podem cadastrar
        return redirect(url_for("home"))

    if request.method == "POST":
        # Capturar dados do formulário
        nome = request.form.get("nome")
        codigo_ibge = request.form.get("codigo_ibge")
        cep = request.form.get("cep")
        tipos_ensino = request.form.getlist("tipos_ensino")

        # Validar campos obrigatórios
        if not all([nome, codigo_ibge, cep, tipos_ensino]):
            flash("Todos os campos são obrigatórios!", "error")
            return render_template("cadastrar_escola.html")

        try:
            # Criar nova escola
            nova_escola = Escolas(
                nome=nome,
                codigo_ibge=codigo_ibge,
                cep=cep
            )
            db.session.add(nova_escola)
            db.session.commit()

            # Associar tipos de ensino à escola
            for tipo_ensino_id in tipos_ensino:
                escola_tipo_ensino = EscolaTiposEnsino(
                    escola_id=nova_escola.id,
                    tipo_ensino_id=int(tipo_ensino_id)
                )
                db.session.add(escola_tipo_ensino)
            db.session.commit()

            flash("Escola cadastrada com sucesso!", "success")
            return redirect(url_for("portal_administrador"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao cadastrar escola: {e}", "error")

    # Buscar todos os tipos de ensino para o formulário
    tipos_ensino = TiposEnsino.query.all()
    return render_template("cadastrar_escola.html", tipos_ensino=tipos_ensino)

@app.route("/portal_administrador/cadastrar_turma_em_massa", methods=["GET", "POST"])
@login_required
def cadastrar_turma_em_massa():
    if current_user.tipo_usuario_id != 1:  # Apenas administradores podem cadastrar
        return redirect(url_for("home"))

    if request.method == "POST":
        if "file" not in request.files:
            flash("Nenhum arquivo enviado", "error")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("Nenhum arquivo selecionado", "error")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            try:
                # Processar o CSV
                df = pd.read_csv(filepath)
                registros_importados = 0

                for _, row in df.iterrows():
                    try:
                        # Criar nova turma
                        nova_turma = Turmas(
                            escola_id=int(row["escola_id"]),
                            tipo_ensino_id=int(row["tipo_ensino_id"]),
                            ano_escolar_id=int(row["ano_escolar_id"]),
                            turma=row["turma"]
                        )
                        db.session.add(nova_turma)
                        registros_importados += 1
                    except Exception as e:
                        print(f"Erro ao inserir linha: {e}")
                        db.session.rollback()
                        raise

                db.session.commit()
                flash(f"Importação concluída com sucesso! {registros_importados} turmas adicionadas.", "success")
                return redirect(url_for("portal_administrador"))

            except Exception as e:
                print(f"Erro ao processar arquivo: {e}")
                flash(f"Erro ao processar arquivo: {e}", "error")
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
        else:
            flash("Tipo de arquivo não permitido.", "error")
            return redirect(request.url)

    return render_template("cadastrar_turma_em_massa.html")

@app.route("/portal_administrador/cadastrar_usuario_em_massa", methods=["GET", "POST"])
@login_required
def cadastrar_usuario_em_massa():
    if current_user.tipo_usuario_id != 1:  # Apenas administradores podem cadastrar
        return redirect(url_for("home"))

    if request.method == "POST":
        if "file" not in request.files:
            flash("Nenhum arquivo enviado", "error")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("Nenhum arquivo selecionado", "error")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            try:
                # Processar o CSV
                df = pd.read_csv(filepath)
                registros_importados = 0

                for _, row in df.iterrows():
                    try:
                        # Gerar hash da senha
                        senha_hash = generate_password_hash(str(row["senha"]))

                        # Criar novo usuário
                        novo_usuario = Usuarios(
                            nome=row["nome"],
                            email=row["email"],
                            senha=senha_hash,
                            tipo_usuario_id=int(row["tipo_usuario_id"]),
                            escola_id=int(row["escola_id"]) if not pd.isna(row["escola_id"]) else None,
                            turma_id=int(row["turma_id"]) if not pd.isna(row["turma_id"]) else None,
                            tipo_ensino_id=int(row["tipo_ensino_id"]) if not pd.isna(row["tipo_ensino_id"]) else None,
                            ano_escolar_id=int(row["ano_escolar_id"]) if not pd.isna(row["ano_escolar_id"]) else None,
                            codigo_ibge=row["codigo_ibge"],
                            cep=row["cep"]
                        )
                        db.session.add(novo_usuario)

                        # Se for professor, adicionar relações com turmas
                        if int(row["tipo_usuario_id"]) == 3:  # Professor
                            turmas = row["turmas_ids"].split("|") if not pd.isna(row["turmas_ids"]) else []
                            escolas = row["escolas_ids"].split("|") if not pd.isna(row["escolas_ids"]) else []
                            tipos_ensino = row["tipos_ensino_ids"].split("|") if not pd.isna(row["tipos_ensino_ids"]) else []
                            Ano_escolar = row["ano_escolar_ids"].split("|") if not pd.isna(row["ano_escolar_ids"]) else []

                            for t, e, te, s in zip(turmas, escolas, tipos_ensino, Ano_escolar):
                                prof_turma = ProfessorTurmaEscola(
                                    professor_id=novo_usuario.id,
                                    escola_id=int(e),
                                    turma_id=int(t),
                                    tipo_ensino_id=int(te),
                                    ano_escolar_id=int(s)
                                )
                                db.session.add(prof_turma)

                        registros_importados += 1
                    except Exception as e:
                        print(f"Erro ao inserir linha: {e}")
                        db.session.rollback()
                        raise

                db.session.commit()
                flash(f"Importação concluída com sucesso! {registros_importados} usuários adicionados.", "success")
                return redirect(url_for("portal_administrador"))

            except Exception as e:
                print(f"Erro ao processar arquivo: {e}")
                flash(f"Erro ao processar arquivo: {e}", "error")
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
        else:
            flash("Tipo de arquivo não permitido.", "error")
            return redirect(request.url)

    return render_template("cadastrar_usuario_em_massa.html")

@app.route("/portal_administrador/cadastrar_assunto", methods=["GET", "POST"])
@login_required
def cadastrar_assunto():
    if current_user.tipo_usuario_id != 1:  # Apenas administradores podem cadastrar
        return redirect(url_for("home"))

    if request.method == "POST":
        disciplina = request.form.get("disciplina")
        assunto = request.form.get("assunto")
        ano_escolar_id = request.form.get("ano_escolar_id")

        if not all([disciplina, assunto, ano_escolar_id]):
            flash("Todos os campos são obrigatórios!", "error")
            return render_template("cadastrar_assunto.html")

        try:
            novo_assunto = Assunto(
                disciplina=disciplina,
                assunto=assunto,
                ano_escolar_id=ano_escolar_id
            )
            db.session.add(novo_assunto)
            db.session.commit()

            flash("Assunto cadastrado com sucesso!", "success")
            return redirect(url_for("portal_administrador"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao cadastrar assunto: {e}", "error")

    # Buscar séries para o formulário
    Ano_escolar = Ano_escolar.query.all()
    return render_template("cadastrar_assunto.html", Ano_escolar=Ano_escolar)

# Rotas de API para os selects dinâmicos
@app.route("/api/get_tipo_ensino", methods=["GET"])
@login_required
def api_get_tipo_ensino():
    escola_id = request.args.get("escola_id")
    if not escola_id:
        return jsonify([])
    
    tipos_ensino = db.session.query(TiposEnsino)\
        .join(EscolaTiposEnsino)\
        .filter(EscolaTiposEnsino.escola_id == escola_id)\
        .all()
    
    return jsonify([{
        'id': tipo.id,
        'nome': tipo.nome
    } for tipo in tipos_ensino])

@app.route("/api/get_Ano_escolar", methods=["GET"])
@login_required
def api_get_Ano_escolar():
    tipo_ensino_id = request.args.get("tipo_ensino_id")
    if not tipo_ensino_id:
        return jsonify([])
    
    Ano_escolar = Ano_escolar.query.all()
    return jsonify([{
        'id': Ano_escolar.id,
        'nome': Ano_escolar.nome
    } for Ano_escolar in Ano_escolar])

@app.route("/api/get_turmas", methods=["GET"])
@login_required
def api_get_turmas():
    escola_id = request.args.get("escola_id")
    tipo_ensino_id = request.args.get("tipo_ensino_id")
    ano_escolar_id = request.args.get("ano_escolar_id")
    
    if not all([escola_id, tipo_ensino_id, ano_escolar_id]):
        return jsonify([])
    
    turmas = Turmas.query.filter_by(
        escola_id=escola_id,
        tipo_ensino_id=tipo_ensino_id,
        ano_escolar_id=ano_escolar_id
    ).all()
    
    return jsonify([{
        'id': turma.id,
        'nome': turma.turma
    } for turma in turmas])

@app.route("/api/buscar_alunos", methods=["GET"])
@login_required
def api_buscar_alunos():
    termo = request.args.get("termo", "")
    if not termo:
        return jsonify([])
    
    alunos = Usuarios.query.filter(
        Usuarios.tipo_usuario_id == 4,  # Tipo aluno
        Usuarios.nome.ilike(f"%{termo}%")
    ).limit(10).all()
    
    return jsonify([{
        'id': aluno.id,
        'nome': aluno.nome,
        'email': aluno.email
    } for aluno in alunos])

# Rotas do Portal Administrador
@app.route('/portal_administrador')
@login_required
def portal_administrador():
    # Verifica se o tipo_usuario_id é 1 (Administrador)
    if current_user.tipo_usuario_id != 1:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    return render_template(
        'portal_administrador.html',
        title="Portal do Administrador"
    )

@app.route("/portal_administrador/cadastrar_disciplina", methods=["GET", "POST"])
@login_required
def cadastrar_disciplina():
    if current_user.tipo_usuario_id != 1:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    if request.method == "POST":
        nome = request.form.get("nome")

        if not nome:
            flash("Nome da disciplina é obrigatório.", "danger")
            return redirect(url_for('cadastrar_disciplina'))

        # Verifica se a disciplina já existe
        disciplina_existente = Disciplinas.query.filter_by(nome=nome).first()
        if disciplina_existente:
            flash("Esta disciplina já está cadastrada.", "danger")
            return redirect(url_for('cadastrar_disciplina'))

        # Cria nova disciplina
        nova_disciplina = Disciplinas(nome=nome)
        db.session.add(nova_disciplina)
        
        try:
            db.session.commit()
            flash("Disciplina cadastrada com sucesso!", "success")
            return redirect(url_for('portal_administrador'))
        except Exception as e:
            db.session.rollback()
            flash("Erro ao cadastrar disciplina. Por favor, tente novamente.", "danger")
            return redirect(url_for('cadastrar_disciplina'))

    return render_template('cadastrar_disciplina.html')

@app.route("/portal_administrador/cadastrar_turma", methods=["GET", "POST"])
@login_required
def cadastrar_turma_admin():
    if current_user.tipo_usuario_id != 1:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    if request.method == "POST":
        escola_id = request.form.get("escola_id")
        tipo_ensino_id = request.form.get("tipo_ensino_id")
        ano_escolar_id = request.form.get("ano_escolar_id")
        turma = request.form.get("turma")
        codigo_inep = request.form.get("codigo_inep")

        # Validações básicas
        if not all([escola_id, tipo_ensino_id, ano_escolar_id, turma, codigo_inep]):
            flash("Todos os campos são obrigatórios.", "danger")
            return redirect(url_for('cadastrar_turma'))

        # Verifica se a escola existe
        escola = Escolas.query.get(escola_id)
        if not escola:
            flash("Escola não encontrada.", "danger")
            return redirect(url_for('cadastrar_turma'))

        # Cria nova turma
        nova_turma = Turmas(
            codigo_inep=codigo_inep,
            escola_id=escola_id,
            tipo_ensino_id=tipo_ensino_id,
            ano_escolar_id=ano_escolar_id,
            turma=turma
        )
        db.session.add(nova_turma)
        
        try:
            db.session.commit()
            flash("Turma cadastrada com sucesso!", "success")
            return redirect(url_for('portal_administrador'))

        except Exception as e:
            db.session.rollback()
            flash("Erro ao cadastrar turma. Por favor, tente novamente.", "danger")
            return redirect(url_for('cadastrar_turma'))

    # Busca dados para os selects
    escolas = Escolas.query.all()
    tipos_ensino = TiposEnsino.query.all()
    Ano_escolar = Ano_escolar.query.all()

    return render_template(
        'cadastrar_turma.html',
        escolas=escolas,
        tipos_ensino=tipos_ensino,
        Ano_escolar=Ano_escolar
    )

@app.route("/portal_administrador/cadastrar_escola", methods=["GET", "POST"])
@login_required
def cadastrar_escola_admin():
    if current_user.tipo_usuario_id != 1:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    if request.method == "POST":
        codigo_inep = request.form.get("codigo_inep")
        nome_da_escola = request.form.get("nome_da_escola")
        cep = request.form.get("cep")
        codigo_ibge = request.form.get("codigo_ibge")
        endereco = request.form.get("endereco")
        numero = request.form.get("numero")
        complemento = request.form.get("complemento")
        bairro = request.form.get("bairro")
        ddd = request.form.get("ddd")
        telefone = request.form.get("telefone")
        telefone_2 = request.form.get("telefone_2")
        email = request.form.get("email")
        ensino_fundamental = request.form.get("ensino_fundamental")

        # Validações básicas
        if not all([codigo_inep, nome_da_escola, codigo_ibge]):
            flash("Código INEP, nome da escola e código IBGE são obrigatórios.", "danger")
            return redirect(url_for('cadastrar_escola'))

        # Verifica se a escola já existe
        escola_existente = Escolas.query.filter_by(codigo_inep=codigo_inep).first()
        if escola_existente:
            flash("Esta escola já está cadastrada.", "danger")
            return redirect(url_for('cadastrar_escola'))

        # Cria nova escola
        nova_escola = Escolas(
            codigo_inep=codigo_inep,
            nome_da_escola=nome_da_escola,
            cep=cep,
            codigo_ibge=codigo_ibge,
            endereco=endereco,
            numero=numero,
            complemento=complemento,
            bairro=bairro,
            ddd=ddd,
            telefone=telefone,
            telefone_2=telefone_2,
            email=email,
            ensino_fundamental=ensino_fundamental
        )
        db.session.add(nova_escola)
        
        try:
            db.session.commit()
            flash("Escola cadastrada com sucesso!", "success")
            return redirect(url_for('portal_administrador'))

        except Exception as e:
            db.session.rollback()
            flash("Erro ao cadastrar escola. Por favor, tente novamente.", "danger")
            return redirect(url_for('cadastrar_escola'))

    return render_template('cadastrar_escola.html')

@app.route("/portal_administrador/cadastrar_usuario", methods=["GET", "POST"])
@login_required
def cadastrar_usuario_admin():
    if current_user.tipo_usuario_id != 1:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    if request.method == "POST":
        cpf = request.form.get("cpf")
        email = request.form.get("email")
        senha = request.form.get("senha")
        nome = request.form.get("nome")
        data_nascimento = request.form.get("data_nascimento")
        mae = request.form.get("mae")
        pai = request.form.get("pai")
        sexo = request.form.get("sexo")
        codigo_ibge = request.form.get("codigo_ibge")
        cep = request.form.get("cep")
        escola_id = request.form.get("escola_id")
        tipo_ensino_id = request.form.get("tipo_ensino_id")
        ano_escolar_id = request.form.get("ano_escolar_id")
        turma_id = request.form.get("turma_id")
        tipo_usuario_id = request.form.get("tipo_usuario_id")

        # Validações básicas
        if not all([nome, email, senha, tipo_usuario_id]):
            flash("Nome, email, senha e tipo de usuário são obrigatórios.", "danger")
            return redirect(url_for('cadastrar_usuario'))

        # Verifica se o usuário já existe
        usuario_existente = Usuarios.query.filter(
            (Usuarios.email == email) | (Usuarios.cpf == cpf)
        ).first()
        
        if usuario_existente:
            flash("Este usuário já está cadastrado.", "danger")
            return redirect(url_for('cadastrar_usuario'))

        # Cria novo usuário
        novo_usuario = Usuarios(
            cpf=cpf,
            email=email,
            senha=generate_password_hash(senha),
            nome=nome,
            data_nascimento=data_nascimento,
            mae=mae,
            pai=pai,
            sexo=sexo,
            codigo_ibge=codigo_ibge,
            cep=cep,
            escola_id=escola_id,
            tipo_ensino_id=tipo_ensino_id,
            ano_escolar_id=ano_escolar_id,
            turma_id=turma_id,
            tipo_usuario_id=tipo_usuario_id
        )
        db.session.add(novo_usuario)
        
        try:
            db.session.commit()
            flash("Usuário cadastrado com sucesso!", "success")
            return redirect(url_for('portal_administrador'))

        except Exception as e:
            db.session.rollback()
            flash("Erro ao cadastrar usuário. Por favor, tente novamente.", "danger")
            return redirect(url_for('cadastrar_usuario'))

    # Busca dados para os selects
    escolas = Escolas.query.all()
    tipos_ensino = TiposEnsino.query.all()
    Ano_escolar = Ano_escolar.query.all()
    turmas = Turmas.query.all()
    tipos_usuarios = TiposUsuarios.query.all()

    return render_template(
        'cadastrar_usuario.html',
        escolas=escolas,
        tipos_ensino=tipos_ensino,
        Ano_escolar=Ano_escolar,
        turmas=turmas,
        tipos_usuarios=tipos_usuarios
    )

@app.route("/upload_usuarios_escolas_massa", methods=["GET", "POST"])
@login_required
def upload_usuarios_escolas_massa():
    if current_user.tipo_usuario_id != 1 and current_user.tipo_usuario_id != 5:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    if request.method == "POST":
        if "file" not in request.files:
            flash("Nenhum arquivo enviado", "error")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("Nenhum arquivo selecionado", "error")
            return redirect(request.url)

        if file and file.filename.endswith(('.xlsx', '.xls')):
            try:
                # Ler o arquivo Excel
                df = pd.read_excel(file)
                
                # Converter todas as colunas datetime para string
                for col in df.select_dtypes(include=['datetime64[ns]']).columns:
                    df[col] = df[col].astype(str)
                
                # Extrair escolas únicas
                colunas_obrigatorias_escola = ['codigo_inep_escola', 'nome_da_escola', 'codigo_ibge', 'DEP_ADMINISTRATIVA', 'DC_LOCALIZACAO']
                colunas_opcionais_escola = ['email', 'telefone', 'endereco', 'numero', 'complemento', 'bairro', 'cep_escola']
                
                colunas_faltantes = [col for col in colunas_obrigatorias_escola if col not in df.columns]
                if colunas_faltantes:
                    raise ValueError(f"Colunas obrigatórias faltando: {', '.join(colunas_faltantes)}")
                
                colunas_escola = colunas_obrigatorias_escola + [col for col in colunas_opcionais_escola if col in df.columns]
                escolas_df = df[colunas_escola].drop_duplicates()
                escolas_list = escolas_df.to_dict('records')
                
                # Extrair turmas únicas
                colunas_obrigatorias_turma = ['codigo_inep_escola', 'nome_da_escola', 'ano_escolar_id', 'turma', 'turma_institucional']
                colunas_opcionais_turma = ['turno', 'tipo_ensino_id']
                
                colunas_turma = colunas_obrigatorias_turma + [col for col in colunas_opcionais_turma if col in df.columns]
                turmas_df = df[colunas_turma].drop_duplicates()
                turmas_list = turmas_df.to_dict('records')
                
                # Salvar dados em arquivos temporários
                upload_data = {
                    'escolas': escolas_list,
                    'turmas': turmas_list,
                    'usuarios': df.to_dict('records')
                }
                
                temp_id = save_temp_data(upload_data, 'upload_massa')
                session['upload_massa_temp_id'] = temp_id
                
                return render_template('upload_usuarios_escolas_massa.html',
                                    preview_data={
                                        'escolas': escolas_list[:10],  # Mostrar apenas 10 primeiros
                                        'turmas': turmas_list[:10]
                                    },
                                    session_id=temp_id)
                
            except Exception as e:
                flash(f"Erro ao processar o arquivo: {str(e)}", "error")
                return redirect(request.url)
        else:
            flash("Tipo de arquivo não permitido. Use apenas .xlsx ou .xls", "error")
            return redirect(request.url)

    return render_template("upload_usuarios_escolas_massa.html")

@app.route("/confirmar_cadastro_massa", methods=["POST"])
@login_required
def confirmar_cadastro_massa():
    if current_user.tipo_usuario_id != 1 and current_user.tipo_usuario_id != 5:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    temp_id = session.get('upload_massa_temp_id')
    if not temp_id:
        flash("Nenhum dado para confirmar", "error")
        return redirect(url_for('upload_usuarios_escolas_massa'))

    upload_data = get_temp_data(temp_id, 'upload_massa')
    if not upload_data:
        flash("Dados temporários expirados. Por favor, faça o upload novamente.", "error")
        return redirect(url_for('upload_usuarios_escolas_massa'))

    try:
        from datetime import datetime
        import pandas as pd
        
        session['upload_progress'] = {'status': 'Iniciando processamento...', 'progress': 0}
        
        def print_timestamp(message):
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {message}")
            session['upload_progress'] = {'status': message, 'progress': session['upload_progress']['progress']}
            
        print_timestamp("Iniciando processamento de dados...")
        
        # Processar escolas
        total_escolas = len(upload_data['escolas'])
        print_timestamp(f"Processando {total_escolas} escolas:")
        print("[", end="", flush=True)
        
        # Preparar dados das escolas para bulk insert/update
        escolas_map = {}  # codigo_inep -> id
        escolas_dict = []
        escolas_atualizar = []
        
        # Mapear escolas existentes
        for escola in db.session.query(Escolas).all():
            escolas_map[str(escola.codigo_inep)] = escola.id
            
        def clean_value(value, default=None):
            try:
                if pd.isna(value):
                    return default
                if value is None or value == '':
                    return default
                return str(value)  # Converter para string para evitar problemas com MySQL
            except:
                return default
            
        def clean_numeric(value):
            if value is None or pd.isna(value):
                return None
            try:
                return str(int(float(value)))
            except:
                return str(value)

        def get_endereco_by_cep(cep):
            try:
                # Limpar o CEP, mantendo apenas números
                cep_limpo = ''.join(filter(str.isdigit, str(cep)))
                if len(cep_limpo) != 8:
                    return None
                
                # Fazer requisição ao ViaCEP
                url = f'https://viacep.com.br/ws/{cep_limpo}/json/'
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if 'erro' not in data:
                        return {
                            'logradouro': data.get('logradouro', ''),
                            'bairro': data.get('bairro', ''),
                            'cidade': data.get('localidade', ''),
                            'uf': data.get('uf', ''),
                            'endereco': data.get('logradouro', ''),
                            'numero': '',
                            'complemento': ''
                        }
            except Exception as e:
                print(f"Erro ao consultar CEP: {str(e)}")
            return None

        def map_dep_administrativa(valor):
            # Mapeamento de valores comuns para o padrão
            mapa = {
                'MUNICIPAL': 'Municipal',
                'ESTADUAL': 'Estadual',
                'FEDERAL': 'Federal',
                'PRIVADA': 'Privada',
                'PARTICULAR': 'Privada'
            }
            if not valor:
                return 'Municipal'  # Valor padrão
            valor = str(valor).upper().strip()
            return mapa.get(valor, 'Municipal')

        def map_localizacao(valor):
            # Mapeamento de valores comuns para o padrão
            mapa = {
                'URBANA': 'Urbana',
                'RURAL': 'Rural',
                'CAMPO': 'Rural',
                'CIDADE': 'Urbana'
            }
            if not valor:
                return 'Urbana'  # Valor padrão
            valor = str(valor).upper().strip()
            return mapa.get(valor, 'Urbana')

        def map_turno(valor):
            # Mapeamento de valores comuns para o padrão
            mapa = {
                'MANHA': 'matutino',
                'MANHÃ': 'matutino',
                'MATUTINO': 'matutino',
                'TARDE': 'vespertino',
                'VESPERTINO': 'vespertino',
                'NOITE': 'noturno',
                'NOTURNO': 'noturno',
                'INTEGRAL': 'integral'
            }
            if not valor:
                return 'matutino'  # Valor padrão
            valor = str(valor).upper().strip()
            return mapa.get(valor, 'matutino')

        for i, escola in enumerate(upload_data['escolas'], 1):
            codigo_inep = clean_numeric(escola['codigo_inep_escola'])
            print_timestamp(f"Dados da escola {codigo_inep}:")
            print_timestamp(f"Escola completa: {escola}")
            print_timestamp(f"Tipo do CEP: {type(escola.get('cep_escola'))}")
            print_timestamp(f"CEP da planilha (raw): {escola.get('cep_escola')}")
            

            # Criar dicionário base da escola
            escola_dict = {
                'codigo_inep': codigo_inep,
                'nome_da_escola': escola['nome_da_escola'],
                'codigo_ibge': clean_value(escola.get('codigo_ibge')),
                'DEP_ADMINISTRATIVA': escola.get('DEP_ADMINISTRATIVA', ''),
                'DC_LOCALIZACAO': escola.get('DC_LOCALIZACAO', ''),
                'email': clean_value(escola.get('email')),
                'telefone': clean_value(escola.get('telefone')),
                'cep_escola': clean_value(escola.get('cep_escola')),
                'ensino_fundamental': 1
            }

            # Buscar dados do CEP
            if escola_dict['cep_escola']:
                endereco = get_endereco_by_cep(escola_dict['cep_escola'])
                if endereco:
                    escola_dict.update(endereco)
                    print_timestamp(f"Dados do CEP encontrados: {endereco}")
                else:
                    print_timestamp(f"Não encontrou dados para o CEP: {escola_dict['cep_escola']}")

            print_timestamp(f"CEP final no dicionário: {escola_dict['cep_escola']}")

            # Para buscar no ViaCEP, remove pontos e hífens
            cep_busca = escola_dict['cep_escola'].replace('.', '').replace('-', '') if escola_dict['cep_escola'] else None

            print_timestamp(f"CEP final no dicionário: {escola_dict['cep_escola']}")
            
            if codigo_inep in escolas_map:
                # Atualizar escola existente
                escola_dict['id'] = escolas_map[codigo_inep]
                escolas_atualizar.append(escola_dict)
            else:
                # Nova escola
                escolas_dict.append(escola_dict)
            
            progress = int((i / total_escolas) * 33)  # 33% do progresso total
            session['upload_progress'] = {'status': f"Processando escolas... {i}/{total_escolas}", 'progress': progress}
            
            if i % (total_escolas // 50 or 1) == 0:
                print("=", end="", flush=True)
                
        # Bulk insert/update escolas
        if escolas_dict:
            db.session.bulk_insert_mappings(Escolas, escolas_dict)
        if escolas_atualizar:
            db.session.bulk_update_mappings(Escolas, escolas_atualizar)
        db.session.flush()
        
        # Atualizar o mapeamento de escolas após inserir/atualizar
        escolas_map.clear()  # Limpar o mapeamento antigo
        for escola in db.session.query(Escolas).all():
            escolas_map[str(escola.codigo_inep)] = escola.id
            
        print_timestamp(f"Escolas: {len(escolas_dict)} novas, {len(escolas_atualizar)} atualizadas")
        
        # Processar turmas
        total_turmas = len(upload_data['turmas'])
        print_timestamp(f"Processando {total_turmas} turmas:")
        print("[", end="", flush=True)
        
        # Mapear turmas existentes
        turmas_existentes = {}
        for turma in db.session.query(Turmas).all():
            # Chave composta: codigo_inep_escola + turma + ano_escolar_id
            chave = f"{turma.codigo_inep}_{turma.turma}_{turma.ano_escolar_id}"
            turmas_existentes[chave] = turma.id
            
        turmas_novas = []
        turmas_atualizar = []
        chunk_size = 1000
        
        for i, turma in enumerate(upload_data['turmas'], 1):
            codigo_inep = clean_numeric(turma['codigo_inep_escola'])
            escola_id = escolas_map.get(codigo_inep)
            
            if escola_id is None:
                raise ValueError(f"Escola com código INEP {codigo_inep} não encontrada")
                
            # Processar turno
            turno = turma.get('turno')
            if pd.isna(turno):
                turno = None
            elif isinstance(turno, str):
                turno = turno.strip()
            elif isinstance(turno, (int, float)):
                turno = str(int(turno))

            print_timestamp(f"Processando turma - Dados:")
            print(f"Turno original: '{turma.get('turno')}'")
            print(f"Turno processado: '{turno}'")

            turma_dict = {
                'codigo_inep': clean_numeric(turma['codigo_inep_escola']),
                'escola_id': escola_id,
                'tipo_ensino_id': clean_value(turma.get('tipo_ensino_id'), 1),
                'ano_escolar_id': turma['ano_escolar_id'],
                'turma': clean_value(turma.get('turma')),  # A, B, C...
                'turma_institucional': clean_value(turma.get('turma_institucional')),  # Código da turma
                'turno': turno  # Usando o valor processado
            }

            print(f"Turno no dicionário: {turma_dict['turno']}")
            
            # Chave composta para verificar se turma existe
            chave = f"{codigo_inep}_{turma['turma']}_{turma['ano_escolar_id']}"
            
            if chave in turmas_existentes:
                # Atualizar turma existente
                turma_dict['id'] = turmas_existentes[chave]
                turmas_atualizar.append(turma_dict)
            else:
                # Nova turma
                turmas_novas.append(turma_dict)
            
            progress = 33 + int((i / total_turmas) * 33)  # 33% a 66% do progresso total
            session['upload_progress'] = {'status': f"Processando turmas... {i}/{total_turmas}", 'progress': progress}
            
            # Commit parcial a cada chunk_size registros
            if len(turmas_novas) >= chunk_size:
                if turmas_novas:
                    db.session.bulk_insert_mappings(Turmas, turmas_novas)
                if turmas_atualizar:
                    db.session.bulk_update_mappings(Turmas, turmas_atualizar)
                db.session.flush()
                turmas_novas = []
                turmas_atualizar = []
            
            if i % (total_turmas // 50 or 1) == 0:
                print("=", end="", flush=True)
                
        # Inserir turmas restantes
        if turmas_novas:
            db.session.bulk_insert_mappings(Turmas, turmas_novas)
        if turmas_atualizar:
            db.session.bulk_update_mappings(Turmas, turmas_atualizar)
        db.session.flush()
            
        print_timestamp(f"Turmas: {len(turmas_novas)} novas, {len(turmas_atualizar)} atualizadas")
        
        # Processar usuários
        total_usuarios = len(upload_data['usuarios'])
        print_timestamp(f"Processando {total_usuarios} usuários:")
        print("[", end="", flush=True)
        
        # Mapear usuários existentes
        usuarios_existentes = {}
        total_usuarios_banco = 0
        
        for usuario in db.session.query(Usuarios).all():
            total_usuarios_banco += 1
            
            # Criar múltiplas chaves para o mesmo usuário
            chaves = []
            
            # Chave por CPF se disponível
            if usuario.cpf:
                chaves.append(f"cpf_{usuario.cpf}")
            
            # Chave por matrícula se disponível
            if usuario.matricula_aluno:
                chaves.append(f"matricula_{usuario.matricula_aluno}")
            
            # Chave por código INEP se disponível
            if usuario.codigo_inep_aluno:
                chaves.append(f"inep_{usuario.codigo_inep_aluno}")
            
            # Chave por nome + escola como fallback
            chaves.append(f"nome_{usuario.nome}_{usuario.escola_id}")
            
            # Adicionar todas as chaves ao mapeamento
            for chave in chaves:
                usuarios_existentes[chave] = {
                    'id': usuario.id,
                    'cpf': usuario.cpf,
                    'matricula': usuario.matricula_aluno,
                    'email': usuario.email,
                    'senha': usuario.senha
                }
        
        print_timestamp(f"Total de usuários no banco: {total_usuarios_banco}")
        
        usuarios_novos = []
        usuarios_atualizar = []
        senha_padrao = generate_password_hash('123456')
        
        def map_sexo(sexo):
            if not sexo:
                return None
            sexo = str(sexo).upper()
            return 1 if sexo == 'MASCULINO' else 2 if sexo == 'FEMININO' else None
            
        for i, usuario in enumerate(upload_data['usuarios'], 1):
            codigo_inep = clean_numeric(usuario['codigo_inep_escola'])
            escola_id = escolas_map.get(codigo_inep)
            
            if escola_id is None:
                raise ValueError(f"Escola com código INEP {codigo_inep} não encontrada")
                
            nome = clean_value(usuario.get('nome'), '')
            chave = f"{nome}_{escola_id}"
            
            turma_id = None
            turno = None
            turma_institucional = None

            # Buscar a turma usando o código da turma e ano escolar
            if usuario.get('turma') and usuario.get('ano_escolar_id'):
                turma = db.session.query(Turmas).filter(
                    Turmas.codigo_inep == codigo_inep,
                    Turmas.turma == str(usuario.get('turma')),
                    Turmas.ano_escolar_id == usuario.get('ano_escolar_id')
                ).first()
                
                if turma:
                    turma_id = turma.id
                    turno = turma.turno
                    turma_institucional = turma.turma_institucional
                    print_timestamp(f"Encontrou turma para {nome}: turma_id={turma_id}, turno={turno}, turma_institucional={turma_institucional}")
                else:
                    print_timestamp(f"Não encontrou turma para {nome} com turma={usuario.get('turma')}, ano_escolar={usuario.get('ano_escolar_id')}")
            
            usuario_dict = {
                'nome': nome,
                'email': None,  # Email será adicionado depois pelo usuário
                'senha': senha_padrao,
                'tipo_usuario_id': int(clean_value(usuario.get('tipo_usuario_id'), 4)),
                'escola_id': escola_id,
                'cidade_id': 1,
                'codigo_inep_escola': clean_numeric(usuario.get('codigo_inep_escola')),
                'cpf': ''.join(filter(str.isdigit, str(usuario.get('cpf', '')))),
                'data_nascimento': clean_value(usuario.get('data_nascimento')),
                'mae': clean_value(usuario.get('mae')),  # Mantendo o nome do campo como 'mae'
                'pai': clean_value(usuario.get('nome_pai')),
                'sexo': map_sexo(usuario.get('sexo')),
                'codigo_ibge': clean_value(usuario.get('codigo_ibge')),
                'cep_usuario': clean_value(usuario.get('cep_usuario')),  # Nome atualizado do campo
                'tipo_ensino_id': clean_value(usuario.get('tipo_ensino_id')),
                'ano_escolar_id': clean_value(usuario.get('ano_escolar_id')),
                'turma_institucional': turma_institucional,
                'turma_id': turma_id,
                'matricula_aluno': clean_value(usuario.get('matricula_aluno')),
                'codigo_inep_aluno': clean_numeric(usuario.get('codigo_inep_aluno')),
                'cor': clean_value(usuario.get('cor')),
                'turno': clean_value(usuario.get('turno'))
            }
            
            usuario_existente = usuarios_existentes.get(chave)
            if usuario_existente:
                # Atualizar usuário existente
                usuario_dict['id'] = usuario_existente['id']
                
                # Manter email e senha existentes se não forem nulos
                if usuario_existente['email']:
                    usuario_dict['email'] = usuario_existente['email']
                if usuario_existente['senha']:
                    usuario_dict['senha'] = usuario_existente['senha']
                    
                # Buscar usuário existente para verificar campos vazios
                usuario_atual = db.session.get(Usuarios, usuario_existente['id'])
                if usuario_atual:
                    # Atualizar apenas campos vazios
                    if not usuario_atual.cpf and usuario_dict['cpf']:
                        print_timestamp(f"Atualizando CPF de {nome}: {usuario_dict['cpf']}")
                    if not usuario_atual.data_nascimento and usuario_dict['data_nascimento']:
                        print_timestamp(f"Atualizando data de nascimento de {nome}: {usuario_dict['data_nascimento']}")
                    if not usuario_atual.mae and usuario_dict['mae']:
                        print_timestamp(f"Atualizando nome da mãe de {nome}: {usuario_dict['mae']}")
                    if not usuario_atual.pai and usuario_dict['pai']:
                        print_timestamp(f"Atualizando nome do pai de {nome}: {usuario_dict['pai']}")
                    if not usuario_atual.sexo and usuario_dict['sexo']:
                        print_timestamp(f"Atualizando sexo de {nome}: {usuario_dict['sexo']}")
                    if not usuario_atual.cor and usuario_dict['cor']:
                        print_timestamp(f"Atualizando cor de {nome}: {usuario_dict['cor']}")
                    if not usuario_atual.codigo_inep_aluno and usuario_dict['codigo_inep_aluno']:
                        print_timestamp(f"Atualizando código INEP de {nome}: {usuario_dict['codigo_inep_aluno']}")
                    
                    # Adicionar o ID do usuário para o bulk update
                    usuario_dict['id'] = usuario_atual.id
                    usuarios_atualizar.append(usuario_dict)  # Movido para dentro do if
                    if i % 100 == 0:
                        print_timestamp(f"Atualizando usuário: {nome}")
            else:
                # Novo usuário
                usuarios_novos.append(usuario_dict)
            
            progress = 66 + int((i / total_usuarios) * 33)  # 66% a 99% do progresso total
            session['upload_progress'] = {'status': f"Processando usuários... {i}/{total_usuarios}", 'progress': progress}
            
            # Commit parcial a cada chunk_size registros
            if len(usuarios_novos) >= chunk_size:
                if usuarios_novos:
                    db.session.bulk_insert_mappings(Usuarios, usuarios_novos)
                if usuarios_atualizar:
                    db.session.bulk_update_mappings(Usuarios, usuarios_atualizar)
                db.session.flush()
                usuarios_novos = []
                usuarios_atualizar = []
            
            if i % (total_usuarios // 50 or 1) == 0:
                print("=", end="", flush=True)
                
        # Inserir usuários restantes
        if usuarios_novos:
            db.session.bulk_insert_mappings(Usuarios, usuarios_novos)
        if usuarios_atualizar:
            db.session.bulk_update_mappings(Usuarios, usuarios_atualizar)
        db.session.flush()
            
        print_timestamp(f"Usuários: {len(usuarios_novos)} novos, {len(usuarios_atualizar)} atualizados")
        
        print_timestamp("Finalizando e salvando no banco de dados...")
        db.session.commit()
        session['upload_progress'] = {'status': 'Processamento concluído com sucesso!', 'progress': 100, 'complete': True}
        flash('Dados importados com sucesso!', 'success')
        return redirect(url_for('upload_usuarios_escolas_massa'))

    except Exception as e:
        db.session.rollback()
        session['upload_progress'] = {'error': True, 'message': str(e)}
        flash(f'Erro durante o processamento: {str(e)}', 'error')
        return redirect(url_for('upload_usuarios_escolas_massa'))

@app.route('/progress')
def progress():
    def generate():
        while True:
            progress = session.get('upload_progress', {})
            if progress:
                if 'progress' in progress:
                    progress['percent'] = progress['progress']
                yield f"data: {json.dumps(progress)}\n\n"
                if progress.get('complete') or progress.get('error'):
                    break
            time.sleep(0.5)
    return Response(generate(), mimetype='text/event-stream')

def limpar_nome_para_email(nome):
    # Remove acentos
    nome = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    # Converte para minúsculas
    nome = nome.lower()
    # Remove caracteres especiais
    nome = re.sub(r'[^a-z0-9]', '.', nome)
    # Remove pontos duplicados
    nome = re.sub(r'\.+', '.', nome)
    # Remove pontos no início e fim
    nome = nome.strip('.')
    return nome

def clean_value(value, default=None):
    """Limpa um valor, substituindo nan por None"""
    if pd.isna(value):
        return default
    return value

def clean_numeric(value):
    if value is None or pd.isna(value):
        return None
    try:
        return str(int(float(value)))
    except:
        return str(value)

@app.route('/static/questoes_imagens/<path:filename>')
def serve_image(filename):
    return send_from_directory('static/questoes_imagens', filename)

if __name__ == "__main__":
    app.run(debug=True)

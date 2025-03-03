from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, make_response, send_file
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from urllib.parse import quote_plus
from datetime import datetime
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


# Carrega variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)

# Configurações básicas do Flask
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave-secreta-temporaria')

# Codificando a senha para URL
password = quote_plus('31952814Gg@')
# String de conexão MySQL usando pymysql
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://mila_user:{password}@127.0.0.1/mila_educacional'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'  # pasta onde os PDFs serão temporariamente salvos

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
        self.Ano_escolar_id = user_data.Ano_escolar_id
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

@app.route("/cadastrar_escolas_massa", methods=["GET", "POST"])
@login_required
def cadastrar_escolas_massa():
    if current_user.tipo_usuario_id != 1:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    if request.method == "POST":
        # Verificar se o arquivo foi enviado
        if "file" not in request.files:
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

                # Armazenar os dados na sessão para confirmação
                session['escolas_data'] = df.to_dict('records')
                
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

    if 'escolas_data' not in session:
        flash("Nenhum dado de escola para confirmar", "error")
        return redirect(url_for('cadastrar_escolas_massa'))

    escolas_data = session['escolas_data']

    if request.method == "POST":
        try:
            for escola in escolas_data:
                nova_escola = Escolas(
                    tipo_de_registro='10',
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
            session.pop('escolas_data', None)
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

@app.route("/cadastrar_turmas_massa", methods=["GET", "POST"])
@login_required
def cadastrar_turmas_massa():
    if current_user.tipo_usuario_id != 1:
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

        if file:
            try:
                content = file.read().decode('utf-8')
                df = pd.read_csv(StringIO(content))

                # Validar colunas necessárias
                required_columns = ['escola_id', 'tipo_ensino_id', 'Ano_escolar_id', 'turma']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    flash(f"Faltam as seguintes colunas no arquivo CSV: {', '.join(missing_columns)}", "error")
                    return redirect(request.url)

                # Armazenar os dados na sessão para confirmação
                session['turmas_data'] = df.to_dict('records')
                return redirect(url_for('confirmar_cadastro_turmas'))

            except Exception as e:
                flash(f"Erro ao processar o arquivo: {str(e)}", "error")
                return redirect(request.url)

    escolas = Escolas.query.all()
    tipos_ensino = TiposEnsino.query.all()
    Ano_escolar = Ano_escolar.query.all()

    return render_template(
        "cadastrar_turmas_massa.html",
        escolas=escolas,
        tipos_ensino=tipos_ensino,
        Ano_escolar=Ano_escolar
    )

@app.route("/confirmar_cadastro_turmas", methods=["GET", "POST"])
@login_required
def confirmar_cadastro_turmas():
    if current_user.tipo_usuario_id != 1:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    if 'turmas_data' not in session:
        flash("Nenhum dado de turma para confirmar", "error")
        return redirect(url_for('cadastrar_turmas_massa'))

    turmas_data = session['turmas_data']

    if request.method == "POST":
        try:
            for turma in turmas_data:
                nova_turma = Turmas(
                    tipo_de_registro='20',
                    escola_id=turma['escola_id'],
                    tipo_ensino_id=turma['tipo_ensino_id'],
                    Ano_escolar_id=turma['Ano_escolar_id'],
                    turma=turma['turma']
                )
                db.session.add(nova_turma)

            db.session.commit()
            session.pop('turmas_data', None)
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

@app.route("/cadastrar_usuarios_massa", methods=["GET", "POST"])
@login_required
def cadastrar_usuarios_massa():
    if current_user.tipo_usuario_id != 1:
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

        if file:
            try:
                content = file.read().decode('utf-8')
                df = pd.read_csv(StringIO(content))

                # Validar colunas necessárias
                required_columns = [
                    'nome', 'email', 'cpf', 'tipo_usuario_id', 'escola_id',
                    'tipo_ensino_id', 'Ano_escolar_id', 'turma_id'
                ]
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    flash(f"Faltam as seguintes colunas no arquivo CSV: {', '.join(missing_columns)}", "error")
                    return redirect(request.url)

                # Armazenar os dados na sessão para confirmação
                session['usuarios_data'] = df.to_dict('records')
                return redirect(url_for('confirmar_cadastro_usuarios'))

            except Exception as e:
                flash(f"Erro ao processar o arquivo: {str(e)}", "error")
                return redirect(request.url)

    escolas = Escolas.query.all()
    tipos_ensino = TiposEnsino.query.all()
    Ano_escolar = Ano_escolar.query.all()
    turmas = Turmas.query.all()
    tipos_usuarios = TiposUsuarios.query.all()

    return render_template(
        "cadastrar_usuarios_massa.html",
        escolas=escolas,
        tipos_ensino=tipos_ensino,
        Ano_escolar=Ano_escolar,
        turmas=turmas,
        tipos_usuarios=tipos_usuarios
    )

@app.route("/confirmar_cadastro_usuarios", methods=["GET", "POST"])
@login_required
def confirmar_cadastro_usuarios():
    if current_user.tipo_usuario_id != 1:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    if 'usuarios_data' not in session:
        flash("Nenhum dado de usuário para confirmar", "error")
        return redirect(url_for('cadastrar_usuarios_massa'))

    usuarios_data = session['usuarios_data']

    if request.method == "POST":
        try:
            for usuario in usuarios_data:
                # Gerar senha inicial
                senha_inicial = generate_password_hash('123456')

                novo_usuario = Usuarios(
                    tipo_registro='00',
                    nome=usuario['nome'],
                    email=usuario['email'],
                    senha=senha_inicial,
                    tipo_usuario_id=usuario['tipo_usuario_id'],
                    escola_id=usuario['escola_id'],
                    turma_id=usuario['turma_id'],
                    tipo_ensino_id=usuario['tipo_ensino_id'],
                    Ano_escolar_id=usuario['Ano_escolar_id'],
                    codigo_ibge=usuario['codigo_ibge'],
                    cep=usuario['cep']
                )
                db.session.add(novo_usuario)

            db.session.commit()
            session.pop('usuarios_data', None)
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
                            Ano_escolar_id=row['Ano_escolar_id'],
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
        Ano_escolar_id = request.form.get("Ano_escolar_id", "").strip()
        turma_nome = request.form.get("turma", "").strip()

        # Printar os valores recebidos para depuração
        print(f"escola_id: {escola_id}")
        print(f"tipo_ensino_id: {tipo_ensino_id}")
        print(f"Ano_escolar_id: {Ano_escolar_id}")
        print(f"turma_nome: {turma_nome}")

        # Validar campos obrigatórios
        if not all([escola_id, tipo_ensino_id, Ano_escolar_id, turma_nome]):
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
                Ano_escolar_id=int(Ano_escolar_id),
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
    Ano_escolar_id = request.args.get("Ano_escolar_id")

    app.logger.info(f"Parâmetros recebidos: escola_id={escola_id}, tipo_ensino_id={tipo_ensino_id}, Ano_escolar_id={Ano_escolar_id}")

    if not all([escola_id, tipo_ensino_id, Ano_escolar_id]):
        app.logger.warning("Parâmetros insuficientes fornecidos para /get_turmas.")
        return jsonify([])

    # Buscar turmas com os filtros
    turmas = Turmas.query.join(
        Ano_escolar, Turmas.Ano_escolar_id == Ano_escolar.id
    ).filter(
        Turmas.escola_id == escola_id,
        Turmas.tipo_ensino_id == tipo_ensino_id,
        Turmas.Ano_escolar_id == Ano_escolar_id
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
        Ano_escolar_ids = request.form.getlist("Ano_escolar[]")
        turmas_ids = request.form.getlist("turma_id[]")

        print(f"Recebidos: Nome={nome}, Email={email}, Tipo={tipo_usuario_id}, Turmas={turmas_ids}")

        # Validar campos obrigatórios
        if not all([nome, email, senha, tipo_usuario_id, codigo_ibge, cep]):
            print("Erro: Campos obrigatórios não preenchidos.")
            flash("Todos os campos são obrigatórios!", "error")
            return render_template("cadastrar_usuario.html", escolas=escolas)

        # Validação específica para professores e alunos
        if tipo_usuario_id == "4":  # Aluno
            if not all([escolas_ids[0], turmas_ids[0], tipos_ensino_ids[0], Ano_escolar_ids[0]]):
                flash("Escola, Tipo de Ensino, Ano Escolar e Turma são obrigatórios para Alunos!", "error")
                return render_template("cadastrar_usuario.html", escolas=escolas)

        if tipo_usuario_id == "3":  # Professor
            if not all([escolas_ids, turmas_ids, tipos_ensino_ids, Ano_escolar_ids]):
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
                    Ano_escolar_id=Ano_escolar_ids[0],
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
                for escola_id, tipo_ensino_id, Ano_escolar_id, turma_id in zip(escolas_ids, tipos_ensino_ids, Ano_escolar_ids, turmas_ids):
                    prof_turma = ProfessorTurmaEscola(
                        professor_id=novo_professor.id,
                        escola_id=escola_id,
                        turma_id=turma_id,
                        tipo_ensino_id=tipo_ensino_id,
                        Ano_escolar_id=Ano_escolar_id
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
                            Ano_escolar_id=int(row["Ano_escolar_id"]),
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
                            Ano_escolar_id=int(row["Ano_escolar_id"]) if not pd.isna(row["Ano_escolar_id"]) else None,
                            codigo_ibge=row["codigo_ibge"],
                            cep=row["cep"]
                        )
                        db.session.add(novo_usuario)

                        # Se for professor, adicionar relações com turmas
                        if int(row["tipo_usuario_id"]) == 3:  # Professor
                            turmas = row["turmas_ids"].split("|") if not pd.isna(row["turmas_ids"]) else []
                            escolas = row["escolas_ids"].split("|") if not pd.isna(row["escolas_ids"]) else []
                            tipos_ensino = row["tipos_ensino_ids"].split("|") if not pd.isna(row["tipos_ensino_ids"]) else []
                            Ano_escolar = row["Ano_escolar_ids"].split("|") if not pd.isna(row["Ano_escolar_ids"]) else []

                            for t, e, te, s in zip(turmas, escolas, tipos_ensino, Ano_escolar):
                                prof_turma = ProfessorTurmaEscola(
                                    professor_id=novo_usuario.id,
                                    escola_id=int(e),
                                    turma_id=int(t),
                                    tipo_ensino_id=int(te),
                                    Ano_escolar_id=int(s)
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
        Ano_escolar_id = request.form.get("Ano_escolar_id")

        if not all([disciplina, assunto, Ano_escolar_id]):
            flash("Todos os campos são obrigatórios!", "error")
            return render_template("cadastrar_assunto.html")

        try:
            novo_assunto = Assunto(
                disciplina=disciplina,
                assunto=assunto,
                Ano_escolar_id=Ano_escolar_id
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
    Ano_escolar_id = request.args.get("Ano_escolar_id")
    
    if not all([escola_id, tipo_ensino_id, Ano_escolar_id]):
        return jsonify([])
    
    turmas = Turmas.query.filter_by(
        escola_id=escola_id,
        tipo_ensino_id=tipo_ensino_id,
        Ano_escolar_id=Ano_escolar_id
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
        Ano_escolar_id = request.form.get("Ano_escolar_id")
        turma = request.form.get("turma")
        codigo_inep = request.form.get("codigo_inep")

        # Validações básicas
        if not all([escola_id, tipo_ensino_id, Ano_escolar_id, turma, codigo_inep]):
            flash("Todos os campos são obrigatórios.", "danger")
            return redirect(url_for('cadastrar_turma'))

        # Verifica se a escola existe
        escola = Escolas.query.get(escola_id)
        if not escola:
            flash("Escola não encontrada.", "danger")
            return redirect(url_for('cadastrar_turma'))

        # Cria nova turma
        nova_turma = Turmas(
            tipo_de_registro='20',
            codigo_inep=codigo_inep,
            escola_id=escola_id,
            tipo_ensino_id=tipo_ensino_id,
            Ano_escolar_id=Ano_escolar_id,
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
        tipo_de_registro = request.form.get("tipo_de_registro", "10")
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
            tipo_de_registro=tipo_de_registro,
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
        tipo_registro = request.form.get("tipo_registro", "00")
        codigo_inep_escola = request.form.get("codigo_inep_escola")
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
        Ano_escolar_id = request.form.get("Ano_escolar_id")
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
            tipo_registro=tipo_registro,
            codigo_inep_escola=codigo_inep_escola,
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
            Ano_escolar_id=Ano_escolar_id,
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

if __name__ == "__main__":
    app.run(debug=True)

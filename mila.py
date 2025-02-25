#Sistema_Mila_IA

import json
import io
from flask import Flask, g, render_template, request, redirect, url_for, session
from flask_login import LoginManager, login_required, login_user, logout_user, current_user, UserMixin
import openai
from flask import jsonify
from werkzeug.security import check_password_hash
from werkzeug.security import check_password_hash, generate_password_hash
from flask import make_response
from flask_login import UserMixin
from datetime import datetime
from flask import Flask, render_template, jsonify, flash, redirect, url_for, request
from werkzeug.utils import secure_filename
import os
import json
import PyPDF2  # vamos usar este para extrair texto
import pdfplumber  # se precisar deste para outra funcionalidade
from werkzeug.security import generate_password_hash
from flask import send_file
import tempfile
from routes import conteudo_bp, professores_bp, alunos_bp, simulados_bp, secretaria_educacao_bp


# Configuração básica do app
import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mila_user:31952814Gg@127.0.0.1/mila_educacional'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'  # pasta onde os PDFs serão temporariamente salvos
# Certifique-se que a pasta existe
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
app.secret_key = os.getenv('SECRET_KEY', 'chave-secreta-temporaria')

from models import db

db.init_app(app)

app.register_blueprint(conteudo_bp)
app.register_blueprint(professores_bp)
app.register_blueprint(alunos_bp)
app.register_blueprint(simulados_bp)
app.register_blueprint(secretaria_educacao_bp)

# Adicionando `enumerate` ao contexto Jinja2
@app.context_processor
def utility_processor():
    return dict(enumerate=enumerate)

@app.template_filter('chr')
def jinja_chr(value):
    try:
        return chr(value)
    except Exception:
        return ""


# Configuração do gerenciador de login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Por favor, faça login para acessar esta página."



# Configure a chave de API da OpenAI
openai.api_key="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"

# Modelo de usuário para Flask-Login
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, nome, tipo_usuario_id, escola_id, Ano_escolar_id, turma_id, email, codigo_ibge):
        self.id = id
        self.nome = nome
        self.tipo_usuario_id = tipo_usuario_id
        self.escola_id = escola_id
        self.Ano_escolar_id = Ano_escolar_id
        self.turma_id = turma_id
        self.email = email
        self.codigo_ibge = codigo_ibge

    def get_id(self):
        return str(self.id)



@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, nome, tipo_usuario_id, escola_id, Ano_escolar_id, turma_id, email, codigo_ibge
        FROM usuarios
        WHERE id = ?
    """, (user_id,))
    user_data = cursor.fetchone()

    if user_data:
        app.logger.info(f"Usuário carregado: {user_data}")
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
    app.logger.warning(f"Usuário com ID {user_id} não encontrado.")
    return None







# Função para obter a conexão com o banco de dados
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

# Função para obter a conexão com o banco de dados
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def get_relatorio_rede():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            escolas.nome AS escola,
            COUNT(alunos.id) AS total_alunos,
            AVG(simulados.desempenho) AS media_desempenho
        FROM escolas
        LEFT JOIN alunos ON escolas.id = alunos.escola_id
        LEFT JOIN simulados ON alunos.id = simulados.aluno_id
        GROUP BY escolas.id
    """)
    return cursor.fetchall()


# Função para buscar a escola associada ao usuário
def get_escola_alocada(user_id):
    """
    Busca a escola associada ao usuário logado no banco de dados.
    Retorna um dicionário com as informações da escola.
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT e.id, e.nome_da_escola
        FROM escolas e
        JOIN usuarios u ON u.escola_id = e.id
        WHERE u.id = ?
    """, (user_id,))
    escola = cursor.fetchone()

    if escola:
        return {
            "id": escola[0],
            "nome": escola[1]
        }
    else:
        return None
    
def gerar_parecer_ia(relatorio):
    # Supondo que você tenha uma função `analise_ia` que recebe os dados do relatório
    # e retorna uma análise detalhada e sugestões para melhoria
    parecer = analise_ia(relatorio)
    return parecer


# Função para buscar tipos de ensino de uma escola (para uso interno)
def get_tipos_ensino(escola_id):
    """
    Busca os tipos de ensino associados a uma escola pelo ID.
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT tipo_ensino
        FROM escolas
        WHERE id = ?
    """, (escola_id,))
    result = cursor.fetchone()

    if result and result[0]:
        return result[0].split(", ")
    return []




# Fecha a conexão com o banco de dados ao final de cada requisição
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# Função para gerar perguntas com OpenAI
import openai
import re

import random

def gerar_perguntas(disciplina, assunto, quantidade, nivel, alternativas):
    prompt = f"""
    Crie {quantidade} perguntas de múltipla escolha sobre o assunto "{assunto}" na disciplina "{disciplina}".
    Nível de dificuldade: {nivel}.
    Cada pergunta deve ter {alternativas} alternativas.

    Formato esperado:
    1. Pergunta
    A) Opção 1
    B) Opção 2
    C) Opção 3
    D) Opção 4
    Resposta correta: (A, B, C, ou D)
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um gerador de perguntas de múltipla escolha."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7,
        )

        perguntas_raw = response['choices'][0]['message']['content']
        print(f"Resposta bruta da IA: {perguntas_raw}")

        import re
        perguntas = []
        blocos = perguntas_raw.strip().split("\n\n")

        for bloco in blocos:
            try:
                linhas = bloco.strip().split("\n")
                pergunta_texto = re.search(r"^\d+\.\s*(.+)", linhas[0]).group(1).strip()
                opcoes = [linha[3:].strip() for linha in linhas[1:alternativas + 1]]
                resposta_correta = re.search(r"Resposta correta:\s*\(?([ABCD])\)?", bloco, re.IGNORECASE).group(1).strip()

                perguntas.append({
                    "pergunta": pergunta_texto,
                    "opcoes": opcoes,
                    "resposta_correta": resposta_correta  # Certifique-se de que é apenas 'A', 'B', etc.
                })
            except (IndexError, AttributeError) as e:
                print(f"Erro ao processar bloco: {bloco}\nErro: {e}")
                continue

        if not perguntas:
            raise ValueError("Nenhuma pergunta válida foi encontrada na resposta da IA.")

        print(f"Perguntas processadas: {perguntas}")
        return perguntas

    except openai.error.OpenAIError as api_error:
        print(f"Erro ao acessar a API OpenAI: {api_error}")
        return None
    except Exception as e:
        print(f"Erro inesperado ao gerar perguntas: {e}")
        return None

def enviar_questoes_automaticamente(Ano_escolar_id, codigo_ibge):
    """
    Envia automaticamente as questões do banco_questoes para alunos da série especificada
    em escolas vinculadas ao código IBGE (codigo_ibge).
    """
    db = get_db()
    cursor = db.cursor()

    # Buscar as questões do banco para a série especificada
    cursor.execute(
        """
        SELECT id, questao, alternativa_a, alternativa_b, alternativa_c, alternativa_d, alternativa_e, questao_correta
        FROM banco_questoes
        WHERE Ano_escolar_id = ?
        """,
        (Ano_escolar_id,),
    )
    questoes = cursor.fetchall()

    if not questoes:
        print(f"Nenhuma questão encontrada para a série ID {Ano_escolar_id}.")
        return

    # Buscar alunos (tipo_usuario_id = 4) da série nas escolas vinculadas ao código IBGE
    cursor.execute(
        """
        SELECT usuarios.id, usuarios.nome, usuarios.email
        FROM usuarios
        JOIN escolas ON usuarios.escola_id = escolas.id
        WHERE usuarios.Ano_escolar_id = ? AND usuarios.tipo_usuario_id = 4 AND escolas.codigo_ibge = ?
        """,
        (Ano_escolar_id, codigo_ibge),
    )
    alunos = cursor.fetchall()

    if not alunos:
        print(f"Nenhum aluno encontrado para a série ID {Ano_escolar_id} e cidade ID {codigo_ibge}.")
        return

    # Criar o simulado no banco
    cursor.execute(
        """
        INSERT INTO simulados (titulo, Ano_escolar_id)
        VALUES (?, ?)
        """,
        (f"Simulado Automático Ano Escolar {Ano_escolar_id}", Ano_escolar_id),
    )
    simulado_id = cursor.lastrowid

    # Associar as questões ao simulado
    for questao in questoes:
        cursor.execute(
            """
            INSERT INTO simulado_questoes (simulado_id, questao_id)
            VALUES (?, ?)
            """,
            (simulado_id, questao[0]),
        )

    # Associar o simulado aos alunos
    for aluno in alunos:
        cursor.execute(
            """
            INSERT INTO aluno_simulado (aluno_id, simulado_id)
            VALUES (?, ?)
            """,
            (aluno[0], simulado_id),
        )

    # Finalizar a operação
    db.commit()
    print(f"Simulado ID {simulado_id} enviado para {len(alunos)} alunos da série ID {Ano_escolar_id}.")


# Inicializa o banco de dados
def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        # Demais inicializações...

        # Tabela de disciplinas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS disciplinas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE
            )
        """)

        # Outras tabelas existentes no sistema...
        # Tabela de assuntos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assunto (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                disciplina TEXT NOT NULL,
                assunto TEXT NOT NULL,
                professor_id INTEGER,
                FOREIGN KEY (professor_id) REFERENCES usuarios (id)
            )
        """)
        # Insere disciplinas básicas (caso não existam)
        disciplinas_iniciais = [
            "Português", "Matemática", "Ciências", "História", "Geografia"
        ]
        for disciplina in disciplinas_iniciais:
            cursor.execute("""
                INSERT OR IGNORE INTO disciplinas (nome) VALUES (?)
            """, (disciplina,))

        db.commit()
        print("Banco de dados inicializado!")

        # Criação da tabela `pontuacoes`
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pontuacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aluno_id INTEGER NOT NULL,
                pontos INTEGER DEFAULT 0,
                FOREIGN KEY (aluno_id) REFERENCES alunos(id)
            )
        """)

        # Tabelas básicas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                tipo_usuario_id TEXT NOT NULL,
                escola_id INTEGER,
                FOREIGN KEY (escola_id) REFERENCES escolas(id)
            )
        """)
        # Demais tabelas (escolas, alunos, professores, etc.) conforme seu código original
        db.commit()
        print("Tabelas criadas/verificadas com sucesso!")

import re

# Função de validação de respostas
# Função de validação de respostas
def validar_resposta(pergunta, resposta_ia, assunto):
    import re
    numeros = re.findall(r"([\d]+(?:\.\d+)?)", pergunta)
    if numeros:
        try:
            numeros = [float(n) for n in numeros]
            if "adição" in assunto.lower():
                resultado_correto = sum(numeros)
            elif "subtração" in assunto.lower():
                resultado_correto = numeros[0] - sum(numeros[1:])
            elif "multiplicação" in assunto.lower():
                resultado_correto = 1
                for n in numeros:
                    resultado_correto *= n
            elif "divisão" in assunto.lower():
                resultado_correto = numeros[0]
                for n in numeros[1:]:
                    resultado_correto /= n
            else:
                # Para assuntos sem validação específica
                return True

            # Comparar com a resposta fornecida pela IA
            return abs(resultado_correto - float(resposta_ia)) < 0.01
        except Exception as e:
            print(f"[DEBUG] Erro ao validar resposta: {e}")
            return False
    return True


from datetime import datetime
import json
import openai
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

def gerar_perguntas_conhecimentos_gerais(quantidade=10, nivel="Médio"):
    prompt = f"""
    Gere {quantidade} perguntas de conhecimentos gerais no nível {nivel}.
    Cada pergunta deve incluir 4 alternativas (A, B, C, D) e uma resposta correta.
    Formato de exemplo:
    1. Qual é a capital da França?
    A) Paris
    B) Londres
    C) Roma
    D) Berlim
    Resposta correta: A
    """
    try:
        resposta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um gerador de simulados."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        perguntas_texto = resposta['choices'][0]['message']['content']

        perguntas = []
        for pergunta in perguntas_texto.split("\n\n"):
            linhas = pergunta.strip().split("\n")
            if len(linhas) < 6:  # Ignorar perguntas incompletas
                continue
            pergunta_texto = linhas[0]
            alternativas = [linha[3:] for linha in linhas[1:5]]
            resposta_correta = linhas[5].split(":")[-1].strip()
            perguntas.append({
                "pergunta": pergunta_texto,
                "opcoes": alternativas,
                "correta": resposta_correta
            })
        return perguntas
    except Exception as e:
        print(f"Erro ao gerar perguntas: {e}")
        return []


def criar_simulado_diario():
    db = get_db()
    cursor = db.cursor()

    # Verificar se já existe um simulado diário para hoje
    cursor.execute("SELECT id FROM simulado_diario WHERE data = date('now')")
    simulado_existente = cursor.fetchone()

    if simulado_existente:
        print("Simulado diário já existe para hoje.")
        return  # Não criar novamente

    # Criar o novo simulado diário
    cursor.execute("""
        INSERT INTO simulado_diario (data, perguntas)
        VALUES (date('now'), NULL)
    """)
    simulado_id = cursor.lastrowid

    # Selecionar 10 perguntas aleatórias para o novo simulado
    cursor.execute("""
        SELECT id, texto_pergunta, alternativa_a, alternativa_b, alternativa_c, alternativa_d, correta
        FROM perguntas_simulado
        ORDER BY RANDOM()
        LIMIT 10
    """)
    perguntas = cursor.fetchall()

    # Inserir perguntas associadas ao simulado
    for pergunta in perguntas:
        cursor.execute("""
            INSERT INTO perguntas_simulado (simulado_id, texto_pergunta, alternativa_a, alternativa_b, alternativa_c, alternativa_d, correta)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (simulado_id, pergunta[1], pergunta[2], pergunta[3], pergunta[4], pergunta[5], pergunta[6]))

    db.commit()
    print("Novo simulado diário criado com sucesso.")


# Rota protegida: home

@app.route("/")
def index():
    print("Função 'index' chamada!")
    return redirect(url_for("login"))

@app.route("/home")
@login_required
def home():
    # Verificar o tipo de usuário
    tipo_usuario_id = current_user.tipo_usuario_id

    # Redirecionar com base no tipo de usuário
    if tipo_usuario_id == "Professor":
        return redirect(url_for("portal_professores"))
    elif tipo_usuario_id == "Aluno":
        return redirect(url_for("alunos_bp.portal_alunos"))
    elif tipo_usuario_id == "Administrador":
        return redirect(url_for("portal_administrador"))
    elif tipo_usuario_id == "Administração da Escola":
        return redirect(url_for("portal_administracao"))
    elif tipo_usuario_id == "Secretaria de Educação":
        return redirect(url_for("secretaria_educacao.portal_secretaria_educacao"))
    else:
        return redirect(url_for("login"))



from flask_login import login_user, current_user
from flask import flash, session

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        login_identifier = request.form['email']  # Pode ser email ou CPF
        senha = request.form['senha']

        db = get_db()
        cursor = db.cursor()
        # Modifica a consulta para buscar por email OU CPF
        cursor.execute("""
            SELECT id, nome, tipo_usuario_id, escola_id, Ano_escolar_id, turma_id, email, senha, codigo_ibge
            FROM usuarios
            WHERE email = ? OR cpf = ?
        """, (login_identifier, login_identifier))
        user_data = cursor.fetchone()

        if user_data:
            user_id, nome, tipo_usuario_id, escola_id, Ano_escolar_id, turma_id, email_db, senha_hash, codigo_ibge = user_data

            if check_password_hash(senha_hash, senha):
                user = User(
                    id=user_id,
                    nome=nome,
                    tipo_usuario_id=tipo_usuario_id,
                    escola_id=escola_id,
                    Ano_escolar_id=Ano_escolar_id,
                    turma_id=turma_id,
                    email=email_db,
                    codigo_ibge=codigo_ibge
                )
                login_user(user)

                next_page = request.args.get('next') or {
                    1: 'portal_administrador',
                    2: 'portal_administracao',
                    3: 'portal_professores',
                    4: 'alunos_bp.portal_alunos',  # Alterado para usar o endpoint do blueprint
                    5: 'secretaria_educacao.portal_secretaria_educacao'
                }.get(tipo_usuario_id, 'login')

                return redirect(url_for(next_page))
            else:
                error = "Senha incorreta. Por favor, tente novamente."
        else:
            error = "Usuário não encontrado. Por favor, verifique seu email ou CPF."

    return render_template('login.html', error=error)

# Rota de logout

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

import base64

@app.route('/redefinir-senha', defaults={'token': None}, methods=['GET', 'POST'])
@app.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    if not token:
        flash("Token inválido ou ausente.", "danger")
        return redirect(url_for('recuperar_senha'))

    try:
        # Decodificar o token
        token_data = base64.urlsafe_b64decode(token.encode()).decode()
        user_id, email = token_data.split(":")
        user_id = int(user_id)

        if request.method == 'POST':
            nova_senha = request.form.get('nova_senha')
            confirmar_senha = request.form.get('confirmar_senha')

            if nova_senha != confirmar_senha:
                flash("As senhas não coincidem.", "danger")
                return redirect(url_for('redefinir_senha', token=token))

            db = get_db()
            cursor = db.cursor()

            # Verificar se a nova senha é igual à atual
            cursor.execute("SELECT senha FROM usuarios WHERE id = ?", (user_id,))
            current_password_hash = cursor.fetchone()

            if not current_password_hash:
                flash("Usuário não encontrado ou token inválido.", "danger")
                return redirect(url_for('recuperar_senha'))

            current_password_hash = current_password_hash[0]

            if check_password_hash(current_password_hash, nova_senha):
                flash("Essa já é a sua senha.", "warning")
                return redirect(url_for('redefinir_senha', token=token))

            # Atualizar a senha no banco
            nova_senha_hash = generate_password_hash(nova_senha)
            cursor.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (nova_senha_hash, user_id))
            db.commit()

            # Mensagem de sucesso
            flash("Senha redefinida com sucesso!", "success")
            return redirect(url_for('redefinir_senha', token=token))

    except Exception as e:
        flash(f"Erro ao processar o token: {e}", "danger")
        return redirect(url_for('recuperar_senha'))

    return render_template('redefinir_senha.html', token=token)


import base64
import json

@app.route('/recuperar-senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form['email']
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, nome FROM usuarios WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            user_id, nome = user

            # Gerar um token simples baseado no ID e email
            token_data = f"{user_id}:{email}"
            token = base64.urlsafe_b64encode(token_data.encode()).decode()

            reset_link = url_for('redefinir_senha', token=token, _external=True)
            print(f"Link de redefinição de senha para {email}: {reset_link}")

            flash("Link de redefinição de senha gerado e visível no console.", "success")
        else:
            flash("Email não encontrado.", "danger")

    return render_template('recuperar_senha.html')



# Portais (rotas protegidas)
@app.route('/portal_administrador')
@login_required
def portal_administrador():
    # Verifica se o tipo_usuario_id é 1 (Administrador)
    if current_user.tipo_usuario_id != 1:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()

    # Buscar informações gerais, caso necessário
    # Exemplo de lógica para futuras implementações
    # cursor.execute("SELECT COUNT(*) FROM escolas")
    # total_escolas = cursor.fetchone()[0]


    return render_template(
        'portal_administrador.html',
        title="Portal do Administrador"
    )

def extrair_texto_pdf(pdf_path):
    """
    Extrai texto de um arquivo PDF
    """
    import PyPDF2
    texto = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                texto += page.extract_text() + "\n"
        return texto
    except Exception as e:
        print(f"Erro ao extrair texto do PDF: {str(e)}")
        return None

@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            return jsonify({"error": "Nenhum arquivo enviado"}), 400

        file = request.files["file"]
        usar_ia = request.form.get("usar_ia") == "true"

        if file.filename == "":
            return jsonify({"error": "Nenhum arquivo selecionado"}), 400

        if not file.filename.endswith(".pdf"):
            return jsonify({"error": "Apenas arquivos PDF são permitidos"}), 400

        # Criar pasta temporária se não existir
        if not os.path.exists(app.config["UPLOAD_FOLDER"]):
            os.makedirs(app.config["UPLOAD_FOLDER"])

        # Salvar arquivo temporariamente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(temp_path)

        # Extrair texto do PDF
        text = extrair_texto_pdf(temp_path)
        
        # Remover arquivo temporário
        os.remove(temp_path)

        if not text:
            return jsonify({"error": "Não foi possível extrair texto do PDF"}), 400

        # Processar o texto para extrair questões
        if usar_ia:
            questoes = processar_com_ia(text)
        else:
            questoes = processar_sem_ia(text)

        if not questoes:
            return jsonify({"error": "Nenhuma questão encontrada no arquivo"}), 400

        # Verificar se todas as questões têm disciplina_id
        for questao in questoes:
            if not questao.get("disciplina_id"):
                return jsonify({"error": "ID da disciplina não encontrado em uma ou mais questões"}), 400

        # Salvar questões no banco
        salvar_questoes_no_banco(questoes)

        return jsonify({"message": "Arquivo processado com sucesso", "questoes": len(questoes)}), 200

    except Exception as e:
        print(f"Erro ao processar arquivo: {str(e)}")
        return jsonify({"error": str(e)}), 500
        


@app.route("/debug_usuarios")
def debug_usuarios():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, nome, email, senha, tipo_usuario_id FROM usuarios;")
    usuarios = cursor.fetchall()
    return jsonify(usuarios)

@app.route("/atualizar_senhas", methods=["GET"])
def atualizar_senhas():
    db = get_db()
    cursor = db.cursor()

    # Selecionar todas as senhas em texto simples
    cursor.execute("SELECT id, senha FROM usuarios;")
    usuarios = cursor.fetchall()

    for usuario in usuarios:
        usuario_id, senha = usuario

        # Verificar se a senha já está em hash (hashes começam com 'pbkdf2:')
        if not senha.startswith("pbkdf2:sha256:"):
            senha_hash = generate_password_hash(senha, method="pbkdf2:sha256", salt_length=8)

            # Atualizar a senha no banco
            cursor.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (senha_hash, usuario_id))
            db.commit()

    return "Todas as senhas foram convertidas para hash com sucesso!"



@app.route('/importar_assuntos', methods=['GET', 'POST'])
@login_required
def importar_assuntos():
    if current_user.tipo_usuario_id != 1:
        flash("Acesso negado!", "danger")
        return redirect(url_for('portal_administrador'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash("Nenhum arquivo foi enviado.", "danger")
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash("Nenhum arquivo selecionado.", "danger")
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])
                
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                # Processar o CSV
                with open(filepath, newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    db = get_db()
                    cursor = db.cursor()
                    registros_importados = 0

                    for row in reader:
                        print(f"Processando linha: {row}")  # Debug
                        try:
                            cursor.execute("""
                                INSERT INTO assunto (disciplina, assunto, Ano_escolar_id, turma_id, escola_id, professor_id)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (row['disciplina'], row['assunto'], row['Ano_escolar_id'], None, None, None))
                            registros_importados += 1
                        except Exception as e:
                            print(f"Erro ao inserir linha: {e}")
                            db.rollback()
                            raise

                    db.commit()
                    flash(f"Importação concluída com sucesso! {registros_importados} registros adicionados.", "success")
                    return redirect(url_for('portal_administrador'))

            except Exception as e:
                print(f"Erro ao processar o arquivo: {e}")
                flash(f"Erro ao processar o arquivo: {e}", "danger")
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
        else:
            flash("Formato de arquivo inválido. Envie um arquivo CSV.", "danger")

    return render_template('importar_assuntos.html')




@app.route("/cadastrar_disciplina", methods=["GET", "POST"])
@login_required
def cadastrar_disciplina():
    # Verifica se o usuário é Administrador
    if current_user.tipo_usuario_id != 1:
        return redirect(url_for("home"))

    db = get_db()
    cursor = db.cursor()

    # Lógica para POST
    if request.method == "POST":
        nome = request.form.get("nome")

        # Validação do campo "nome"
        if not nome.strip():
            return render_template(
                "cadastrar_disciplina.html",
                error="O nome da disciplina é obrigatório!"
            )

        try:
            # Inserir no banco de dados
            cursor.execute("""
                INSERT INTO disciplinas (nome)
                VALUES (?)
            """, (nome.strip(),))
            db.commit()
            return render_template(
                "cadastrar_disciplina.html",
                success="Disciplina cadastrada com sucesso!"
            )
        except sqlite3.IntegrityError:
            # Trata duplicidade no banco
            return render_template(
                "cadastrar_disciplina.html",
                error="Essa disciplina já está cadastrada!"
            )

    # Renderiza o template para método GET
    return render_template("cadastrar_disciplina.html")


@app.route("/portal_administrador/cadastrar_turma", methods=["GET", "POST"])
@login_required
def cadastrar_turma():
    if current_user.tipo_usuario_id != 1:  # Apenas administradores podem cadastrar
        return redirect(url_for("home"))

    db = get_db()
    cursor = db.cursor()

    # Buscar escolas cadastradas para o menu suspenso
    cursor.execute("SELECT id, nome FROM escolas")
    escolas = cursor.fetchall()

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
            # Inserir a turma no banco de dados
            cursor.execute(
                """
                INSERT INTO turmas (escola_id, tipo_ensino_id, Ano_escolar_id, turma)
                VALUES (?, ?, ?, ?)
                """,
                (int(escola_id), int(tipo_ensino_id), int(Ano_escolar_id), turma_nome)
            )
            db.commit()
            print("Turma cadastrada com sucesso!")
            return render_template(
                "cadastrar_turma.html",
                escolas=escolas,
                success="Turma cadastrada com sucesso!"
            )
        except sqlite3.IntegrityError:
            print("Erro: Turma já cadastrada!")
            return render_template(
                "cadastrar_turma.html",
                escolas=escolas,
                error="Essa turma já está cadastrada!"
            )
        except Exception as e:
            print(f"Erro ao cadastrar turma: {e}")
            return render_template(
                "cadastrar_turma.html",
                escolas=escolas,
                error="Erro ao cadastrar turma. Por favor, tente novamente!"
            )

    return render_template("cadastrar_turma.html", escolas=escolas)




@app.route("/cadastrar_escola", methods=["GET", "POST"])
@login_required
def cadastrar_escola():
    if current_user.tipo_usuario_id != 1:  # Apenas administradores podem acessar
        return redirect(url_for("home"))

    db = get_db()
    cursor = db.cursor()

    # Buscar tipos de ensino do banco de dados
    cursor.execute("SELECT id, nome FROM tipos_ensino")
    tipos_ensino = cursor.fetchall()  # Retorna uma lista de tuplas [(1, "Ensino Infantil"), ...]

    if request.method == "POST":
        nome = request.form.get("nome")
        cep = request.form.get("cep")
        estado = request.form.get("estado")
        cidade = request.form.get("cidade")
        bairro = request.form.get("bairro")
        endereco = request.form.get("endereco")
        numero = request.form.get("numero")
        telefone = request.form.get("telefone")
        cnpj = request.form.get("cnpj")
        diretor = request.form.get("diretor")
        codigo_ibge = request.form.get("codigo_ibge")
        tipos_ensino_selecionados = request.form.getlist("tipos_ensino[]")  # Lista dos IDs dos tipos de ensino selecionados

        # Validar campos obrigatórios
        if not all([nome, cep, estado, cidade, bairro, endereco, numero, telefone, cnpj, diretor, codigo_ibge]):
            flash("Todos os campos são obrigatórios!", "danger")
            return render_template(
                "cadastrar_escola.html",
                tipos_ensino=tipos_ensino
            )

        try:
            # Inserir escola no banco de dados
            cursor.execute("""
                INSERT INTO escolas (
                    nome, cep, estado, cidade, bairro, endereco, numero, telefone, cnpj, diretor, codigo_ibge
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nome, cep, estado, cidade, bairro, endereco, numero, telefone, cnpj, diretor, codigo_ibge))
            escola_id = cursor.lastrowid  # Pega o ID da escola recém-criada

            # Associar tipos de ensino à escola
            for tipo_id in tipos_ensino_selecionados:
                cursor.execute("""
                    INSERT INTO escola_tipos_ensino (escola_id, tipo_ensino_id)
                    VALUES (?, ?)
                """, (escola_id, tipo_id))

            db.commit()
            flash("Escola cadastrada com sucesso!", "success")
            return redirect(url_for("portal_administrador"))

        except Exception as e:
            db.rollback()
            flash(f"Erro ao cadastrar escola: {e}", "danger")
            return render_template(
                "cadastrar_escola.html",
                tipos_ensino=tipos_ensino
            )

    return render_template("cadastrar_escola.html", tipos_ensino=tipos_ensino)


@app.route("/get_tipo_ensino", methods=["GET"])
@login_required
def get_tipo_ensino():
    escola_id = request.args.get("escola_id")
    if not escola_id:
        return jsonify([])

    db = get_db()
    cursor = db.cursor()

    # Buscar os tipos de ensino associados à escola
    cursor.execute(
        """
        SELECT te.id, te.nome
        FROM escola_tipos_ensino ete
        JOIN tipos_ensino te ON ete.tipo_ensino_id = te.id
        WHERE ete.escola_id = ?
        """,
        (escola_id,)
    )
    tipos_ensino = cursor.fetchall()

    if not tipos_ensino:
        app.logger.info(f"Nenhum tipo de ensino encontrado para a escola {escola_id}.")
        return jsonify([])

    app.logger.info(f"Tipos de ensino encontrados: {get_tipos_ensino}")
    return jsonify([{"id": tipo[0], "nome": tipo[1]} for tipo in tipos_ensino])


@app.route("/get_Ano_escolar", methods=["GET"])
@login_required
def get_Ano_escolar():
    tipo_ensino_id = request.args.get("tipo_ensino_id")
    codigo_ibge = current_user.codigo_ibge

    if not tipo_ensino_id:
        return jsonify([])

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT DISTINCT Ano_escolar.id, Ano_escolar.nome
        FROM Ano_escolar
        JOIN escolas ON Ano_escolar.tipo_ensino_id = escolas.tipo_ensino_id
        WHERE escolas.codigo_ibge = ?
        """,
        (codigo_ibge,),
    )
    Ano_escolar = cursor.fetchall()

    return jsonify([{"id": s[0], "nome": s[1]} for s in Ano_escolar])

import logging

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

    db = get_db()
    cursor = db.cursor()

    try:
        # Consulta para buscar turmas e nomes de série
        cursor.execute(
            """
            SELECT turmas.id, Ano_escolar.nome Ano_escolar, turmas.turma
            FROM turmas
            JOIN Ano_escolar ON turmas.Ano_escolar_id = Ano_escolar.id
            WHERE turmas.escola_id = ? AND turmas.tipo_ensino_id = ? AND turmas.Ano_escolar_id = ?
            """,
            (escola_id, tipo_ensino_id, Ano_escolar_id),
        )
        turmas = cursor.fetchall()

        app.logger.info(f"Turmas encontradas: {turmas}")

        # Retorna série e turma separadas
        return jsonify([{"id": turma[0], "Ano_escolar": turma[1], "turma": turma[2]} for turma in turmas])
    except Exception as e:
        app.logger.error(f"Erro ao buscar turmas: {e}")
        return jsonify([])



@app.route('/buscar_alunos', methods=['GET'])
@login_required
def buscar_alunos():
    turma_id = request.args.get("turma_id")
    
    if not turma_id:
        return jsonify([])  # Caso não exista turma_id, retorna vazio

    db = get_db()
    cursor = db.cursor()

    # Buscar os alunos vinculados à turma
    cursor.execute("""
        SELECT id, nome 
        FROM usuarios
        WHERE turma_id = ? AND tipo_usuario_id = 4
    """, (turma_id,))
    alunos = cursor.fetchall()

    # Formatar resposta JSON
    return jsonify([{"id": aluno[0], "nome": aluno[1]} for aluno in alunos])

@app.route("/autocomplete_alunos", methods=["GET"])
@login_required
def autocomplete_alunos():
    # Verifica se o usuário tem permissão
    if current_user.tipo_usuario_id not in ["Secretaria Acadêmica"]:
        return jsonify([])

    query = request.args.get("query", "").strip()
    if len(query) < 2:
        return jsonify([])

    db = get_db()
    cursor = db.cursor()

    # Buscar nomes de alunos que correspondem à query
    cursor.execute("""
        SELECT nome 
        FROM usuarios 
        WHERE tipo_usuario_id = 4 AND nome LIKE ?
    """, (f"%{query}%",))
    alunos = [row[0] for row in cursor.fetchall()]

    return jsonify(alunos)





@app.route("/criar_administrador", methods=["GET", "POST"])
def criar_administrador():
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")

        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO usuarios (nome, email, senha, tipo_usuario_id, escola_id)
            VALUES (?, ?, ?, ?, NULL)
        """, (nome, email, senha, "Administrador"))
        db.commit()

        return "Administrador criado com sucesso!"

    return render_template("criar_administrador.html")



@app.route('/buscar_tipo_ensino', methods=["GET"])
@login_required
def buscar_tipo_ensino():
    escola_id = request.args.get('escola_id')
    db = get_db()
    cursor = db.cursor()

    # Busca os tipos de ensino da escola pelo ID
    cursor.execute("SELECT tipo_ensino FROM escolas WHERE id = ?", (escola_id,))
    result = cursor.fetchone()
    
    if result:
        tipo_ensino = result[0].split(",")  # Divide os tipos de ensino separados por vírgula
        return jsonify([tipo.strip() for tipo in tipo_ensino])  # Remove espaços extras
    return jsonify([])


@app.route("/cadastrar_usuario", methods=["GET", "POST"])
@login_required
def cadastrar_usuario():
    print("Entrou na rota de cadastro de usuário!")  # Log para depuração
    
    if current_user.tipo_usuario_id != 1:  # Apenas administradores podem cadastrar
        print("Usuário não é administrador, redirecionando...")
        return redirect(url_for("home"))

    db = get_db()
    cursor = db.cursor()

    # Buscar escolas disponíveis para exibir no formulário
    cursor.execute("SELECT id, nome FROM escolas")
    escolas = cursor.fetchall()

    if request.method == "POST":
        print("Formulário de cadastro recebido!")

        # Capturando os dados do formulário
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")
        tipo_usuario_id = request.form.get("tipo_usuario_id")
        codigo_ibge = request.form.get("codigo_ibge")  # Código IBGE da cidade
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
            # Inserindo o usuário na tabela `usuarios` apenas se não for professor
            senha_hash = generate_password_hash(senha)

            if tipo_usuario_id != "3":  # Não é professor
                cursor.execute(
                    """
                    INSERT INTO usuarios (nome, email, senha, tipo_usuario_id, escola_id, turma_id, tipo_ensino_id, Ano_escolar_id, codigo_ibge, cep)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        nome,
                        email,
                        senha_hash,
                        tipo_usuario_id,
                        escolas_ids[0],
                        turmas_ids[0],
                        tipos_ensino_ids[0],
                        Ano_escolar_ids[0],
                        codigo_ibge,
                        cep,
                    ),
                )
                db.commit()
                print(f"Usuário {nome} cadastrado na tabela `usuarios` com sucesso!")
                flash("Usuário cadastrado com sucesso!", "success")
            else:  # Professor
                # Insere o professor na tabela `usuarios` com dados básicos
                cursor.execute(
                    """
                    INSERT INTO usuarios (nome, email, senha, tipo_usuario_id, codigo_ibge, cep)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        nome,
                        email,
                        senha_hash,
                        tipo_usuario_id,
                        codigo_ibge,
                        cep,
                    ),
                )
                usuario_id = cursor.lastrowid
                print(f"Professor {nome} cadastrado na tabela `usuarios` com ID {usuario_id}")

                # Insere as turmas do professor na tabela `professor_turma_escola`
                for escola_id, tipo_ensino_id, Ano_escolar_id, turma_id in zip(escolas_ids, tipos_ensino_ids, Ano_escolar_ids, turmas_ids):
                    cursor.execute(
                        """
                        INSERT INTO professor_turma_escola (professor_id, escola_id, turma_id, tipo_ensino_id, Ano_escolar_id)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            usuario_id,
                            escola_id,
                            turma_id,
                            tipo_ensino_id,
                            Ano_escolar_id,
                        ),
                    )
                db.commit()
                print(f"Turmas do professor {nome} cadastradas com sucesso!")
                flash("Professor cadastrado com sucesso com todas as turmas!", "success")

            return redirect(url_for("portal_administrador"))

        except Exception as e:
            db.rollback()
            print(f"Erro ao cadastrar usuário: {e}")
            flash(f"Erro ao cadastrar usuário: {e}", "error")

    return render_template("cadastrar_usuario.html", escolas=escolas)

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
            db = get_db()
            cursor = db.cursor()

            # Obter a senha atual do banco de dados
            cursor.execute("SELECT senha FROM usuarios WHERE id = ?", (current_user.id,))
            senha_atual_hash = cursor.fetchone()[0]

            # Validar a senha atual
            if not check_password_hash(senha_atual_hash, senha_atual):
                error = "A senha atual está incorreta. Por favor, tente novamente."
            else:
                # Gerar hash da nova senha
                nova_senha_hash = generate_password_hash(nova_senha)

                # Atualizar a senha no banco de dados
                cursor.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (nova_senha_hash, current_user.id))
                db.commit()
                success = "Senha alterada com sucesso!"

    return render_template('alterar_senha.html', error=error, success=success)


@app.route('/get_tipos_usuarios')
def get_tipos_usuarios():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, descricao FROM tipos_usuarios")
    tipos = cursor.fetchall()
    return jsonify(tipos)

import csv
import pandas as pd
from flask import request, render_template, flash, redirect, url_for
from werkzeug.utils import secure_filename
from io import StringIO

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


import pandas as pd
import sys  # Aqui está a importação do módulo sys para forçar os prints


@app.route("/cadastrar_escolas_massa", methods=["GET", "POST"])
@login_required
def cadastrar_escolas_massa():
    print("Entrou na rota de cadastro de escolas em massa!")
    sys.stdout.flush()  # Força a exibição no terminal

    if request.method == "POST":
        print("Formulário de cadastro de escolas em massa recebido!")
        sys.stdout.flush()

        # Verificar se o arquivo foi enviado
        if "file" not in request.files:
            flash("Nenhum arquivo enviado", "error")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("Nenhum arquivo selecionado", "error")
            return redirect(request.url)

        try:
            # Lê o conteúdo do CSV e converte em um DataFrame, garantindo que os nomes das colunas sejam tratados corretamente
            data = pd.read_csv(file, dtype=str)
            data.columns = data.columns.str.strip()  # Remove espaços extras dos nomes das colunas

            print("Colunas detectadas no CSV:", list(data.columns))  # Mostra as colunas detectadas
            sys.stdout.flush()

            print("Primeiras linhas do CSV:\n", data.head())  # Mostra os primeiros registros do CSV
            sys.stdout.flush()

            # Definição das colunas esperadas
            required_columns = [
                'tipo_de_registro', 'codigo_inep', 'nome_da_escola', 'cep', 'codigo_ibge',
                'endereco', 'numero', 'complemento', 'bairro', 'ddd', 'telefone', 
                'telefone_2', 'email', 'ensino_fundamental'
            ]

            # Verificar se todas as colunas necessárias estão presentes
            missing_columns = [col for col in required_columns if col not in data.columns]

            if missing_columns:
                print("Faltando colunas:", missing_columns)  # Debug para ver quais colunas faltam
                sys.stdout.flush()
                flash(f"Faltam as seguintes colunas no arquivo CSV: {', '.join(missing_columns)}", "error")
                return redirect(request.url)

            # Converter os valores padrão corretamente
            data['tipo_de_registro'] = '00'  # Garante que sempre seja '00'
            data['ensino_fundamental'] = '1'  # Garante que sempre seja '1'

            # Renderizar a página de visualização com os dados do CSV
            return render_template("visualizar_escolas_massa.html", data=data.to_dict(orient='records'))

        except Exception as e:
            print(f"Erro ao processar o arquivo CSV: {e}")
            sys.stdout.flush()
            flash(f"Erro ao processar o arquivo CSV: {e}", "error")
            return redirect(request.url)

    return render_template("upload_escolas_massa.html")

@app.route("/confirmar_cadastro_escolas_massa", methods=["POST"])
@login_required
def confirmar_cadastro_escolas_massa():
    if current_user.tipo_usuario_id != 1:  # Apenas administradores podem cadastrar
        return redirect(url_for("home"))

    try:
        # Receber os dados enviados pelo AJAX
        data = request.get_json()
        escolas_data = data.get("escolas_data", [])

        if not escolas_data:
            flash("Nenhuma escola foi selecionada para cadastro.", "error")
            return redirect(request.url)

        db = get_db()
        cursor = db.cursor()

        print(f"Dados recebidos: {escolas_data}")  # Log dos dados recebidos

        # Iterar sobre as escolas para inserir os dados no banco
        for escola in escolas_data:
            escola_data = {
                "tipo_de_registro": escola.get('tipo_de_registro', '00'),
                "codigo_inep": escola.get('codigo_inep', '').strip(),
                "nome_da_escola": escola.get('nome_da_escola', '').strip(),
                "cep": escola.get('cep', '').strip(),
                "codigo_ibge": escola.get('codigo_ibge', '').strip(),
                "endereco": escola.get('endereco', '').strip(),
                "numero": escola.get('numero', '').strip(),
                "complemento": escola.get('complemento', '').strip(),
                "bairro": escola.get('bairro', '').strip(),
                "ddd": escola.get('ddd', '').strip(),
                "telefone": escola.get('telefone', '').strip(),
                "telefone_2": escola.get('telefone_2', '').strip(),
                "email": escola.get('email', '').strip(),
                "ensino_fundamental": escola.get('ensino_fundamental', 1)
            }

            print(f"Inserindo dados da escola: {escola_data}")

            # Inserir a escola no banco
            cursor.execute(""" 
                INSERT INTO escolas (
                    tipo_de_registro, codigo_inep, nome_da_escola, cep, codigo_ibge, 
                    endereco, numero, complemento, bairro, ddd, telefone, telefone_2, 
                    email, ensino_fundamental
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                escola_data["tipo_de_registro"], escola_data["codigo_inep"], escola_data["nome_da_escola"],
                escola_data["cep"], escola_data["codigo_ibge"], escola_data["endereco"],
                escola_data["numero"], escola_data["complemento"], escola_data["bairro"],
                escola_data["ddd"], escola_data["telefone"], escola_data["telefone_2"],
                escola_data["email"], escola_data["ensino_fundamental"]
            ))

            # Capturar o ID gerado pelo banco para a escola recém-inserida
            escola_id = cursor.lastrowid
            print(f"ID da escola gerado: {escola_id}")

            # Aqui você pode usar o `escola_id` para outros relacionamentos, se necessário

        # Confirmar as transações no banco
        db.commit()

        flash("Escolas cadastradas com sucesso!", "success")
        return jsonify({"status": "success"}), 200  # Resposta de sucesso para AJAX

    except Exception as e:
        print(f"Erro ao processar o cadastro das escolas: {e}")
        flash(f"Erro ao cadastrar escolas: {str(e)}", "error")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/portal_administrador/cadastrar_turmas_massa", methods=["GET", "POST"])
@login_required
def cadastrar_turmas_massa():
    if current_user.tipo_usuario_id != 1:  # Apenas administradores podem cadastrar
        return redirect(url_for("home"))

    db = get_db()
    cursor = db.cursor()

    if request.method == "POST":
        if "file" not in request.files:
            flash("Nenhum arquivo enviado", "error")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("Nenhum arquivo selecionado", "error")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            try:
                # Ler o arquivo como UTF-8
                file_content = file.stream.read().decode("utf-8")
                data = pd.read_csv(StringIO(file_content), dtype=str)  # Certifique-se de que todos os valores são strings
                print("Dados do arquivo carregados:", data.head())

                # Processar os dados
                for index, turma in data.iterrows():
                    codigo_inep = turma['Codigo_inep'].strip()
                    tipo_ensino_nome = turma['Tipo_ensino_id'].strip()
                    Ano_escolar_nome = turma['Ano_escolar_id'].strip()
                    turma_nome = turma['Turma'].strip()

                    # Buscar o ID da escola com base no Código INEP
                    cursor.execute("SELECT id, codigo_inep FROM escolas WHERE codigo_inep = ?", (codigo_inep,))
                    escola = cursor.fetchone()
                    if escola:
                        data.at[index, 'escola_id'] = int(escola[0])  # Converte para inteiro
                        data.at[index, 'codigo_inep'] = escola[1]
                    else:
                        data.at[index, 'escola_id'] = None
                        data.at[index, 'codigo_inep'] = None

                    # Buscar o ID do tipo de ensino com base no nome
                    cursor.execute("SELECT id FROM tipos_ensino WHERE nome = ?", (tipo_ensino_nome,))
                    tipo_ensino_id = cursor.fetchone()
                    if tipo_ensino_id:
                        data.at[index, 'tipo_ensino_id'] = int(tipo_ensino_id[0])  # Converte para inteiro
                    else:
                        print(f"Tipo de ensino '{tipo_ensino_nome}' não encontrado no banco de dados.")
                        data.at[index, 'tipo_ensino_id'] = None

                    # Buscar o ID da série com base no nome
                    cursor.execute("SELECT id FROM Ano_escolar WHERE nome = ?", (Ano_escolar_nome,))
                    Ano_escolar_id = cursor.fetchone()
                    if Ano_escolar_id:
                        data.at[index, 'Ano_escolar_id'] = int(Ano_escolar_id[0])  # Converte para inteiro
                    else:
                        print(f"Ano Escolar '{Ano_escolar_nome}' não encontrada no banco de dados.")
                        data.at[index, 'Ano_escolar_id'] = None

                    # Validar a letra da turma
                    if turma_nome and turma_nome.strip():
                        data.at[index, 'turma'] = turma_nome
                    else:
                        data.at[index, 'turma'] = None

                # Converter IDs para inteiros
                data['escola_id'] = data['escola_id'].astype('Int64')  # Usa Int64 para permitir valores nulos
                data['tipo_ensino_id'] = data['tipo_ensino_id'].astype('Int64')
                data['Ano_escolar_id'] = data['Ano_escolar_id'].astype('Int64')

                print("Dados após conversão de IDs:", data)

                # Passar os dados para o template de visualização
                return render_template("visualizar_turmas_massa.html", data=data.to_dict(orient="records"))

            except Exception as e:
                print(f"Erro ao processar o arquivo: {e}")
                flash(f"Erro ao processar o arquivo: {e}", "error")
                return redirect(request.url)

    return render_template("upload_turmas_massa.html")



@app.route("/confirmar_cadastro_turmas", methods=["POST"])
@login_required
def confirmar_cadastro_turmas():
    if current_user.tipo_usuario_id != 1:
        return redirect(url_for("home"))

    db = get_db()
    cursor = db.cursor()

    try:
        turmas_data = request.get_json()
        if not turmas_data:
            return jsonify({"status": "error", "message": "Nenhuma turma foi selecionada para cadastro."})

        for turma in turmas_data:
            escola_id = turma.get('escola_id')
            codigo_inep = turma.get('codigo_inep')  # Agora enviado corretamente
            tipo_ensino_id = turma.get('tipo_ensino_id')
            Ano_escolar_id = turma.get('Ano_escolar_id')
            turma_nome = turma.get('turma')

            # Verificar se todos os dados necessários estão presentes
            if not all([escola_id, codigo_inep, tipo_ensino_id, Ano_escolar_id, turma_nome]):
                print(f"Dados incompletos para a turma: {turma}")
                continue

            # Inserir a turma no banco de dados
            cursor.execute("""
                INSERT INTO turmas (tipo_de_registro, codigo_inep, escola_id, tipo_ensino_id, Ano_escolar_id, turma)
                VALUES ('20', ?, ?, ?, ?, ?)
            """, (codigo_inep, escola_id, tipo_ensino_id, Ano_escolar_id, turma_nome))

            print(f"Turma cadastrada com sucesso: {turma_nome}")

        db.commit()
        return jsonify({"status": "success", "message": "Cadastro realizado com sucesso!"})

    except Exception as e:
        db.rollback()
        print(f"Erro ao processar o cadastro das turmas: {e}")
        return jsonify({"status": "error", "message": f"Erro ao cadastrar turmas: {str(e)}"})



@app.route("/portal_administrador/cadastrar_usuarios_massa", methods=["GET", "POST"])
@login_required
def cadastrar_usuarios_massa():
    if current_user.tipo_usuario_id != 1:  # Apenas administradores podem acessar
        return redirect(url_for("home"))

    db = get_db()
    cursor = db.cursor()

    if request.method == "POST":
        if "file" not in request.files:
            flash("Nenhum arquivo enviado.", "error")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("Nenhum arquivo selecionado.", "error")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            try:
                # Lê o conteúdo do arquivo CSV
                file_content = file.stream.read().decode("utf-8")
                
                # Modificação aqui: configurações específicas para leitura do CSV
                data = pd.read_csv(
                    StringIO(file_content),
                    sep=',',
                    engine='python',
                    quoting=csv.QUOTE_NONE,
                    on_bad_lines='skip',
                    escapechar='\\',
                    skipinitialspace=True
                )
                
                # Limpar nomes das colunas
                data.columns = [col.strip().strip('"') for col in data.columns]
                
                # Limpar valores das colunas de texto
                for col in data.columns:
                    if data[col].dtype == 'object':
                        data[col] = data[col].str.strip().str.strip('"')
                
                print("Dados brutos do arquivo:")
                print(data.to_string())  # Mostra todos os dados sem truncar
                print("\nColunas encontradas:", data.columns.tolist())
                
                # Verificar se as colunas necessárias estão no arquivo
                colunas_necessarias = [
                    "tipo_registro", "codigo_inep_escola", "cpf",
                    "nome", "data_nascimento", "mae", "pai", "sexo", "codigo_ibge",
                    "cep", "escola_id", "tipo_ensino_id", "Ano_escolar_id", "turma_id", 
                    "codigo_ibge", "tipo_usuario_id"
                ]
                
                # Tentar corrigir o DataFrame se ele tiver apenas uma coluna
                if len(data.columns) == 1:
                    # Dividir a única coluna em várias usando o separador ','
                    data = pd.DataFrame([x.split(',') for x in data[data.columns[0]]], columns=colunas_necessarias)
                
                colunas_presentes = set(data.columns)
                
                if not set(colunas_necessarias).issubset(colunas_presentes):
                    missing_columns = set(colunas_necessarias) - colunas_presentes
                    flash(f"Colunas faltando no arquivo: {', '.join(missing_columns)}", "error")
                    return redirect(request.url)

                # Conversão e validação dos IDs e outros campos
                for index, usuario in data.iterrows():
                    try:
                        print(f"\nProcessando usuário: {usuario['nome']}")  # Log para cada usuário
                        tipo_usuario = int(usuario["tipo_usuario_id"])

                        # Para alunos e professores, buscar IDs das referências
                        if tipo_usuario in [3, 4]:
                            # Tentar buscar escola pelo nome primeiro
                            print(f"Buscando escola pelo nome: {usuario['escola_id']}")
                            cursor.execute("SELECT id FROM escolas WHERE nome_da_escola = ? OR codigo_inep = ?", (usuario["escola_id"], usuario["codigo_inep_escola"]))
                            escola_result = cursor.fetchone()
                            
                            # Se não encontrar pelo nome, tentar pelo código INEP
                            if not escola_result:
                                print(f"Escola não encontrada pelo nome, tentando código INEP: {usuario['codigo_inep_escola']}")
                                cursor.execute("SELECT id FROM escolas WHERE codigo_inep = ?", (usuario["codigo_inep_escola"],))
                                escola_result = cursor.fetchone()
                            
                            escola_id = escola_result[0] if escola_result else None
                            print(f"ID da escola encontrado: {escola_id}")

                            # Buscar tipo de ensino pela descrição
                            print(f"Buscando tipo de ensino: {usuario['tipo_ensino_id']}")
                            cursor.execute("SELECT id FROM tipos_ensino WHERE nome = ?", (usuario["tipo_ensino_id"],))
                            tipo_ensino_id = cursor.fetchone()
                            tipo_ensino_id = tipo_ensino_id[0] if tipo_ensino_id else None
                            print(f"ID do tipo de ensino encontrado: {tipo_ensino_id}")

                            # Buscar série
                            print(f"Buscando série: {usuario['Ano_escolar_id']}")
                            cursor.execute("SELECT id FROM Ano_escolar WHERE nome = ?", (usuario["Ano_escolar_id"],))
                            Ano_escolar_id = cursor.fetchone()
                            Ano_escolar_id = Ano_escolar_id[0] if Ano_escolar_id else None
                            print(f"ID da série encontrado: {Ano_escolar_id}")

                            # Buscar turma
                            print(f"Buscando turma: {usuario['turma_id']}")
                            cursor.execute(
                                "SELECT id FROM turmas WHERE turma = ? AND escola_id = ? AND Ano_escolar_id = ?",
                                (usuario["turma_id"], escola_id, Ano_escolar_id)
                            )
                            turma_id = cursor.fetchone()
                            turma_id = turma_id[0] if turma_id else None
                            print(f"ID da turma encontrado: {turma_id}")

                            if not all([escola_id, tipo_ensino_id, Ano_escolar_id, turma_id]):
                                print("AVISO: Alguns IDs não foram encontrados:")
                                print(f"- Escola ID: {escola_id}")
                                print(f"- Tipo Ensino ID: {tipo_ensino_id}")
                                print(f"- Ano Escolar ID: {Ano_escolar_id}")
                                print(f"- Turma ID: {turma_id}")
                        else:
                            escola_id, tipo_ensino_id, Ano_escolar_id, turma_id = None, None, None, None

                        # Atualizar os valores no DataFrame
                        data.at[index, "escola_id"] = escola_id
                        data.at[index, "tipo_ensino_id"] = tipo_ensino_id
                        data.at[index, "Ano_escolar_id"] = Ano_escolar_id
                        data.at[index, "turma_id"] = turma_id

                        # Gerar senha padrão para cada usuário
                        data.at[index, "senha"] = "123456"  # Senha padrão para todos os usuários

                        # Gerar email padrão para cada usuário usando o CPF
                        if pd.notna(usuario["cpf"]) and str(usuario["cpf"]).strip():
                            cpf = str(usuario["cpf"]).strip()
                            data.at[index, "email"] = f"{cpf}@aluno.edu.br"

                        print(f"IDs convertidos: escola_id={escola_id}, tipo_ensino_id={tipo_ensino_id}, Ano_escolar_id={Ano_escolar_id}, turma_id={turma_id}")

                    except Exception as e:
                        print(f"Erro ao processar o usuário {usuario['nome']}: {e}")
                        print(f"Dados do usuário que causou erro: {usuario}")

                print("\nDados após conversão de IDs:", data.head())  # Log final

                # Renderizar pré-visualização dos dados
                return render_template("visualizar_usuarios_massa.html", data=data.to_dict(orient="records"))

            except Exception as e:
                print(f"Erro ao processar o arquivo: {e}")
                flash(f"Erro ao processar o arquivo: {e}", "error")
                return redirect(request.url)

    return render_template("upload_usuarios_massa.html")


@app.route("/confirmar_cadastro_usuarios", methods=["POST"])
@login_required
def confirmar_cadastro_usuarios():
    if current_user.tipo_usuario_id != 1:
        print("Erro: Usuário sem permissão")
        return jsonify({"status": "error", "message": "Você não tem permissão para realizar esta ação."})

    try:
        print("1. Iniciando processo de confirmação de cadastro")
        
        # Receber os dados enviados via AJAX
        data = request.get_json()
        usuarios_data = data.get("usuarios", [])

        print(f"2. Dados recebidos do AJAX: {data}")
        print(f"3. Lista de usuários para cadastro: {usuarios_data}")

        if not usuarios_data:
            print("Erro: Nenhum usuário recebido para cadastro")
            return jsonify({"status": "error", "message": "Nenhum usuário selecionado."})

        db = get_db()
        cursor = db.cursor()

        for usuario in usuarios_data:
            try:
                print(f"\n4. Iniciando cadastro do usuário: {usuario.get('nome', 'Nome não fornecido')}")
                print(f"5. Dados completos do usuário: {usuario}")

                tipo_usuario = int(usuario["tipo_usuario_id"])
                print(f"6. Tipo de usuário: {tipo_usuario}")

                # Verifica se o usuário já existe
                if "cpf" in usuario and usuario["cpf"]:
                    print(f"7a. Verificando existência por CPF: {usuario['cpf']}")
                    cursor.execute("SELECT id FROM usuarios WHERE cpf = ?", (usuario["cpf"],))
                else:
                    print(f"7b. Verificando existência por email: {usuario.get('email', 'Email não fornecido')}")
                    cursor.execute("SELECT id FROM usuarios WHERE email = ?", (usuario["email"],))
                
                usuario_existente = cursor.fetchone()
                print(f"8. Usuário existente? {usuario_existente is not None}")

                if usuario_existente:
                    usuario_id = usuario_existente[0]
                    print(f"9a. Usuário já existe com ID: {usuario_id}")
                else:
                    print("9b. Preparando para inserir novo usuário")
                    print(f"10. Valores para inserção:")
                    valores = (
                        usuario["nome"],
                        usuario.get("email"),
                        generate_password_hash(usuario["senha"]),
                        usuario["tipo_usuario_id"],
                        usuario.get("escola_id"),
                        usuario.get("turma_id"),
                        usuario.get("Ano_escolar_id"),
                        usuario.get("tipo_ensino_id"),
                        usuario.get("cep"),
                        usuario.get("codigo_ibge"),
                        usuario.get("cpf"),
                        usuario.get("data_nascimento"),
                        usuario.get("mae"),
                        usuario.get("pai"),
                        usuario.get("sexo"),
                        usuario.get("codigo_ibge")
                    )
                    print(f"Valores: {valores}")

                    cursor.execute(
                        """
                        INSERT INTO usuarios (
                            nome, email, senha, tipo_usuario_id, escola_id, turma_id,
                            Ano_escolar_id, tipo_ensino_id, cep, codigo_ibge, cpf, data_nascimento,
                            mae, pai, sexo, codigo_ibge
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        valores
                    )
                    db.commit()
                    usuario_id = cursor.lastrowid
                    print(f"11. Novo usuário inserido com ID: {usuario_id}")

                # Se for professor, associá-lo à tabela professor_turma_escola
                if tipo_usuario == 3:
                    print("12. Usuário é professor, vinculando à turma")
                    cursor.execute("SELECT COUNT(*) FROM professor_turma_escola WHERE professor_id = ?", (usuario_id,))
                    if cursor.fetchone()[0] == 0:
                        print("13. Inserindo vínculo professor-turma")
                        cursor.execute(
                            """
                            INSERT INTO professor_turma_escola (professor_id, escola_id, turma_id, tipo_ensino_id, Ano_escolar_id)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (usuario_id, usuario["escola_id"], usuario["turma_id"], usuario["tipo_ensino_id"], usuario["Ano_escolar_id"]),
                        )
                        db.commit()
                        print("14. Vínculo professor-turma criado com sucesso")

            except Exception as e:
                db.rollback()
                print(f"ERRO ao cadastrar usuário {usuario.get('nome', 'Nome não fornecido')}")
                print(f"Detalhes do erro: {str(e)}")
                print(f"Dados que causaram erro: {usuario}")
                raise  # Re-lança a exceção para ser capturada pelo try/except externo

        print("15. Processo finalizado com sucesso")
        return jsonify({"status": "success", "message": "Usuários cadastrados com sucesso!"})

    except Exception as e:
        db.rollback()
        erro_msg = f"Erro ao processar cadastro: {str(e)}"
        print(f"ERRO FATAL: {erro_msg}")
        return jsonify({"status": "error", "message": erro_msg})
# Inicialização do Banco e Servidor

# if __name__ == "__main__":
#     init_db()
#     app.run(debug=True)

import logging

if __name__ == "__main__":
    app.debug = True
    app.config["PROPAGATE_EXCEPTIONS"] = True  # Força o Flask a exibir erros
    logging.basicConfig(level=logging.DEBUG)  # Ativa logging detalhado
    app.run(debug=True)

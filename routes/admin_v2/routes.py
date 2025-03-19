from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Escolas, Disciplinas, Turmas, Cidades, TIPO_USUARIO_ADMIN, TIPO_USUARIO_SECRETARIA_EDUCACAO, TIPO_USUARIO_PROFESSOR
import pandas as pd
import requests
from functools import wraps
from . import admin_v2

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Acesso negado. Você precisa ser um administrador.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_escolas():
    """Retorna as escolas que o usuário tem acesso"""
    if current_user.is_admin:
        return Escolas.query.all()
    elif current_user.tipo_usuario_id == TIPO_USUARIO_SECRETARIA_EDUCACAO:
        return Escolas.query.filter_by(cidade_id=current_user.cidade_id).all()
    elif current_user.tipo_usuario_id == TIPO_USUARIO_PROFESSOR:
        return [current_user.escola_vinculada] if current_user.escola_vinculada else []
    return []

@admin_v2.route('/dashboard')
@login_required
def dashboard():
    return render_template('admin_v2/dashboard.html')

# Rota para buscar endereço via CEP
@admin_v2.route('/buscar-cep/<cep>')
@login_required
def buscar_cep(cep):
    """Busca endereço usando a API do ViaCEP"""
    try:
        # Remove caracteres não numéricos do CEP
        cep = ''.join(filter(str.isdigit, cep))
        
        if len(cep) != 8:
            return jsonify({'error': 'CEP inválido'}), 400
            
        # Consulta a API do ViaCEP
        response = requests.get(f'https://viacep.com.br/ws/{cep}/json/')
        data = response.json()
        
        if 'erro' in data:
            return jsonify({'error': 'CEP não encontrado'}), 404
            
        # Busca a cidade no banco pelo IBGE
        cidade = Cidades.query.filter_by(codigo_ibge=data['ibge']).first()
        
        return jsonify({
            'logradouro': data['logradouro'],
            'bairro': data['bairro'],
            'cidade_id': cidade.id if cidade else None,
            'cidade_nome': data['localidade'],
            'uf': data['uf']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rotas para cadastro de escolas
@admin_v2.route('/escolas')
@login_required
def escolas_list():
    """Lista todas as escolas"""
    escolas = get_user_escolas()
    return render_template('admin_v2/escolas/list.html', escolas=escolas)

@admin_v2.route('/escolas/create', methods=['GET', 'POST'])
@login_required
def escolas_create():
    """Criar nova escola"""
    if request.method == 'POST':
        nome = request.form['nome']
        codigo_inep = request.form['codigo_inep']
        cep = request.form['cep']
        logradouro = request.form['logradouro']
        numero = request.form['numero']
        complemento = request.form['complemento']
        bairro = request.form['bairro']
        cidade_id = request.form['cidade_id']
        
        # Tipos de ensino
        tem_fundamental_1 = 'tem_fundamental_1' in request.form
        tem_fundamental_2 = 'tem_fundamental_2' in request.form
        tem_medio = 'tem_medio' in request.form
        tem_eja = 'tem_eja' in request.form
        tem_tecnico = 'tem_tecnico' in request.form
        
        escola = Escolas(
            nome=nome,
            codigo_inep=codigo_inep,
            cep=cep,
            logradouro=logradouro,
            numero=numero,
            complemento=complemento,
            bairro=bairro,
            cidade_id=cidade_id,
            tem_fundamental_1=tem_fundamental_1,
            tem_fundamental_2=tem_fundamental_2,
            tem_medio=tem_medio,
            tem_eja=tem_eja,
            tem_tecnico=tem_tecnico
        )
        
        db.session.add(escola)
        db.session.commit()
        
        flash('Escola criada com sucesso!', 'success')
        return redirect(url_for('admin_v2.escolas_list'))
    
    # Filtrar cidades baseado no tipo de usuário
    if current_user.is_admin:
        cidades = Cidades.query.all()
    elif current_user.tipo_usuario_id == TIPO_USUARIO_SECRETARIA_EDUCACAO:
        cidades = [current_user.cidade]
    else:
        cidades = []
    
    return render_template('admin_v2/escolas/create.html', cidades=cidades)

@admin_v2.route('/escolas/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def escolas_edit(id):
    """Editar escola existente"""
    escola = Escolas.query.get_or_404(id)
    
    # Verificar permissão
    if current_user.tipo_usuario_id == TIPO_USUARIO_SECRETARIA_EDUCACAO and escola.cidade_id != current_user.cidade_id:
        flash('Você não tem permissão para editar esta escola.', 'error')
        return redirect(url_for('admin_v2.escolas_list'))
    
    if request.method == 'POST':
        escola.nome = request.form['nome']
        escola.codigo_inep = request.form['codigo_inep']
        escola.cep = request.form['cep']
        escola.logradouro = request.form['logradouro']
        escola.numero = request.form['numero']
        escola.complemento = request.form['complemento']
        escola.bairro = request.form['bairro']
        escola.cidade_id = request.form['cidade_id']
        
        # Tipos de ensino
        escola.tem_fundamental_1 = 'tem_fundamental_1' in request.form
        escola.tem_fundamental_2 = 'tem_fundamental_2' in request.form
        escola.tem_medio = 'tem_medio' in request.form
        escola.tem_eja = 'tem_eja' in request.form
        escola.tem_tecnico = 'tem_tecnico' in request.form
        
        db.session.commit()
        flash('Escola atualizada com sucesso!', 'success')
        return redirect(url_for('admin_v2.escolas_list'))
    
    # Filtrar cidades baseado no tipo de usuário
    if current_user.is_admin:
        cidades = Cidades.query.all()
    elif current_user.tipo_usuario_id == TIPO_USUARIO_SECRETARIA_EDUCACAO:
        cidades = [current_user.cidade]
    else:
        cidades = []
    
    return render_template('admin_v2/escolas/edit.html', escola=escola, cidades=cidades)

@admin_v2.route('/escolas/delete/<int:id>')
@login_required
def escolas_delete(id):
    """Excluir escola"""
    escola = Escolas.query.get_or_404(id)
    
    # Verificar permissão
    if current_user.tipo_usuario_id == TIPO_USUARIO_SECRETARIA_EDUCACAO and escola.cidade_id != current_user.cidade_id:
        flash('Você não tem permissão para excluir esta escola.', 'error')
        return redirect(url_for('admin_v2.escolas_list'))
    
    db.session.delete(escola)
    db.session.commit()
    flash('Escola excluída com sucesso!', 'success')
    return redirect(url_for('admin_v2.escolas_list'))

@admin_v2.route('/escolas/upload', methods=['GET', 'POST'])
@login_required
def cadastro_massa_escolas():
    """Upload em massa de escolas via CSV"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo enviado.', 'error')
            return redirect(url_for('admin_v2.cadastro_massa_escolas'))
        
        file = request.files['file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado.', 'error')
            return redirect(url_for('admin_v2.cadastro_massa_escolas'))
        
        if file and file.filename.endswith('.csv'):
            try:
                # Ler CSV
                import pandas as pd
                df = pd.read_csv(file)
                
                # Validar colunas obrigatórias
                required_columns = ['nome', 'codigo_inep', 'cep', 'logradouro', 'numero', 'bairro', 'cidade_id']
                if not all(col in df.columns for col in required_columns):
                    flash('CSV inválido. Colunas obrigatórias: nome, codigo_inep, cep, logradouro, numero, bairro, cidade_id', 'error')
                    return redirect(url_for('admin_v2.cadastro_massa_escolas'))
                
                # Processar cada linha
                for _, row in df.iterrows():
                    escola = Escolas(
                        nome=row['nome'],
                        codigo_inep=row['codigo_inep'],
                        cep=row['cep'],
                        logradouro=row['logradouro'],
                        numero=row['numero'],
                        bairro=row['bairro'],
                        cidade_id=row['cidade_id']
                    )
                    db.session.add(escola)
                
                db.session.commit()
                flash('Escolas importadas com sucesso!', 'success')
                return redirect(url_for('admin_v2.escolas_list'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao processar arquivo: {str(e)}', 'error')
                return redirect(url_for('admin_v2.cadastro_massa_escolas'))
        else:
            flash('Arquivo deve estar no formato CSV.', 'error')
    
    return render_template('admin_v2/cadastro_massa/escolas.html')

# Rotas para cadastro de disciplinas
@admin_v2.route('/disciplinas', methods=['GET'])
@login_required
@admin_required
def disciplinas_list():
    """Lista todas as disciplinas"""
    disciplinas = Disciplinas.query.all()
    return render_template('admin_v2/disciplinas/list.html', disciplinas=disciplinas)

@admin_v2.route('/disciplinas/create', methods=['GET', 'POST'])
@login_required
@admin_required
def disciplina_create():
    """Criar nova disciplina"""
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        
        if not nome:
            flash('O nome da disciplina é obrigatório.', 'error')
            return redirect(url_for('admin_v2.disciplina_create'))
        
        try:
            disciplina = Disciplinas(
                nome=nome,
                descricao=descricao
            )
            db.session.add(disciplina)
            db.session.commit()
            flash('Disciplina criada com sucesso!', 'success')
            return redirect(url_for('admin_v2.disciplinas_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar disciplina.', 'error')
            
    return render_template('admin_v2/disciplinas/create.html')

# Rotas para cadastro de turmas
@admin_v2.route('/turmas', methods=['GET'])
@login_required
@admin_required
def turmas_list():
    """Lista todas as turmas"""
    turmas = Turmas.query.all()
    escolas = Escolas.query.all()
    return render_template('admin_v2/turmas/list.html', turmas=turmas, escolas=escolas)

@admin_v2.route('/turmas/create', methods=['GET', 'POST'])
@login_required
@admin_required
def turma_create():
    """Criar nova turma"""
    if request.method == 'POST':
        nome = request.form.get('nome')
        escola_id = request.form.get('escola_id', type=int)
        Ano_escolar = request.form.get('Ano_escolar')
        turno = request.form.get('turno')
        
        if not all([nome, escola_id, Ano_escolar, turno]):
            flash('Todos os campos são obrigatórios.', 'error')
            return redirect(url_for('admin_v2.turma_create'))
        
        try:
            turma = Turmas(
                nome=nome,
                escola_id=escola_id,
                Ano_escolar=Ano_escolar,
                turno=turno
            )
            db.session.add(turma)
            db.session.commit()
            flash('Turma criada com sucesso!', 'success')
            return redirect(url_for('admin_v2.turmas_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar turma.', 'error')
    
    escolas = Escolas.query.all()
    return render_template('admin_v2/turmas/create.html', escolas=escolas)

# Rotas para cadastros em massa
@admin_v2.route('/cadastro-massa/turmas', methods=['GET', 'POST'])
@login_required
@admin_required
def cadastro_massa_turmas():
    """Cadastro em massa de turmas via arquivo CSV"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo enviado.', 'error')
            return redirect(url_for('admin_v2.cadastro_massa_turmas'))
            
        file = request.files['file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado.', 'error')
            return redirect(url_for('admin_v2.cadastro_massa_turmas'))
            
        if file and file.filename.endswith('.csv'):
            try:
                import pandas as pd
                df = pd.read_csv(file)
                
                # Validar colunas necessárias
                required_columns = ['nome', 'escola_id', 'Ano_escolar', 'turno']
                if not all(col in df.columns for col in required_columns):
                    flash('Arquivo CSV deve conter as colunas: nome, escola_id, Ano_escolar, turno', 'error')
                    return redirect(url_for('admin_v2.cadastro_massa_turmas'))
                
                # Processar dados
                for _, row in df.iterrows():
                    turma = Turmas(
                        nome=row['nome'],
                        escola_id=int(row['escola_id']),
                        Ano_escolar=row['Ano_escolar'],
                        turno=row['turno']
                    )
                    db.session.add(turma)
                
                db.session.commit()
                flash(f'{len(df)} turmas cadastradas com sucesso!', 'success')
                return redirect(url_for('admin_v2.turmas_list'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao processar arquivo: {str(e)}', 'error')
        else:
            flash('Arquivo deve estar no formato CSV.', 'error')
            
    return render_template('admin_v2/cadastro_massa/turmas.html')

# Rotas para gerenciamento de usuários
@admin_v2.route('/users')
@login_required
@admin_required
def users_list():
    """Lista todos os usuários"""
    users = User.query.all()
    return render_template('admin_v2/users/list.html', users=users)

@admin_v2.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def user_create():
    """Criar novo usuário"""
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        tipo_usuario_id = request.form.get('tipo_usuario_id', type=int)
        
        if not all([nome, email, senha, tipo_usuario_id]):
            flash('Todos os campos são obrigatórios.', 'error')
            return redirect(url_for('admin_v2.user_create'))
        
        # Verifica se o email já está em uso
        if User.query.filter_by(email=email).first():
            flash('Este email já está em uso.', 'error')
            return redirect(url_for('admin_v2.user_create'))
        
        try:
            user = User(
                nome=nome,
                email=email,
                tipo_usuario_id=tipo_usuario_id
            )
            user.senha = senha  # Isso irá usar o setter que faz o hash da senha
            
            db.session.add(user)
            db.session.commit()
            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('admin_v2.users_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar usuário: {str(e)}', 'error')
    
    return render_template('admin_v2/users/create.html')

@admin_v2.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def user_edit(user_id):
    """Editar usuário existente"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        tipo_usuario_id = request.form.get('tipo_usuario_id', type=int)
        nova_senha = request.form.get('nova_senha')
        
        if not all([nome, email, tipo_usuario_id]):
            flash('Nome, email e tipo de usuário são obrigatórios.', 'error')
            return redirect(url_for('admin_v2.user_edit', user_id=user_id))
        
        # Verifica se o novo email já está em uso por outro usuário
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user_id:
            flash('Este email já está em uso por outro usuário.', 'error')
            return redirect(url_for('admin_v2.user_edit', user_id=user_id))
        
        try:
            user.nome = nome
            user.email = email
            user.tipo_usuario_id = tipo_usuario_id
            
            if nova_senha:
                user.senha = nova_senha  # Isso irá usar o setter que faz o hash da senha
            
            db.session.commit()
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('admin_v2.users_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar usuário: {str(e)}', 'error')
    
    return render_template('admin_v2/users/edit.html', user=user)

@admin_v2.route('/users/delete/<int:user_id>')
@login_required
@admin_required
def user_delete(user_id):
    """Excluir usuário"""
    user = User.query.get_or_404(user_id)
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash('Usuário excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir usuário: {str(e)}', 'error')
    
    return redirect(url_for('admin_v2.users_list'))

@admin_v2.route('/usuarios/vincular', methods=['GET', 'POST'])
@login_required
@admin_required
def vincular_usuario():
    if request.method == 'POST':
        usuario_id = request.form['usuario_id']
        tipo_vinculo = request.form['tipo_vinculo']
        vinculo_id = request.form['vinculo_id']
        
        usuario = User.query.get(usuario_id)
        if not usuario:
            flash('Usuário não encontrado.', 'error')
            return redirect(url_for('admin_v2.vincular_usuario'))
        
        if tipo_vinculo == 'escola':
            escola = Escolas.query.get(vinculo_id)
            if not escola:
                flash('Escola não encontrada.', 'error')
                return redirect(url_for('admin_v2.vincular_usuario'))
            
            usuario.escola_id = escola.id
            flash('Professor vinculado à escola com sucesso!', 'success')
            
        elif tipo_vinculo == 'cidade':
            cidade = Cidades.query.get(vinculo_id)
            if not cidade:
                flash('Cidade não encontrada.', 'error')
                return redirect(url_for('admin_v2.vincular_usuario'))
            
            usuario.cidade_id = cidade.id
            flash('Usuário vinculado à cidade com sucesso!', 'success')
        
        db.session.commit()
        return redirect(url_for('admin_v2.vincular_usuario'))
    
    # Carregar usuários, escolas e cidades para o formulário
    professores = User.query.filter_by(tipo_usuario_id=TIPO_USUARIO_PROFESSOR).all()
    secretarios = User.query.filter_by(tipo_usuario_id=TIPO_USUARIO_SECRETARIA_EDUCACAO).all()
    escolas = Escolas.query.all()
    cidades = Cidades.query.all()
    
    return render_template('admin_v2/usuarios/vincular.html',
                         professores=professores,
                         secretarios=secretarios,
                         escolas=escolas,
                         cidades=cidades)

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from flask_login import login_required, current_user
from extensions import db
from models import Usuarios, Escolas, Cidades, TiposUsuarios, Turmas
from werkzeug.security import generate_password_hash
import pandas as pd

# Registrando o Blueprint
administrador_bp = Blueprint('administrador', __name__, url_prefix='/administrador')

@administrador_bp.before_request
@login_required
def verificar_permissao():
    """Verifica se o usuário tem permissão de administrador."""
    if current_user.tipo_usuario_id != 6:  # ADM
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

@administrador_bp.before_app_request
def propagar_codigo_ibge():
    """Propaga o código IBGE selecionado para outros portais."""
    if 'codigo_ibge_selecionado' in session:
        g.codigo_ibge = session['codigo_ibge_selecionado']
    else:
        g.codigo_ibge = None

@administrador_bp.route('/')
def portal_administrador2():
    """Página principal do portal do administrador."""
    # Buscar todas as cidades
    cidades = db.session.query(Cidades).order_by(Cidades.nome).all()
    
    # Pegar a cidade selecionada da sessão
    cidade_selecionada = None
    if 'codigo_ibge_selecionado' in session:
        cidade_selecionada = db.session.query(Cidades).filter_by(
            codigo_ibge=session['codigo_ibge_selecionado']
        ).first()
    
    # Contagem de usuários por tipo
    usuarios_por_tipo = db.session.query(
        TiposUsuarios.descricao,
        db.func.count(Usuarios.id)
    ).join(
        Usuarios, Usuarios.tipo_usuario_id == TiposUsuarios.id
    )
    
    # Se tiver cidade selecionada, filtrar por código IBGE
    if cidade_selecionada:
        usuarios_por_tipo = usuarios_por_tipo.filter(
            Usuarios.codigo_ibge == cidade_selecionada.codigo_ibge
        )
    
    usuarios_por_tipo = usuarios_por_tipo.group_by(
        TiposUsuarios.descricao
    ).all()
    
    # Contagem de escolas
    total_escolas = db.session.query(db.func.count(Escolas.id))
    if cidade_selecionada:
        total_escolas = total_escolas.filter(
            Escolas.codigo_ibge == cidade_selecionada.codigo_ibge
        )
    total_escolas = total_escolas.scalar()
    
    return render_template(
        'administrador/portal_administrador.html',
        cidades=cidades,
        cidade_selecionada=cidade_selecionada,
        usuarios_por_tipo=usuarios_por_tipo,
        total_escolas=total_escolas
    )

@administrador_bp.route('/selecionar_cidade2', methods=['POST'])
def selecionar_cidade2():
    """Seleciona uma cidade para filtrar os dados."""
    codigo_ibge = request.form.get('codigo_ibge')
    if codigo_ibge:
        session['codigo_ibge_selecionado'] = codigo_ibge
        flash('Cidade selecionada com sucesso!', 'success')
    else:
        session.pop('codigo_ibge_selecionado', None)
        flash('Filtro de cidade removido!', 'info')
    return redirect(url_for('administrador.portal_administrador2'))

@administrador_bp.route('/upload_usuarios_escolas_massa', methods=['GET', 'POST'])
def upload_usuarios_escolas_massa():
    """Página de upload em massa de usuários, escolas e turmas."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo foi enviado.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Nenhum arquivo foi selecionado.', 'error')
            return redirect(request.url)
        
        if not file.filename.endswith('.xlsx'):
            flash('Por favor, envie um arquivo Excel (.xlsx)', 'error')
            return redirect(request.url)
        
        # Ler o arquivo Excel
        try:
            df = pd.read_excel(file)
            # Guardar os dados na sessão para confirmar depois
            session['upload_data'] = df.to_dict('records')
            return render_template('upload_usuarios_escolas_massa.html', preview_data=df.to_dict('records'))
        except Exception as e:
            flash(f'Erro ao ler o arquivo: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('upload_usuarios_escolas_massa.html')

@administrador_bp.route('/confirmar_cadastro_massa', methods=['POST'])
def confirmar_cadastro_massa():
    """Confirma o cadastro em massa após a prévia."""
    if 'upload_data' not in session:
        flash('Nenhum dado para cadastrar. Faça o upload primeiro.', 'error')
        return redirect(url_for('administrador.upload_usuarios_escolas_massa'))
    
    try:
        data = session['upload_data']
        
        # Processar escolas
        for escola in data:
            nova_escola = Escolas(
                nome=escola['nome'],
                codigo_inep=escola['codigo_inep'],
                codigo_ibge=escola['codigo_ibge']
            )
            db.session.add(nova_escola)
        
        # Processar turmas
        for turma in data:
            nova_turma = Turmas(
                nome=turma['turma'],
                escola_id=turma['escola_id'],
                ano_escolar_id=turma['ano_escolar_id']
            )
            db.session.add(nova_turma)
        
        # Processar usuários
        for usuario in data:
            novo_usuario = Usuarios(
                nome=usuario['nome'],
                email=usuario['email'],
                senha=generate_password_hash(usuario['senha']),
                tipo_usuario_id=usuario['tipo_usuario_id'],
                escola_id=usuario['escola_id'],
                turma_id=usuario['turma_id'],
                ano_escolar_id=usuario['ano_escolar_id'],
                codigo_ibge=usuario['codigo_ibge']
            )
            db.session.add(novo_usuario)
        
        db.session.commit()
        flash('Cadastro em massa realizado com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao realizar o cadastro: {str(e)}', 'error')
    
    # Limpar dados da sessão
    session.pop('upload_data', None)
    return redirect(url_for('administrador.upload_usuarios_escolas_massa'))

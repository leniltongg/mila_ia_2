from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from flask_login import login_required, current_user
from extensions import db
from models import Usuarios, Escolas, Cidades, TiposUsuarios

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

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, TemasRedacao, RedacoesAlunos
from datetime import datetime

bp = Blueprint('alunos', __name__)

@bp.route('/temas_redacao')
@login_required
def temas_redacao():
    """Lista os temas de redação disponíveis para o aluno"""
    if current_user.tipo_usuario_id != 4:  # Aluno
        flash('Acesso não autorizado', 'danger')
        return redirect(url_for('index'))
        
    # Busca temas ativos para o ano escolar do aluno
    temas = TemasRedacao.query.filter_by(
        codigo_ibge=current_user.codigo_ibge,
        ano_escolar_id=current_user.ano_escolar_id,
        status='ativo'
    ).order_by(TemasRedacao.data_envio.desc()).all()
    
    # Para cada tema, verifica se o aluno já respondeu
    for tema in temas:
        redacao = RedacoesAlunos.query.filter_by(
            tema_id=tema.id,
            aluno_id=current_user.id
        ).first()
        tema.respondido = redacao is not None
        if tema.respondido:
            tema.nota = redacao.nota_final
    
    return render_template('alunos/temas_redacao.html', temas=temas)

@bp.route('/preparar_redacao/<int:tema_id>')
@login_required
def preparar_redacao(tema_id):
    """Mostra a página para escrever a redação"""
    if current_user.tipo_usuario_id != 4:  # Aluno
        flash('Acesso não autorizado', 'danger')
        return redirect(url_for('index'))
        
    # Verifica se o tema existe e está disponível
    tema = TemasRedacao.query.filter_by(
        id=tema_id,
        codigo_ibge=current_user.codigo_ibge,
        ano_escolar_id=current_user.ano_escolar_id,
        status='ativo'
    ).first_or_404()
    
    # Verifica se já respondeu
    redacao = RedacoesAlunos.query.filter_by(
        tema_id=tema.id,
        aluno_id=current_user.id
    ).first()
    
    if redacao:
        flash('Você já respondeu este tema', 'warning')
        return redirect(url_for('alunos.temas_redacao'))
        
    return render_template('alunos/preparar_redacao.html', tema=tema)

@bp.route('/analisar_redacao', methods=['POST'])
@login_required
def analisar_redacao():
    """Analisa a redação do aluno e salva no banco"""
    if current_user.tipo_usuario_id != 4:  # Aluno
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
        
    data = request.get_json()
    
    # Verifica se o tema existe e está ativo
    tema = TemasRedacao.query.filter_by(
        id=data['tema_id'],
        codigo_ibge=current_user.codigo_ibge,
        ano_escolar_id=current_user.ano_escolar_id,
        status='ativo'
    ).first()
    
    if not tema:
        return jsonify({'success': False, 'message': 'Tema não encontrado ou não disponível'}), 404
    
    # Verifica se já respondeu
    redacao_existente = RedacoesAlunos.query.filter_by(
        tema_id=tema.id,
        aluno_id=current_user.id
    ).first()
    
    if redacao_existente:
        return jsonify({'success': False, 'message': 'Você já respondeu este tema'}), 400
    
    try:
        # Aqui você chamaria a API de análise de redação
        # Por enquanto vamos simular uma resposta
        analise = {
            'nota_final': 800,
            'comp1': 160,
            'comp2': 160,
            'comp3': 160,
            'comp4': 160,
            'comp5': 160,
            'estrutura': 'Análise da estrutura...',
            'argumentacao': 'Análise dos argumentos...',
            'gramatica': 'Análise gramatical...',
            'sugestoes': 'Sugestões de melhoria...'
        }
        
        # Salva a redação e a análise
        redacao = RedacoesAlunos(
            tema_id=tema.id,
            aluno_id=current_user.id,
            texto=data['redacao'],
            nota_final=analise['nota_final'],
            comp1=analise['comp1'],
            comp2=analise['comp2'],
            comp3=analise['comp3'],
            comp4=analise['comp4'],
            comp5=analise['comp5'],
            analise_estrutura=analise['estrutura'],
            analise_argumentos=analise['argumentacao'],
            analise_gramatical=analise['gramatica'],
            sugestoes_melhoria=analise['sugestoes']
        )
        
        db.session.add(redacao)
        db.session.commit()
        
        return jsonify({'success': True, 'analise': analise})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

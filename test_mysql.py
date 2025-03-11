from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, send_file
from flask_login import login_required, current_user
import os
from werkzeug.utils import secure_filename
import pandas as pd
from weasyprint import HTML
import tempfile
from io import BytesIO
from datetime import datetime
from extensions import db
from models import Usuarios, Escolas, Ano_escolar, SimuladosGerados, Disciplinas, DesempenhoSimulado

# Dicionário de meses
MESES_NOMES[int(mes)]= {
    1: 'Janeiro',
    2: 'Fevereiro',
    3: 'Março',
    4: 'Abril',
    5: 'Maio',
    6: 'Junho',
    7: 'Julho',
    8: 'Agosto',
    9: 'Setembro',
    10: 'Outubro',
    11: 'Novembro',
    12: 'Dezembro'
}

# Registrando o Blueprint com url_prefix
secretaria_educacao_bp = Blueprint('secretaria_educacao', __name__, url_prefix='/secretaria_educacao')

def get_db():
    return db

@secretaria_educacao_bp.teardown_app_request
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def get_nome_mes(mes_id):
    meses = {
        1: 'Janeiro',
        2: 'Fevereiro',
        3: 'Março',
        4: 'Abril',
        5: 'Maio',
        6: 'Junho',
        7: 'Julho',
        8: 'Agosto',
        9: 'Setembro',
        10: 'Outubro',
        11: 'Novembro',
        12: 'Dezembro'
    }
    return meses.get(mes_id, '-')

# @secretaria_educacao_bp.route('/criar_simulado', methods=['GET'])
# @login_required
# def criar_simulado():
#     """Cria um novo simulado."""
#     if current_user.tipo_usuario_id not in [5, 6]:  # Verifica se é secretaria
#         flash("Acesso não autorizado.", "danger")
#         return redirect(url_for("index"))
    
#     db = get_db()
#     # Buscar disciplinas
#     disciplinas = db.execute('SELECT * FROM disciplinas ORDER BY nome').fetchall()
#     # Buscar todas as séries
#     Ano_escolar = db.execute('SELECT * FROM Ano_escolar ORDER BY nome').fetchall()
#     # Buscar meses
#     meses = db.execute('SELECT * FROM meses ORDER BY id').fetchall()
    
#     return render_template('secretaria_educacao/criar_simulado.html', 
#                          disciplinas=disciplinas,
#                          Ano_escolar=Ano_escolar,
#                          meses=meses)

@secretaria_educacao_bp.route('/criar_simulado', methods=['GET'])
@login_required
def criar_simulado():
    """Cria um novo simulado ou edita um existente."""
    if current_user.tipo_usuario_id not in [5, 6]:  # Verifica se é secretaria
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    db = get_db()
    # Buscar disciplinas
    disciplinas = db.execute('SELECT * FROM disciplinas ORDER BY nome').fetchall()
    # Buscar todas as séries
    Ano_escolar = db.execute('SELECT * FROM Ano_escolar ORDER BY nome').fetchall()
    # Buscar meses
    meses = db.execute('SELECT * FROM meses ORDER BY id').fetchall()
    
    # Verificar se é edição
    simulado_id = request.args.get('id', type=int)
    simulado_data = None
    questoes_selecionadas = []
    
    if simulado_id:
        # Buscar dados do simulado
        cursor = db.cursor()
        cursor.execute("""
            SELECT 
                sgs.id,
                sgs.disciplina_id,
                sgs.ano_escolar_id,
                sgs.mes_id,
                sgs.status,
                d.nome as disciplina_nome,
                s.nome Ano_escolar_nome,
                m.nome as mes_nome
            FROM simulados_gerados sgs
            JOIN disciplinas d ON d.id = sgs.disciplina_id
            JOIN Ano_escolar s ON s.id = sgs.ano_escolar_id
            JOIN meses m ON m.id = sgs.mes_id
            WHERE sgs.id = ?
        """, [simulado_id])
        simulado = cursor.fetchone()
        
        if simulado:
            # Verificar se o status é 'gerado'
            if simulado['status'] != 'gerado':
                flash('Não é possível editar um simulado que já foi enviado. Cancele o envio primeiro.', 'warning')
                return redirect(url_for('secretaria_educacao.meus_simulados'))
            
            # Converter a tupla em um dicionário com todos os dados necessários
            simulado_data = {
                'id': simulado['id'],
                'disciplina_id': simulado['disciplina_id'],
                'ano_escolar_id': simulado['ano_escolar_id'],
                'mes_id': simulado['mes_id'],
                'status': simulado['status'],
                'disciplina_nome': simulado['disciplina_nome'],
                'Ano_escolar_nome': simulado['Ano_escolar_nome'],
                'mes_nome': simulado['mes_nome']
            }
            
            # Buscar questões do simulado
            cursor.execute("""
                SELECT 
                    bq.id,
                    bq.questao,
                    bq.alternativa_a,
                    bq.alternativa_b,
                    bq.alternativa_c,
                    bq.alternativa_d,
                    bq.alternativa_e,
                    bq.questao_correta,
                    bq.assunto,
                    bq.disciplina_id,
                    bq.ano_escolar_id,
                    bq.mes_id
                FROM simulado_questoes sqs
                JOIN banco_questoes bq ON bq.id = sqs.questao_id
                WHERE sqs.simulado_id = ?
                ORDER BY sqs.id
            """, [simulado_id])
            questoes_selecionadas = cursor.fetchall()
    
    return render_template('secretaria_educacao/criar_simulado.html', 
                         disciplinas=disciplinas,
                         Ano_escolar=Ano_escolar,
                         meses=meses,
                         simulado=simulado_data,
                         questoes_selecionadas=questoes_selecionadas)

@secretaria_educacao_bp.route('/salvar_simulado', methods=['POST'])
@login_required
def salvar_simulado():
    if current_user.tipo_usuario_id not in [5, 6]:  # Mudei de 5 para 2
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        # Pegar dados do formulário
        ano_escolar_id = request.form.get('ano_escolar_id')
        mes_id = request.form.get('mes_id')
        disciplina_id = request.form.get('disciplina_id')
        questoes = request.form.getlist('questoes[]')  # Lista de IDs das questões
        simulado_id = request.form.get('simulado_id')
        
        if not all([ano_escolar_id, mes_id, disciplina_id]) or not questoes:
            return jsonify({'success': False, 'message': 'Dados incompletos'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        if simulado_id:  # Edição
            # Atualizar simulado existente
            cursor.execute("""
                UPDATE simulados_gerados 
                SET ano_escolar_id = ?, mes_id = ?, disciplina_id = ?
                WHERE id = ? AND status = 'gerado'
            """, (ano_escolar_id, mes_id, disciplina_id, simulado_id))
            
            # Remover questões antigas
            cursor.execute("DELETE FROM simulado_questoes WHERE simulado_id = ?", [simulado_id])
            
            # Inserir novas questões
            for questao_id in questoes:
                cursor.execute(
                    "INSERT INTO simulado_questoes (simulado_id, questao_id) VALUES (?, ?)",
                    (simulado_id, questao_id)
                )
        else:  # Novo simulado
            # Criar novo simulado
            cursor.execute("""
                INSERT INTO simulados_gerados (ano_escolar_id, mes_id, disciplina_id, status, data_envio)
                VALUES (?, ?, ?, 'gerado', CURRENT_TIMESTAMP)
            """, (ano_escolar_id, mes_id, disciplina_id))
            simulado_id = cursor.lastrowid
            
            # Inserir questões do simulado
            for questao_id in questoes:
                cursor.execute(
                    "INSERT INTO simulado_questoes (simulado_id, questao_id) VALUES (?, ?)",
                    (simulado_id, questao_id)
                )
        
        db.commit()
        return jsonify({'success': True, 'message': 'Simulado salvo com sucesso!', 'simulado_id': simulado_id})
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao salvar simulado: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao salvar simulado'}), 500

# @secretaria_educacao_bp.route('/buscar_questoes', methods=['GET'])
# @login_required
# def buscar_questoes():
#     if current_user.tipo_usuario_id not in [5, 6]:
#         return jsonify({'error': 'Acesso não autorizado'}), 403

#     ano_escolar_id = request.args.get('ano_escolar_id', '')
#     disciplina_id = request.args.get('disciplina_id', '')
#     assunto = request.args.get('assunto', '')
    
#     db = get_db()
#     cursor = db.cursor()

#     query = """
#         SELECT 
#             bq.*,
#             d.nome as disciplina_nome,
#             s.nome Ano_escolar_nome
#         FROM banco_questoes bq
#         LEFT JOIN Ano_escolar s ON bq.ano_escolar_id = s.id
#         LEFT JOIN disciplinas d ON bq.disciplina_id = d.id
#         WHERE 1=1
#     """
#     params = []

#     if ano_escolar_id:
#         query += " AND bq.ano_escolar_id = ?"
#         params.append(ano_escolar_id)
    
#     if disciplina_id:
#         query += " AND bq.disciplina_id = ?"
#         params.append(disciplina_id)
    
#     if assunto:
#         query += " AND bq.assunto LIKE ?"
#         params.append(f"%{assunto}%")

#     query += " ORDER BY bq.id DESC"
    
#     try:
#         cursor.execute(query, params)
#         questoes = cursor.fetchall()

#         questoes_list = []
#         for q in questoes:
#             questao = {
#                 'id': q[0],
#                 'questao': q[1],
#                 'alternativa_a': q[2],
#                 'alternativa_b': q[3],
#                 'alternativa_c': q[4],
#                 'alternativa_d': q[5],
#                 'alternativa_e': q[6],
#                 'questao_correta': q[7],
#                 'disciplina_id': q[8],
#                 'assunto': q[9],
#                 'ano_escolar_id': q[10],
#                 'mes_id': q[11],
#                 'disciplina_nome': q[12],
#                 'Ano_escolar_nome': q[13]
#             }
#             questoes_list.append(questao)

#         return jsonify(questoes_list)
#     except Exception as e:
#         print(f"Erro ao buscar questões: {str(e)}")
#         return jsonify({'error': 'Erro ao buscar questões'}), 500

@secretaria_educacao_bp.route('/buscar_questoes')
def buscar_questoes():
    ano_escolar_id = request.args.get('ano_escolar_id')
    disciplina_id = request.args.get('disciplina_id')
    assunto = request.args.get('assunto', '')
    
    query = """
        SELECT 
            bq.*,
            d.nome as disciplina_nome,
            s.nome Ano_escolar_nome,
            (
                SELECT COUNT(DISTINCT sq.simulado_id)
                FROM simulado_questoes sq
                WHERE sq.questao_id = bq.id
            ) as total_usos
        FROM banco_questoes bq
        JOIN disciplinas d ON d.id = bq.disciplina_id
        JOIN Ano_escolar s ON s.id = bq.ano_escolar_id
        WHERE 1=1
    """
    params = []
    
    if ano_escolar_id:
        query += " AND bq.ano_escolar_id = ?"
        params.append(ano_escolar_id)
    
    if disciplina_id:
        query += " AND bq.disciplina_id = ?"
        params.append(disciplina_id)
    
    if assunto:
        query += " AND bq.assunto LIKE ?"
        params.append(f"%{assunto}%")
    
    query += " ORDER BY bq.id DESC"
    
    db = get_db()
    questoes = db.execute(query, params).fetchall()
    return jsonify([dict(q) for q in questoes])

@secretaria_educacao_bp.route('/gerar_simulado_automatico', methods=['POST'])
@login_required
def gerar_simulado_automatico():
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
        
    try:
        data = request.get_json()
        ano_escolar_id = data.get('ano_escolar_id')
        disciplina_id = data.get('disciplina_id')
        quantidade = int(data.get('quantidade', 10))
        
        if not ano_escolar_id or not disciplina_id:
            return jsonify({'success': False, 'message': 'Ano Escolar e disciplina são obrigatórios'}), 400
        
        db = get_db()
        questoes = db.execute(
            "SELECT id FROM banco_questoes WHERE ano_escolar_id = ? AND disciplina_id = ? ORDER BY RANDOM() LIMIT ?",
            [ano_escolar_id, disciplina_id, quantidade]
        ).fetchall()
        
        questoes_ids = [q['id'] for q in questoes]
        if not questoes_ids:
            return jsonify({'success': False, 'message': 'Nenhuma questão encontrada'}), 404
        
        return jsonify({'success': True, 'questoes': questoes_ids})
        
    except Exception as e:
        print(f"Erro ao gerar simulado automático: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao gerar simulado automático'}), 500




# @secretaria_educacao_bp.route('/salvar_simulado', methods=['POST'])
# @login_required
# def salvar_simulado():
#     if current_user.tipo_usuario_id not in [5, 6]:
#         return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
#     try:
#         # Pegar dados do formulário
#         ano_escolar_id = request.form.get('ano_escolar_id')
#         mes_id = request.form.get('mes_id')
#         disciplina_id = request.form.get('disciplina_id')
#         questoes = request.form.getlist('questoes[]')  # Lista de IDs das questões
        
#         if not all([ano_escolar_id, mes_id, disciplina_id, questoes]):
#             return jsonify({'success': False, 'message': 'Dados incompletos'}), 400
        
#         # Criar novo simulado
#         query = """
#             INSERT INTO simulados_gerados (ano_escolar_id, mes_id, disciplina_id, status, data_envio)
#             VALUES (?, ?, ?, 'gerado', CURRENT_TIMESTAMP)
#         """
#         cursor = get_db().cursor()
#         cursor.execute(query, (ano_escolar_id, mes_id, disciplina_id))
#         simulado_id = cursor.lastrowid
        
#         # Inserir questões do simulado
#         for questao_id in questoes:
#             cursor.execute(
#                 "INSERT INTO simulado_questoes (simulado_id, questao_id) VALUES (?, ?)",
#                 (simulado_id, questao_id)
#             )
        
#         get_db().commit()
#         return jsonify({'success': True, 'message': 'Simulado criado com sucesso!', 'simulado_id': simulado_id})
        
#     except Exception as e:
#         get_db().rollback()
#         print(f"Erro ao salvar simulado: {str(e)}")
#         return jsonify({'success': False, 'message': 'Erro ao salvar simulado'}), 500

@secretaria_educacao_bp.route('/banco_questoes', methods=['GET', 'POST'])
@login_required
def banco_questoes():
    if current_user.tipo_usuario_id not in [5, 6]:
        return redirect(url_for('index'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Buscar todas as questões com informações relacionadas
    cursor.execute("""
        SELECT 
            q.id,
            q.questao,
            q.alternativa_a,
            q.alternativa_b,
            q.alternativa_c,
            q.alternativa_d,
            q.alternativa_e,
            q.questao_correta,
            q.disciplina_id,
            q.assunto,
            q.ano_escolar_id,
            q.mes_id,
            q.data_criacao,
            d.nome as disciplina_nome,
            s.nome Ano_escolar_nome
        FROM banco_questoes q
        LEFT JOIN disciplinas d ON q.disciplina_id = d.id
        LEFT JOIN Ano_escolar s ON q.ano_escolar_id = s.id
        ORDER BY q.id DESC
    """)
    questoes_raw = cursor.fetchall()
    
    # Buscar disciplinas e séries para os selects
    cursor.execute("SELECT * FROM disciplinas ORDER BY nome")
    disciplinas = cursor.fetchall()
    
    cursor.execute("SELECT * FROM Ano_escolar ORDER BY nome")
    Ano_escolar = cursor.fetchall()
    
    # Processar as questões para incluir nomes
    questoes = []
    for q in questoes_raw:
        mes_nome = get_nome_mes(q[11]) if q[11] else None
        questao = {
            'id': q[0],
            'questao': q[1],
            'alternativa_a': q[2],
            'alternativa_b': q[3],
            'alternativa_c': q[4],
            'alternativa_d': q[5],
            'alternativa_e': q[6],
            'questao_correta': q[7],
            'disciplina_id': q[8],
            'assunto': q[9],
            'ano_escolar_id': q[10],
            'mes_id': q[11],
            'data_criacao': q[12],
            'disciplina_nome': q[13],
            'Ano_escolar_nome': q[14]
        }
        questoes.append(questao)
    
    return render_template('secretaria_educacao/banco_questoes.html', 
                         questoes=questoes,
                         disciplinas=disciplinas,
                         Ano_escolar=Ano_escolar)

@secretaria_educacao_bp.route('/relatorios_dashboard', methods=['GET'])
@login_required
def relatorios_dashboard():
    if current_user.tipo_usuario_id not in [5, 6]:  # Apenas para Secretaria de Educação
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    codigo_ibge = current_user.codigo_ibge

    # Desempenho geral
    from sqlalchemy import func, desc, case

    desempenho_geral = db.session.query(
        func.avg(DesempenhoSimulado.desempenho).label('desempenho_geral')
    ).join(
        Usuarios, DesempenhoSimulado.aluno_id == Usuarios.id
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4
    ).scalar() or 0

    # Melhor escola
    melhor_escola = db.session.query(
        Escolas.nome_da_escola,
        func.avg(DesempenhoSimulado.desempenho).label('media_escola')
    ).join(
        Usuarios, DesempenhoSimulado.aluno_id == Usuarios.id
    ).join(
        Escolas, Usuarios.escola_id == Escolas.id
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4,
        Escolas.codigo_ibge == codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).order_by(
        desc('media_escola')
    ).first() or ("Nenhuma escola", 0)

    # Desempenho mensal
    desempenho_mensal = db.session.query(
        func.extract('month', DesempenhoSimulado.data_resposta).label('mes'),
        func.avg(DesempenhoSimulado.desempenho).label('media_desempenho')
    ).join(
        Usuarios, DesempenhoSimulado.aluno_id == Usuarios.id
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4
    ).group_by(
        'mes'
    ).order_by(
        'mes'
    ).all()

    # Converter números dos meses para nomes
    desempenho_mensal = [(MESES[int(mes)], media) for mes, media in desempenho_mensal]

    # Ranking de escolas
    ranking_escolas = db.session.query(
        Escolas.nome_da_escola,
        func.avg(DesempenhoSimulado.desempenho).label('media_escola')
    ).join(
        Usuarios, DesempenhoSimulado.aluno_id == Usuarios.id
    ).join(
        Escolas, Usuarios.escola_id == Escolas.id
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4,
        Escolas.codigo_ibge == codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).order_by(
        desc('media_escola')
    ).all()

    # Ranking dos 5 melhores alunos por ano escolar
    ranking_alunos = db.session.query(
        Ano_escolar.nome.label('ano_escolar'),
        Usuarios.nome.label('aluno'),
        func.avg(DesempenhoSimulado.desempenho).label('media_aluno')
    ).join(
        Usuarios, DesempenhoSimulado.aluno_id == Usuarios.id
    ).join(
        Ano_escolar, Usuarios.ano_escolar_id == Ano_escolar.id
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4
    ).group_by(
        Ano_escolar.id, Ano_escolar.nome, Usuarios.id, Usuarios.nome
    ).order_by(
        Ano_escolar.id,
        desc('media_aluno')
    ).limit(5).all()

    # Contagem de alunos por faixa de desempenho
    faixas = db.session.query(
        func.count(case((DesempenhoSimulado.desempenho.between(0, 20), 1))).label('faixa_0_20'),
        func.count(case((DesempenhoSimulado.desempenho.between(21, 40), 1))).label('faixa_21_40'),
        func.count(case((DesempenhoSimulado.desempenho.between(41, 60), 1))).label('faixa_41_60'),
        func.count(case((DesempenhoSimulado.desempenho.between(61, 80), 1))).label('faixa_61_80'),
        func.count(case((DesempenhoSimulado.desempenho.between(81, 100), 1))).label('faixa_81_100')
    ).join(
        Usuarios, DesempenhoSimulado.aluno_id == Usuarios.id
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4
    ).first()

    return render_template(
        'secretaria_educacao/relatorios_dashboard.html',
        desempenho_geral=desempenho_geral,
        melhor_escola=melhor_escola,
        desempenho_mensal=desempenho_mensal,
        ranking_escolas=ranking_escolas,
        ranking_alunos=ranking_alunos,
        faixa_0_20=faixas[0] if faixas else 0,
        faixa_21_40=faixas[1] if faixas else 0,
        faixa_41_60=faixas[2] if faixas else 0,
        faixa_61_80=faixas[3] if faixas else 0,
        faixa_81_100=faixas[4] if faixas else 0
    )

@secretaria_educacao_bp.route('/relatorios_gerenciais')
@login_required
def relatorios_gerenciais():
    """Página de relatórios gerenciais."""
    if current_user.tipo_usuario_id not in [5, 6]:  # Verifica se é secretaria
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    return render_template('secretaria_educacao/relatorios_gerenciais.html')

@secretaria_educacao_bp.route("/portal_secretaria_educacao", methods=["GET", "POST"])
@login_required
def portal_secretaria_educacao():
    if current_user.tipo_usuario_id not in [5, 6]:  # Verifica se é uma Secretaria de Educação
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    # Buscar escolas que têm o mesmo codigo_ibge
    escolas = Escolas.query.filter_by(codigo_ibge=current_user.codigo_ibge).all()
    total_escolas = len(escolas)

    # Buscar o número de alunos na mesma codigo_ibge
    numero_alunos = Usuarios.query.filter_by(
        tipo_usuario_id=4,
        codigo_ibge=current_user.codigo_ibge
    ).count()

    # Buscar o número de simulados gerados na mesma codigo_ibge
    numero_simulados_gerados = db.session.query(SimuladosGerados)\
        .join(Usuarios, SimuladosGerados.ano_escolar_id == Usuarios.ano_escolar_id)\
        .filter(Usuarios.codigo_ibge == current_user.codigo_ibge)\
        .count()

    # Calcular a média geral de desempenho dos simulados respondidos na mesma codigo_ibge
    media_query = db.session.query(db.func.avg(DesempenhoSimulado.desempenho))\
        .join(Usuarios, DesempenhoSimulado.aluno_id == Usuarios.id)\
        .filter(Usuarios.codigo_ibge == current_user.codigo_ibge)\
        .scalar()
    media_geral = media_query or 0

    # Buscar simulados já gerados
    simulados_gerados = db.session.query(
        SimuladosGerados.id,
        Ano_escolar.nome.label('Ano_escolar_nome'),
        SimuladosGerados.mes_id,
        Disciplinas.nome.label('disciplina_nome'),
        SimuladosGerados.data_envio,
        SimuladosGerados.status
    ).join(Ano_escolar, SimuladosGerados.ano_escolar_id == Ano_escolar.id)\
     .join(Disciplinas, SimuladosGerados.disciplina_id == Disciplinas.id)\
     .order_by(SimuladosGerados.data_envio.desc())\
     .all()

    return render_template(
        "secretaria_educacao/portal_secretaria_educacao.html",
        simulados_gerados=simulados_gerados,
        total_escolas=total_escolas,
        total_alunos=numero_alunos,
        total_simulados=numero_simulados_gerados,
        media_geral=media_geral
    )

@secretaria_educacao_bp.route('/importar_questoes', methods=['POST'])
@login_required
def importar_questoes():
    if current_user.tipo_usuario_id not in [5, 6]:  # Verifica se é uma Secretaria de Educação
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('secretaria_educacao.portal_secretaria_educacao'))

    arquivo = request.files['arquivo']
    if arquivo.filename == '':
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('secretaria_educacao.portal_secretaria_educacao'))

    if arquivo and arquivo.filename.endswith('.pdf'):
        # Aqui você pode implementar a lógica para processar o arquivo PDF
        # Por exemplo, extrair texto, identificar questões, etc.
        try:
            # Salvar o arquivo temporariamente
            filename = secure_filename(arquivo.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            arquivo.save(filepath)

            # Processar o arquivo (implementar lógica específica)
            # ...

            flash('Arquivo processado com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao processar arquivo: {str(e)}', 'danger')
        finally:
            # Limpar arquivo temporário se existir
            if os.path.exists(filepath):
                os.remove(filepath)
    else:
        flash('Formato de arquivo inválido. Por favor, envie um arquivo PDF.', 'danger')

    return redirect(url_for('secretaria_educacao.portal_secretaria_educacao'))

@secretaria_educacao_bp.route('/meus_simulados', methods=['GET'])
@login_required
def meus_simulados():
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    db = get_db()
    cursor = db.cursor()

    # Buscar simulados gerados pela secretaria
    cursor.execute("""
        SELECT sg.*, s.nome Ano_escolar_nome, m.nome as mes_nome,
               d.nome as disciplina_nome,
               COUNT(DISTINCT r.aluno_id) as total_responderam,
               COUNT(DISTINCT sq.questao_id) as total_questoes
        FROM simulados_gerados sg
        JOIN Ano_escolar s ON sg.ano_escolar_id = s.id
        JOIN meses m ON sg.mes_id = m.id
        JOIN disciplinas d ON sg.disciplina_id = d.id
        LEFT JOIN respostas_simulado r ON sg.id = r.simulado_id
        LEFT JOIN simulado_questoes sq ON sg.id = sq.simulado_id
        GROUP BY sg.id
        ORDER BY sg.data_envio DESC
    """)
    simulados = cursor.fetchall()
    
    return render_template(
        'secretaria_educacao/meus_simulados.html',
        simulados=simulados
    )

@secretaria_educacao_bp.route('/enviar_simulado/<int:simulado_id>', methods=['POST'])
@login_required
def enviar_simulado(simulado_id):
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'})
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Verificar se o simulado existe e pertence ao usuário
        cursor.execute("""
            SELECT status
            FROM simulados_gerados
            WHERE id = ?
        """, (simulado_id,))
        simulado = cursor.fetchone()
        
        if not simulado:
            return jsonify({'success': False, 'message': 'Simulado não encontrado'})
        
        if simulado[0] != 'gerado':
            return jsonify({'success': False, 'message': 'Este simulado já foi enviado'})
        
        # Atualizar status do simulado
        cursor.execute("""
            UPDATE simulados_gerados
            SET status = 'enviado',
                data_envio = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (simulado_id,))
        
        db.commit()
        return jsonify({'success': True, 'message': 'Simulado enviado com sucesso'})
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao enviar simulado: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao enviar simulado: {str(e)}'})

@secretaria_educacao_bp.route('/visualizar_simulado/<int:simulado_id>')
@login_required
def visualizar_simulado(simulado_id):
    if current_user.tipo_usuario_id not in [5, 6]:
        flash('Acesso não autorizado', 'danger')
        return redirect(url_for('secretaria_educacao.portal_secretaria_educacao'))
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Buscar dados do simulado
        cursor.execute("""
            SELECT 
                sg.*,
                s.nome Ano_escolar_nome,
                d.nome as disciplina_nome,
                m.nome as mes_nome
            FROM simulados_gerados sg
            JOIN Ano_escolar s ON sg.ano_escolar_id = s.id
            JOIN disciplinas d ON sg.disciplina_id = d.id
            JOIN meses m ON sg.mes_id = m.id
            WHERE sg.id = ?
        """, (simulado_id,))
        simulado = cursor.fetchone()
        
        if not simulado:
            flash('Simulado não encontrado', 'danger')
            return redirect(url_for('secretaria_educacao.meus_simulados'))
        
        # Buscar as questões através da tabela simulado_questoes
        cursor.execute("""
            SELECT bq.*
            FROM banco_questoes bq
            INNER JOIN simulado_questoes sq ON sq.questao_id = bq.id
            WHERE sq.simulado_id = ?
        """, (simulado_id,))
        questoes = cursor.fetchall()
        
        if not questoes:
            flash('Nenhuma questão encontrada para este simulado', 'warning')
            return redirect(url_for('secretaria_educacao.meus_simulados'))
        
        # Converter para dicionário
        simulado_dict = {
            'id': simulado[0],
            'ano_escolar_id': simulado[1],
            'mes_id': simulado[2],
            'disciplina_id': simulado[3],
            'status': simulado[4],
            'data_envio': simulado[5],
            'Ano_escolar_nome': simulado[6],
            'disciplina_nome': simulado[7],
            'mes_nome': simulado[8]
        }
        
        questoes_list = []
        for q in questoes:
            questoes_list.append({
                'id': q[0],
                'questao': q[1],
                'alternativa_a': q[2],
                'alternativa_b': q[3],
                'alternativa_c': q[4],
                'alternativa_d': q[5],
                'alternativa_e': q[6],
                'questao_correta': q[7]
            })
        
        return render_template(
            'secretaria_educacao/visualizar_simulado.html',
            simulado=simulado_dict,
            questoes=questoes_list
        )
        
    except Exception as e:
        print(f"Erro ao visualizar simulado: {str(e)}")
        flash('Erro ao visualizar simulado', 'danger')
        return redirect(url_for('secretaria_educacao.meus_simulados'))

@secretaria_educacao_bp.route('/salvar_edicao_simulado/<int:simulado_id>', methods=['POST'])
@login_required
def salvar_edicao_simulado(simulado_id):
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'})
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Obter dados do formulário
        perguntas = request.form.to_dict()
        
        # Para cada pergunta atualizada
        for index, dados in enumerate(perguntas.values()):
            cursor.execute("""
                UPDATE questoes
                SET questao = ?,
                    alternativa_a = ?,
                    alternativa_b = ?,
                    alternativa_c = ?,
                    alternativa_d = ?,
                    alternativa_e = ?,
                    questao_correta = ?
                WHERE id = (
                    SELECT questao_id
                    FROM simulado_questoes
                    WHERE simulado_id = ?
                    LIMIT 1 OFFSET ?
                )
            """, (
                dados['pergunta'],
                dados['alternativa_a'],
                dados['alternativa_b'],
                dados['alternativa_c'],
                dados['alternativa_d'],
                dados['alternativa_e'],
                dados['questao_correta'],
                simulado_id,
                index
            ))
        
        db.commit()
        return jsonify({'success': True, 'message': 'Simulado atualizado com sucesso'})
        
    except Exception as e:
        print(f"Erro ao salvar edição do simulado: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao salvar edição do simulado'})

@secretaria_educacao_bp.route('/excluir_questao/<int:questao_id>', methods=['POST'])
@login_required
def excluir_questao(questao_id):
    if current_user.tipo_usuario_id not in [5, 6]:  # Verifica se é uma Secretaria de Educação
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403

    try:
        db = get_db()
        
        # Verifica se a questão existe
        questao = db.execute('SELECT id FROM banco_questoes WHERE id = ?', (questao_id,)).fetchone()
        if not questao:
            return jsonify({'success': False, 'message': 'Questão não encontrada'}), 404
            
        # Exclui a questão
        db.execute('DELETE FROM banco_questoes WHERE id = ?', (questao_id,))
        db.commit()
        
        return jsonify({'success': True, 'message': 'Questão excluída com sucesso'})
    except Exception as e:
        db.rollback()  # Reverte a transação em caso de erro
        print(f"Erro ao excluir questão: {str(e)}")  # Log do erro
        return jsonify({'success': False, 'message': f'Erro ao excluir questão: {str(e)}'}), 500

@secretaria_educacao_bp.route('/buscar_questao/<int:questao_id>', methods=['GET'])
@login_required
def buscar_questao(questao_id):
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Buscar questão
        cursor.execute("""
            SELECT q.*, d.nome as disciplina_nome, s.nome Ano_escolar_nome
            FROM banco_questoes q
            LEFT JOIN disciplinas d ON q.disciplina_id = d.id
            LEFT JOIN Ano_escolar s ON q.ano_escolar_id = s.id
            WHERE q.id = ?
        """, (questao_id,))
        
        questao = cursor.fetchone()
        
        if questao is None:
            return jsonify({'success': False, 'message': 'Questão não encontrada'}), 404
        
        # Converter o número do mês para nome
        mes_nome = get_nome_mes(questao[11]) if questao[11] else None
        
        return jsonify({
            'success': True,
            'questao': {
                'id': questao[0],
                'questao': questao[1],
                'alternativa_a': questao[2],
                'alternativa_b': questao[3],
                'alternativa_c': questao[4],
                'alternativa_d': questao[5],
                'alternativa_e': questao[6],
                'questao_correta': questao[7],
                'disciplina_id': questao[8],
                'disciplina_nome': questao[12],  # Agora é o nome do componente
                'assunto': questao[9],
                'ano_escolar_id': questao[10],
                'Ano_escolar_nome': questao[13],  # Agora é o nome do ano escolar
                'mes_id': questao[11],
                'mes_nome': mes_nome
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@secretaria_educacao_bp.route('/atualizar_questao/<int:questao_id>', methods=['POST'])
@login_required
def atualizar_questao(questao_id):
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Pegar os dados do formulário
        questao = request.form.get('questao')
        alternativa_a = request.form.get('alternativa_a')
        alternativa_b = request.form.get('alternativa_b')
        alternativa_c = request.form.get('alternativa_c')
        alternativa_d = request.form.get('alternativa_d')
        alternativa_e = request.form.get('alternativa_e')
        questao_correta = request.form.get('questao_correta')
        disciplina_id = request.form.get('disciplina_id')
        assunto = request.form.get('assunto')
        
        # Trata campos opcionais
        ano_escolar_id = request.form.get('ano_escolar_id')
        mes_id = request.form.get('mes_id')
        
        # Converte para None se vazio
        ano_escolar_id = None if not ano_escolar_id else int(ano_escolar_id)
        mes_id = None if not mes_id else int(mes_id)
        
        # Validate required fields
        if not all([questao, alternativa_a, alternativa_b, alternativa_c, alternativa_d, 
                   questao_correta, disciplina_id, assunto]):
            return jsonify({'success': False, 'message': 'Por favor, preencha todos os campos obrigatórios.'}), 400

        # Validate that the correct answer exists
        if questao_correta == 'E' and not alternativa_e:
            return jsonify({'success': False, 'message': 'A alternativa E foi marcada como correta, mas não foi preenchida.'}), 400

        # Atualizar questão
        cursor.execute("""
            UPDATE banco_questoes 
            SET questao = ?,
                alternativa_a = ?,
                alternativa_b = ?,
                alternativa_c = ?,
                alternativa_d = ?,
                alternativa_e = ?,
                questao_correta = ?,
                disciplina_id = ?,
                assunto = ?,
                ano_escolar_id = ?,
                mes_id = ?
            WHERE id = ?
        """, (questao, alternativa_a, alternativa_b, alternativa_c, alternativa_d,
              alternativa_e, questao_correta, disciplina_id, assunto, ano_escolar_id, mes_id, questao_id))
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Questão atualizada com sucesso!'
        })
    except Exception as e:
        print(f"Erro ao atualizar questão: {str(e)}")  # Log do erro
        return jsonify({'success': False, 'message': str(e)}), 500

@secretaria_educacao_bp.route('/relatorio_rede_municipal')
@login_required
def relatorio_rede_municipal():
    """Relatório de desempenho da rede municipal."""
    if current_user.tipo_usuario_id not in [5, 6]:  # Verifica se é secretaria
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    codigo_ibge = current_user.codigo_ibge
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    from sqlalchemy import func, and_, extract, case

    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Buscar dados gerais
    total_escolas = db.session.query(
        func.count(Escolas.id)
    ).filter(
        Escolas.codigo_ibge == codigo_ibge
    ).scalar()

    total_alunos = db.session.query(
        func.count(Usuarios.id)
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4
    ).scalar()
    
    # Total de simulados com filtro de data
    total_simulados = db.session.query(
        func.count(func.distinct(DesempenhoSimulado.simulado_id))
    ).filter(
        DesempenhoSimulado.codigo_ibge == codigo_ibge,
        *data_condition
    ).scalar()
    
    # Buscar dados de cada escola
    escolas_query = db.session.query(
        Escolas.id,
        Escolas.nome_da_escola.label('nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.escola_id == Escolas.id,
            Usuarios.tipo_usuario_id == 4,
            Usuarios.codigo_ibge == codigo_ibge
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            DesempenhoSimulado.codigo_ibge == codigo_ibge,
            *data_condition
        )
    ).filter(
        Escolas.codigo_ibge == codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).order_by(
        db.desc('media')
    )
    
    escolas = [dict(zip(['id', 'nome', 'total_alunos', 'alunos_ativos', 'media'], escola)) 
               for escola in escolas_query.all()]
    
    # Calcular totais
    total_alunos_ativos = sum(escola['alunos_ativos'] for escola in escolas)
    soma_medias_ponderadas = sum(escola['media'] * escola['alunos_ativos'] for escola in escolas)
    media_geral = soma_medias_ponderadas / total_alunos_ativos if total_alunos_ativos > 0 else 0.0
    
    # Buscar desempenho por disciplina
    disciplinas_query = db.session.query(
        Disciplinas.id,
        Disciplinas.nome.label('disciplina'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_questoes'),
        func.round(func.avg(DesempenhoSimulado.desempenho), 1).label('media_acertos')
    ).outerjoin(
        SimuladosGerados, SimuladosGerados.disciplina_id == Disciplinas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.simulado_id == SimuladosGerados.id,
            DesempenhoSimulado.codigo_ibge == codigo_ibge,
            *data_condition
        )
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        db.desc('media_acertos')
    )
    
    disciplinas = [dict(zip(['id', 'disciplina', 'total_alunos', 'total_questoes', 'media_acertos'], disc)) 
                  for disc in disciplinas_query.all()]
    
    # Preparar dados para o gráfico de disciplinas
    disciplinas_nomes = [d['disciplina'] for d in disciplinas]
    disciplinas_medias = [float(d['media_acertos']) for d in disciplinas]
    
    # Buscar desempenho por série
    anos_escolares_query = db.session.query(
        Ano_escolar.id,
        Ano_escolar.nome.label('Ano_escolar_nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.ano_escolar_id == Ano_escolar.id,
            Usuarios.tipo_usuario_id == 4,
            Usuarios.codigo_ibge == codigo_ibge
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).filter(
        Ano_escolar.id.between(1, 9)
    ).group_by(
        Ano_escolar.id, Ano_escolar.nome
    ).order_by(
        Ano_escolar.id
    )
    
    Ano_escolar = [dict(zip(['id', 'Ano_escolar_nome', 'total_alunos', 'alunos_ativos', 'media'], Ano_escolar)) 
              for Ano_escolar in anos_escolares_query.all()]
    
    # Preparar dados para o gráfico de séries
    Ano_escolar_nomes = [s['Ano_escolar_nome'] for s in Ano_escolar]
    Ano_escolar_medias = [float(s['media']) for s in Ano_escolar]
    
    # Preparar dados para o gráfico de escolas
    escolas_nomes = [e['nome'] for e in escolas]
    escolas_medias = [float(e['media']) for e in escolas]
    
    return render_template(
        'secretaria_educacao/relatorio_rede_municipal.html',
        escolas=escolas,
        total_escolas=total_escolas,
        total_alunos=total_alunos,
        total_simulados=total_simulados,
        media_geral=f"{media_geral:.1f}",
        disciplinas=disciplinas,
        disciplinas_nomes=disciplinas_nomes,
        disciplinas_medias=disciplinas_medias,
        Ano_escolar=Ano_escolar,
        Ano_escolar_nomes=Ano_escolar_nomes,
        Ano_escolar_medias=Ano_escolar_medias,
        escolas_nomes=escolas_nomes,
        escolas_medias=escolas_medias,
        mes=mes,
        ano=ano
    )

@secretaria_educacao_bp.route('/relatorio_rede_municipal/export_pdf')
@login_required
def export_pdf_relatorio():
    """Exportar relatório em PDF."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    codigo_ibge = current_user.codigo_ibge
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    from sqlalchemy import func, and_, extract, case
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Buscar dados gerais
    total_escolas = db.session.query(
        func.count(Escolas.id)
    ).filter(
        Escolas.codigo_ibge == codigo_ibge
    ).scalar()

    total_alunos = db.session.query(
        func.count(Usuarios.id)
    ).filter(
        Usuarios.codigo_ibge == codigo_ibge,
        Usuarios.tipo_usuario_id == 4
    ).scalar()
    
    # Total de simulados com filtro de data
    total_simulados = db.session.query(
        func.count(func.distinct(DesempenhoSimulado.simulado_id))
    ).filter(
        DesempenhoSimulado.codigo_ibge == codigo_ibge,
        *data_condition
    ).scalar()
    
    # Buscar dados das escolas
    escolas_query = db.session.query(
        Escolas.id,
        Escolas.nome_da_escola.label('nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.escola_id == Escolas.id,
            Usuarios.tipo_usuario_id == 4,
            Usuarios.codigo_ibge == codigo_ibge
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            DesempenhoSimulado.codigo_ibge == codigo_ibge,
            *data_condition
        )
    ).filter(
        Escolas.codigo_ibge == codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).order_by(
        db.desc('media')
    )
    
    escolas = [dict(zip(['id', 'nome', 'total_alunos', 'alunos_ativos', 'media'], escola))
               for escola in escolas_query.all()]
    
    # Calcular média geral ponderada
    total_alunos_ativos = sum(escola['alunos_ativos'] for escola in escolas)
    soma_medias_ponderadas = sum(escola['media'] * escola['alunos_ativos'] for escola in escolas)
    media_geral = soma_medias_ponderadas / total_alunos_ativos if total_alunos_ativos > 0 else 0.0
    
    # Buscar desempenho por disciplina
    disciplinas_query = db.session.query(
        Disciplinas.id,
        Disciplinas.nome.label('disciplina'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_questoes'),
        func.round(func.avg(DesempenhoSimulado.desempenho), 1).label('media_acertos')
    ).outerjoin(
        SimuladosGerados, SimuladosGerados.disciplina_id == Disciplinas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.simulado_id == SimuladosGerados.id,
            DesempenhoSimulado.codigo_ibge == codigo_ibge,
            *data_condition
        )
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        db.desc('media_acertos')
    )
    
    disciplinas = [dict(zip(['id', 'disciplina', 'total_alunos', 'total_questoes', 'media_acertos'], disc))
                  for disc in disciplinas_query.all()]
    
    # Preparar dados para o gráfico de disciplinas
    disciplinas_nomes = [d['disciplina'] for d in disciplinas]
    disciplinas_medias = [float(d['media_acertos']) for d in disciplinas]
    
    # Renderizar o template HTML para PDF
    html_content = render_template(
        'secretaria_educacao/relatorio_rede_municipal_pdf.html',  # Template específico para PDF
        escolas=escolas,
        total_escolas=total_escolas,
        total_alunos=total_alunos,
        total_simulados=total_simulados,
        media_geral=f"{media_geral:.1f}",
        disciplinas=disciplinas,
        disciplinas_nomes=disciplinas_nomes,
        disciplinas_medias=disciplinas_medias,
        escolas_nomes=[e['nome'] for e in escolas],
        escolas_medias=[float(e['media']) for e in escolas],
        mes=mes,
        ano=ano
    )
    
    # Criar PDF usando WeasyPrint
    pdf = HTML(string=html_content).write_pdf()
    
    # Retornar o PDF como download
    return send_file(
        BytesIO(pdf),
        download_name='relatorio_rede_municipal.pdf',
        mimetype='application/pdf'
    )

@secretaria_educacao_bp.route('/relatorio_rede_municipal/export_excel')
@login_required
def export_excel_relatorio():
    """Exportar relatório em Excel."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    db = get_db()
    cursor = db.cursor()
    
    # Buscar o `codigo_ibge` do usuário
    cursor.execute("SELECT codigo_ibge FROM usuarios WHERE id = ?", (current_user.id,))
    codigo_ibge = cursor.fetchone()[0]
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = "strftime('%Y', data_resposta) = ?"
    data_params = [str(ano)]
    
    if mes:
        data_condition += " AND strftime('%m', data_resposta) = ?"
        data_params.append(f"{mes:02d}")
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Aba Visão Geral - Dados das escolas
    escolas_query = f'''
        SELECT 
            e.id,
            e.nome_da_escola as nome,
            COUNT(DISTINCT u.id) as total_alunos,
            COUNT(DISTINCT ds.aluno_id) as alunos_ativos,
            COALESCE(AVG(ds.desempenho), 0) as media
        FROM escolas e
        LEFT JOIN usuarios u ON u.escola_id = e.id AND u.tipo_usuario_id = 4 AND u.codigo_ibge = ?
        LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id AND {data_condition}
        WHERE e.codigo_ibge = ?
        GROUP BY e.id, e.nome_da_escola
        ORDER BY media DESC
    '''
    
    escolas = cursor.execute(escolas_query, [codigo_ibge] + data_params + [codigo_ibge]).fetchall()
    df_escolas = pd.DataFrame([dict(row) for row in escolas])
    if not df_escolas.empty:
        df_escolas = df_escolas.rename(columns={
            'nome': 'Escola',
            'total_alunos': 'Total de Alunos',
            'alunos_ativos': 'Alunos Ativos',
            'media': 'Média (%)'
        })
        df_escolas['Média (%)'] = df_escolas['Média (%)'].round(1)
        df_escolas.drop('id', axis=1, inplace=True)
    df_escolas.to_excel(writer, sheet_name='Visão Geral', index=False)
    
    # Aba Desempenho por Disciplina
    disciplinas_query = f'''
        WITH SimuladosDisciplinas AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                CASE 
                    WHEN ds.tipo_usuario_id = 5 THEN sg.disciplina_id
                    WHEN ds.tipo_usuario_id = 3 THEN sgp.disciplina_id
                END as disciplina_id
            FROM desempenho_simulado ds
            LEFT JOIN simulados_gerados sg ON sg.id = ds.simulado_id AND ds.tipo_usuario_id = 5
            LEFT JOIN simulados_gerados_professor sgp ON sgp.id = ds.simulado_id AND ds.tipo_usuario_id = 3
            WHERE ds.codigo_ibge = ? AND {data_condition}
        ),
        DesempenhoDisciplina AS (
            SELECT 
                d.nome as disciplina,
                COUNT(DISTINCT sd.aluno_id) as total_alunos,
                COUNT(DISTINCT sd.simulado_id) as total_questoes,
                ROUND(AVG(sd.desempenho), 1) as media_acertos
            FROM disciplinas d
            LEFT JOIN SimuladosDisciplinas sd ON sd.disciplina_id = d.id
            GROUP BY d.id, d.nome
            HAVING total_alunos > 0
            ORDER BY media_acertos DESC
        )
        SELECT *
        FROM DesempenhoDisciplina
    '''
    
    disciplinas = cursor.execute(disciplinas_query, [codigo_ibge] + data_params).fetchall()
    df_disciplinas = pd.DataFrame([dict(row) for row in disciplinas])
    if not df_disciplinas.empty:
        df_disciplinas = df_disciplinas.rename(columns={
            'disciplina': 'Disciplina',
            'total_alunos': 'Total de Alunos',
            'total_questoes': 'Total de Questões',
            'media_acertos': 'Média de Acertos (%)'
        })
    df_disciplinas.to_excel(writer, sheet_name='Desempenho por Disciplina', index=False)

    # Buscar todas as séries
    Ano_escolar = cursor.execute('''
        SELECT id, nome 
        FROM Ano_escolar 
        ORDER BY id
    ''').fetchall()

    # Para cada série, criar uma aba com desempenho por escola
    for Ano_escolar in Ano_escolar:
        ano_escolar_id = Ano_escolar['id']
        Ano_escolar_nome = Ano_escolar['nome']
        
        # Query para buscar dados da série específica
        query = f'''
            WITH DadosAno_escolar AS (
                SELECT 
                    e.id as escola_id,
                    e.nome_da_escola,
                    COUNT(DISTINCT u.id) as total_alunos,
                    COUNT(DISTINCT ds.aluno_id) as alunos_responderam,
                    COALESCE(AVG(ds.desempenho), 0) as media_geral
                FROM escolas e
                LEFT JOIN usuarios u ON u.escola_id = e.id 
                    AND u.tipo_usuario_id = 4 
                    AND u.ano_escolar_id = ? 
                    AND u.codigo_ibge = ?
                LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id 
                    AND {data_condition}
                WHERE e.codigo_ibge = ?
                GROUP BY e.id, e.nome_da_escola
            ),
            DesempenhoDisciplina AS (
                SELECT 
                    u.escola_id,
                    d.nome as disciplina,
                    COALESCE(AVG(ds.desempenho), 0) as media_disciplina
                FROM desempenho_simulado ds
                JOIN usuarios u ON u.id = ds.aluno_id 
                    AND u.ano_escolar_id = ? 
                    AND u.codigo_ibge = ?
                JOIN disciplinas d ON d.id = (
                    CASE 
                        WHEN ds.tipo_usuario_id = 5 THEN (SELECT disciplina_id FROM simulados_gerados WHERE id = ds.simulado_id)
                        WHEN ds.tipo_usuario_id = 3 THEN (SELECT disciplina_id FROM simulados_gerados_professor WHERE id = ds.simulado_id)
                    END
                )
                WHERE ds.codigo_ibge = ? 
                    AND {data_condition}
                GROUP BY u.escola_id, d.nome
            )
            SELECT 
                ds.*,
                dd.disciplina,
                dd.media_disciplina
            FROM DadosAno_escolar ds
            LEFT JOIN DesempenhoDisciplina dd ON dd.escola_id = ds.escola_id
            WHERE ds.total_alunos > 0
            ORDER BY ds.media_geral DESC
        '''
        
        params = [ano_escolar_id, codigo_ibge] + data_params + [codigo_ibge, ano_escolar_id, codigo_ibge, codigo_ibge] + data_params
        rows = cursor.execute(query, params).fetchall()
        
        # Transformar os dados em um DataFrame
        df_Ano_escolar = pd.DataFrame([dict(row) for row in rows])
        
        if not df_Ano_escolar.empty:
            # Renomear colunas para melhor legibilidade
            df_Ano_escolar = df_Ano_escolar.rename(columns={
                'nome_da_escola': 'Escola',
                'total_alunos': 'Total de Alunos',
                'alunos_responderam': 'Alunos Ativos',
                'media_geral': 'Média Geral (%)'
            })

            # Arredondar médias para uma casa decimal
            df_Ano_escolar['Média Geral (%)'] = df_Ano_escolar['Média Geral (%)'].round(1)
            
            # Pivotear a tabela para ter disciplinas como colunas
            if 'disciplina' in df_Ano_escolar.columns:
                df_pivot = df_Ano_escolar.pivot_table(
                    index=['escola_id', 'Escola', 'Total de Alunos', 'Alunos Ativos', 'Média Geral (%)'],
                    columns='disciplina',
                    values='media_disciplina',
                    aggfunc='first'
                ).reset_index()
                
                # Arredondar médias das disciplinas
                for col in df_pivot.columns:
                    if col not in ['escola_id', 'Escola', 'Total de Alunos', 'Alunos Ativos', 'Média Geral (%)']:
                        df_pivot[col] = df_pivot[col].round(1)
                        df_pivot = df_pivot.rename(columns={col: f'{col} (%)'})
                
                # Remover coluna escola_id
                df_pivot.drop('escola_id', axis=1, inplace=True)
                
                # Salvar na planilha
                df_pivot.to_excel(writer, sheet_name=Ano_escolar_nome, index=False)
            else:
                # Se não houver dados de disciplinas, salvar apenas os dados gerais
                df_Ano_escolar.drop(['escola_id', 'disciplina', 'media_disciplina'], axis=1, errors='ignore', inplace=True)
                df_Ano_escolar.to_excel(writer, sheet_name=Ano_escolar_nome, index=False)
    
    writer.close()
    output.seek(0)
    
    return send_file(
        output,
        download_name='relatorio_rede_municipal.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

def get_relatorio_data():
    cursor = get_db().cursor()
    cursor.execute("SELECT codigo_ibge FROM usuarios WHERE id = ?", (current_user.id,))
    codigo_ibge = cursor.fetchone()[0]
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = "strftime('%Y', data_resposta) = ?"
    data_params = [str(ano)]
    
    if mes:
        data_condition += " AND strftime('%m', data_resposta) = ?"
        data_params.append(f"{mes:02d}")
        
    # Buscar todos os dados necessários para o relatório
    # ... (resto do código atual da função relatorio_rede_municipal)
    
    return {
        'codigo_ibge': codigo_ibge,
        'mes': mes,
        'ano': ano,
        'escolas': escolas,
        'total_escolas': total_escolas,
        'total_alunos': total_alunos,
        'total_simulados': total_simulados,
        'media_geral': media_geral,
        'disciplinas': disciplinas,
        'disciplinas_nomes': disciplinas_nomes,
        'disciplinas_medias': disciplinas_medias
    }

# @secretaria_educacao_bp.route('/relatorio_escola')
# @login_required
# def relatorio_escola():
#     """Página de relatório por escola."""
#     if current_user.tipo_usuario_id not in [5, 6]:
#         flash("Acesso não autorizado.", "danger")
#         return redirect(url_for("index"))
    
#     db = get_db()
#     cursor = db.cursor()
    
#     # Buscar o `codigo_ibge` do usuário
#     cursor.execute("SELECT codigo_ibge FROM usuarios WHERE id = ?", (current_user.id,))
#     codigo_ibge = cursor.fetchone()[0]
    
#     # Buscar todas as escolas do município
#     cursor.execute("""
#         SELECT id, nome_da_escola as nome
#         FROM escolas
#         WHERE codigo_ibge = ?
#         ORDER BY nome_da_escola
#     """, [codigo_ibge])
#     escolas = cursor.fetchall()
    
#     # Obter escola_id e mês da query string
#     escola_id = request.args.get('escola_id', type=int)
#     mes = request.args.get('mes', type=int)
#     ano = 2025  # Fixado em 2025
    
#     # Se uma escola foi selecionada, buscar seus dados
#     if escola_id:
#         # Construir a condição de data
#         data_condition = "strftime('%Y', data_resposta) = ?"
#         data_params = [str(ano)]
        
#         if mes:
#             data_condition += " AND strftime('%m', data_resposta) = ?"
#             data_params.append(f"{mes:02d}")
        
#         # Buscar dados da escola
#         cursor.execute("""
#             SELECT nome_da_escola, ensino_fundamental
#             FROM escolas
#             WHERE id = ?
#         """, [escola_id])
#         escola = cursor.fetchone()
        
#         # Buscar turmas e seus desempenhos
#         cursor.execute(f"""
#             SELECT 
#                 t.id,
#                 t.turma,
#                 COUNT(DISTINCT u.id) as total_alunos,
#                 COUNT(DISTINCT ds.aluno_id) as alunos_ativos,
#                 COALESCE(AVG(ds.desempenho), 0) as media
#             FROM turmas t
#             LEFT JOIN usuarios u ON u.turma_id = t.id AND u.tipo_usuario_id = 4
#             LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id
#             WHERE t.escola_id = ?
#             AND ({data_condition} OR ds.data_resposta IS NULL)
#             GROUP BY t.id, t.turma
#             ORDER BY t.turma
#         """, [escola_id] + data_params)
        
#         turmas = cursor.fetchall()
        
#         # Buscar alunos e seus desempenhos
#         cursor.execute(f"""
#             SELECT 
#                 u.id as aluno_id,
#                 u.nome as aluno_nome,
#                 u.turma_id,
#                 COUNT(ds.id) as total_simulados,
#                 COALESCE(AVG(ds.desempenho), 0) as media
#             FROM usuarios u
#             LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id
#             WHERE u.escola_id = ? 
#             AND u.tipo_usuario_id = 4
#             AND ({data_condition} OR ds.data_resposta IS NULL)
#             GROUP BY u.id, u.nome, u.turma_id
#             ORDER BY u.nome
#         """, [escola_id] + data_params)
        
#         alunos = cursor.fetchall()
        
#         return render_template(
#             'secretaria_educacao/relatorio_escola.html',
#             escolas=escolas,
#             escola_id=escola_id,
#             escola=escola,
#             mes=mes,
#             ano=ano,
#             turmas=turmas,
#             alunos=alunos
#         )
    
#     return render_template(
#         'secretaria_educacao/relatorio_escola.html',
#         escolas=escolas,
#         escola_id=None,
#         mes=mes,
#         ano=ano
#     )

@secretaria_educacao_bp.route('/relatorio_escola')
@login_required
def relatorio_escola():
    """Página de relatório por escola."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    db = get_db()
    cursor = db.cursor()
    
    # Buscar o `codigo_ibge` do usuário
    cursor.execute("SELECT codigo_ibge FROM usuarios WHERE id = ?", (current_user.id,))
    codigo_ibge = cursor.fetchone()[0]
    
    # Buscar todas as escolas do município
    cursor.execute("""
        SELECT id, nome_da_escola as nome
        FROM escolas
        WHERE codigo_ibge = ?
        ORDER BY nome_da_escola
    """, [codigo_ibge])
    escolas = cursor.fetchall()
    
    # Obter escola_id e mês da query string
    escola_id = request.args.get('escola_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Se uma escola foi selecionada, buscar seus dados
    if escola_id:
        # Construir a condição de data
        data_condition = "strftime('%Y', data_resposta) = ?"
        data_params = [str(ano)]
        
        if mes:
            data_condition += " AND strftime('%m', data_resposta) = ?"
            data_params.append(f"{mes:02d}")
        
        # Buscar dados gerais da escola
        cursor.execute(f"""
            SELECT 
                e.nome_da_escola as nome,
                COUNT(DISTINCT u.id) as total_alunos,
                COUNT(DISTINCT ds.aluno_id) as alunos_ativos,
                COUNT(DISTINCT ds.simulado_id) as total_simulados,
                COALESCE(AVG(ds.desempenho), 0) as media_geral
            FROM escolas e
            LEFT JOIN usuarios u ON u.escola_id = e.id AND u.tipo_usuario_id = 4
            LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id AND {data_condition}
            WHERE e.id = ?
            GROUP BY e.id, e.nome_da_escola
        """, data_params + [escola_id])
        escola = cursor.fetchone()
        
        # Buscar dados por série
        cursor.execute(f"""
            SELECT 
                s.id,
                s.nome,
                COUNT(DISTINCT u.id) as total_alunos,
                COUNT(DISTINCT ds.aluno_id) as alunos_ativos,
                COALESCE(AVG(ds.desempenho), 0) as media
            FROM Ano_escolar s
            LEFT JOIN usuarios u ON u.ano_escolar_id = s.id 
                AND u.tipo_usuario_id = 4 
                AND u.escola_id = ?
            LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id 
                AND {data_condition}
            GROUP BY s.id, s.nome
            ORDER BY s.id
        """, [escola_id] + data_params)
        Ano_escolar = cursor.fetchall()
        
        # Buscar dados por disciplina
        cursor.execute(f"""
            WITH SimuladosDisciplinas AS (
                SELECT 
                    ds.aluno_id,
                    ds.simulado_id,
                    ds.desempenho,
                    CASE 
                        WHEN ds.tipo_usuario_id = 5 THEN sg.disciplina_id
                        WHEN ds.tipo_usuario_id = 3 THEN sgp.disciplina_id
                    END as disciplina_id
                FROM desempenho_simulado ds
                LEFT JOIN simulados_gerados sg ON sg.id = ds.simulado_id AND ds.tipo_usuario_id = 5
                LEFT JOIN simulados_gerados_professor sgp ON sgp.id = ds.simulado_id AND ds.tipo_usuario_id = 3
                JOIN usuarios u ON u.id = ds.aluno_id AND u.escola_id = ?
                WHERE {data_condition}
            )
            SELECT 
                d.nome as disciplina,
                COUNT(DISTINCT sd.aluno_id) as total_alunos,
                COUNT(DISTINCT sd.simulado_id) as total_questoes,
                ROUND(AVG(sd.desempenho), 1) as media_acertos
            FROM disciplinas d
            LEFT JOIN SimuladosDisciplinas sd ON sd.disciplina_id = d.id
            GROUP BY d.id, d.nome
            HAVING total_alunos > 0
            ORDER BY media_acertos DESC
        """, [escola_id] + data_params)
        disciplinas = cursor.fetchall()


        #Buscar dados por turma
        cursor.execute(f"""
            SELECT 
                t.id,
                s.nome || ' ' || t.turma as turma,
                COUNT(DISTINCT u.id) as total_alunos,
                COUNT(DISTINCT ds.aluno_id) as alunos_ativos,
                COALESCE(AVG(ds.desempenho), 0) as media
            FROM turmas t
            JOIN Ano_escolar s ON s.id = t.ano_escolar_id
            LEFT JOIN usuarios u ON u.turma_id = t.id 
                AND u.tipo_usuario_id = 4
                AND u.escola_id = ?
            LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id 
                AND {data_condition}
            GROUP BY t.id, t.turma, s.nome
            HAVING total_alunos > 0
            ORDER BY s.nome, t.turma
        """, [escola_id] + data_params)
        
        turmas = cursor.fetchall()
        
        #Buscar alunos e seus desempenhos
        cursor.execute(f"""
            SELECT 
                u.id as aluno_id,
                u.nome as aluno_nome,
                u.turma_id,
                COUNT(ds.id) as total_simulados,
                COALESCE(AVG(ds.desempenho), 0) as media
            FROM usuarios u
            LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id
            WHERE u.escola_id = ? 
            AND u.tipo_usuario_id = 4
            AND ({data_condition} OR ds.data_resposta IS NULL)
            GROUP BY u.id, u.nome, u.turma_id
            ORDER BY u.nome
        """, [escola_id] + data_params)
        
        alunos = cursor.fetchall()

        # Buscar dados dos alunos por turma com desempenho por disciplina
        cursor.execute(f"""
            WITH SimuladosDisciplinas AS (
                SELECT 
                    ds.aluno_id,
                    ds.simulado_id,
                    ds.desempenho,
                    COALESCE(sg.disciplina_id, sgp.disciplina_id) as disciplina_id,
                    u.turma_id
                FROM desempenho_simulado ds
                JOIN usuarios u ON u.id = ds.aluno_id
                LEFT JOIN simulados_gerados sg ON sg.id = ds.simulado_id AND ds.tipo_usuario_id = 5
                LEFT JOIN simulados_gerados_professor sgp ON sgp.id = ds.simulado_id AND ds.tipo_usuario_id = 3
                WHERE u.escola_id = ? 
                AND COALESCE(sg.disciplina_id, sgp.disciplina_id) IS NOT NULL
            ),
            MediasPorDisciplina AS (
                SELECT 
                    sd.aluno_id,
                    sd.turma_id,
                    d.id as disciplina_id,
                    ROUND(AVG(sd.desempenho), 1) as media_disciplina
                FROM SimuladosDisciplinas sd
                JOIN disciplinas d ON d.id = sd.disciplina_id
                GROUP BY sd.aluno_id, sd.turma_id, d.id
            )
            SELECT 
                t.id as turma_id,
                u.id as aluno_id,
                u.nome as aluno_nome,
                COUNT(DISTINCT CASE WHEN {data_condition} THEN ds.simulado_id END) as total_simulados,
                COALESCE(AVG(CASE WHEN {data_condition} THEN ds.desempenho END), 0) as media,
                MAX(CASE WHEN mpd.disciplina_id = 2 THEN mpd.media_disciplina END) as media_matematica,
                MAX(CASE WHEN mpd.disciplina_id = 1 THEN mpd.media_disciplina END) as media_portugues,
                MAX(CASE WHEN mpd.disciplina_id = 3 THEN mpd.media_disciplina END) as media_ciencias,
                MAX(CASE WHEN mpd.disciplina_id = 4 THEN mpd.media_disciplina END) as media_historia,
                MAX(CASE WHEN mpd.disciplina_id = 5 THEN mpd.media_disciplina END) as media_geografia
            FROM turmas t
            JOIN usuarios u ON u.turma_id = t.id 
                AND u.tipo_usuario_id = 4
                AND u.escola_id = ?
            LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id 
            LEFT JOIN MediasPorDisciplina mpd ON mpd.aluno_id = u.id AND mpd.turma_id = t.id
            GROUP BY t.id, t.turma, u.id, u.nome
            ORDER BY t.turma, u.nome
        """, [escola_id] + data_params + data_params + [escola_id])
        
        # Aqui está o problema - precisamos armazenar o resultado em alunos
        alunos = cursor.fetchall()
        
        return render_template('secretaria_educacao/relatorio_escola.html',
                             ano=ano,
                             mes=mes,
                             escolas=escolas,
                             escola_id=escola_id,
                             media_geral=round(escola['media_geral'], 1),
                             total_alunos=escola['total_alunos'],
                             alunos_ativos=escola['alunos_ativos'],
                             total_simulados=escola['total_simulados'],
                             Ano_escolar=Ano_escolar,
                             disciplinas=disciplinas,
                             turmas=turmas,
                             alunos=alunos)
    
    return render_template('secretaria_educacao/relatorio_escola.html',
                         ano=ano,
                         mes=mes,
                         escolas=escolas,
                         escola_id=None)

                         
@secretaria_educacao_bp.route('/relatorio_escola/export_pdf')
@login_required
def export_pdf_escola():
    """Exportar relatório da escola em PDF."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    db = get_db()
    cursor = db.cursor()
    
    # Obter escola_id e mês da query string
    escola_id = request.args.get('escola_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    if not escola_id:
        flash("Escola não especificada.", "danger")
        return redirect(url_for("secretaria_educacao.relatorio_escola"))
    
    # Construir a condição de data
    data_condition = "strftime('%Y', data_resposta) = ?"
    data_params = [str(ano)]
    
    if mes:
        data_condition += " AND strftime('%m', data_resposta) = ?"
        data_params.append(f"{mes:02d}")
    
    # Buscar dados da escola
    cursor.execute(f"""
        SELECT 
            e.nome_da_escola as nome,
            COUNT(DISTINCT u.id) as total_alunos,
            COUNT(DISTINCT ds.aluno_id) as alunos_ativos,
            COUNT(DISTINCT ds.simulado_id) as total_simulados,
            COALESCE(AVG(ds.desempenho), 0) as media_geral
        FROM escolas e
        LEFT JOIN usuarios u ON u.escola_id = e.id AND u.tipo_usuario_id = 4
        LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id AND {data_condition}
        WHERE e.id = ?
        GROUP BY e.id, e.nome_da_escola
    """, data_params + [escola_id])
    escola = cursor.fetchone()
    
    # Buscar dados por série
    cursor.execute(f"""
        SELECT 
            s.id,
            s.nome,
            COUNT(DISTINCT u.id) as total_alunos,
            COUNT(DISTINCT ds.aluno_id) as alunos_ativos,
            COALESCE(AVG(ds.desempenho), 0) as media
        FROM Ano_escolar s
        LEFT JOIN usuarios u ON u.ano_escolar_id = s.id 
            AND u.tipo_usuario_id = 4 
            AND u.escola_id = ?
        LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id 
            AND {data_condition}
        GROUP BY s.id, s.nome
        ORDER BY s.id
    """, [escola_id] + data_params)
    Ano_escolar = cursor.fetchall()
    
    # Buscar dados por disciplina
    cursor.execute(f"""
        WITH SimuladosDisciplinas AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                CASE 
                    WHEN ds.tipo_usuario_id = 5 THEN sg.disciplina_id
                    WHEN ds.tipo_usuario_id = 3 THEN sgp.disciplina_id
                END as disciplina_id
            FROM desempenho_simulado ds
            LEFT JOIN simulados_gerados sg ON sg.id = ds.simulado_id AND ds.tipo_usuario_id = 5
            LEFT JOIN simulados_gerados_professor sgp ON sgp.id = ds.simulado_id AND ds.tipo_usuario_id = 3
            JOIN usuarios u ON u.id = ds.aluno_id AND u.escola_id = ?
            WHERE {data_condition}
        )
        SELECT 
            d.nome as disciplina,
            COUNT(DISTINCT sd.aluno_id) as total_alunos,
            COUNT(DISTINCT sd.simulado_id) as total_questoes,
            ROUND(AVG(sd.desempenho), 1) as media_acertos
        FROM disciplinas d
        LEFT JOIN SimuladosDisciplinas sd ON sd.disciplina_id = d.id
        GROUP BY d.id, d.nome
        HAVING total_alunos > 0
        ORDER BY media_acertos DESC
    """, [escola_id] + data_params)
    disciplinas = cursor.fetchall()
    
    # Renderizar o template HTML
    html = render_template('secretaria_educacao/relatorio_escola_pdf.html',
                         ano=ano,
                         mes=MESES.get(mes) if mes else None,
                         escola=escola,
                         media_geral=round(escola['media_geral'], 1),
                         total_alunos=escola['total_alunos'],
                         alunos_ativos=escola['alunos_ativos'],
                         total_simulados=escola['total_simulados'],
                         Ano_escolar=Ano_escolar,
                         disciplinas=disciplinas)
    
    # Gerar o PDF
    pdf = HTML(string=html).write_pdf()
    
    return send_file(
        BytesIO(pdf),
        download_name=f'relatorio_escola_{escola_id}.pdf',
        mimetype='application/pdf'
    )

@secretaria_educacao_bp.route('/relatorio_escola/export_excel')
@login_required
def export_excel_escola():
    """Exportar relatório da escola em Excel."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    db = get_db()
    cursor = db.cursor()
    
    # Obter escola_id e mês da query string
    escola_id = request.args.get('escola_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    if not escola_id:
        flash("Escola não especificada.", "danger")
        return redirect(url_for("secretaria_educacao.relatorio_escola"))
    
    # Construir a condição de data
    data_condition = "strftime('%Y', data_resposta) = ?"
    data_params = [str(ano)]
    
    if mes:
        data_condition += " AND strftime('%m', data_resposta) = ?"
        data_params.append(f"{mes:02d}")
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Aba Visão Geral
    cursor.execute(f"""
        SELECT 
            e.nome_da_escola as nome,
            COUNT(DISTINCT u.id) as total_alunos,
            COUNT(DISTINCT ds.aluno_id) as alunos_ativos,
            COUNT(DISTINCT ds.simulado_id) as total_simulados,
            COALESCE(AVG(ds.desempenho), 0) as media_geral
        FROM escolas e
        LEFT JOIN usuarios u ON u.escola_id = e.id AND u.tipo_usuario_id = 4
        LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id AND {data_condition}
        WHERE e.id = ?
        GROUP BY e.id, e.nome_da_escola
    """, data_params + [escola_id])
    escola = cursor.fetchone()
    
    df_geral = pd.DataFrame([{
        'Indicador': 'Média Geral',
        'Valor': f"{round(escola['media_geral'], 1)}%"
    }, {
        'Indicador': 'Total de Alunos',
        'Valor': str(escola['total_alunos'])
    }, {
        'Indicador': 'Alunos Ativos',
        'Valor': str(escola['alunos_ativos'])
    }, {
        'Indicador': 'Simulados Realizados',
        'Valor': str(escola['total_simulados'])
    }])
    df_geral.to_excel(writer, sheet_name='Visão Geral', index=False)
    
    # Aba Desempenho por Ano Escolar
    cursor.execute(f"""
        SELECT 
            s.nome Ano_escolar,
            COUNT(DISTINCT u.id) as total_alunos,
            COUNT(DISTINCT ds.aluno_id) as alunos_ativos,
            COALESCE(AVG(ds.desempenho), 0) as media
        FROM Ano_escolar s
        LEFT JOIN usuarios u ON u.ano_escolar_id = s.id 
            AND u.tipo_usuario_id = 4 
            AND u.escola_id = ?
        LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id 
            AND {data_condition}
        GROUP BY s.id, s.nome
        ORDER BY s.id
    """, [escola_id] + data_params)
    Ano_escolar = cursor.fetchall()
    
    df_Ano_escolar = pd.DataFrame([dict(row) for row in Ano_escolar])
    if not df_Ano_escolar.empty:
        df_Ano_escolar = df_Ano_escolar.rename(columns={
            'Ano_escolar': 'Ano Escolar',
            'total_alunos': 'Total de Alunos',
            'alunos_ativos': 'Alunos Ativos',
            'media': 'Média (%)'
        })
        df_Ano_escolar['Média (%)'] = df_Ano_escolar['Média (%)'].round(1)
    df_Ano_escolar.to_excel(writer, sheet_name='Desempenho por Ano Escolar', index=False)
    
    # Aba Desempenho por Disciplina
    cursor.execute(f"""
        WITH SimuladosDisciplinas AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                CASE 
                    WHEN ds.tipo_usuario_id = 5 THEN sg.disciplina_id
                    WHEN ds.tipo_usuario_id = 3 THEN sgp.disciplina_id
                END as disciplina_id
            FROM desempenho_simulado ds
            LEFT JOIN simulados_gerados sg ON sg.id = ds.simulado_id AND ds.tipo_usuario_id = 5
            LEFT JOIN simulados_gerados_professor sgp ON sgp.id = ds.simulado_id AND ds.tipo_usuario_id = 3
            JOIN usuarios u ON u.id = ds.aluno_id AND u.escola_id = ?
            WHERE {data_condition}
        )
        SELECT 
            d.nome as disciplina,
            COUNT(DISTINCT sd.aluno_id) as total_alunos,
            COUNT(DISTINCT sd.simulado_id) as total_questoes,
            ROUND(AVG(sd.desempenho), 1) as media_acertos
        FROM disciplinas d
        LEFT JOIN SimuladosDisciplinas sd ON sd.disciplina_id = d.id
        GROUP BY d.id, d.nome
        HAVING total_alunos > 0
        ORDER BY media_acertos DESC
    """, [escola_id] + data_params)
    disciplinas = cursor.fetchall()
    
    df_disciplinas = pd.DataFrame([dict(row) for row in disciplinas])
    if not df_disciplinas.empty:
        df_disciplinas = df_disciplinas.rename(columns={
            'disciplina': 'Disciplina',
            'total_alunos': 'Total de Alunos',
            'total_questoes': 'Total de Questões',
            'media_acertos': 'Média de Acertos (%)'
        })
    df_disciplinas.to_excel(writer, sheet_name='Desempenho por Disciplina', index=False)
    
    writer.close()
    output.seek(0)
    
    return send_file(
        output,
        download_name=f'relatorio_escola_{escola_id}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@secretaria_educacao_bp.route('/relatorio_disciplina')
@login_required
def relatorio_disciplina():
    """Página de relatório por disciplina."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    db = get_db()
    cursor = db.cursor()
    
    # Buscar o `codigo_ibge` do usuário
    cursor.execute("SELECT codigo_ibge FROM usuarios WHERE id = ?", (current_user.id,))
    codigo_ibge = cursor.fetchone()[0]
    
    # Buscar todas as disciplinas
    cursor.execute("""
        SELECT id, nome
        FROM disciplinas
        ORDER BY nome
    """)
    disciplinas = cursor.fetchall()
    
    # Obter disciplina_id e mês da query string
    disciplina_id = request.args.get('disciplina_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Se uma disciplina foi selecionada, buscar seus dados
    if disciplina_id:
        # Construir a condição de data
        data_condition = "strftime('%Y', data_resposta) = ?"
        data_params = [str(ano)]
        
        if mes:
            data_condition += " AND strftime('%m', data_resposta) = ?"
            data_params.append(f"{mes:02d}")
        
        # Buscar dados gerais da disciplina
        cursor.execute(f"""
            WITH SimuladosDisciplina AS (
                SELECT 
                    ds.aluno_id,
                    ds.simulado_id,
                    ds.desempenho
                FROM desempenho_simulado ds
                WHERE (
                    (ds.tipo_usuario_id = 5 AND EXISTS (
                        SELECT 1 FROM simulados_gerados 
                        WHERE id = ds.simulado_id AND disciplina_id = ?
                    ))
                    OR 
                    (ds.tipo_usuario_id = 3 AND EXISTS (
                        SELECT 1 FROM simulados_gerados_professor 
                        WHERE id = ds.simulado_id AND disciplina_id = ?
                    ))
                )
                AND ds.codigo_ibge = ?
                AND {data_condition}
            )
            SELECT 
                d.nome,
                COUNT(DISTINCT sd.aluno_id) as total_alunos,
                COUNT(DISTINCT sd.simulado_id) as total_simulados,
                COUNT(sd.simulado_id) as total_questoes,
                COALESCE(AVG(sd.desempenho), 0) as media_geral
            FROM disciplinas d
            LEFT JOIN SimuladosDisciplina sd ON 1=1
            WHERE d.id = ?
            GROUP BY d.id, d.nome
        """, [disciplina_id, disciplina_id, codigo_ibge] + data_params + [disciplina_id])
        disciplina = cursor.fetchone()
        
        # Buscar dados por série
        cursor.execute(f"""
            WITH SimuladosDisciplina AS (
                SELECT 
                    ds.aluno_id,
                    ds.simulado_id,
                    ds.desempenho,
                    u.ano_escolar_id
                FROM desempenho_simulado ds
                JOIN usuarios u ON u.id = ds.aluno_id
                WHERE (
                    (ds.tipo_usuario_id = 5 AND EXISTS (
                        SELECT 1 FROM simulados_gerados 
                        WHERE id = ds.simulado_id AND disciplina_id = ?
                    ))
                    OR 
                    (ds.tipo_usuario_id = 3 AND EXISTS (
                        SELECT 1 FROM simulados_gerados_professor 
                        WHERE id = ds.simulado_id AND disciplina_id = ?
                    ))
                )
                AND ds.codigo_ibge = ?
                AND {data_condition}
            )
            SELECT 
                s.id,
                s.nome,
                COUNT(DISTINCT sd.aluno_id) as total_alunos,
                COUNT(sd.simulado_id) as total_questoes,
                COALESCE(AVG(sd.desempenho), 0) as media
            FROM Ano_escolar s
            LEFT JOIN SimuladosDisciplina sd ON sd.ano_escolar_id = s.id
            GROUP BY s.id, s.nome
            ORDER BY s.id
        """, [disciplina_id, disciplina_id, codigo_ibge] + data_params)
        Ano_escolar = cursor.fetchall()
        
        # Buscar dados por escola
        cursor.execute(f"""
            WITH SimuladosDisciplina AS (
                SELECT 
                    ds.aluno_id,
                    ds.simulado_id,
                    ds.desempenho,
                    u.escola_id
                FROM desempenho_simulado ds
                JOIN usuarios u ON u.id = ds.aluno_id
                WHERE (
                    (ds.tipo_usuario_id = 5 AND EXISTS (
                        SELECT 1 FROM simulados_gerados 
                        WHERE id = ds.simulado_id AND disciplina_id = ?
                    ))
                    OR 
                    (ds.tipo_usuario_id = 3 AND EXISTS (
                        SELECT 1 FROM simulados_gerados_professor 
                        WHERE id = ds.simulado_id AND disciplina_id = ?
                    ))
                )
                AND ds.codigo_ibge = ?
                AND {data_condition}
            )
            SELECT 
                e.nome_da_escola as nome,
                COUNT(DISTINCT sd.aluno_id) as total_alunos,
                COUNT(sd.simulado_id) as total_questoes,
                ROUND(AVG(sd.desempenho), 1) as media_acertos
            FROM escolas e
            LEFT JOIN SimuladosDisciplina sd ON sd.escola_id = e.id
            WHERE e.codigo_ibge = ?
            GROUP BY e.id, e.nome_da_escola
            HAVING total_alunos > 0
            ORDER BY media_acertos DESC
        """, [disciplina_id, disciplina_id, codigo_ibge] + data_params + [codigo_ibge])
        escolas = cursor.fetchall()
        
        return render_template('secretaria_educacao/relatorio_disciplina.html',
                             ano=ano,
                             mes=mes,
                             disciplinas=disciplinas,
                             disciplina_id=disciplina_id,
                             media_geral=round(disciplina['media_geral'], 1),
                             total_alunos=disciplina['total_alunos'],
                             total_questoes=disciplina['total_questoes'],
                             total_simulados=disciplina['total_simulados'],
                             Ano_escolar=Ano_escolar,
                             escolas=escolas)
    
    return render_template('secretaria_educacao/relatorio_disciplina.html',
                         ano=ano,
                         mes=mes,
                         disciplinas=disciplinas,
                         disciplina_id=None)

@secretaria_educacao_bp.route('/relatorio_disciplina/export_pdf')
@login_required
def export_pdf_disciplina():
    """Exportar relatório da disciplina em PDF."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    db = get_db()
    cursor = db.cursor()
    
    # Obter disciplina_id e mês da query string
    disciplina_id = request.args.get('disciplina_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    if not disciplina_id:
        flash("Disciplina não especificada.", "danger")
        return redirect(url_for("secretaria_educacao.relatorio_disciplina"))
    
    # Construir a condição de data
    data_condition = "strftime('%Y', data_resposta) = ?"
    data_params = [str(ano)]
    
    if mes:
        data_condition += " AND strftime('%m', data_resposta) = ?"
        data_params.append(f"{mes:02d}")
    
    # Buscar dados da disciplina
    cursor.execute(f"""
        WITH SimuladosDisciplina AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho
            FROM desempenho_simulado ds
            WHERE (
                (ds.tipo_usuario_id = 5 AND EXISTS (
                    SELECT 1 FROM simulados_gerados 
                    WHERE id = ds.simulado_id AND disciplina_id = ?
                ))
                OR 
                (ds.tipo_usuario_id = 3 AND EXISTS (
                    SELECT 1 FROM simulados_gerados_professor 
                    WHERE id = ds.simulado_id AND disciplina_id = ?
                ))
            )
            AND ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            d.nome,
            COUNT(DISTINCT sd.aluno_id) as total_alunos,
            COUNT(DISTINCT sd.simulado_id) as total_simulados,
            COUNT(sd.simulado_id) as total_questoes,
            COALESCE(AVG(sd.desempenho), 0) as media_geral
        FROM disciplinas d
        LEFT JOIN SimuladosDisciplina sd ON 1=1
        WHERE d.id = ?
        GROUP BY d.id, d.nome
    """, [disciplina_id, disciplina_id, current_user.codigo_ibge] + data_params + [disciplina_id])
    disciplina = cursor.fetchone()
    
    # Buscar dados por série
    cursor.execute(f"""
        WITH SimuladosDisciplina AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                u.ano_escolar_id
            FROM desempenho_simulado ds
            JOIN usuarios u ON u.id = ds.aluno_id
            WHERE (
                (ds.tipo_usuario_id = 5 AND EXISTS (
                    SELECT 1 FROM simulados_gerados 
                    WHERE id = ds.simulado_id AND disciplina_id = ?
                ))
                OR 
                (ds.tipo_usuario_id = 3 AND EXISTS (
                    SELECT 1 FROM simulados_gerados_professor 
                    WHERE id = ds.simulado_id AND disciplina_id = ?
                ))
            )
            AND ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            s.id,
            s.nome,
            COUNT(DISTINCT sd.aluno_id) as total_alunos,
            COUNT(sd.simulado_id) as total_questoes,
            COALESCE(AVG(sd.desempenho), 0) as media
        FROM Ano_escolar s
        LEFT JOIN SimuladosDisciplina sd ON sd.ano_escolar_id = s.id
        GROUP BY s.id, s.nome
        ORDER BY s.id
    """, [disciplina_id, disciplina_id, current_user.codigo_ibge] + data_params)
    Ano_escolar = cursor.fetchall()
    
    # Buscar dados por escola
    cursor.execute(f"""
        WITH SimuladosDisciplina AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                u.escola_id
            FROM desempenho_simulado ds
            JOIN usuarios u ON u.id = ds.aluno_id
            WHERE (
                (ds.tipo_usuario_id = 5 AND EXISTS (
                    SELECT 1 FROM simulados_gerados 
                    WHERE id = ds.simulado_id AND disciplina_id = ?
                ))
                OR 
                (ds.tipo_usuario_id = 3 AND EXISTS (
                    SELECT 1 FROM simulados_gerados_professor 
                    WHERE id = ds.simulado_id AND disciplina_id = ?
                ))
            )
            AND ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            e.nome_da_escola as nome,
            COUNT(DISTINCT sd.aluno_id) as total_alunos,
            COUNT(sd.simulado_id) as total_questoes,
            ROUND(AVG(sd.desempenho), 1) as media_acertos
        FROM escolas e
        LEFT JOIN SimuladosDisciplina sd ON sd.escola_id = e.id
        WHERE e.codigo_ibge = ?
        GROUP BY e.id, e.nome_da_escola
        HAVING total_alunos > 0
        ORDER BY media_acertos DESC
    """, [disciplina_id, disciplina_id, current_user.codigo_ibge] + data_params + [current_user.codigo_ibge])
    escolas = cursor.fetchall()
    
    # Renderizar o template HTML
    html = render_template('secretaria_educacao/relatorio_disciplina_pdf.html',
                         ano=ano,
                         mes=MESES.get(mes) if mes else None,
                         disciplina=disciplina,
                         media_geral=round(disciplina['media_geral'], 1),
                         total_alunos=disciplina['total_alunos'],
                         total_questoes=disciplina['total_questoes'],
                         total_simulados=disciplina['total_simulados'],
                         Ano_escolar=Ano_escolar,
                         escolas=escolas)
    
    # Gerar o PDF
    pdf = HTML(string=html).write_pdf()
    
    return send_file(
        BytesIO(pdf),
        download_name=f'relatorio_disciplina_{disciplina_id}.pdf',
        mimetype='application/pdf'
    )

@secretaria_educacao_bp.route('/relatorio_disciplina/export_excel')
@login_required
def export_excel_disciplina():
    """Exportar relatório da disciplina em Excel."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    db = get_db()
    cursor = db.cursor()
    
    # Obter disciplina_id e mês da query string
    disciplina_id = request.args.get('disciplina_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    if not disciplina_id:
        flash("Disciplina não especificada.", "danger")
        return redirect(url_for("secretaria_educacao.relatorio_disciplina"))
    
    # Construir a condição de data
    data_condition = "strftime('%Y', data_resposta) = ?"
    data_params = [str(ano)]
    
    if mes:
        data_condition += " AND strftime('%m', data_resposta) = ?"
        data_params.append(f"{mes:02d}")
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Aba Visão Geral
    cursor.execute(f"""
        WITH SimuladosDisciplina AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho
            FROM desempenho_simulado ds
            WHERE (
                (ds.tipo_usuario_id = 5 AND EXISTS (
                    SELECT 1 FROM simulados_gerados 
                    WHERE id = ds.simulado_id AND disciplina_id = ?
                ))
                OR 
                (ds.tipo_usuario_id = 3 AND EXISTS (
                    SELECT 1 FROM simulados_gerados_professor 
                    WHERE id = ds.simulado_id AND disciplina_id = ?
                ))
            )
            AND ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            d.nome,
            COUNT(DISTINCT sd.aluno_id) as total_alunos,
            COUNT(DISTINCT sd.simulado_id) as total_simulados,
            COUNT(sd.simulado_id) as total_questoes,
            COALESCE(AVG(sd.desempenho), 0) as media_geral
        FROM disciplinas d
        LEFT JOIN SimuladosDisciplina sd ON 1=1
        WHERE d.id = ?
        GROUP BY d.id, d.nome
    """, [disciplina_id, disciplina_id, current_user.codigo_ibge] + data_params + [disciplina_id])
    disciplina = cursor.fetchone()
    
    df_geral = pd.DataFrame([{
        'Indicador': 'Média Geral',
        'Valor': f"{round(disciplina['media_geral'], 1)}%"
    }, {
        'Indicador': 'Total de Alunos',
        'Valor': str(disciplina['total_alunos'])
    }, {
        'Indicador': 'Total de Questões',
        'Valor': str(disciplina['total_questoes'])
    }, {
        'Indicador': 'Simulados com a Disciplina',
        'Valor': str(disciplina['total_simulados'])
    }])
    df_geral.to_excel(writer, sheet_name='Visão Geral', index=False)
    
    # Aba Desempenho por Ano Escolar
    cursor.execute(f"""
        WITH SimuladosDisciplina AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                u.ano_escolar_id
            FROM desempenho_simulado ds
            JOIN usuarios u ON u.id = ds.aluno_id
            WHERE (
                (ds.tipo_usuario_id = 5 AND EXISTS (
                    SELECT 1 FROM simulados_gerados 
                    WHERE id = ds.simulado_id AND disciplina_id = ?
                ))
                OR 
                (ds.tipo_usuario_id = 3 AND EXISTS (
                    SELECT 1 FROM simulados_gerados_professor 
                    WHERE id = ds.simulado_id AND disciplina_id = ?
                ))
            )
            AND ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            s.nome Ano_escolar,
            COUNT(DISTINCT sd.aluno_id) as total_alunos,
            COUNT(sd.simulado_id) as total_questoes,
            COALESCE(AVG(sd.desempenho), 0) as media
        FROM Ano_escolar s
        LEFT JOIN SimuladosDisciplina sd ON sd.ano_escolar_id = s.id
        GROUP BY s.id, s.nome
        ORDER BY s.id
    """, [disciplina_id, disciplina_id, current_user.codigo_ibge] + data_params)
    Ano_escolar = cursor.fetchall()
    
    df_Ano_escolar = pd.DataFrame([dict(row) for row in Ano_escolar])
    if not df_Ano_escolar.empty:
        df_Ano_escolar = df_Ano_escolar.rename(columns={
            'Ano_escolar': 'Ano Escolar',
            'total_alunos': 'Total de Alunos',
            'total_questoes': 'Total de Questões',
            'media': 'Média (%)'
        })
        df_Ano_escolar['Média (%)'] = df_Ano_escolar['Média (%)'].round(1)
    df_Ano_escolar.to_excel(writer, sheet_name='Desempenho por Ano Escolar', index=False)
    
    # Aba Desempenho por Escola
    cursor.execute(f"""
        WITH SimuladosDisciplina AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                u.escola_id
            FROM desempenho_simulado ds
            JOIN usuarios u ON u.id = ds.aluno_id
            WHERE (
                (ds.tipo_usuario_id = 5 AND EXISTS (
                    SELECT 1 FROM simulados_gerados 
                    WHERE id = ds.simulado_id AND disciplina_id = ?
                ))
                OR 
                (ds.tipo_usuario_id = 3 AND EXISTS (
                    SELECT 1 FROM simulados_gerados_professor 
                    WHERE id = ds.simulado_id AND disciplina_id = ?
                ))
            )
            AND ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            e.nome_da_escola as escola,
            COUNT(DISTINCT sd.aluno_id) as total_alunos,
            COUNT(sd.simulado_id) as total_questoes,
            ROUND(AVG(sd.desempenho), 1) as media_acertos
        FROM escolas e
        LEFT JOIN SimuladosDisciplina sd ON sd.escola_id = e.id
        WHERE e.codigo_ibge = ?
        GROUP BY e.id, e.nome_da_escola
        HAVING total_alunos > 0
        ORDER BY media_acertos DESC
    """, [disciplina_id, disciplina_id, current_user.codigo_ibge] + data_params + [current_user.codigo_ibge])
    escolas = cursor.fetchall()
    
    df_escolas = pd.DataFrame([dict(row) for row in escolas])
    if not df_escolas.empty:
        df_escolas = df_escolas.rename(columns={
            'escola': 'Escola',
            'total_alunos': 'Total de Alunos',
            'total_questoes': 'Total de Questões',
            'media_acertos': 'Média de Acertos (%)'
        })
    df_escolas.to_excel(writer, sheet_name='Desempenho por Escola', index=False)
    
    writer.close()
    output.seek(0)
    
    return send_file(
        output,
        download_name=f'relatorio_disciplina_{disciplina_id}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@secretaria_educacao_bp.route('/relatorio_tipo_ensino')
@login_required
def relatorio_tipo_ensino():
    """Página do relatório por tipo de ensino."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    db = get_db()
    cursor = db.cursor()
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = "strftime('%Y', data_resposta) = ?"
    data_params = [str(ano)]
    
    if mes:
        data_condition += " AND strftime('%m', data_resposta) = ?"
        data_params.append(f"{mes:02d}")
    
    # Obter dados gerais
    cursor.execute(f"""
        WITH SimuladosAlunos AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                u.escola_id,
                e.tipo_ensino_id
            FROM desempenho_simulado ds
            JOIN usuarios u ON u.id = ds.aluno_id
            JOIN escolas e ON e.id = u.escola_id
            WHERE ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            COUNT(DISTINCT sa.aluno_id) as total_alunos,
            COUNT(DISTINCT sa.simulado_id) as total_simulados,
            COUNT(sa.simulado_id) as total_questoes,
            COALESCE(AVG(sa.desempenho), 0) as media_geral
        FROM SimuladosAlunos sa
    """, [current_user.codigo_ibge] + data_params)
    dados_gerais = cursor.fetchone()
    
    # Obter dados por tipo de ensino
    cursor.execute(f"""
        WITH SimuladosAlunos AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                u.escola_id,
                e.tipo_ensino_id
            FROM desempenho_simulado ds
            JOIN usuarios u ON u.id = ds.aluno_id
            JOIN escolas e ON e.id = u.escola_id
            WHERE ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            te.nome,
            COUNT(DISTINCT sa.aluno_id) as total_alunos,
            COUNT(sa.simulado_id) as total_questoes,
            COALESCE(AVG(sa.desempenho), 0) as media
        FROM tipos_ensino te
        LEFT JOIN SimuladosAlunos sa ON sa.tipo_ensino_id = te.id
        GROUP BY te.id, te.nome
        HAVING total_alunos > 0
        ORDER BY media DESC
    """, [current_user.codigo_ibge] + data_params)
    tipos_ensino = cursor.fetchall()
    
    # Obter dados por escola
    cursor.execute(f"""
        WITH SimuladosAlunos AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                u.escola_id,
                e.tipo_ensino_id
            FROM desempenho_simulado ds
            JOIN usuarios u ON u.id = ds.aluno_id
            JOIN escolas e ON e.id = u.escola_id
            WHERE ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            e.nome_da_escola as nome,
            te.nome as tipo_ensino,
            COUNT(DISTINCT sa.aluno_id) as total_alunos,
            COUNT(sa.simulado_id) as total_questoes,
            COALESCE(AVG(sa.desempenho), 0) as media
        FROM escolas e
        JOIN tipos_ensino te ON te.id = e.tipo_ensino_id
        LEFT JOIN SimuladosAlunos sa ON sa.escola_id = e.id
        WHERE e.codigo_ibge = ?
        GROUP BY e.id, e.nome_da_escola, te.nome
        HAVING total_alunos > 0
        ORDER BY media DESC
    """, [current_user.codigo_ibge] + data_params + [current_user.codigo_ibge])
    escolas = cursor.fetchall()
    
    return render_template(
        'secretaria_educacao/relatorio_tipo_ensino.html',
        ano=ano,
        mes=mes,
        media_geral=dados_gerais['media_geral'],
        total_alunos=dados_gerais['total_alunos'],
        total_questoes=dados_gerais['total_questoes'],
        total_simulados=dados_gerais['total_simulados'],
        tipos_ensino=tipos_ensino,
        escolas=escolas
    )

@secretaria_educacao_bp.route('/relatorio_tipo_ensino/export_pdf')
@login_required
def export_pdf_tipo_ensino():
    """Exportar relatório por tipo de ensino em PDF."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    db = get_db()
    cursor = db.cursor()
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = "strftime('%Y', data_resposta) = ?"
    data_params = [str(ano)]
    
    if mes:
        data_condition += " AND strftime('%m', data_resposta) = ?"
        data_params.append(f"{mes:02d}")
    
    # Obter dados gerais
    cursor.execute(f"""
        WITH SimuladosAlunos AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                u.escola_id,
                e.tipo_ensino_id
            FROM desempenho_simulado ds
            JOIN usuarios u ON u.id = ds.aluno_id
            JOIN escolas e ON e.id = u.escola_id
            WHERE ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            COUNT(DISTINCT sa.aluno_id) as total_alunos,
            COUNT(DISTINCT sa.simulado_id) as total_simulados,
            COUNT(sa.simulado_id) as total_questoes,
            COALESCE(AVG(sa.desempenho), 0) as media_geral
        FROM SimuladosAlunos sa
    """, [current_user.codigo_ibge] + data_params)
    dados_gerais = cursor.fetchone()
    
    # Obter dados por tipo de ensino
    cursor.execute(f"""
        WITH SimuladosAlunos AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                u.escola_id,
                e.tipo_ensino_id
            FROM desempenho_simulado ds
            JOIN usuarios u ON u.id = ds.aluno_id
            JOIN escolas e ON e.id = u.escola_id
            WHERE ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            te.nome,
            COUNT(DISTINCT sa.aluno_id) as total_alunos,
            COUNT(sa.simulado_id) as total_questoes,
            COALESCE(AVG(sa.desempenho), 0) as media
        FROM tipos_ensino te
        LEFT JOIN SimuladosAlunos sa ON sa.tipo_ensino_id = te.id
        GROUP BY te.id, te.nome
        HAVING total_alunos > 0
        ORDER BY media DESC
    """, [current_user.codigo_ibge] + data_params)
    tipos_ensino = cursor.fetchall()
    
    # Obter dados por escola
    cursor.execute(f"""
        WITH SimuladosAlunos AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                u.escola_id,
                e.tipo_ensino_id
            FROM desempenho_simulado ds
            JOIN usuarios u ON u.id = ds.aluno_id
            JOIN escolas e ON e.id = u.escola_id
            WHERE ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            e.nome_da_escola as nome,
            te.nome as tipo_ensino,
            COUNT(DISTINCT sa.aluno_id) as total_alunos,
            COUNT(sa.simulado_id) as total_questoes,
            COALESCE(AVG(sa.desempenho), 0) as media
        FROM escolas e
        JOIN tipos_ensino te ON te.id = e.tipo_ensino_id
        LEFT JOIN SimuladosAlunos sa ON sa.escola_id = e.id
        WHERE e.codigo_ibge = ?
        GROUP BY e.id, e.nome_da_escola, te.nome
        HAVING total_alunos > 0
        ORDER BY media DESC
    """, [current_user.codigo_ibge] + data_params + [current_user.codigo_ibge])
    escolas = cursor.fetchall()
    
    # Renderizar o template
    html = render_template(
        'secretaria_educacao/relatorio_tipo_ensino_pdf.html',
        ano=ano,
        mes=meses.get(mes, ''),
        media_geral=dados_gerais['media_geral'],
        total_alunos=dados_gerais['total_alunos'],
        total_questoes=dados_gerais['total_questoes'],
        total_simulados=dados_gerais['total_simulados'],
        tipos_ensino=tipos_ensino,
        escolas=escolas
    )
    
    # Converter para PDF
    pdf = HTML(string=html).write_pdf()
    
    return send_file(
        BytesIO(pdf),
        download_name='relatorio_tipo_ensino.pdf',
        mimetype='application/pdf'
    )

@secretaria_educacao_bp.route('/relatorio_tipo_ensino/export_excel')
@login_required
def export_excel_tipo_ensino():
    """Exportar relatório por tipo de ensino em Excel."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    db = get_db()
    cursor = db.cursor()
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = "strftime('%Y', data_resposta) = ?"
    data_params = [str(ano)]
    
    if mes:
        data_condition += " AND strftime('%m', data_resposta) = ?"
        data_params.append(f"{mes:02d}")
    
    # Obter dados gerais
    cursor.execute(f"""
        WITH SimuladosAlunos AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                u.escola_id,
                e.tipo_ensino_id
            FROM desempenho_simulado ds
            JOIN usuarios u ON u.id = ds.aluno_id
            JOIN escolas e ON e.id = u.escola_id
            WHERE ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            COUNT(DISTINCT sa.aluno_id) as total_alunos,
            COUNT(DISTINCT sa.simulado_id) as total_simulados,
            COUNT(sa.simulado_id) as total_questoes,
            COALESCE(AVG(sa.desempenho), 0) as media_geral
        FROM SimuladosAlunos sa
    """, [current_user.codigo_ibge] + data_params)
    dados_gerais = cursor.fetchone()
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Aba Visão Geral
    df_geral = pd.DataFrame([{
        'Indicador': 'Média Geral',
        'Valor': f"{round(dados_gerais['media_geral'], 1)}%"
    }, {
        'Indicador': 'Total de Alunos',
        'Valor': str(dados_gerais['total_alunos'])
    }, {
        'Indicador': 'Total de Questões',
        'Valor': str(dados_gerais['total_questoes'])
    }, {
        'Indicador': 'Total de Simulados',
        'Valor': str(dados_gerais['total_simulados'])
    }])
    df_geral.to_excel(writer, sheet_name='Visão Geral', index=False)
    
    # Obter dados por tipo de ensino
    cursor.execute(f"""
        WITH SimuladosAlunos AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                u.escola_id,
                e.tipo_ensino_id
            FROM desempenho_simulado ds
            JOIN usuarios u ON u.id = ds.aluno_id
            JOIN escolas e ON e.id = u.escola_id
            WHERE ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            te.nome,
            COUNT(DISTINCT sa.aluno_id) as total_alunos,
            COUNT(sa.simulado_id) as total_questoes,
            COALESCE(AVG(sa.desempenho), 0) as media
        FROM tipos_ensino te
        LEFT JOIN SimuladosAlunos sa ON sa.tipo_ensino_id = te.id
        GROUP BY te.id, te.nome
        HAVING total_alunos > 0
        ORDER BY media DESC
    """, [current_user.codigo_ibge] + data_params)
    tipos_ensino = cursor.fetchall()
    
    df_tipos = pd.DataFrame([dict(row) for row in tipos_ensino])
    if not df_tipos.empty:
        df_tipos = df_tipos.rename(columns={
            'nome': 'Tipo de Ensino',
            'total_alunos': 'Total de Alunos',
            'total_questoes': 'Total de Questões',
            'media': 'Média (%)'
        })
        df_tipos['Média (%)'] = df_tipos['Média (%)'].round(1)
    df_tipos.to_excel(writer, sheet_name='Desempenho por Tipo', index=False)
    
    # Obter dados por escola
    cursor.execute(f"""
        WITH SimuladosAlunos AS (
            SELECT 
                ds.aluno_id,
                ds.simulado_id,
                ds.desempenho,
                u.escola_id,
                e.tipo_ensino_id
            FROM desempenho_simulado ds
            JOIN usuarios u ON u.id = ds.aluno_id
            JOIN escolas e ON e.id = u.escola_id
            WHERE ds.codigo_ibge = ?
            AND {data_condition}
        )
        SELECT 
            e.nome_da_escola as nome,
            te.nome as tipo_ensino,
            COUNT(DISTINCT sa.aluno_id) as total_alunos,
            COUNT(sa.simulado_id) as total_questoes,
            COALESCE(AVG(sa.desempenho), 0) as media
        FROM escolas e
        JOIN tipos_ensino te ON te.id = e.tipo_ensino_id
        LEFT JOIN SimuladosAlunos sa ON sa.escola_id = e.id
        WHERE e.codigo_ibge = ?
        GROUP BY e.id, e.nome_da_escola, te.nome
        HAVING total_alunos > 0
        ORDER BY media DESC
    """, [current_user.codigo_ibge] + data_params + [current_user.codigo_ibge])
    escolas = cursor.fetchall()
    
    df_escolas = pd.DataFrame([dict(row) for row in escolas])
    if not df_escolas.empty:
        df_escolas = df_escolas.rename(columns={
            'nome': 'Escola',
            'tipo_ensino': 'Tipo de Ensino',
            'total_alunos': 'Total de Alunos',
            'total_questoes': 'Total de Questões',
            'media': 'Média (%)'
        })
        df_escolas['Média (%)'] = df_escolas['Média (%)'].round(1)
    df_escolas.to_excel(writer, sheet_name='Desempenho por Escola', index=False)
    
    writer.close()
    output.seek(0)
    
    return send_file(
        output,
        download_name='relatorio_tipo_ensino.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@secretaria_educacao_bp.route('/relatorio_turma')
@login_required
def relatorio_turma():
    """Página de relatório por turma."""
    cursor = get_db().cursor()

    # Pegar parâmetros da URL
    escola_id = request.args.get('escola_id', type=int)
    turma_id = request.args.get('turma_id', type=int)
    ano = request.args.get('ano', default=datetime.now().year, type=int)
    mes = request.args.get('mes', type=int)

    # Construir condição de data
    data_condition = "1=1"
    data_params = []
    if mes:
        data_condition = "strftime('%m', ds.data_resposta) = ?"
        data_params = [f"{mes:02d}"]

    # Buscar todas as escolas
    cursor.execute("""
        SELECT id, nome 
        FROM escolas 
        ORDER BY nome
    """)
    escolas = [dict(id=row[0], nome=row[1]) for row in cursor.fetchall()]

    if escola_id:
        # Buscar turmas da escola selecionada
        cursor.execute("""
            SELECT t.id, t.turma,
                COUNT(DISTINCT u.id) as total_alunos,
                COUNT(DISTINCT CASE WHEN ds.id IS NOT NULL THEN u.id END) as alunos_ativos,
                COUNT(DISTINCT ds.simulado_id) as total_simulados,
                COALESCE(AVG(ds.desempenho), 0) as media
            FROM turmas t
            LEFT JOIN usuarios u ON u.turma_id = t.id AND u.tipo_usuario_id = 4
            LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id
            WHERE t.escola_id = ?
            GROUP BY t.id, t.turma
            ORDER BY t.turma
        """, [escola_id])
        turmas = [dict(row) for row in cursor.fetchall()]

        # Buscar métricas gerais da escola
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT u.id) as total_alunos,
                COUNT(DISTINCT CASE WHEN ds.id IS NOT NULL THEN u.id END) as alunos_ativos,
                COUNT(DISTINCT ds.simulado_id) as total_simulados,
                COALESCE(AVG(ds.desempenho), 0) as media_geral
            FROM usuarios u
            LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id
            WHERE u.escola_id = ? AND u.tipo_usuario_id = 4
        """, [escola_id])
        escola = dict(cursor.fetchone())

        # Buscar dados dos alunos com desempenho por disciplina
        cursor.execute(f"""
            WITH SimuladosDisciplinas AS (
                SELECT 
                    ds.aluno_id,
                    ds.simulado_id,
                    ds.desempenho,
                    COALESCE(sg.disciplina_id, sgp.disciplina_id) as disciplina_id,
                    u.turma_id
                FROM desempenho_simulado ds
                JOIN usuarios u ON u.id = ds.aluno_id
                LEFT JOIN simulados_gerados sg ON sg.id = ds.simulado_id AND ds.tipo_usuario_id = 5
                LEFT JOIN simulados_gerados_professor sgp ON sgp.id = ds.simulado_id AND ds.tipo_usuario_id = 3
                WHERE u.escola_id = ? 
                AND COALESCE(sg.disciplina_id, sgp.disciplina_id) IS NOT NULL
                AND ({data_condition})
            ),
            MediasPorDisciplina AS (
                SELECT 
                    sd.aluno_id,
                    sd.turma_id,
                    d.id as disciplina_id,
                    ROUND(AVG(sd.desempenho), 1) as media_disciplina
                FROM SimuladosDisciplinas sd
                JOIN disciplinas d ON d.id = sd.disciplina_id
                GROUP BY sd.aluno_id, sd.turma_id, d.id
            )
            SELECT 
                t.id as turma_id,
                u.id as aluno_id,
                u.nome as aluno_nome,
                COUNT(DISTINCT CASE WHEN {data_condition} THEN ds.simulado_id END) as total_simulados,
                COALESCE(AVG(CASE WHEN {data_condition} THEN ds.desempenho END), 0) as media,
                MAX(CASE WHEN mpd.disciplina_id = 2 THEN mpd.media_disciplina END) as media_matematica,
                MAX(CASE WHEN mpd.disciplina_id = 1 THEN mpd.media_disciplina END) as media_portugues,
                MAX(CASE WHEN mpd.disciplina_id = 3 THEN mpd.media_disciplina END) as media_ciencias,
                MAX(CASE WHEN mpd.disciplina_id = 4 THEN mpd.media_disciplina END) as media_historia,
                MAX(CASE WHEN mpd.disciplina_id = 5 THEN mpd.media_disciplina END) as media_geografia
            FROM turmas t
            JOIN usuarios u ON u.turma_id = t.id 
                AND u.tipo_usuario_id = 4
                AND u.escola_id = ?
            LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id 
            LEFT JOIN MediasPorDisciplina mpd ON mpd.aluno_id = u.id AND mpd.turma_id = t.id
            {f'WHERE t.id = {turma_id}' if turma_id else ''}
            GROUP BY t.id, t.turma, u.id, u.nome
            ORDER BY t.turma, u.nome
        """, [escola_id] + data_params + data_params + [escola_id])
        
        alunos = cursor.fetchall()

        return render_template('secretaria_educacao/relatorio_turma.html',
                             ano=ano,
                             mes=mes,
                             escolas=escolas,
                             escola_id=escola_id,
                             turma_id=turma_id,
                             media_geral=round(escola['media_geral'], 1),
                             total_alunos=escola['total_alunos'],
                             alunos_ativos=escola['alunos_ativos'],
                             total_simulados=escola['total_simulados'],
                             turmas=turmas,
                             alunos=alunos)
    
    return render_template('secretaria_educacao/relatorio_turma.html',
                         ano=ano,
                         mes=mes,
                         escolas=escolas,
                         escola_id=None,
                         turma_id=None)

@secretaria_educacao_bp.route('/relatorio_turma/export_pdf')
@login_required
def export_pdf_turma():
    """Exportar relatório por turma em PDF."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    db = get_db()
    cursor = db.cursor()
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = "strftime('%Y', data_resposta) = ?"
    data_params = [str(ano)]
    
    if mes:
        data_condition += " AND strftime('%m', data_resposta) = ?"
        data_params.append(f"{mes:02d}")
    
    # Obter dados gerais
    cursor.execute(f"""
        SELECT 
            COUNT(DISTINCT ds.aluno_id) as total_alunos,
            COUNT(DISTINCT ds.simulado_id) as total_simulados,
            COUNT(ds.simulado_id) as total_questoes,
            COALESCE(AVG(ds.desempenho), 0) as media_geral
        FROM desempenho_simulado ds
        JOIN usuarios u ON u.id = ds.aluno_id
        WHERE ds.codigo_ibge = ?
        AND {data_condition}
    """, [current_user.codigo_ibge] + data_params)
    dados_gerais = cursor.fetchone()
    
    # Obter dados por turma
    cursor.execute(f"""
        SELECT 
            t.turma,
            COUNT(DISTINCT ds.aluno_id) as total_alunos,
            COUNT(ds.simulado_id) as total_questoes,
            COALESCE(AVG(ds.desempenho), 0) as media
        FROM usuarios u
        JOIN turmas t ON t.id = u.turma_id
        LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id 
            AND ds.codigo_ibge = ?
            AND {data_condition}
        WHERE u.tipo_usuario_id = 1  -- Alunos
        AND u.codigo_ibge = ?
        GROUP BY t.id, t.turma
        HAVING total_alunos > 0
        ORDER BY t.turma
    """, [current_user.codigo_ibge] + data_params + [current_user.codigo_ibge])
    turmas = cursor.fetchall()
    
    # Obter dados por escola e turma
    cursor.execute(f"""
        SELECT 
            e.nome_da_escola as escola,
            t.turma,
            COUNT(DISTINCT ds.aluno_id) as total_alunos,
            COUNT(ds.simulado_id) as total_questoes,
            COALESCE(AVG(ds.desempenho), 0) as media
        FROM escolas e
        JOIN usuarios u ON u.escola_id = e.id
        JOIN turmas t ON t.id = u.turma_id
        LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id 
            AND ds.codigo_ibge = ?
            AND {data_condition}
        WHERE u.tipo_usuario_id = 1  -- Alunos
        AND e.codigo_ibge = ?
        GROUP BY e.id, e.nome_da_escola, t.id, t.turma
        HAVING total_alunos > 0
        ORDER BY e.nome_da_escola, t.turma
    """, [current_user.codigo_ibge] + data_params + [current_user.codigo_ibge])
    escolas_turmas = cursor.fetchall()
    
    # Renderizar o template
    html = render_template(
        'secretaria_educacao/relatorio_turma_pdf.html',
        ano=ano,
        mes=MESES.get(mes, ''),
        media_geral=dados_gerais['media_geral'],
        total_alunos=dados_gerais['total_alunos'],
        total_questoes=dados_gerais['total_questoes'],
        total_simulados=dados_gerais['total_simulados'],
        turmas=turmas,
        escolas_turmas=escolas_turmas
    )
    
    # Converter para PDF
    pdf = HTML(string=html).write_pdf()
    
    return send_file(
        BytesIO(pdf),
        download_name='relatorio_turma.pdf',
        mimetype='application/pdf'
    )

@secretaria_educacao_bp.route('/relatorio_turma/export_excel')
@login_required
def export_excel_turma():
    """Exportar relatório por turma em Excel."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    db = get_db()
    cursor = db.cursor()
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = "strftime('%Y', data_resposta) = ?"
    data_params = [str(ano)]
    
    if mes:
        data_condition += " AND strftime('%m', data_resposta) = ?"
        data_params.append(f"{mes:02d}")
    
    # Obter dados gerais
    cursor.execute(f"""
        SELECT 
            COUNT(DISTINCT ds.aluno_id) as total_alunos,
            COUNT(DISTINCT ds.simulado_id) as total_simulados,
            COUNT(ds.simulado_id) as total_questoes,
            COALESCE(AVG(ds.desempenho), 0) as media_geral
        FROM desempenho_simulado ds
        JOIN usuarios u ON u.id = ds.aluno_id
        WHERE ds.codigo_ibge = ?
        AND {data_condition}
    """, [current_user.codigo_ibge] + data_params)
    dados_gerais = cursor.fetchone()
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Aba Visão Geral
    df_geral = pd.DataFrame([{
        'Indicador': 'Média Geral',
        'Valor': f"{round(dados_gerais['media_geral'], 1)}%"
    }, {
        'Indicador': 'Total de Alunos',
        'Valor': str(dados_gerais['total_alunos'])
    }, {
        'Indicador': 'Total de Questões',
        'Valor': str(dados_gerais['total_questoes'])
    }, {
        'Indicador': 'Total de Simulados',
        'Valor': str(dados_gerais['total_simulados'])
    }])
    df_geral.to_excel(writer, sheet_name='Visão Geral', index=False)
    
    # Obter dados por turma
    cursor.execute(f"""
        SELECT 
            t.turma,
            COUNT(DISTINCT ds.aluno_id) as total_alunos,
            COUNT(ds.simulado_id) as total_questoes,
            COALESCE(AVG(ds.desempenho), 0) as media
        FROM usuarios u
        JOIN turmas t ON t.id = u.turma_id
        LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id 
            AND ds.codigo_ibge = ?
            AND {data_condition}
        WHERE u.tipo_usuario_id = 1  -- Alunos
        AND u.codigo_ibge = ?
        GROUP BY t.id, t.turma
        HAVING total_alunos > 0
        ORDER BY t.turma
    """, [current_user.codigo_ibge] + data_params + [current_user.codigo_ibge])
    turmas = cursor.fetchall()
    
    df_turmas = pd.DataFrame([dict(row) for row in turmas])
    if not df_turmas.empty:
        df_turmas = df_turmas.rename(columns={
            'turma': 'Turma',
            'total_alunos': 'Total de Alunos',
            'total_questoes': 'Total de Questões',
            'media': 'Média (%)'
        })
        df_turmas['Média (%)'] = df_turmas['Média (%)'].round(1)
    df_turmas.to_excel(writer, sheet_name='Desempenho por Turma', index=False)
    
    # Obter dados por escola e turma
    cursor.execute(f"""
        SELECT 
            e.nome_da_escola as escola,
            t.turma,
            COUNT(DISTINCT ds.aluno_id) as total_alunos,
            COUNT(ds.simulado_id) as total_questoes,
            COALESCE(AVG(ds.desempenho), 0) as media
        FROM escolas e
        JOIN usuarios u ON u.escola_id = e.id
        JOIN turmas t ON t.id = u.turma_id
        LEFT JOIN desempenho_simulado ds ON ds.aluno_id = u.id 
            AND ds.codigo_ibge = ?
            AND {data_condition}
        WHERE u.tipo_usuario_id = 1  -- Alunos
        AND e.codigo_ibge = ?
        GROUP BY e.id, e.nome_da_escola, t.id, t.turma
        HAVING total_alunos > 0
        ORDER BY e.nome_da_escola, t.turma
    """, [current_user.codigo_ibge] + data_params + [current_user.codigo_ibge])
    escolas_turmas = cursor.fetchall()
    
    df_escolas = pd.DataFrame([dict(row) for row in escolas_turmas])
    if not df_escolas.empty:
        df_escolas = df_escolas.rename(columns={
            'escola': 'Escola',
            'turma': 'Turma',
            'total_alunos': 'Total de Alunos',
            'total_questoes': 'Total de Questões',
            'media': 'Média (%)'
        })
        df_escolas['Média (%)'] = df_escolas['Média (%)'].round(1)
    df_escolas.to_excel(writer, sheet_name='Desempenho por Escola', index=False)
    
    writer.close()
    output.seek(0)
    
    return send_file(
        output,
        download_name='relatorio_turma.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@secretaria_educacao_bp.route('/cancelar_envio_simulado/<int:simulado_id>', methods=['POST'])
@login_required
def cancelar_envio_simulado(simulado_id):
    if current_user.tipo_usuario_id not in [5, 6]:  # Apenas secretaria de educação pode acessar
        return jsonify({'success': False, 'error': 'Acesso não autorizado'}), 403
    
    try:
        db = get_db()
        
        # Verificar se o simulado existe
        simulado = db.execute(
            'SELECT id FROM simulados_gerados WHERE id = ?',
            [simulado_id]
        ).fetchone()
        
        if not simulado:
            return jsonify({'success': False, 'error': 'Simulado não encontrado'}), 404
        
        # Remover registros de aluno_simulado
        db.execute('DELETE FROM aluno_simulado WHERE simulado_id = ?', [simulado_id])
        
        # Atualizar status para gerado
        db.execute(
            'UPDATE simulados_gerados SET status = ?, data_envio = NULL WHERE id = ?',
            ['gerado', simulado_id]
        )
        
        db.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao cancelar envio do simulado: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from flask_login import login_required, current_user
import sqlite3
import os
from werkzeug.utils import secure_filename

# Registrando o Blueprint com url_prefix
secretaria_educacao_bp = Blueprint('secretaria_educacao', __name__, url_prefix='/secretaria_educacao')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('educacional.db')
        g.db.row_factory = sqlite3.Row
    return g.db

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

@secretaria_educacao_bp.route('/criar_simulado', methods=['GET'])
@login_required
def criar_simulado():
    """Cria um novo simulado."""
    if current_user.tipo_usuario_id != 5:  # Verifica se é secretaria
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    db = get_db()
    # Buscar disciplinas
    disciplinas = db.execute('SELECT * FROM disciplinas ORDER BY nome').fetchall()
    # Buscar todas as séries
    series = db.execute('SELECT * FROM series ORDER BY nome').fetchall()
    # Buscar meses
    meses = db.execute('SELECT * FROM meses ORDER BY id').fetchall()
    
    return render_template('secretaria_educacao/criar_simulado.html', 
                         disciplinas=disciplinas,
                         series=series,
                         meses=meses)

@secretaria_educacao_bp.route('/buscar_questoes', methods=['GET'])
@login_required
def buscar_questoes():
    if current_user.tipo_usuario_id != 5:
        return jsonify({'error': 'Acesso não autorizado'}), 403

    serie_id = request.args.get('serie_id', '')
    disciplina_id = request.args.get('disciplina_id', '')
    assunto = request.args.get('assunto', '')
    
    db = get_db()
    cursor = db.cursor()

    query = """
        SELECT 
            bq.*,
            d.nome as disciplina_nome,
            s.nome as serie_nome
        FROM banco_questoes bq
        LEFT JOIN series s ON bq.serie_id = s.id
        LEFT JOIN disciplinas d ON bq.disciplina_id = d.id
        WHERE 1=1
    """
    params = []

    if serie_id:
        query += " AND bq.serie_id = ?"
        params.append(serie_id)
    
    if disciplina_id:
        query += " AND bq.disciplina_id = ?"
        params.append(disciplina_id)
    
    if assunto:
        query += " AND bq.assunto LIKE ?"
        params.append(f"%{assunto}%")

    query += " ORDER BY bq.id DESC"
    
    try:
        cursor.execute(query, params)
        questoes = cursor.fetchall()

        questoes_list = []
        for q in questoes:
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
                'serie_id': q[10],
                'mes_id': q[11],
                'disciplina_nome': q[12],
                'serie_nome': q[13]
            }
            questoes_list.append(questao)

        return jsonify(questoes_list)
    except Exception as e:
        print(f"Erro ao buscar questões: {str(e)}")
        return jsonify({'error': 'Erro ao buscar questões'}), 500

@secretaria_educacao_bp.route('/salvar_simulado', methods=['POST'])
@login_required
def salvar_simulado():
    if current_user.tipo_usuario_id != 5:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        # Pegar dados do formulário
        serie_id = request.form.get('serie_id')
        mes_id = request.form.get('mes_id')
        disciplina_id = request.form.get('disciplina_id')
        questoes = request.form.getlist('questoes[]')  # Lista de IDs das questões
        
        if not all([serie_id, mes_id, disciplina_id, questoes]):
            return jsonify({'success': False, 'message': 'Dados incompletos'}), 400
        
        # Criar novo simulado
        query = """
            INSERT INTO simulados_gerados (serie_id, mes_id, disciplina_id, status, data_envio)
            VALUES (?, ?, ?, 'gerado', CURRENT_TIMESTAMP)
        """
        cursor = get_db().cursor()
        cursor.execute(query, (serie_id, mes_id, disciplina_id))
        simulado_id = cursor.lastrowid
        
        # Inserir questões do simulado
        for questao_id in questoes:
            cursor.execute(
                "INSERT INTO simulado_questoes (simulado_id, questao_id) VALUES (?, ?)",
                (simulado_id, questao_id)
            )
        
        get_db().commit()
        return jsonify({'success': True, 'message': 'Simulado criado com sucesso!', 'simulado_id': simulado_id})
        
    except Exception as e:
        get_db().rollback()
        print(f"Erro ao salvar simulado: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao salvar simulado'}), 500

@secretaria_educacao_bp.route('/banco_questoes', methods=['GET', 'POST'])
@login_required
def banco_questoes():
    if current_user.tipo_usuario_id != 5:
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
            q.serie_id,
            q.mes_id,
            q.data_criacao,
            d.nome as disciplina_nome,
            s.nome as serie_nome
        FROM banco_questoes q
        LEFT JOIN disciplinas d ON q.disciplina_id = d.id
        LEFT JOIN series s ON q.serie_id = s.id
        ORDER BY q.id DESC
    """)
    questoes_raw = cursor.fetchall()
    
    # Buscar disciplinas e séries para os selects
    cursor.execute("SELECT * FROM disciplinas ORDER BY nome")
    disciplinas = cursor.fetchall()
    
    cursor.execute("SELECT * FROM series ORDER BY nome")
    series = cursor.fetchall()
    
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
            'serie_id': q[10],
            'mes_id': q[11],
            'data_criacao': q[12],
            'disciplina_nome': q[13],
            'serie_nome': q[14]
        }
        questoes.append(questao)
    
    return render_template('secretaria_educacao/banco_questoes.html', 
                         questoes=questoes,
                         disciplinas=disciplinas,
                         series=series)

@secretaria_educacao_bp.route('/relatorios_dashboard', methods=['GET'])
@login_required
def relatorios_dashboard():
    if current_user.tipo_usuario_id != 5:  # Apenas para Secretaria de Educação
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    db = get_db()
    cursor = db.cursor()

    # Buscar o `codigo_ibge` do usuário
    cursor.execute("SELECT codigo_ibge FROM usuarios WHERE id = ?", (current_user.id,))
    codigo_ibge= cursor.fetchone()[0]

    # Desempenho geral
    cursor.execute("""
        WITH UltimoDesempenho AS (
            SELECT 
                d.aluno_id,
                AVG(d.desempenho) as desempenho,
                ROW_NUMBER() OVER (PARTITION BY d.aluno_id ORDER BY d.data_resposta DESC) as rn
            FROM desempenho_simulado d
            JOIN usuarios u ON d.aluno_id = u.id
            WHERE u.codigo_ibge = ? AND u.tipo_usuario_id = 4
            GROUP BY d.aluno_id
        )
        SELECT AVG(desempenho) AS desempenho_geral
        FROM UltimoDesempenho
        WHERE rn = 1
    """, (codigo_ibge,))
    desempenho_geral = cursor.fetchone()[0] or 0  # Define 0 se não houver dados

    # Melhor escola
    cursor.execute("""
        WITH DesempenhoEscola AS (
            SELECT 
                u.escola_id,
                AVG(d.desempenho) as media_escola
            FROM desempenho_simulado d
            JOIN usuarios u ON d.aluno_id = u.id
            WHERE u.codigo_ibge = ? AND u.tipo_usuario_id = 4
            GROUP BY u.escola_id
        )
        SELECT e.nome_da_escola, de.media_escola
        FROM escolas e
        JOIN DesempenhoEscola de ON e.id = de.escola_id
        WHERE e.codigo_ibge = ?
        ORDER BY de.media_escola DESC
        LIMIT 1
    """, (codigo_ibge, codigo_ibge))
    melhor_escola = cursor.fetchone() or ("Nenhuma escola", 0)  # Define valores padrão se não houver dados

    # Desempenho geral por mês
    cursor.execute("""
        WITH DesempenhoMensal AS (
            SELECT 
                d.aluno_id,
                AVG(d.desempenho) as media_desempenho,
                CASE strftime('%m', d.data_resposta)
                    WHEN '01' THEN 'Janeiro'
                    WHEN '02' THEN 'Fevereiro'
                    WHEN '03' THEN 'Março'
                    WHEN '04' THEN 'Abril'
                    WHEN '05' THEN 'Maio'
                    WHEN '06' THEN 'Junho'
                    WHEN '07' THEN 'Julho'
                    WHEN '08' THEN 'Agosto'
                    WHEN '09' THEN 'Setembro'
                    WHEN '10' THEN 'Outubro'
                    WHEN '11' THEN 'Novembro'
                    WHEN '12' THEN 'Dezembro'
                END as mes_nome,
                strftime('%m', d.data_resposta) as mes_numero
            FROM desempenho_simulado d
            JOIN usuarios u ON d.aluno_id = u.id
            WHERE u.codigo_ibge = ? AND u.tipo_usuario_id = 4
            GROUP BY d.aluno_id, strftime('%m', d.data_resposta)
        )
        SELECT 
            mes_nome, 
            AVG(media_desempenho) AS media_desempenho
        FROM DesempenhoMensal
        GROUP BY mes_nome, mes_numero
        ORDER BY mes_numero
    """, (codigo_ibge,))
    desempenho_mensal = cursor.fetchall()

    # Ranking de escolas
    cursor.execute("""
        WITH DesempenhoEscola AS (
            SELECT 
                u.escola_id,
                AVG(d.desempenho) as media_escola
            FROM desempenho_simulado d
            JOIN usuarios u ON d.aluno_id = u.id
            WHERE u.codigo_ibge = ? AND u.tipo_usuario_id = 4
            GROUP BY u.escola_id
        )
        SELECT e.nome_da_escola, de.media_escola
        FROM escolas e
        JOIN DesempenhoEscola de ON e.id = de.escola_id
        WHERE e.codigo_ibge = ?
        ORDER BY de.media_escola DESC
    """, (codigo_ibge, codigo_ibge))
    ranking_escolas = cursor.fetchall()

    # Ranking dos 5 melhores alunos por ano escolar
    cursor.execute("""
        WITH DesempenhoAluno AS (
            SELECT 
                d.aluno_id,
                AVG(d.desempenho) as media_desempenho
            FROM desempenho_simulado d
            JOIN usuarios u ON d.aluno_id = u.id
            WHERE u.codigo_ibge = ? AND u.tipo_usuario_id = 4
            GROUP BY d.aluno_id
        )
        SELECT s.nome AS ano_escolar, u.nome AS aluno, da.media_desempenho AS media_aluno
        FROM series s
        JOIN usuarios u ON s.id = u.serie_id
        JOIN DesempenhoAluno da ON u.id = da.aluno_id
        ORDER BY s.id, media_aluno DESC
        LIMIT 5
    """, (codigo_ibge,))
    ranking_alunos = cursor.fetchall()

    # Contagem de alunos por faixa de desempenho
    cursor.execute("""
        WITH DesempenhoMedioAluno AS (
            SELECT 
                d.aluno_id,
                AVG(d.desempenho) as media_desempenho
            FROM desempenho_simulado d
            JOIN usuarios u ON d.aluno_id = u.id
            WHERE u.codigo_ibge = ? AND u.tipo_usuario_id = 4
            GROUP BY d.aluno_id
        )
        SELECT 
            COUNT(CASE WHEN media_desempenho BETWEEN 0 AND 20 THEN 1 END) as faixa_0_20,
            COUNT(CASE WHEN media_desempenho BETWEEN 21 AND 40 THEN 1 END) as faixa_21_40,
            COUNT(CASE WHEN media_desempenho BETWEEN 41 AND 60 THEN 1 END) as faixa_41_60,
            COUNT(CASE WHEN media_desempenho BETWEEN 61 AND 80 THEN 1 END) as faixa_61_80,
            COUNT(CASE WHEN media_desempenho BETWEEN 81 AND 100 THEN 1 END) as faixa_81_100
        FROM DesempenhoMedioAluno
    """, (codigo_ibge,))
    faixas = cursor.fetchone()

    return render_template(
        'secretaria_educacao/relatorios_dashboard.html',
        desempenho_geral=desempenho_geral,
        melhor_escola=melhor_escola,
        desempenho_mensal=desempenho_mensal,
        ranking_escolas=ranking_escolas,
        ranking_alunos=ranking_alunos,
        faixa_0_20=faixas[0],
        faixa_21_40=faixas[1],
        faixa_41_60=faixas[2],
        faixa_61_80=faixas[3],
        faixa_81_100=faixas[4]
    )

@secretaria_educacao_bp.route("/portal_secretaria_educacao", methods=["GET", "POST"])
@login_required
def portal_secretaria_educacao():
    if current_user.tipo_usuario_id != 5:  # Verifica se é uma Secretaria de Educação
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    db = get_db()
    cursor = db.cursor()

    # Buscar o codigo_ibge do usuário atual (Secretaria de Educação)
    cursor.execute("SELECT codigo_ibge FROM usuarios WHERE id = ?", (current_user.id,))
    codigo_ibge = cursor.fetchone()[0]

    # Buscar escolas que têm o mesmo codigo_ibge
    cursor.execute("""
        SELECT id, nome_da_escola
        FROM escolas
        WHERE codigo_ibge = ?
    """, (codigo_ibge,))
    escolas = cursor.fetchall()

    # Buscar o número total de escolas
    total_escolas = len(escolas)

    # Buscar o número de alunos na mesma codigo_ibge
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE tipo_usuario_id = 4 AND codigo_ibge = ?", (codigo_ibge,))
    numero_alunos = cursor.fetchone()[0]

    # Buscar o número de simulados gerados na mesma codigo_ibge
    cursor.execute("""
        SELECT COUNT(*)
        FROM simulados_gerados sg
        JOIN usuarios u ON sg.serie_id = u.serie_id
        WHERE u.codigo_ibge = ?
    """, (codigo_ibge,))
    numero_simulados_gerados = cursor.fetchone()[0]

    # Calcular a média geral de desempenho dos simulados respondidos na mesma codigo_ibge
    cursor.execute("""
        SELECT AVG(d.desempenho)
        FROM desempenho_simulado d
        JOIN usuarios u ON d.aluno_id = u.id
        WHERE u.codigo_ibge = ?
    """, (codigo_ibge,))
    media_geral = cursor.fetchone()[0] or 0

    # Buscar simulados já gerados
    cursor.execute("""
        SELECT sg.id, s.nome AS serie_nome, sg.mes_id, d.nome AS disciplina_nome, 
           sg.data_envio, sg.status
        FROM simulados_gerados sg
        JOIN series s ON sg.serie_id = s.id
        JOIN disciplinas d ON sg.disciplina_id = d.id
        ORDER BY sg.data_envio DESC
    """)
    simulados_gerados = cursor.fetchall()

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
    if current_user.tipo_usuario_id != 5:  # Verifica se é uma Secretaria de Educação
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
    if current_user.tipo_usuario_id != 5:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    db = get_db()
    cursor = db.cursor()

    # Buscar simulados gerados pela secretaria
    cursor.execute("""
        SELECT sg.*, s.nome as serie_nome, m.nome as mes_nome,
               d.nome as disciplina_nome,
               COUNT(DISTINCT r.aluno_id) as total_responderam,
               COUNT(DISTINCT sq.questao_id) as total_questoes
        FROM simulados_gerados sg
        JOIN series s ON sg.serie_id = s.id
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
    if current_user.tipo_usuario_id != 5:
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
    if current_user.tipo_usuario_id != 5:
        flash('Acesso não autorizado', 'danger')
        return redirect(url_for('secretaria_educacao.portal_secretaria_educacao'))
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Buscar dados do simulado
        cursor.execute("""
            SELECT 
                sg.*,
                s.nome as serie_nome,
                d.nome as disciplina_nome,
                m.nome as mes_nome
            FROM simulados_gerados sg
            JOIN series s ON sg.serie_id = s.id
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
            'serie_id': simulado[1],
            'mes_id': simulado[2],
            'disciplina_id': simulado[3],
            'status': simulado[4],
            'data_envio': simulado[5],
            'serie_nome': simulado[6],
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
    if current_user.tipo_usuario_id != 5:
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
    if current_user.tipo_usuario_id != 5:  # Verifica se é uma Secretaria de Educação
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
    if current_user.tipo_usuario_id != 5:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Buscar questão
        cursor.execute("""
            SELECT q.*, d.nome as disciplina_nome, s.nome as serie_nome
            FROM banco_questoes q
            LEFT JOIN disciplinas d ON q.disciplina_id = d.id
            LEFT JOIN series s ON q.serie_id = s.id
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
                'serie_id': questao[10],
                'serie_nome': questao[13],  # Agora é o nome do ano escolar
                'mes_id': questao[11],
                'mes_nome': mes_nome
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@secretaria_educacao_bp.route('/atualizar_questao/<int:questao_id>', methods=['POST'])
@login_required
def atualizar_questao(questao_id):
    if current_user.tipo_usuario_id != 5:
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
        serie_id = request.form.get('serie_id')
        mes_id = request.form.get('mes_id')
        
        # Converte para None se vazio
        serie_id = None if not serie_id else int(serie_id)
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
                serie_id = ?,
                mes_id = ?
            WHERE id = ?
        """, (questao, alternativa_a, alternativa_b, alternativa_c, alternativa_d,
              alternativa_e, questao_correta, disciplina_id, assunto, serie_id, mes_id, questao_id))
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Questão atualizada com sucesso!'
        })
    except Exception as e:
        print(f"Erro ao atualizar questão: {str(e)}")  # Log do erro
        return jsonify({'success': False, 'message': str(e)}), 500

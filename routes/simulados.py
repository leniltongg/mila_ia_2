from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g, abort
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
import sqlite3

simulados_bp = Blueprint('simulados', __name__)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('educacional.db')
        g.db.row_factory = sqlite3.Row
    return g.db

@simulados_bp.teardown_app_request
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Rotas para professores
@simulados_bp.route('/professores/banco-questoes')
@login_required
def banco_questoes():
    if current_user.tipo_usuario_id != 3:  # 1 = professor
        abort(403)
    return render_template('professores/banco_questoes.html')

@simulados_bp.route('/professores/criar-simulado')
@login_required
def criar_simulado():
    if current_user.tipo_usuario_id != 3:  # 3 = professor
        abort(403)
    
    db = get_db()
    cursor = db.cursor()
    
    # Verificar se é edição
    simulado_id = request.args.get('id', type=int)
    simulado_data = None
    questoes_selecionadas = []
    
    if simulado_id:
        # Buscar dados do simulado
        cursor.execute("""
            SELECT 
                sgp.id,
                sgp.professor_id,
                sgp.disciplina_id,
                sgp.serie_id,
                sgp.mes_id,
                sgp.status,
                d.nome as disciplina_nome,
                s.nome as serie_nome,
                m.nome as mes_nome
            FROM simulados_gerados_professor sgp
            JOIN disciplinas d ON d.id = sgp.disciplina_id
            JOIN series s ON s.id = sgp.serie_id
            JOIN meses m ON m.id = sgp.mes_id
            WHERE sgp.id = ? AND sgp.professor_id = ?
        """, [simulado_id, current_user.id])
        simulado = cursor.fetchone()
        
        if simulado:
            # Verificar se o status é 'gerado'
            if simulado[5] != 'gerado':
                flash('Não é possível editar um simulado que já foi enviado. Cancele o envio primeiro.', 'warning')
                return redirect(url_for('simulados.listar_simulados_professor'))
            
            # Converter a tupla em um dicionário com todos os dados necessários
            simulado_data = {
                'id': simulado[0],
                'professor_id': simulado[1],
                'disciplina_id': simulado[2],
                'serie_id': simulado[3],
                'mes_id': simulado[4],
                'status': simulado[5],
                'disciplina_nome': simulado[6],
                'serie_nome': simulado[7],
                'mes_nome': simulado[8]
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
                    bq.serie_id,
                    bq.mes_id
                FROM simulado_questoes_professor sqp
                JOIN banco_questoes bq ON bq.id = sqp.questao_id
                WHERE sqp.simulado_id = ?
                ORDER BY sqp.id
            """, [simulado_id])
            questoes = cursor.fetchall()
            
            questoes_selecionadas = [{
                'id': q[0],
                'enunciado': q[1],
                'alternativas': {
                    'a': q[2],
                    'b': q[3],
                    'c': q[4],
                    'd': q[5],
                    'e': q[6] if q[6] else None
                },
                'resposta': q[7],
                'assunto': q[8],
                'disciplina_id': q[9],
                'serie_id': q[10],
                'mes_id': q[11]
            } for q in questoes]

    # Buscar séries que o professor está alocado
    cursor.execute("""
        SELECT DISTINCT s.id, s.nome
        FROM series s
        JOIN professor_turma_escola pte ON pte.professor_id = ?
        JOIN turmas t ON t.serie_id = s.id AND t.id = pte.turma_id
        ORDER BY s.nome
    """, [current_user.id])
    series = [{'id': row[0], 'nome': row[1]} for row in cursor.fetchall()]

    # Buscar disciplinas
    cursor.execute("SELECT id, nome FROM disciplinas ORDER BY nome")
    disciplinas = [{'id': row[0], 'nome': row[1]} for row in cursor.fetchall()]

    # Buscar meses
    cursor.execute("SELECT id, nome FROM meses ORDER BY id")
    meses = [{'id': row[0], 'nome': row[1]} for row in cursor.fetchall()]

    return render_template('professores/criar_simulado.html', 
                         series=series,
                         disciplinas=disciplinas,
                         meses=meses,
                         simulado=simulado_data,
                         questoes_selecionadas=questoes_selecionadas)

@simulados_bp.route('/professores/salvar-simulado', methods=['POST'])
@simulados_bp.route('/professores/salvar-simulado/<int:simulado_id>', methods=['POST'])
@login_required
def salvar_simulado(simulado_id=None):
    if current_user.tipo_usuario_id != 3:  # 3 = professor
        return jsonify({'success': False, 'error': 'Acesso negado'})
    
    try:
        data = request.get_json()
        print("Dados recebidos:", data)  # Debug
        
        serie_id = data.get('serie_id')
        disciplina_id = data.get('disciplina_id')
        mes_id = data.get('mes_id')
        questoes = data.get('questoes', [])
        
        if not all([serie_id, disciplina_id, mes_id]) or not questoes:
            return jsonify({'success': False, 'error': 'Dados incompletos'})
        
        db = get_db()
        cursor = db.cursor()
        
        if simulado_id:
            # Verificar se o simulado existe e pertence ao professor
            cursor.execute("""
                SELECT status FROM simulados_gerados_professor 
                WHERE id = ? AND professor_id = ?
            """, [simulado_id, current_user.id])
            simulado = cursor.fetchone()
            
            if not simulado:
                return jsonify({'success': False, 'error': 'Simulado não encontrado'})
            
            if simulado[0] != 'gerado':
                return jsonify({'success': False, 'error': 'Não é possível editar um simulado que já foi enviado'})
            
            print(f"Atualizando simulado {simulado_id}")  # Debug
            
            # Atualizar simulado
            cursor.execute("""
                UPDATE simulados_gerados_professor 
                SET serie_id = ?, disciplina_id = ?, mes_id = ?
                WHERE id = ? AND professor_id = ?
            """, [serie_id, disciplina_id, mes_id, simulado_id, current_user.id])
            
            # Remover questões antigas
            cursor.execute("DELETE FROM simulado_questoes_professor WHERE simulado_id = ?", [simulado_id])
            
            # Inserir novas questões
            for questao_id in questoes:
                cursor.execute("""
                    INSERT INTO simulado_questoes_professor (simulado_id, questao_id)
                    VALUES (?, ?)
                """, [simulado_id, questao_id])
                
            print(f"Inseridas {len(questoes)} questões")  # Debug
        else:
            # Criar novo simulado
            cursor.execute("""
                INSERT INTO simulados_gerados_professor (professor_id, serie_id, disciplina_id, mes_id, status)
                VALUES (?, ?, ?, ?, 'gerado')
            """, [current_user.id, serie_id, disciplina_id, mes_id])
            
            simulado_id = cursor.lastrowid
            print(f"Criado novo simulado {simulado_id}")  # Debug
            
            # Inserir questões
            for questao_id in questoes:
                cursor.execute("""
                    INSERT INTO simulado_questoes_professor (simulado_id, questao_id)
                    VALUES (?, ?)
                """, [simulado_id, questao_id])
            
            print(f"Inseridas {len(questoes)} questões")  # Debug
        
        db.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Erro ao salvar simulado: {str(e)}")  # Debug
        db.rollback()
        return jsonify({'success': False, 'error': str(e)})

@simulados_bp.route('/professores/salvar-questao', methods=['POST'])
@login_required
def salvar_questao():
    if current_user.tipo_usuario_id != 3:  # 1 = professor
        abort(403)
    
    try:
        data = request.get_json()
        db = get_db()
        
        # Preparar dados
        alternativas = json.dumps(data.get('alternativas')) if data.get('alternativas') else None
        
        # Inserir questão
        cursor = db.execute('''
            INSERT INTO banco_questoes (
                professor_id, disciplina, assunto, nivel, tipo,
                enunciado, alternativas, resposta_correta, explicacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            current_user.id, data['disciplina'], data['assunto'],
            data['nivel'], data['tipo'], data['enunciado'],
            alternativas, data['resposta'], data.get('explicacao')
        ))
        
        db.commit()
        
        return jsonify({
            'success': True,
            'id': cursor.lastrowid
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@simulados_bp.route('/professores/pesquisar-questoes')
@login_required
def pesquisar_questoes():
    if current_user.tipo_usuario_id != 3:  # 1 = professor
        abort(403)
    
    try:
        # Parâmetros de filtro
        disciplina = request.args.get('disciplina')
        assunto = request.args.get('assunto')
        nivel = request.args.get('nivel')
        tipo = request.args.get('tipo')
        pagina = int(request.args.get('pagina', 1))
        por_pagina = 10
        
        # Construir query
        query = 'SELECT * FROM banco_questoes WHERE 1=1'
        params = []
        
        if disciplina:
            query += ' AND disciplina = ?'
            params.append(disciplina)
        if assunto:
            query += ' AND assunto LIKE ?'
            params.append(f'%{assunto}%')
        if nivel:
            query += ' AND nivel = ?'
            params.append(nivel)
        if tipo:
            query += ' AND tipo = ?'
            params.append(tipo)
        
        # Adicionar paginação
        query += ' ORDER BY id DESC LIMIT ? OFFSET ?'
        params.extend([por_pagina, (pagina - 1) * por_pagina])
        
        # Executar query
        db = get_db()
        questoes = db.execute(query, params).fetchall()
        
        # Contar total para paginação
        total = db.execute(query.split('ORDER BY')[0].replace('*', 'COUNT(*)'), 
                          params[:-2]).fetchone()[0]
        
        return jsonify({
            'success': True,
            'questoes': [{
                'id': q['id'],
                'disciplina': q['disciplina'],
                'assunto': q['assunto'],
                'nivel': q['nivel'],
                'tipo': q['tipo'],
                'enunciado': q['enunciado'],
                'alternativas': json.loads(q['alternativas']) if q['alternativas'] else None,
                'resposta': q['resposta_correta'],
                'explicacao': q['explicacao']
            } for q in questoes],
            'total_paginas': (total + por_pagina - 1) // por_pagina
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@simulados_bp.route('/professores/simulados')
@login_required
def listar_simulados_professor():
    if current_user.tipo_usuario_id != 3:  # Apenas professores podem acessar
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
        
    db = get_db()
    
    # Buscar simulados criados pelo professor
    simulados = db.execute("""
        SELECT 
            sgp.id,
            d.nome as disciplina_nome,
            m.nome as mes_nome,
            sgp.data_criacao,
            (
                SELECT COUNT(DISTINCT sqp.id)
                FROM simulado_questoes_professor sqp
                WHERE sqp.simulado_id = sgp.id
            ) as total_questoes,
            (
                SELECT COUNT(DISTINCT asi.aluno_id)
                FROM aluno_simulado asi
                WHERE asi.simulado_id = sgp.id
            ) as total_alunos_responderam,
            CASE 
                WHEN EXISTS (
                    SELECT 1 
                    FROM aluno_simulado asi 
                    WHERE asi.simulado_id = sgp.id
                ) THEN 'enviado'
                ELSE sgp.status 
            END as status
        FROM simulados_gerados_professor sgp
        JOIN disciplinas d ON d.id = sgp.disciplina_id
        JOIN meses m ON m.id = sgp.mes_id
        WHERE sgp.professor_id = ?
        ORDER BY sgp.data_criacao DESC
    """, [current_user.id]).fetchall()
    
    return render_template('professores/listar_simulados.html', simulados=simulados)

@simulados_bp.route('/professores/visualizar-simulado/<int:simulado_id>')
@login_required
def visualizar_simulado_professor(simulado_id):
    if current_user.tipo_usuario_id != 3:  # Apenas professores podem acessar
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
        
    db = get_db()
    
    # Buscar informações do simulado
    simulado = db.execute("""
        SELECT 
            sgp.id,
            sgp.status,
            d.nome as disciplina_nome,
            se.nome as serie_nome,
            m.nome as mes_nome,
            strftime('%d/%m/%Y', sgp.data_criacao) as data_criacao,
            (
                SELECT COUNT(DISTINCT a.id)
                FROM aluno_simulado asi
                JOIN usuarios a ON a.id = asi.aluno_id
                WHERE asi.simulado_id = sgp.id
            ) as total_alunos_responderam
        FROM simulados_gerados_professor sgp
        JOIN disciplinas d ON d.id = sgp.disciplina_id
        JOIN series se ON se.id = sgp.serie_id
        JOIN meses m ON m.id = sgp.mes_id
        WHERE sgp.id = ? AND sgp.professor_id = ?
    """, [simulado_id, current_user.id]).fetchone()
    
    if not simulado:
        flash("Simulado não encontrado.", "danger")
        return redirect(url_for("simulados.listar_simulados_professor"))
    
    # Buscar questões do simulado
    questoes = db.execute("""
        SELECT 
            bq.id,
            bq.questao,
            bq.alternativa_a,
            bq.alternativa_b,
            bq.alternativa_c,
            bq.alternativa_d,
            bq.alternativa_e,
            bq.questao_correta,
            bq.assunto
        FROM simulado_questoes_professor sqp
        JOIN banco_questoes bq ON bq.id = sqp.questao_id
        WHERE sqp.simulado_id = ?
        ORDER BY sqp.id
    """, [simulado_id]).fetchall()
    
    # Buscar alunos que responderam
    alunos = db.execute("""
        SELECT 
            u.nome as aluno_nome,
            ds.desempenho,
            strftime('%d/%m/%Y %H:%M', ds.data_resposta) as data_resposta
        FROM aluno_simulado asi
        JOIN usuarios u ON u.id = asi.aluno_id
        LEFT JOIN desempenho_simulado ds ON ds.simulado_id = asi.simulado_id 
            AND ds.aluno_id = asi.aluno_id
        WHERE asi.simulado_id = ?
        ORDER BY u.nome
    """, [simulado_id]).fetchall()
    
    return render_template('professores/visualizar_simulado.html', 
                         simulado=simulado,
                         questoes=questoes,
                         alunos=alunos)

@simulados_bp.route('/professores/api/visualizar-simulado/<int:simulado_id>')
@login_required
def visualizar_simulado_professor_json(simulado_id):
    if current_user.tipo_usuario_id != 3:  # Apenas professores podem acessar
        return jsonify({"error": "Acesso não autorizado"}), 403
        
    db = get_db()
    
    # Buscar informações do simulado
    simulado = db.execute("""
        SELECT 
            sgp.id,
            sgp.status,
            d.nome as disciplina_nome,
            se.nome as serie_nome,
            m.nome as mes_nome,
            strftime('%d/%m/%Y', sgp.data_criacao) as data_criacao
        FROM simulados_gerados_professor sgp
        JOIN disciplinas d ON d.id = sgp.disciplina_id
        JOIN series se ON se.id = sgp.serie_id
        JOIN meses m ON m.id = sgp.mes_id
        WHERE sgp.id = ? AND sgp.professor_id = ?
    """, [simulado_id, current_user.id]).fetchone()
    
    if not simulado:
        return jsonify({"error": "Simulado não encontrado"}), 404
    
    # Buscar questões do simulado
    questoes = db.execute("""
        SELECT 
            bq.id,
            bq.questao as enunciado,
            bq.alternativa_a,
            bq.alternativa_b,
            bq.alternativa_c,
            bq.alternativa_d,
            bq.alternativa_e,
            bq.questao_correta,
            bq.assunto
        FROM simulado_questoes_professor sqp
        JOIN banco_questoes bq ON bq.id = sqp.questao_id
        WHERE sqp.simulado_id = ?
        ORDER BY sqp.id
    """, [simulado_id]).fetchall()
    
    # Formatar questões para JSON
    questoes_formatadas = []
    for q in questoes:
        alternativas = [
            {"letra": "A", "texto": q["alternativa_a"], "correta": q["questao_correta"] == "a"},
            {"letra": "B", "texto": q["alternativa_b"], "correta": q["questao_correta"] == "b"},
            {"letra": "C", "texto": q["alternativa_c"], "correta": q["questao_correta"] == "c"},
            {"letra": "D", "texto": q["alternativa_d"], "correta": q["questao_correta"] == "d"}
        ]
        if q["alternativa_e"]:
            alternativas.append({"letra": "E", "texto": q["alternativa_e"], "correta": q["questao_correta"] == "e"})
            
        questoes_formatadas.append({
            "id": q["id"],
            "enunciado": q["enunciado"],
            "alternativas": alternativas,
            "assunto": q["assunto"]
        })
    
    return jsonify({
        "id": simulado["id"],
        "status": simulado["status"],
        "disciplina_nome": simulado["disciplina_nome"],
        "serie_nome": simulado["serie_nome"],
        "mes_nome": simulado["mes_nome"],
        "data_criacao": simulado["data_criacao"],
        "questoes": questoes_formatadas
    })

# Rotas para alunos
@simulados_bp.route('/alunos/simulados')
@login_required
def listar_simulados():
    if current_user.tipo_usuario_id != 4:  # Apenas alunos podem acessar
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
        
    db = get_db()
    
    # Buscar simulados do aluno, ordenando por status (não respondido primeiro) e data
    simulados = db.execute("""
        SELECT sgp.id, d.nome AS disciplina_nome, sgp.mes_id, 
               strftime('%d-%m-%Y', date(sgp.data_criacao)) as data_envio,
               am.status, u.nome as professor_nome,
               ds.desempenho as nota
        FROM aluno_simulado am
        JOIN simulados_gerados_professor sgp ON am.simulado_id = sgp.id
        JOIN disciplinas d ON sgp.disciplina_id = d.id
        JOIN usuarios u ON sgp.professor_id = u.id
        LEFT JOIN desempenho_simulado ds ON ds.simulado_id = sgp.id 
            AND ds.aluno_id = am.aluno_id
        WHERE am.aluno_id = ?
        ORDER BY 
            CASE am.status
                WHEN 'não respondido' THEN 0
                ELSE 1
            END,
            sgp.data_criacao DESC
    """, [current_user.id]).fetchall()
    
    # Lista de meses para exibição
    meses = [
        (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"),
        (4, "Abril"), (5, "Maio"), (6, "Junho"),
        (7, "Julho"), (8, "Agosto"), (9, "Setembro"),
        (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
    ]
    
    return render_template('alunos/simulados.html', simulados=simulados, meses=meses)

@simulados_bp.route('/alunos/iniciar-simulado/<int:simulado_id>', methods=['POST'])
@login_required
def iniciar_simulado(simulado_id):
    if current_user.tipo_usuario_id != 4:  # Apenas alunos podem acessar
        abort(403)
    
    try:
        db = get_db()
        origem = request.args.get('origem')
        
        # Verificar se o simulado existe e está atribuído ao aluno
        simulado = None
        if origem == 'professor':
            simulado = db.execute('''
                SELECT sgp.*, am.status
                FROM simulados_gerados_professor sgp
                JOIN aluno_simulado am ON sgp.id = am.simulado_id
                WHERE sgp.id = ? AND am.aluno_id = ?
            ''', [simulado_id, current_user.id]).fetchone()
        else:
            simulado = db.execute('''
                SELECT sg.*, am.status
                FROM simulados_gerados sg
                JOIN aluno_simulado am ON sg.id = am.simulado_id
                WHERE sg.id = ? AND am.aluno_id = ?
            ''', [simulado_id, current_user.id]).fetchone()
        
        if not simulado:
            return 'Simulado não encontrado ou não atribuído ao aluno', 404
            
        if simulado['status'] != 'não respondido':
            return 'Este simulado já foi iniciado ou respondido', 400
            
        # Atualizar status do simulado para 'em andamento'
        db.execute('''
            UPDATE aluno_simulado 
            SET status = 'em andamento'
            WHERE simulado_id = ? AND aluno_id = ?
        ''', [simulado_id, current_user.id])
        
        db.commit()
        
        return redirect(url_for('simulados.fazer_simulado', simulado_id=simulado_id, origem=origem))
        
    except Exception as e:
        return f'Erro ao iniciar simulado: {str(e)}', 500

@simulados_bp.route('/alunos/fazer-simulado/<int:simulado_id>')
@login_required
def fazer_simulado(simulado_id):
    if current_user.tipo_usuario_id != 4:  # Apenas alunos podem acessar
        abort(403)
    
    try:
        db = get_db()
        
        # Verificar se o aluno já iniciou o simulado
        aluno_simulado = db.execute("""
            SELECT status FROM aluno_simulado
            WHERE simulado_id = ? AND aluno_id = ?
        """, [simulado_id, current_user.id]).fetchone()

        if not aluno_simulado:
            flash("Você precisa iniciar o simulado primeiro.", "warning")
            return redirect(url_for('simulados.listar_simulados'))
        
        # Buscar informações do simulado e status
        simulado = db.execute('''
            SELECT sg.*, d.nome as disciplina_nome, am.status,
                   (SELECT COUNT(*) FROM banco_questoes q
                    JOIN simulado_questoes sq ON q.id = sq.questao_id
                    WHERE sq.simulado_id = sg.id) as total_questoes
            FROM simulados_gerados sg
            JOIN aluno_simulado am ON sg.id = am.simulado_id
            JOIN disciplinas d ON sg.disciplina_id = d.id
            WHERE sg.id = ? AND am.aluno_id = ?
        ''', [simulado_id, current_user.id]).fetchone()
        
        if not simulado:
            return 'Simulado não encontrado ou não atribuído ao aluno', 404
            
        if simulado['status'] == 'respondido':
            return 'Este simulado já foi respondido', 400
            
        # Buscar questões do simulado
        questoes = db.execute('''
            SELECT q.*, sq.ordem
            FROM banco_questoes q
            JOIN simulado_questoes sq ON q.id = sq.questao_id
            WHERE sq.simulado_id = ?
            ORDER BY sq.ordem
        ''', [simulado_id]).fetchall()
        
        # Buscar respostas já dadas pelo aluno (se houver)
        respostas = db.execute('''
            SELECT ds.respostas_aluno
            FROM desempenho_simulado ds
            WHERE ds.simulado_id = ? AND ds.aluno_id = ?
        ''', [simulado_id, current_user.id]).fetchone()
        
        respostas_aluno = json.loads(respostas['respostas_aluno']) if respostas and respostas['respostas_aluno'] else {}
        
        return render_template('alunos/fazer_simulado.html',
                             simulado=simulado,
                             questoes=questoes,
                             respostas_aluno=respostas_aluno)
        
    except Exception as e:
        return f'Erro ao carregar simulado: {str(e)}', 500

@simulados_bp.route('/alunos/salvar-resposta', methods=['POST'])
@login_required
def salvar_resposta():
    if current_user.tipo_usuario_id != 4:  # Apenas alunos podem acessar
        abort(403)
    
    try:
        data = request.get_json()
        simulado_id = data.get('simulado_id')
        questao_id = data.get('questao_id')
        resposta = data.get('resposta')
        
        if not all([simulado_id, questao_id, resposta]):
            return 'Dados incompletos', 400
            
        db = get_db()
        
        # Verificar se o simulado existe e está em andamento
        simulado = db.execute('''
            SELECT sg.*, am.status
            FROM simulados_gerados sg
            JOIN aluno_simulado am ON sg.id = am.simulado_id
            WHERE sg.id = ? AND am.aluno_id = ?
        ''', [simulado_id, current_user.id]).fetchone()
        
        if not simulado:
            return 'Simulado não encontrado', 404
            
        if simulado['status'] != 'em andamento':
            return 'Simulado não está em andamento', 400
            
        # Buscar respostas atuais do aluno
        resultado = db.execute('''
            SELECT ds.respostas_aluno
            FROM desempenho_simulado ds
            WHERE ds.simulado_id = ? AND ds.aluno_id = ?
        ''', [simulado_id, current_user.id]).fetchone()
        
        # Se não existe registro no desempenho_simulado, criar
        if not resultado:
            # Buscar informações do aluno
            aluno = db.execute('''
                SELECT escola_id, serie_id, codigo_ibge, turma_id
                FROM usuarios
                WHERE id = ?
            ''', [current_user.id]).fetchone()
            
            # Criar registro inicial
            db.execute('''
                INSERT INTO desempenho_simulado (
                    aluno_id, simulado_id, escola_id, serie_id,
                    codigo_ibge, respostas_aluno, respostas_corretas,
                    desempenho, data_resposta, turma_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP, ?)
            ''', [
                current_user.id, simulado_id,
                aluno['escola_id'], aluno['serie_id'],
                aluno['codigo_ibge'],
                json.dumps({}), json.dumps({}),
                aluno['turma_id']
            ])
            respostas_aluno = {}
        else:
            respostas_aluno = json.loads(resultado['respostas_aluno']) if resultado['respostas_aluno'] else {}
        
        # Atualizar resposta
        respostas_aluno[str(questao_id)] = resposta
        
        # Salvar respostas atualizadas
        db.execute('''
            UPDATE desempenho_simulado
            SET respostas_aluno = ?
            WHERE simulado_id = ? AND aluno_id = ?
        ''', [json.dumps(respostas_aluno), simulado_id, current_user.id])
        
        db.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.rollback()
        return f'Erro ao salvar resposta: {str(e)}', 500

@simulados_bp.route('/alunos/finalizar-simulado/<int:simulado_id>', methods=['POST'])
@login_required
def finalizar_simulado(simulado_id):
    if current_user.tipo_usuario_id != 4:  # Apenas alunos podem acessar
        abort(403)
    
    try:
        db = get_db()
        
        # Verificar se o simulado existe e está em andamento
        simulado = db.execute('''
            SELECT sg.*, am.status
            FROM simulados_gerados sg
            JOIN aluno_simulado am ON sg.id = am.simulado_id
            WHERE sg.id = ? AND am.aluno_id = ?
        ''', [simulado_id, current_user.id]).fetchone()
        
        if not simulado:
            return 'Simulado não encontrado', 404
            
        if simulado['status'] != 'em andamento':
            return 'Simulado não está em andamento', 400
            
        # Buscar questões e respostas corretas
        questoes = db.execute('''
            SELECT q.id, q.resposta_correta
            FROM banco_questoes q
            JOIN simulado_questoes sq ON q.id = sq.questao_id
            WHERE sq.simulado_id = ?
        ''', [simulado_id]).fetchall()
        
        # Criar dicionário de respostas corretas
        respostas_corretas = {str(q['id']): q['resposta_correta'] for q in questoes}
        
        # Buscar respostas do aluno
        resultado = db.execute('''
            SELECT respostas_aluno
            FROM desempenho_simulado
            WHERE simulado_id = ? AND aluno_id = ?
        ''', [simulado_id, current_user.id]).fetchone()
        
        if not resultado or not resultado['respostas_aluno']:
            return 'Nenhuma resposta encontrada', 400
            
        respostas_aluno = json.loads(resultado['respostas_aluno'])
        
        # Calcular desempenho
        acertos = 0
        total_questoes = len(questoes)
        
        for questao_id, resposta_correta in respostas_corretas.items():
            if questao_id in respostas_aluno:
                if respostas_aluno[questao_id].upper() == resposta_correta.upper():
                    acertos += 1
        
        desempenho = (acertos / total_questoes) * 100 if total_questoes > 0 else 0
        
        # Atualizar desempenho e marcar como respondido
        db.execute('''
            UPDATE desempenho_simulado
            SET respostas_corretas = ?,
                desempenho = ?,
                data_resposta = CURRENT_TIMESTAMP
            WHERE simulado_id = ? AND aluno_id = ?
        ''', [json.dumps(respostas_corretas), desempenho, simulado_id, current_user.id])
        
        # Atualizar status do simulado
        db.execute('''
            UPDATE aluno_simulado
            SET status = 'respondido',
                data_resposta = CURRENT_TIMESTAMP
            WHERE simulado_id = ? AND aluno_id = ?
        ''', [simulado_id, current_user.id])
        
        db.commit()
        return jsonify({'success': True, 'desempenho': desempenho})
        
    except Exception as e:
        db.rollback()
        return f'Erro ao finalizar simulado: {str(e)}', 500

@simulados_bp.route('/aluno/simulado/<int:simulado_id>', methods=['GET', 'POST'])
@login_required
def responder_simulado(simulado_id):
    if current_user.tipo_usuario_id != 4:  # Apenas alunos podem acessar
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    db = get_db()
    origem = request.args.get('origem', 'secretaria')
    
    # Verificar se o aluno já iniciou o simulado
    aluno_simulado = db.execute("""
        SELECT status FROM aluno_simulado
        WHERE simulado_id = ? AND aluno_id = ?
    """, [simulado_id, current_user.id]).fetchone()

    if not aluno_simulado:
        try:
            # Tenta iniciar o simulado automaticamente
            db.execute('''
                INSERT INTO aluno_simulado (aluno_id, simulado_id, status)
                VALUES (?, ?, 'em andamento')
            ''', [current_user.id, simulado_id])
            db.commit()
        except Exception as e:
            flash("Erro ao iniciar o simulado. Por favor, tente novamente.", "danger")
            if origem == 'professor':
                return redirect(url_for('simulados.listar_simulados_professores'))
            else:
                return redirect(url_for('simulados.listar_simulados'))
    
    # Buscar informações do simulado
    if origem == 'professor':
        simulado = db.execute("""
            SELECT sgp.id, d.nome as disciplina_nome, u.nome as professor_nome
            FROM simulados_gerados_professor sgp
            JOIN disciplinas d ON sgp.disciplina_id = d.id
            JOIN usuarios u ON sgp.professor_id = u.id
            WHERE sgp.id = ?
        """, [simulado_id]).fetchone()
    else:
        simulado = db.execute("""
            SELECT sg.id, d.nome as disciplina_nome
            FROM simulados_gerados sg
            JOIN disciplinas d ON sg.disciplina_id = d.id
            WHERE sg.id = ?
        """, [simulado_id]).fetchone()

    if not simulado:
        flash("Simulado não encontrado.", "danger")
        return redirect(url_for("simulados.listar_simulados"))
    
    # Verificar se o aluno já respondeu este simulado
    desempenho = db.execute("""
        SELECT respostas_aluno, respostas_corretas, desempenho
        FROM desempenho_simulado
        WHERE aluno_id = ? AND simulado_id = ?
    """, [current_user.id, simulado_id]).fetchone()

    # Buscar questões do simulado com nome da disciplina
    if origem == 'professor':
        questoes = db.execute("""
            SELECT q.id, q.disciplina_id, d.nome as disciplina_nome, q.questao, 
                   q.alternativa_a, q.alternativa_b, q.alternativa_c, 
                   q.alternativa_d, q.alternativa_e, q.questao_correta
            FROM simulado_questoes_professor sq
            JOIN banco_questoes q ON sq.questao_id = q.id
            JOIN disciplinas d ON q.disciplina_id = d.id
            WHERE sq.simulado_id = ?
            ORDER BY q.disciplina_id
        """, [simulado_id]).fetchall()
    else:
        questoes = db.execute("""
            SELECT q.id, q.disciplina_id, d.nome as disciplina_nome, q.questao, 
                   q.alternativa_a, q.alternativa_b, q.alternativa_c, 
                   q.alternativa_d, q.alternativa_e, q.questao_correta
            FROM simulado_questoes sq
            JOIN banco_questoes q ON sq.questao_id = q.id
            JOIN disciplinas d ON q.disciplina_id = d.id
            WHERE sq.simulado_id = ?
            ORDER BY q.disciplina_id
        """, [simulado_id]).fetchall()

    if not questoes:
        flash("Nenhuma questão encontrada para este simulado.", "danger")
        return redirect(url_for("simulados.listar_simulados"))

    questoes_por_disciplina = {}
    for q in questoes:
        disciplina_nome = q['disciplina_nome']
        if disciplina_nome not in questoes_por_disciplina:
            questoes_por_disciplina[disciplina_nome] = []
        questoes_por_disciplina[disciplina_nome].append(q)

    if desempenho:  # Se já respondeu, mostrar resultados
        respostas_aluno = json.loads(desempenho['respostas_aluno'])
        respostas_corretas = json.loads(desempenho['respostas_corretas'])
        
        # Preparar dados para visualização
        resultados = []
        total_questoes = len(questoes)
        acertos = 0
        
        for q in questoes:
            questao_id = str(q['id'])
            resposta_aluno = respostas_aluno.get(questao_id, '')
            resposta_correta = respostas_corretas[questao_id]
            
            resultado = {
                'questao': q['questao'],
                'disciplina': q['disciplina_nome'],
                'alternativas': [
                    q['alternativa_a'], 
                    q['alternativa_b'], 
                    q['alternativa_c'], 
                    q['alternativa_d'], 
                    q['alternativa_e']
                ],
                'resposta_aluno': resposta_aluno,
                'resposta_correta': resposta_correta,
                'acertou': resposta_aluno == resposta_correta,
                'numero_questao': len(resultados) + 1
            }
            if resultado['acertou']:
                acertos += 1
            resultados.append(resultado)
        
        return render_template('alunos/responder_simulado.html',
                             modo_visualizacao=True,
                             resultados=resultados,
                             total_questoes=total_questoes,
                             acertos=acertos,
                             percentual_acertos=desempenho['desempenho'],
                             simulado=simulado)
    
    if request.method == "POST":
        # Converte as respostas do aluno de números para letras (1->A, 2->B, etc)
        respostas = {}
        for key, value in request.form.items():
            if key.startswith("resposta_"):
                questao_id = key.split("_")[1]
                try:
                    respostas[questao_id] = chr(64 + int(value))  # Converte número para letra
                except (ValueError, TypeError):
                    continue
        
        # Pega as respostas corretas do banco (já estão em letra)
        respostas_corretas = {
            str(q['id']): q['questao_correta']
            for q in questoes
        }
        
        # Calcula apenas para as questões que existem em respostas_corretas
        total_questoes = len(respostas_corretas)
        if total_questoes > 0:
            respostas_certas = sum(
                1 for key, value in respostas.items() 
                if key in respostas_corretas and respostas_corretas[key] == value
            )
            desempenho = (respostas_certas / total_questoes) * 100
        else:
            respostas_certas = 0
            desempenho = 0

        # Inserir dados na tabela desempenho_simulado
        db.execute("""
            INSERT INTO desempenho_simulado (
                aluno_id, simulado_id, escola_id, serie_id, codigo_ibge,
                respostas_aluno, respostas_corretas, desempenho, tipo_usuario_id, turma_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            current_user.id,
            simulado_id,
            current_user.escola_id,
            current_user.serie_id,
            current_user.codigo_ibge,
            json.dumps(respostas),
            json.dumps(respostas_corretas),
            desempenho,
            3 if origem == 'professor' else 5,
            current_user.turma_id
        ])
        
        # Atualizar status do simulado
        db.execute("""
            UPDATE aluno_simulado
            SET status = 'finalizado'
            WHERE simulado_id = ? AND aluno_id = ?
        """, [simulado_id, current_user.id])
        
        db.commit()

        flash(f"Simulado respondido com sucesso! Você acertou {respostas_certas} de {total_questoes} questões.", "success")
        return redirect(url_for('simulados.responder_simulado', simulado_id=simulado_id, origem=origem))
    
    return render_template('alunos/responder_simulado.html',
                         modo_visualizacao=False,
                         questoes_por_disciplina=questoes_por_disciplina,
                         simulado=simulado)

@simulados_bp.route('/alunos/simulados-professores')
@login_required
def listar_simulados_professores():
    if current_user.tipo_usuario_id != 4:  # Apenas alunos podem acessar
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
        
    db = get_db()
    
    # Buscar simulados do aluno, ordenando por status (não respondido primeiro) e data
    simulados = db.execute("""
        SELECT DISTINCT sgp.id, d.nome AS disciplina_nome, sgp.mes_id, 
               strftime('%d-%m-%Y', date(sgp.data_criacao)) as data_envio,
               CASE 
                   WHEN ds.id IS NOT NULL THEN 'respondido'
                   ELSE 'disponível'
               END as status,
               u.nome as professor_nome,
               CAST(ROUND(COALESCE(ds.desempenho, 0)) as INTEGER) as nota
        FROM simulados_gerados_professor sgp
        JOIN disciplinas d ON sgp.disciplina_id = d.id
        JOIN usuarios u ON sgp.professor_id = u.id
        LEFT JOIN desempenho_simulado ds ON ds.simulado_id = sgp.id 
            AND ds.aluno_id = ? AND ds.tipo_usuario_id = 3
        ORDER BY 
            CASE 
                WHEN ds.id IS NOT NULL THEN 1
                ELSE 0
            END,
            sgp.data_criacao DESC
    """, [current_user.id]).fetchall()
    
    # Lista de meses para exibição
    meses = [
        (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"),
        (4, "Abril"), (5, "Maio"), (6, "Junho"),
        (7, "Julho"), (8, "Agosto"), (9, "Setembro"),
        (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
    ]
    
    return render_template('alunos/simulados_professores.html', simulados=simulados, meses=meses)

@simulados_bp.route('/alunos/filtrar-simulados-professores')
@login_required
def filtrar_simulados_professores():
    if current_user.tipo_usuario_id != 4:  # Apenas alunos podem acessar
        abort(403)
    
    mes = request.args.get('mes', '')
    
    db = get_db()
    
    # Construir query base
    query = """
        SELECT DISTINCT sgp.id, d.nome AS disciplina_nome, sgp.mes_id, 
               strftime('%d-%m-%Y', date(sgp.data_criacao)) as data_envio,
               CASE 
                   WHEN ds.id IS NOT NULL THEN 'respondido'
                   ELSE 'disponível'
               END as status,
               u.nome as professor_nome,
               CAST(ROUND(COALESCE(ds.desempenho, 0)) as INTEGER) as nota
        FROM simulados_gerados_professor sgp
        JOIN disciplinas d ON sgp.disciplina_id = d.id
        JOIN usuarios u ON sgp.professor_id = u.id
        LEFT JOIN desempenho_simulado ds ON ds.simulado_id = sgp.id 
            AND ds.aluno_id = ? AND ds.tipo_usuario_id = 3
    """
    params = [current_user.id]
    
    # Adicionar filtros
    if mes:
        query += " AND sgp.mes_id = ?"
        params.append(mes)
    
    # Adicionar ordenação
    query += """
        ORDER BY 
            CASE 
                WHEN ds.id IS NOT NULL THEN 1
                ELSE 0
            END,
            sgp.data_criacao DESC
    """
    
    simulados = db.execute(query, params).fetchall()
    
    return render_template('alunos/lista_simulados_professores.html', simulados=simulados)

@simulados_bp.route('/alunos/filtrar-simulados')
@login_required
def filtrar_simulados():
    if current_user.tipo_usuario_id != 4:  # Apenas alunos podem acessar
        abort(403)
    
    mes = request.args.get('mes', '')
    
    db = get_db()
    
    # Construir query base
    query = """
        SELECT DISTINCT sgp.id, d.nome AS disciplina_nome, sgp.mes_id, 
               strftime('%d-%m-%Y', date(sgp.data_criacao)) as data_envio,
               CASE 
                   WHEN ds.id IS NOT NULL THEN 'respondido'
                   ELSE 'disponível'
               END as status,
               u.nome as professor_nome,
               CAST(ROUND(COALESCE(ds.desempenho, 0)) as INTEGER) as nota
        FROM simulados_gerados_professor sgp
        JOIN disciplinas d ON sgp.disciplina_id = d.id
        JOIN usuarios u ON sgp.professor_id = u.id
        LEFT JOIN desempenho_simulado ds ON ds.simulado_id = sgp.id 
            AND ds.aluno_id = ? AND ds.tipo_usuario_id = 3
    """
    params = [current_user.id]
    
    # Adicionar filtros
    if mes:
        query += " AND sgp.mes_id = ?"
        params.append(mes)
    
    # Adicionar ordenação
    query += """
        ORDER BY 
            CASE 
                WHEN ds.id IS NOT NULL THEN 1
                ELSE 0
            END,
            sgp.data_criacao DESC
    """
    
    simulados = db.execute(query, params).fetchall()
    
    return render_template('alunos/lista_simulados.html', simulados=simulados)

@simulados_bp.route('/professores/buscar-questoes')
@login_required
def buscar_questoes():
    if current_user.tipo_usuario_id != 3:  # 3 = professor
        abort(403)
        
    serie_id = request.args.get('serie_id')
    disciplina_id = request.args.get('disciplina_id')
    assunto = request.args.get('assunto')
    
    db = get_db()
    cursor = db.cursor()
    
    query = """
        SELECT 
            bq.id,
            bq.questao as pergunta,
            json_array(
                bq.alternativa_a,
                bq.alternativa_b,
                bq.alternativa_c,
                bq.alternativa_d,
                CASE WHEN bq.alternativa_e IS NOT NULL THEN bq.alternativa_e END
            ) as alternativas,
            CASE 
                WHEN bq.questao_correta = 'A' THEN 0
                WHEN bq.questao_correta = 'B' THEN 1
                WHEN bq.questao_correta = 'C' THEN 2
                WHEN bq.questao_correta = 'D' THEN 3
                WHEN bq.questao_correta = 'E' THEN 4
            END as resposta_correta,
            d.nome as disciplina_nome,
            s.nome as serie_nome,
            bq.assunto
        FROM banco_questoes bq
        JOIN disciplinas d ON d.id = bq.disciplina_id
        JOIN series s ON s.id = bq.serie_id
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
        
    cursor.execute(query, params)
    questoes = []
    
    for row in cursor.fetchall():
        questao = {
            'id': row[0],
            'pergunta': row[1],
            'alternativas': row[2],
            'resposta_correta': row[3],
            'disciplina_nome': row[4],
            'serie_nome': row[5],
            'assunto': row[6]
        }
        questoes.append(questao)
    
    return jsonify(questoes)

@simulados_bp.route('/professores/buscar-turmas/<int:simulado_id>')
@login_required
def buscar_turmas_professor(simulado_id):
    if current_user.tipo_usuario_id != 3:  # Apenas professores podem acessar
        return jsonify({"error": "Acesso não autorizado"}), 403
    
    try:
        db = get_db()
        
        # Primeiro, vamos verificar se o simulado existe e seu status
        simulado = db.execute("""
            SELECT status FROM simulados_gerados_professor
            WHERE id = ? AND professor_id = ?
        """, [simulado_id, current_user.id]).fetchone()
        
        if not simulado:
            return jsonify({"error": "Simulado não encontrado"}), 404
            
        # Se o simulado foi editado ou está gerado, podemos mostrar todas as turmas
        if simulado['status'] in ['editado', 'gerado']:
            turmas = db.execute("""
                SELECT DISTINCT pte.turma_id as id, t.turma as nome
                FROM professor_turma_escola pte
                JOIN turmas t ON t.id = pte.turma_id
                WHERE pte.professor_id = ?
                ORDER BY t.turma
            """, [current_user.id]).fetchall()
        else:
            # Para outros status, só mostra turmas que ainda não receberam
            turmas = db.execute("""
                SELECT DISTINCT pte.turma_id as id, t.turma as nome
                FROM professor_turma_escola pte
                JOIN turmas t ON t.id = pte.turma_id
                WHERE pte.professor_id = ?
                AND NOT EXISTS (
                    SELECT 1 FROM simulados_enviados se
                    WHERE se.simulado_id = ? AND se.turma_id = pte.turma_id
                )
                ORDER BY t.turma
            """, [current_user.id, simulado_id]).fetchall()
        
        # Debug: imprimir informações
        print(f"Professor ID: {current_user.id}")
        print(f"Simulado ID: {simulado_id}")
        print(f"Status do simulado: {simulado['status']}")
        print(f"Turmas encontradas: {len(turmas)}")
        
        # Converter para lista de dicionários
        turmas_list = []
        for row in turmas:
            turmas_list.append({
                "id": row["id"],
                "nome": row["nome"]
            })
            print(f"Adicionando turma: {row['id']} - {row['nome']}")
        
        return jsonify(turmas_list)
        
    except Exception as e:
        print(f"Erro ao buscar turmas: {str(e)}")
        return jsonify({"error": str(e)}), 500

@simulados_bp.route('/professores/enviar-simulado', methods=['POST'])
@login_required
def enviar_simulado_professor():
    if current_user.tipo_usuario_id != 3:  # Apenas professores podem acessar
        return jsonify({"error": "Acesso não autorizado"}), 403
    
    data = request.get_json()
    simulado_id = data.get('simulado_id')
    turmas_ids = data.get('turmas')
    data_limite = data.get('data_limite')
    
    if not all([simulado_id, turmas_ids, data_limite]):
        return jsonify({"error": "Dados incompletos"}), 400
        
    db = get_db()
    
    try:
        # Verificar se o simulado pertence ao professor
        simulado = db.execute("""
            SELECT id FROM simulados_gerados_professor
            WHERE id = ? AND professor_id = ?
        """, [simulado_id, current_user.id]).fetchone()
        
        if not simulado:
            return jsonify({"error": "Simulado não encontrado"}), 404
        
        # Atualizar status do simulado para 'enviado'
        db.execute("""
            UPDATE simulados_gerados_professor
            SET status = 'enviado'
            WHERE id = ?
        """, [simulado_id])
        
        # Inserir registros na tabela simulados_enviados
        for turma_id in turmas_ids:
            db.execute("""
                INSERT INTO simulados_enviados (simulado_id, turma_id, data_limite)
                VALUES (?, ?, ?)
            """, [simulado_id, turma_id, data_limite])
            
            # Criar registros em aluno_simulado para cada aluno da turma
            db.execute("""
                INSERT INTO aluno_simulado (aluno_id, simulado_id)
                SELECT u.id, ?
                FROM usuarios u
                WHERE u.turma_id = ? AND u.tipo_usuario_id = 4
            """, [simulado_id, turma_id])
        
        db.commit()
        return jsonify({"message": "Simulado enviado com sucesso"})
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500

@simulados_bp.route('/professores/cancelar-envio-simulado/<int:simulado_id>', methods=['POST'])
@login_required
def cancelar_envio_simulado(simulado_id):
    if current_user.tipo_usuario_id != 3:  # Apenas professores podem acessar
        return jsonify({'success': False, 'error': 'Acesso não autorizado'}), 403
    
    try:
        db = get_db()
        
        # Verificar se o simulado pertence ao professor
        simulado = db.execute(
            'SELECT id FROM simulados_gerados_professor WHERE id = ? AND professor_id = ?',
            [simulado_id, current_user.id]
        ).fetchone()
        
        if not simulado:
            return jsonify({'success': False, 'error': 'Simulado não encontrado'}), 404
        
        # Remover registros de aluno_simulado
        db.execute('DELETE FROM aluno_simulado WHERE simulado_id = ?', [simulado_id])
        
        # Atualizar status para gerado
        db.execute(
            'UPDATE simulados_gerados_professor SET status = ? WHERE id = ?',
            ['gerado', simulado_id]
        )
        
        db.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao cancelar envio do simulado: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

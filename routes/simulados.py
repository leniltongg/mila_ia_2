from flask import Blueprint, render_template, request, jsonify, g, abort, redirect, url_for
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
    if current_user.tipo_usuario_id != 1:  # 1 = professor
        abort(403)
    return render_template('professores/banco_questoes.html')

@simulados_bp.route('/professores/criar-simulado')
@login_required
def criar_simulado():
    if current_user.tipo_usuario_id != 1:  # 1 = professor
        abort(403)
    return render_template('professores/criar_simulado.html')

@simulados_bp.route('/professores/salvar-questao', methods=['POST'])
@login_required
def salvar_questao():
    if current_user.tipo_usuario_id != 1:  # 1 = professor
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
    if current_user.tipo_usuario_id != 1:  # 1 = professor
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

@simulados_bp.route('/professores/salvar-simulado', methods=['POST'])
@login_required
def salvar_simulado():
    if current_user.tipo_usuario_id != 1:  # 1 = professor
        abort(403)
    
    try:
        data = request.get_json()
        db = get_db()
        
        # Inserir simulado
        cursor = db.execute('''
            INSERT INTO simulados (
                professor_id, titulo, descricao, disciplina,
                duracao, data_inicio, data_fim, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            current_user.id, data['titulo'], data['descricao'],
            data['disciplina'], data['duracao'],
            data['data_inicio'], data['data_fim'], data['status']
        ))
        
        simulado_id = cursor.lastrowid
        
        # Inserir questões do simulado
        for questao in data['questoes']:
            db.execute('''
                INSERT INTO simulado_questoes (
                    simulado_id, questao_id, ordem, pontos
                ) VALUES (?, ?, ?, ?)
            ''', (
                simulado_id, questao['id'],
                questao['ordem'], questao['pontos']
            ))
        
        db.commit()
        
        return jsonify({
            'success': True,
            'id': simulado_id
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
        SELECT sg.id, d.nome AS disciplina_nome, sg.mes_id, 
               strftime('%d-%m-%Y', date(sg.data_envio)) as data_envio,
               am.status,
               ds.desempenho as nota
        FROM aluno_simulado am
        JOIN simulados_gerados sg ON am.simulado_id = sg.id
        JOIN disciplinas d ON sg.disciplina_id = d.id
        LEFT JOIN desempenho_simulado ds ON ds.simulado_id = sg.id 
            AND ds.aluno_id = am.aluno_id
        WHERE am.aluno_id = ?
        ORDER BY 
            CASE am.status
                WHEN 'não respondido' THEN 0
                ELSE 1
            END,
            sg.data_envio DESC
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
        
        # Verificar se o simulado existe e está atribuído ao aluno
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
        
        return redirect(url_for('simulados.fazer_simulado', simulado_id=simulado_id))
        
    except Exception as e:
        db.rollback()
        return f'Erro ao iniciar simulado: {str(e)}', 500

@simulados_bp.route('/alunos/fazer-simulado/<int:simulado_id>')
@login_required
def fazer_simulado(simulado_id):
    if current_user.tipo_usuario_id != 4:  # Apenas alunos podem acessar
        abort(403)
    
    try:
        db = get_db()
        
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
                SELECT escola_id, serie_id, codigo_ibge
                FROM usuarios
                WHERE id = ?
            ''', [current_user.id]).fetchone()
            
            # Criar registro inicial
            db.execute('''
                INSERT INTO desempenho_simulado (
                    aluno_id, simulado_id, escola_id, serie_id,
                    codigo_ibge, respostas_aluno, respostas_corretas,
                    desempenho, data_resposta
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
            ''', [
                current_user.id, simulado_id,
                aluno['escola_id'], aluno['serie_id'],
                aluno['codigo_ibge'],
                json.dumps({}), json.dumps({})
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
    
    # Verificar se o aluno já respondeu este simulado
    desempenho = db.execute("""
        SELECT respostas_aluno, respostas_corretas, desempenho
        FROM desempenho_simulado
        WHERE aluno_id = ? AND simulado_id = ?
    """, [current_user.id, simulado_id]).fetchone()

    # Buscar questões do simulado com nome da disciplina
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
        
        percentual_acertos = (acertos / total_questoes) * 100 if total_questoes > 0 else 0
        
        return render_template(
            "alunos/responder_simulado.html",
            simulado_id=simulado_id,
            questoes_por_disciplina=questoes_por_disciplina,
            modo_visualizacao=True,
            resultados=resultados,
            total_questoes=total_questoes,
            acertos=acertos,
            percentual_acertos=percentual_acertos
        )

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
            INSERT INTO desempenho_simulado (aluno_id, simulado_id, escola_id, serie_id, codigo_ibge, respostas_aluno, respostas_corretas, desempenho)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            current_user.id,
            simulado_id,
            current_user.escola_id,
            current_user.serie_id,
            current_user.codigo_ibge,
            json.dumps(respostas),
            json.dumps(respostas_corretas),
            desempenho
        ])
        
        # Atualizar status do simulado
        db.execute("""
            UPDATE aluno_simulado
            SET status = 'respondido'
            WHERE simulado_id = ? AND aluno_id = ?
        """, [simulado_id, current_user.id])
        
        db.commit()

        flash(f"Simulado respondido com sucesso! Você acertou {respostas_certas} de {total_questoes} questões.", "success")
        return redirect(url_for("simulados.listar_simulados"))

    return render_template(
        "alunos/responder_simulado.html",
        simulado_id=simulado_id,
        questoes_por_disciplina=questoes_por_disciplina,
        modo_visualizacao=False
    )

@simulados_bp.route('/alunos/simulados-professores')
@login_required
def listar_simulados_professores():
    if current_user.tipo_usuario_id != 4:  # Apenas alunos podem acessar
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
        
    db = get_db()
    
    # Buscar simulados do aluno, ordenando por status (não respondido primeiro) e data
    simulados = db.execute("""
        SELECT sg.id, d.nome AS disciplina_nome, sg.mes_id, 
               strftime('%d-%m-%Y', date(sg.data_envio)) as data_envio,
               am.status, u.nome as professor_nome,
               ds.desempenho as nota
        FROM aluno_simulado am
        JOIN simulados_gerados sg ON am.simulado_id = sg.id
        JOIN disciplinas d ON sg.disciplina_id = d.id
        JOIN usuarios u ON sg.professor_id = u.id
        LEFT JOIN desempenho_simulado ds ON ds.simulado_id = sg.id 
            AND ds.aluno_id = am.aluno_id
        WHERE am.aluno_id = ?
        ORDER BY 
            CASE am.status
                WHEN 'não respondido' THEN 0
                ELSE 1
            END,
            sg.data_envio DESC
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
        SELECT sg.id, d.nome AS disciplina_nome, sg.mes_id, 
               strftime('%d-%m-%Y', date(sg.data_envio)) as data_envio,
               am.status, u.nome as professor_nome,
               ds.desempenho as nota
        FROM aluno_simulado am
        JOIN simulados_gerados sg ON am.simulado_id = sg.id
        JOIN disciplinas d ON sg.disciplina_id = d.id
        JOIN usuarios u ON sg.professor_id = u.id
        LEFT JOIN desempenho_simulado ds ON ds.simulado_id = sg.id 
            AND ds.aluno_id = am.aluno_id
        WHERE am.aluno_id = ?
    """
    params = [current_user.id]
    
    # Adicionar filtros
    if mes:
        query += " AND sg.mes_id = ?"
        params.append(mes)
    
    # Adicionar ordenação
    query += """
        ORDER BY 
            CASE am.status
                WHEN 'não respondido' THEN 0
                ELSE 1
            END,
            sg.data_envio DESC
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
        SELECT sg.id, d.nome AS disciplina_nome, sg.mes_id, 
               strftime('%d-%m-%Y', date(sg.data_envio)) as data_envio,
               am.status,
               ds.desempenho as nota
        FROM aluno_simulado am
        JOIN simulados_gerados sg ON am.simulado_id = sg.id
        JOIN disciplinas d ON sg.disciplina_id = d.id
        LEFT JOIN desempenho_simulado ds ON ds.simulado_id = sg.id 
            AND ds.aluno_id = am.aluno_id
        WHERE am.aluno_id = ?
    """
    params = [current_user.id]
    
    # Adicionar filtros
    if mes:
        query += " AND sg.mes_id = ?"
        params.append(mes)
    
    # Adicionar ordenação
    query += """
        ORDER BY 
            CASE am.status
                WHEN 'não respondido' THEN 0
                ELSE 1
            END,
            sg.data_envio DESC
    """
    
    simulados = db.execute(query, params).fetchall()
    
    return render_template('alunos/lista_simulados.html', simulados=simulados)

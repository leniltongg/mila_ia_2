from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g, abort
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
from models import db, Disciplinas, Ano_escolar as AnoEscolarModel, MESES, BancoQuestoes, SimuladosGeradosProfessor, SimuladoQuestoesProfessor, ProfessorTurmaEscola, DesempenhoSimulado, SimuladosEnviados, AlunoSimulado, Usuarios, Turmas

simulados_bp = Blueprint('simulados', __name__)

# Rotas para professores
@simulados_bp.route('/professores/banco-questoes', methods=['GET', 'POST'])
@login_required
def banco_questoes():
    """Lista todas as questões do banco."""
    if current_user.tipo_usuario_id not in [3, 6]:  # Apenas professores
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            # Obter dados do formulário
            questao = request.form.get('questao')
            alternativa_a = request.form.get('alternativa_a')
            alternativa_b = request.form.get('alternativa_b')
            alternativa_c = request.form.get('alternativa_c')
            alternativa_d = request.form.get('alternativa_d')
            alternativa_e = request.form.get('alternativa_e')
            questao_correta = request.form.get('questao_correta')
            disciplina_id = request.form.get('disciplina_id')
            assunto = request.form.get('assunto')
            ano_escolar_id = request.form.get('ano_escolar_id')
            mes_id = request.form.get('mes_id')
            
            # Validar dados
            if not all([questao, alternativa_a, alternativa_b, alternativa_c, alternativa_d,
                       questao_correta, disciplina_id, ano_escolar_id]):
                return jsonify({
                    'success': False,
                    'message': 'Por favor, preencha todos os campos obrigatórios'
                }), 400

            # Criar nova questão
            nova_questao = BancoQuestoes(
                questao=questao,
                alternativa_a=alternativa_a,
                alternativa_b=alternativa_b,
                alternativa_c=alternativa_c,
                alternativa_d=alternativa_d,
                alternativa_e=alternativa_e,
                questao_correta=questao_correta,
                disciplina_id=disciplina_id,
                assunto=assunto,
                ano_escolar_id=ano_escolar_id,
                mes_id=mes_id,
                usuario_id=current_user.id
            )

            db.session.add(nova_questao)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Questão cadastrada com sucesso!'
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Erro ao cadastrar questão: {str(e)}'
            }), 500

    try:
        # Buscar séries, disciplinas e meses para os filtros
        Ano_escolar = db.session.query(AnoEscolarModel).order_by(AnoEscolarModel.nome).all()
        disciplinas = db.session.query(Disciplinas).order_by(Disciplinas.nome).all()
        
        # Buscar questões com informações relacionadas
        questoes = db.session.query(
            BancoQuestoes,
            Disciplinas.nome.label('disciplina_nome'),
            AnoEscolarModel.nome.label('Ano_escolar_nome')
        ).join(
            Disciplinas, Disciplinas.id == BancoQuestoes.disciplina_id
        ).join(
            AnoEscolarModel, AnoEscolarModel.id == BancoQuestoes.ano_escolar_id
        ).filter(
            BancoQuestoes.usuario_id == current_user.id
        ).order_by(
            BancoQuestoes.id.desc()
        ).all()

        # Lista de meses
        meses = db.session.query(MESES).order_by(MESES.id).all()

        return render_template('professores/banco_questoes.html',
                            questoes=questoes,
                            disciplinas=disciplinas,
                            Ano_escolar=Ano_escolar,
                            meses=meses)

    except Exception as e:
        flash(f"Erro ao carregar banco de questões: {str(e)}", "danger")
        return redirect(url_for("index"))

@simulados_bp.route('/professores/criar-simulado')
@login_required
def criar_simulado():
    if current_user.tipo_usuario_id not in [3, 6]:  # 3 = professor
        abort(403)
    
    # Se for super usuário (tipo 6), buscar todos os anos escolares
    if current_user.tipo_usuario_id == 6:
        Ano_escolar = AnoEscolarModel.query.order_by(AnoEscolarModel.nome).all()
    else:
        # Se for professor normal, buscar apenas os anos escolares associados
        Ano_escolar = AnoEscolarModel.query.join(
            ProfessorTurmaEscola, 
            AnoEscolarModel.id == ProfessorTurmaEscola.ano_escolar_id
        ).filter_by(professor_id=current_user.id).distinct().all()
    
    # Buscar disciplinas
    disciplinas = Disciplinas.query.order_by(Disciplinas.nome).all()
    
    # Buscar meses
    meses = sorted(MESES.query.all(), key=lambda mes: {
        'Janeiro': 1,
        'Fevereiro': 2,
        'Março': 3,
        'Abril': 4,
        'Maio': 5,
        'Junho': 6,
        'Julho': 7,
        'Agosto': 8,
        'Setembro': 9,
        'Outubro': 10,
        'Novembro': 11,
        'Dezembro': 12
    }.get(mes.nome, 13))  # 13 para qualquer mês não listado
    
    # Verificar se é edição
    simulado_id = request.args.get('id', type=int)
    simulado_data = None
    questoes_selecionadas = []
    
    if simulado_id:
        # Buscar dados do simulado
        simulado = SimuladosGeradosProfessor.query.filter_by(id=simulado_id, professor_id=current_user.id).first()
        
        if simulado:
            # Verificar se o status é 'gerado'
            if simulado.status != 'gerado':
                flash('Não é possível editar um simulado que já foi enviado. Cancele o envio primeiro.', 'warning')
                return redirect(url_for('simulados.listar_simulados_professor'))
            
            # Converter a tupla em um dicionário com todos os dados necessários
            simulado_data = {
                'id': simulado.id,
                'professor_id': simulado.professor_id,
                'disciplina_id': simulado.disciplina_id,
                'ano_escolar_id': simulado.ano_escolar_id,
                'mes_id': simulado.mes_id,
                'status': simulado.status,
                'disciplina_nome': simulado.disciplina.nome,
                'Ano_escolar_nome': simulado.Ano_escolar.nome,
                'mes_nome': simulado.mes.nome
            }
            
            # Buscar questões do simulado
            questoes = SimuladoQuestoesProfessor.query.filter_by(simulado_id=simulado_id).all()
            
            questoes_selecionadas = [{
                'id': q.questao_id,
                'enunciado': q.questao.questao,
                'alternativas': {
                    'a': q.questao.alternativa_a,
                    'b': q.questao.alternativa_b,
                    'c': q.questao.alternativa_c,
                    'd': q.questao.alternativa_d,
                    'e': q.questao.alternativa_e if q.questao.alternativa_e else None
                },
                'resposta': q.questao.questao_correta,
                'assunto': q.questao.assunto,
                'disciplina_id': q.questao.disciplina_id,
                'ano_escolar_id': q.questao.ano_escolar_id,
                'mes_id': q.questao.mes_id
            } for q in questoes]

    return render_template('professores/criar_simulado.html',
                         Ano_escolar=Ano_escolar,
                         disciplinas=disciplinas,
                         meses=meses,
                         simulado=simulado_data,
                         questoes_selecionadas=questoes_selecionadas)

@simulados_bp.route('/professores/salvar-simulado', methods=['POST'])
@simulados_bp.route('/professores/salvar-simulado/<int:simulado_id>', methods=['POST'])
@login_required
def salvar_simulado(simulado_id=None):
    if current_user.tipo_usuario_id not in [3, 6]:  # 3 = professor
        return jsonify({'success': False, 'error': 'Acesso negado'})
    
    try:
        data = request.get_json()
        print("Dados recebidos:", data)  # Debug
        
        ano_escolar_id = data.get('ano_escolar_id')
        disciplina_id = data.get('disciplina_id')
        mes_id = data.get('mes_id')
        questoes = data.get('questoes', [])
        
        if not all([ano_escolar_id, disciplina_id, mes_id]) or not questoes:
            return jsonify({'success': False, 'error': 'Dados incompletos'})
        
        if simulado_id:
            # Verificar se o simulado existe e pertence ao professor
            simulado = SimuladosGeradosProfessor.query.filter_by(id=simulado_id, professor_id=current_user.id).first()
            
            if not simulado:
                return jsonify({'success': False, 'error': 'Simulado não encontrado'})
            
            if simulado.status != 'gerado':
                return jsonify({'success': False, 'error': 'Não é possível editar um simulado que já foi enviado'})
            
            print(f"Atualizando simulado {simulado_id}")  # Debug
            
            # Atualizar simulado
            simulado.ano_escolar_id = ano_escolar_id
            simulado.disciplina_id = disciplina_id
            simulado.mes_id = mes_id
            
            # Remover questões antigas
            SimuladoQuestoesProfessor.query.filter_by(simulado_id=simulado_id).delete()
            
            # Inserir novas questões
            for questao_id in questoes:
                sqp = SimuladoQuestoesProfessor(simulado_id=simulado_id, questao_id=questao_id)
                db.session.add(sqp)
                
            print(f"Inseridas {len(questoes)} questões")  # Debug
        else:
            # Criar novo simulado
            simulado = SimuladosGeradosProfessor(professor_id=current_user.id, ano_escolar_id=ano_escolar_id, disciplina_id=disciplina_id, mes_id=mes_id, status='gerado')
            db.session.add(simulado)
            db.session.flush()  # Isso força o banco a gerar o ID
            
            simulado_id = simulado.id
            print(f"Criado novo simulado {simulado_id}")  # Debug
            
            # Inserir questões
            for questao_id in questoes:
                sqp = SimuladoQuestoesProfessor(simulado_id=simulado_id, questao_id=questao_id)
                db.session.add(sqp)
            
            print(f"Inseridas {len(questoes)} questões")  # Debug
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Erro ao salvar simulado: {str(e)}")  # Debug
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@simulados_bp.route('/professores/salvar-questao', methods=['POST'])
@login_required
def salvar_questao():
    if current_user.tipo_usuario_id not in [3, 6]:  # 1 = professor
        abort(403)
    
    try:
        data = request.get_json()
        
        # Preparar dados
        alternativas = json.dumps(data.get('alternativas')) if data.get('alternativas') else None
        
        # Inserir questão
        questao = BancoQuestoes(
            usuario_id=current_user.id, 
            disciplina=data['disciplina'], 
            assunto=data['assunto'],
            nivel=data['nivel'], 
            tipo=data['tipo'],
            enunciado=data['enunciado'],
            alternativas=alternativas,
            resposta_correta=data['resposta'], 
            explicacao=data.get('explicacao')
        )
        db.session.add(questao)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'id': questao.id
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@simulados_bp.route('/professores/pesquisar-questoes')
@login_required
def pesquisar_questoes():
    if current_user.tipo_usuario_id not in [3, 6]:  # 1 = professor
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
        query = BancoQuestoes.query
        params = []
        
        if disciplina:
            query = query.filter_by(disciplina=disciplina)
        if assunto:
            query = query.filter(BancoQuestoes.assunto.like(f'%{assunto}%'))
        if nivel:
            query = query.filter_by(nivel=nivel)
        if tipo:
            query = query.filter_by(tipo=tipo)
        
        # Adicionar paginação
        questoes = query.paginate(pagina, por_pagina, False)
        
        # Contar total para paginação
        total = query.count()
        
        return jsonify({
            'success': True,
            'questoes': [{
                'id': q.id,
                'disciplina': q.disciplina,
                'assunto': q.assunto,
                'nivel': q.nivel,
                'tipo': q.tipo,
                'enunciado': q.enunciado,
                'alternativas': json.loads(q.alternativas) if q.alternativas else None,
                'resposta': q.resposta_correta,
                'explicacao': q.explicacao
            } for q in questoes.items],
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
    if current_user.tipo_usuario_id not in [3, 6]:  # Apenas professores podem acessar
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
        
    # Buscar simulados criados pelo professor com informações relacionadas
    simulados = db.session.query(
        SimuladosGeradosProfessor,
        Disciplinas.nome.label('disciplina_nome'),
        AnoEscolarModel.nome.label('Ano_escolar_nome'),
        MESES.nome.label('mes_nome'),
        db.func.count(DesempenhoSimulado.id).label('total_alunos_responderam')
    ).join(
        Disciplinas, SimuladosGeradosProfessor.disciplina_id == Disciplinas.id
    ).join(
        AnoEscolarModel, SimuladosGeradosProfessor.ano_escolar_id == AnoEscolarModel.id
    ).outerjoin(
        MESES, SimuladosGeradosProfessor.mes_id == MESES.id
    ).outerjoin(
        SimuladosEnviados, SimuladosGeradosProfessor.id == SimuladosEnviados.simulado_id
    ).outerjoin(
        DesempenhoSimulado, SimuladosEnviados.id == DesempenhoSimulado.simulado_id
    ).filter(
        SimuladosGeradosProfessor.professor_id == current_user.id
    ).group_by(
        SimuladosGeradosProfessor.id,
        Disciplinas.nome,
        AnoEscolarModel.nome,
        MESES.nome
    ).order_by(
        SimuladosGeradosProfessor.data_criacao.desc()
    ).all()
    
    # Formatar os dados para o template
    simulados_formatados = []
    for simulado, disciplina_nome, Ano_escolar_nome, mes_nome, total_alunos_responderam in simulados:
        simulados_formatados.append({
            'id': simulado.id,
            'disciplina_nome': disciplina_nome,
            'Ano_escolar_nome': Ano_escolar_nome,
            'mes_nome': mes_nome or 'Não definido',
            'data_criacao': simulado.data_criacao.strftime('%d/%m/%Y %H:%M') if simulado.data_criacao else 'Data não definida',
            'status': simulado.status,
            'total_alunos_responderam': total_alunos_responderam
        })
    
    return render_template('professores/meus_simulados.html', simulados=simulados_formatados)

@simulados_bp.route('/professores/visualizar-simulado/<int:simulado_id>')
@login_required
def visualizar_simulado_professor(simulado_id):
    if current_user.tipo_usuario_id not in [3, 6]:  # Apenas professores podem acessar
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
        
    # Buscar informações do simulado
    simulado = db.session.query(
        SimuladosGeradosProfessor,
        Disciplinas.nome.label('disciplina_nome'),
        AnoEscolarModel.nome.label('Ano_escolar_nome'),
        MESES.nome.label('mes_nome')
    ).join(
        Disciplinas, SimuladosGeradosProfessor.disciplina_id == Disciplinas.id
    ).join(
        AnoEscolarModel, SimuladosGeradosProfessor.ano_escolar_id == AnoEscolarModel.id
    ).outerjoin(
        MESES, SimuladosGeradosProfessor.mes_id == MESES.id
    ).filter(
        SimuladosGeradosProfessor.id == simulado_id,
        SimuladosGeradosProfessor.professor_id == current_user.id
    ).first()
    
    if not simulado:
        flash("Simulado não encontrado.", "danger")
        return redirect(url_for("simulados.listar_simulados_professor"))
        
    # Buscar questões do simulado
    questoes = db.session.query(
        BancoQuestoes
    ).join(
        SimuladoQuestoesProfessor, BancoQuestoes.id == SimuladoQuestoesProfessor.questao_id
    ).filter(
        SimuladoQuestoesProfessor.simulado_id == simulado_id
    ).all()
    
    # Formatar dados do simulado
    simulado_info = {
        'id': simulado[0].id,
        'disciplina_nome': simulado[1],
        'Ano_escolar_nome': simulado[2],
        'mes_nome': simulado[3] or 'Não definido',
        'data_criacao': simulado[0].data_criacao.strftime('%d/%m/%Y %H:%M') if simulado[0].data_criacao else 'Data não definida',
        'status': simulado[0].status,
        'questoes': [
            {
                'id': q.id,
                'questao': q.questao,
                'alternativa_a': q.alternativa_a,
                'alternativa_b': q.alternativa_b,
                'alternativa_c': q.alternativa_c,
                'alternativa_d': q.alternativa_d,
                'alternativa_e': q.alternativa_e,
                'questao_correta': q.questao_correta,
                'assunto': q.assunto
            } for q in questoes
        ]
    }
    
    # Se o simulado já foi enviado, buscar informações das turmas
    if simulado[0].status == 'enviado':
        turmas_enviadas = db.session.query(
            Turmas.id,
            Turmas.turma,
            SimuladosEnviados.data_envio,
            SimuladosEnviados.data_limite,
            db.func.count(DesempenhoSimulado.id).label('total_responderam')
        ).join(
            SimuladosEnviados, Turmas.id == SimuladosEnviados.turma_id
        ).outerjoin(
            DesempenhoSimulado, SimuladosEnviados.id == DesempenhoSimulado.simulado_id
        ).filter(
            SimuladosEnviados.simulado_id == simulado_id
        ).group_by(
            Turmas.id,
            Turmas.turma,
            SimuladosEnviados.data_envio,
            SimuladosEnviados.data_limite
        ).all()
        
        simulado_info['turmas'] = [
            {
                'id': t[0],
                'turma': t[1],
                'data_envio': t[2].strftime('%d/%m/%Y %H:%M') if t[2] else 'Não definida',
                'data_limite': t[3].strftime('%d/%m/%Y %H:%M') if t[3] else 'Sem limite',
                'total_responderam': t[4]
            } for t in turmas_enviadas
        ]
    
    return render_template('professores/visualizar_simulado.html', simulado=simulado_info)

@simulados_bp.route('/professores/api/visualizar-simulado/<int:simulado_id>')
@login_required
def visualizar_simulado_professor_json(simulado_id):
    if current_user.tipo_usuario_id not in [3, 6]:  # Apenas professores podem acessar
        return jsonify({"error": "Acesso não autorizado"}), 403
        
    # Buscar informações do simulado
    simulado = SimuladosGeradosProfessor.query.filter_by(id=simulado_id, professor_id=current_user.id).first()
    
    if not simulado:
        return jsonify({"error": "Simulado não encontrado"}), 404
    
    # Buscar questões do simulado
    questoes = SimuladoQuestoesProfessor.query.filter_by(simulado_id=simulado_id).all()
    
    # Formatar questões para JSON
    questoes_formatadas = []
    for q in questoes:
        alternativas = [
            {"letra": "A", "texto": q.questao.alternativa_a, "correta": q.questao.resposta_correta == "a"},
            {"letra": "B", "texto": q.questao.alternativa_b, "correta": q.questao.resposta_correta == "b"},
            {"letra": "C", "texto": q.questao.alternativa_c, "correta": q.questao.resposta_correta == "c"},
            {"letra": "D", "texto": q.questao.alternativa_d, "correta": q.questao.resposta_correta == "d"}
        ]
        if q.questao.alternativa_e:
            alternativas.append({"letra": "E", "texto": q.questao.alternativa_e, "correta": q.questao.resposta_correta == "e"})
            
        questoes_formatadas.append({
            "id": q.questao_id,
            "enunciado": q.questao.enunciado,
            "alternativas": alternativas,
            "assunto": q.questao.assunto
        })
    
    return jsonify({
        "id": simulado.id,
        "status": simulado.status,
        "disciplina_nome": simulado.disciplina.nome,
        "Ano_escolar_nome": simulado.Ano_escolar.nome,
        "mes_nome": simulado.mes.nome,
        "data_criacao": simulado.data_criacao,
        "questoes": questoes_formatadas
    })

# Rotas para alunos
@simulados_bp.route('/alunos/simulados')
@login_required
def listar_simulados():
    if current_user.tipo_usuario_id not in [4, 6]:  # Apenas alunos podem acessar
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
        
    # Buscar simulados do aluno, ordenando por status (não respondido primeiro) e data
    simulados = []
    
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
    if current_user.tipo_usuario_id not in [4, 6]:  # Apenas alunos podem acessar
        abort(403)
    
    try:
        origem = request.args.get('origem')
        
        # Verificar se o simulado existe e está atribuído ao aluno
        simulado = None
        if origem == 'professor':
            simulado = SimuladosGeradosProfessor.query.filter_by(id=simulado_id).first()
        else:
            simulado = SimuladosGerados.query.filter_by(id=simulado_id).first()
        
        if not simulado:
            return 'Simulado não encontrado ou não atribuído ao aluno', 404
            
        if simulado.status != 'não respondido':
            return 'Este simulado já foi iniciado ou respondido', 400
            
        # Atualizar status do simulado para 'em andamento'
        # ...
        
        return redirect(url_for('simulados.fazer_simulado', simulado_id=simulado_id, origem=origem))
        
    except Exception as e:
        return f'Erro ao iniciar simulado: {str(e)}', 500

@simulados_bp.route('/alunos/fazer-simulado/<int:simulado_id>')
@login_required
def fazer_simulado(simulado_id):
    if current_user.tipo_usuario_id not in [4, 6]:  # Apenas alunos podem acessar
        abort(403)
    
    try:
        # Verificar se o aluno já iniciou o simulado
        aluno_simulado = None
        
        # Buscar informações do simulado e status
        simulado = None
        if origem == 'professor':
            simulado = SimuladosGeradosProfessor.query.filter_by(id=simulado_id).first()
        else:
            simulado = SimuladosGerados.query.filter_by(id=simulado_id).first()
        
        if not simulado:
            return 'Simulado não encontrado ou não atribuído ao aluno', 404
            
        if simulado.status == 'respondido':
            return 'Este simulado já foi respondido', 400
            
        # Buscar questões do simulado
        questoes = []
        
        # Buscar respostas já dadas pelo aluno (se houver)
        respostas = []
        
        respostas_aluno = {}
        
        return render_template('alunos/fazer_simulado.html',
                             simulado=simulado,
                             questoes=questoes,
                             respostas_aluno=respostas_aluno)
        
    except Exception as e:
        return f'Erro ao carregar simulado: {str(e)}', 500

@simulados_bp.route('/alunos/salvar-resposta', methods=['POST'])
@login_required
def salvar_resposta():
    if current_user.tipo_usuario_id not in [4, 6]:  # Apenas alunos podem acessar
        abort(403)
    
    try:
        data = request.get_json()
        simulado_id = data.get('simulado_id')
        questao_id = data.get('questao_id')
        resposta = data.get('resposta')
        
        if not all([simulado_id, questao_id, resposta]):
            return 'Dados incompletos', 400
            
        # Verificar se o simulado existe e está em andamento
        simulado = None
        
        # Buscar respostas atuais do aluno
        resultado = []
        
        # Se não existe registro no desempenho_simulado, criar
        if not resultado:
            # Buscar informações do aluno
            aluno = []
            
            # Criar registro inicial
            # ...
            
            respostas_aluno = {}
        else:
            respostas_aluno = json.loads(resultado['respostas_aluno']) if resultado['respostas_aluno'] else {}
        
        # Atualizar resposta
        respostas_aluno[str(questao_id)] = resposta
        
        # Salvar respostas atualizadas
        # ...
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return f'Erro ao salvar resposta: {str(e)}', 500

@simulados_bp.route('/alunos/finalizar-simulado/<int:simulado_id>', methods=['POST'])
@login_required
def finalizar_simulado(simulado_id):
    if current_user.tipo_usuario_id not in [4, 6]:  # Apenas alunos podem acessar
        abort(403)
    
    try:
        # Verificar se o simulado existe e está em andamento
        simulado = None
        
        # Buscar questões e respostas corretas
        questoes = []
        
        # Criar dicionário de respostas corretas
        respostas_corretas = {str(q['id']): q['resposta_correta'] for q in questoes}
        
        # Buscar respostas do aluno
        resultado = []
        
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
        # ...
        
        # Atualizar status do simulado
        # ...
        
        db.session.commit()
        return jsonify({'success': True, 'desempenho': desempenho})
        
    except Exception as e:
        db.session.rollback()
        return f'Erro ao finalizar simulado: {str(e)}', 500

@simulados_bp.route('/aluno/simulado/<int:simulado_id>', methods=['GET', 'POST'])
@login_required
def responder_simulado(simulado_id):
    if current_user.tipo_usuario_id not in [4, 6]:  # Apenas alunos podem acessar
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    origem = request.args.get('origem', 'secretaria')
    
    # Verificar se o aluno já iniciou o simulado
    aluno_simulado = None

    if not aluno_simulado:
        try:
            # Tenta iniciar o simulado automaticamente
            pass  # Mantenha o código existente aqui
        except Exception as e:
            flash("Erro ao iniciar o simulado. Por favor, tente novamente.", "danger")
            if origem == 'professor':
                return redirect(url_for('simulados.listar_simulados_professores'))
            else:
                return redirect(url_for('simulados.listar_simulados'))
    
    # Buscar informações do simulado
    if origem == 'professor':
        simulado = SimuladosGeradosProfessor.query.filter_by(id=simulado_id).first()
    else:
        simulado = SimuladosGerados.query.filter_by(id=simulado_id).first()

    if not simulado:
        flash("Simulado não encontrado.", "danger")
        return redirect(url_for("simulados.listar_simulados"))

    # Verificar se o aluno já respondeu este simulado
    desempenho = None

    # Buscar questões do simulado com nome da disciplina
    if origem == 'professor':
        questoes = []
    else:
        questoes = []
    
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
        # ...
        
        # Atualizar status do simulado
        # ...
        
        db.session.commit()

        flash(f"Simulado respondido com sucesso! Você acertou {respostas_certas} de {total_questoes} questões.", "success")
        return redirect(url_for('simulados.responder_simulado', simulado_id=simulado_id, origem=origem))
    
    return render_template('alunos/responder_simulado.html',
                         modo_visualizacao=False,
                         questoes_por_disciplina=questoes_por_disciplina,
                         simulado=simulado)

@simulados_bp.route('/alunos/simulados-professores')
@login_required
def listar_simulados_professores():
    if current_user.tipo_usuario_id not in [4, 6]:  # Apenas alunos podem acessar
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
        
    # Buscar simulados do aluno, ordenando por status (não respondido primeiro) e data
    simulados = []
    
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
    if current_user.tipo_usuario_id not in [4, 6]:  # Apenas alunos podem acessar
        abort(403)
    
    mes = request.args.get('mes', '')
    
    # Construir query base
    query = []
    params = []
    
    # Adicionar filtros
    if mes:
        query.append(" AND mes_id = ?")
        params.append(mes)
    
    # Adicionar ordenação
    query.append(" ORDER BY data_criacao DESC")
    
    simulados = []
    
    return render_template('alunos/lista_simulados_professores.html', simulados=simulados)

@simulados_bp.route('/alunos/filtrar-simulados')
@login_required
def filtrar_simulados():
    if current_user.tipo_usuario_id not in [4, 6]:  # Apenas alunos podem acessar
        abort(403)
    
    mes = request.args.get('mes', '')
    
    # Construir query base
    query = []
    params = []
    
    # Adicionar filtros
    if mes:
        query.append(" AND mes_id = ?")
        params.append(mes)
    
    # Adicionar ordenação
    query.append(" ORDER BY data_criacao DESC")
    
    simulados = []
    
    return render_template('alunos/lista_simulados.html', simulados=simulados)

@simulados_bp.route('/professores/buscar-questoes')
@login_required
def buscar_questoes():
    if current_user.tipo_usuario_id not in [3, 6]:  # 3 = professor
        return jsonify({'error': 'Não autorizado'}), 403
        
    try:
        print("Iniciando busca de questões...")
        ano_escolar_id = request.args.get('ano_escolar_id')
        disciplina_id = request.args.get('disciplina_id')
        assunto = request.args.get('assunto', '').strip()
        pagina = int(request.args.get('pagina', 1))
        por_pagina = 10
        
        print(f"Parâmetros recebidos: ano_escolar_id={ano_escolar_id}, disciplina_id={disciplina_id}, assunto={assunto}, pagina={pagina}")
        
        # Construir query base
        query = BancoQuestoes.query
        
        # Aplicar filtros
        if ano_escolar_id:
            query = query.filter_by(ano_escolar_id=ano_escolar_id)
        if disciplina_id:
            query = query.filter_by(disciplina_id=disciplina_id)
        if assunto:
            query = query.filter(BancoQuestoes.assunto.like(f'%{assunto}%'))
            
        # Adicionar paginação
        questoes_paginadas = query.paginate(page=pagina, per_page=por_pagina, error_out=False)
        print(f"Total de questões encontradas: {questoes_paginadas.total}")
        
        # Formatar questões para o frontend
        questoes_formatadas = []
        for q in questoes_paginadas.items:
            print(f"Processando questão ID: {q.id}")
            alternativas = [q.alternativa_a, q.alternativa_b, q.alternativa_c, q.alternativa_d]
            if q.alternativa_e:
                alternativas.append(q.alternativa_e)
                
            questao_formatada = {
                'id': q.id,
                'questao': q.questao,
                'alternativa_a': q.alternativa_a,
                'alternativa_b': q.alternativa_b,
                'alternativa_c': q.alternativa_c,
                'alternativa_d': q.alternativa_d,
                'alternativa_e': q.alternativa_e,
                'questao_correta': q.questao_correta,
                'disciplina_nome': q.disciplina.nome if q.disciplina else '',
                'Ano_escolar_nome': q.Ano_escolar.nome if q.Ano_escolar else '',
                'assunto': q.assunto
            }
            print(f"Questão formatada: {questao_formatada}")
            questoes_formatadas.append(questao_formatada)
            
        return jsonify(questoes_formatadas)
        
    except Exception as e:
        print(f"Erro ao buscar questões: {str(e)}")
        print(f"Tipo do erro: {type(e)}")
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@simulados_bp.route('/professores/buscar-turmas/<int:simulado_id>')
@login_required
def buscar_turmas_professor(simulado_id):
    if current_user.tipo_usuario_id not in [3, 6]:  # Apenas professores podem acessar
        return jsonify({"error": "Acesso não autorizado"}), 403
    
    try:
        # Primeiro, vamos verificar se o simulado existe e seu status
        simulado = SimuladosGeradosProfessor.query.filter_by(id=simulado_id, professor_id=current_user.id).first()
        
        if not simulado:
            return jsonify({"error": "Simulado não encontrado"}), 404
            
        # Se o simulado foi editado ou está gerado, podemos mostrar todas as turmas
        if simulado.status in ['editado', 'gerado']:
            turmas = ProfessorTurmaEscola.query.filter_by(professor_id=current_user.id).distinct().all()
        else:
            # Para outros status, só mostra turmas que ainda não receberam
            turmas = ProfessorTurmaEscola.query.filter_by(professor_id=current_user.id).distinct().all()
        
        # Converter para lista de dicionários
        turmas_list = []
        for row in turmas:
            turmas_list.append({
                "id": row.turma_id,
                "nome": row.turma.turma
            })
        
        return jsonify(turmas_list)
        
    except Exception as e:
        print(f"Erro ao buscar turmas: {str(e)}")
        return jsonify({"error": str(e)}), 500

@simulados_bp.route('/professores/enviar-simulado', methods=['POST'])
@login_required
def enviar_simulado_professor():
    if current_user.tipo_usuario_id not in [3, 6]:  # Apenas professores podem acessar
        return jsonify({"error": "Acesso não autorizado"}), 403
    
    data = request.get_json()
    simulado_id = data.get('simulado_id')
    turmas_ids = data.get('turmas')
    data_limite = data.get('data_limite')
    
    if not all([simulado_id, turmas_ids, data_limite]):
        return jsonify({"error": "Dados incompletos"}), 400
        
    try:
        # Verificar se o simulado pertence ao professor
        simulado = SimuladosGeradosProfessor.query.filter_by(id=simulado_id, professor_id=current_user.id).first()
        
        if not simulado:
            return jsonify({"error": "Simulado não encontrado"}), 404
            
        # Atualizar status do simulado para 'enviado'
        simulado.status = 'enviado'
        
        # Inserir registros na tabela simulados_enviados
        for turma_id in turmas_ids:
            # Criar registro do envio do simulado
            simulado_enviado = SimuladosEnviados(
                simulado_id=simulado_id,
                turma_id=turma_id,
                data_limite=data_limite
            )
            db.session.add(simulado_enviado)
            db.session.flush()  # Para obter o ID do simulado_enviado
            
            # Buscar alunos da turma
            alunos = Usuarios.query.filter_by(
                tipo_usuario_id=4,  # Tipo aluno
                turma_id=turma_id
            ).all()
            
            # Criar registros para cada aluno
            for aluno in alunos:
                aluno_simulado = AlunoSimulado(
                    aluno_id=aluno.id,
                    simulado_id=simulado_enviado.id,
                    status='não respondido'
                )
                db.session.add(aluno_simulado)
        
        db.session.commit()
        return jsonify({"message": "Simulado enviado com sucesso"})
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao enviar simulado: {str(e)}")
        return jsonify({"error": str(e)}), 500

@simulados_bp.route('/professores/cancelar-envio-simulado/<int:simulado_id>', methods=['POST'])
@login_required
def cancelar_envio_simulado(simulado_id):
    if current_user.tipo_usuario_id not in [3, 6]:  # Apenas professores podem acessar
        return jsonify({'success': False, 'error': 'Acesso não autorizado'}), 403
    
    try:
        # Verificar se o simulado pertence ao professor
        simulado = SimuladosGeradosProfessor.query.filter_by(id=simulado_id, professor_id=current_user.id).first()
        
        if not simulado:
            return jsonify({'success': False, 'error': 'Simulado não encontrado'}), 404
        
        # Remover registros de aluno_simulado
        # ...
        
        # Atualizar status para gerado
        simulado.status = 'gerado'
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao cancelar envio do simulado: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@simulados_bp.route('/professores/relatorio-simulado/<int:simulado_id>')
@login_required
def relatorio_simulado(simulado_id):
    if current_user.tipo_usuario_id not in [3, 6]:  # Apenas professores podem acessar
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
        
    # Buscar informações do simulado
    simulado = db.session.query(
        SimuladosGeradosProfessor,
        Disciplinas.nome.label('disciplina_nome'),
        AnoEscolarModel.nome.label('Ano_escolar_nome'),
        MESES.nome.label('mes_nome')
    ).join(
        Disciplinas, SimuladosGeradosProfessor.disciplina_id == Disciplinas.id
    ).join(
        AnoEscolarModel, SimuladosGeradosProfessor.ano_escolar_id == AnoEscolarModel.id
    ).outerjoin(
        MESES, SimuladosGeradosProfessor.mes_id == MESES.id
    ).filter(
        SimuladosGeradosProfessor.id == simulado_id,
        SimuladosGeradosProfessor.professor_id == current_user.id
    ).first()
    
    if not simulado:
        flash("Simulado não encontrado.", "danger")
        return redirect(url_for("simulados.listar_simulados_professor"))
    
    # Formatar dados do simulado
    simulado_info = {
        'id': simulado[0].id,
        'disciplina_nome': simulado[1],
        'Ano_escolar_nome': simulado[2],
        'mes_nome': simulado[3] or 'Não definido',
        'data_criacao': simulado[0].data_criacao.strftime('%d/%m/%Y %H:%M') if simulado[0].data_criacao else 'Data não definida',
        'status': simulado[0].status
    }
    
    # Buscar estatísticas de desempenho dos alunos
    if simulado[0].status == 'enviado':
        # Buscar total de alunos que responderam e estatísticas
        estatisticas_query = db.session.query(
            db.func.count(DesempenhoSimulado.id).label('total_alunos'),
            db.func.avg(DesempenhoSimulado.desempenho).label('media_geral'),
            db.func.max(DesempenhoSimulado.desempenho).label('melhor_desempenho'),
            db.func.min(DesempenhoSimulado.desempenho).label('pior_desempenho')
        ).join(
            SimuladosEnviados, DesempenhoSimulado.simulado_id == SimuladosEnviados.id
        ).filter(
            SimuladosEnviados.simulado_id == simulado_id
        ).first()
        
        # Buscar distribuição de notas
        distribuicao_query = db.session.query(
            db.case(
                (DesempenhoSimulado.desempenho <= 20, '0-20'),
                (DesempenhoSimulado.desempenho <= 40, '21-40'),
                (DesempenhoSimulado.desempenho <= 60, '41-60'),
                (DesempenhoSimulado.desempenho <= 80, '61-80'),
                else_='81-100'
            ).label('faixa'),
            db.func.count(DesempenhoSimulado.id).label('total')
        ).join(
            SimuladosEnviados, DesempenhoSimulado.simulado_id == SimuladosEnviados.id
        ).filter(
            SimuladosEnviados.simulado_id == simulado_id
        ).group_by('faixa').all()
        
        # Formatar distribuição
        distribuicao = {
            '0-20': 0,
            '21-40': 0,
            '41-60': 0,
            '61-80': 0,
            '81-100': 0
        }
        for faixa, total in distribuicao_query:
            distribuicao[faixa] = total
        
        estatisticas = {
            'total_alunos': estatisticas_query[0] or 0,
            'media_geral': float(estatisticas_query[1] or 0),
            'melhor_desempenho': float(estatisticas_query[2] or 0),
            'pior_desempenho': float(estatisticas_query[3] or 0),
            'distribuicao_notas': distribuicao
        }
    else:
        estatisticas = {
            'total_alunos': 0,
            'media_geral': 0,
            'melhor_desempenho': 0,
            'pior_desempenho': 0,
            'distribuicao_notas': {
                '0-20': 0,
                '21-40': 0,
                '41-60': 0,
                '61-80': 0,
                '81-100': 0
            }
        }
    
    return render_template('professores/relatorio_simulado.html', 
                         simulado=simulado_info,
                         estatisticas=estatisticas)

@simulados_bp.route('/professores/enviar-simulado/<int:simulado_id>')
@login_required
def pagina_enviar_simulado(simulado_id):
    if current_user.tipo_usuario_id not in [3, 6]:  # Apenas professores podem acessar
        abort(403)
    
    try:
        # Verificar se o simulado pertence ao professor
        simulado = SimuladosGeradosProfessor.query\
            .join(Disciplinas, SimuladosGeradosProfessor.disciplina_id == Disciplinas.id)\
            .join(AnoEscolarModel, SimuladosGeradosProfessor.ano_escolar_id == AnoEscolarModel.id)\
            .join(MESES, SimuladosGeradosProfessor.mes_id == MESES.id)\
            .add_columns(
                Disciplinas.nome.label('disciplina_nome'),
                AnoEscolarModel.nome.label('Ano_escolar_nome'),
                MESES.nome.label('mes_nome')
            )\
            .filter(SimuladosGeradosProfessor.id == simulado_id, SimuladosGeradosProfessor.professor_id == current_user.id)\
            .first()
        
        if not simulado:
            abort(404)
            
        # Buscar turmas do professor
        turmas = ProfessorTurmaEscola.query\
            .join(Turmas, ProfessorTurmaEscola.turma_id == Turmas.id)\
            .join(AnoEscolarModel, ProfessorTurmaEscola.ano_escolar_id == AnoEscolarModel.id)\
            .filter(
                ProfessorTurmaEscola.professor_id == current_user.id,
                ProfessorTurmaEscola.ano_escolar_id == simulado[0].ano_escolar_id
            )\
            .all()
        
        return render_template('professores/enviar_simulado.html', 
                             simulado=simulado[0],
                             disciplina_nome=simulado.disciplina_nome,
                             Ano_escolar_nome=simulado.Ano_escolar_nome,
                             mes_nome=simulado.mes_nome,
                             turmas=turmas)
                             
    except Exception as e:
        print(f"Erro ao carregar página de envio: {str(e)}")
        abort(500)

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
from models import Usuarios, Escolas, Ano_escolar, SimuladosGerados, Disciplinas, DesempenhoSimulado, MESES, BancoQuestoes, RespostasSimulado, SimuladosEnviados, Turmas, SimuladosGeradosProfessor
from sqlalchemy import text, func, extract, and_, case, exists, or_, literal
from models import SimuladoQuestoes
from utils import verificar_permissao
from models import ImagemQuestao

# Dicionário de meses
MESES_NOMES = {
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
#     """Cria um novo simulado."""aria_educacao_bp.route('/salvar_simulado', methods=['POST'])
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
    
    # Buscar disciplinas
    disciplinas = db.session.query(Disciplinas).order_by(Disciplinas.nome).all()
    
    # Buscar todas as séries
    Anos_escolares = db.session.query(Ano_escolar).order_by(Ano_escolar.nome).all()
    
    # Buscar meses
    meses = db.session.query(MESES).order_by(MESES.id).all()
    
    # Verificar se é edição
    simulado_id = request.args.get('id', type=int)
    simulado_data = None
    questoes_selecionadas = []
    
    if simulado_id:
        # Buscar dados do simulado
        simulado = db.session.query(
            SimuladosGerados.id,
            SimuladosGerados.disciplina_id,
            SimuladosGerados.Ano_escolar_id,
            SimuladosGerados.mes_id,
            SimuladosGerados.status,
            Disciplinas.nome.label('disciplina_nome'),
            Ano_escolar.nome.label('Ano_escolar_nome'),
            MESES.nome.label('mes_nome')
        ).join(
            Disciplinas, Disciplinas.id == SimuladosGerados.disciplina_id
        ).join(
            Ano_escolar, Ano_escolar.id == SimuladosGerados.Ano_escolar_id
        ).join(
            MESES, MESES.id == SimuladosGerados.mes_id
        ).filter(
            SimuladosGerados.id == simulado_id
        ).first()
        
        if simulado:
            # Verificar se o status é 'gerado'
            if simulado.status != 'gerado':
                flash('Não é possível editar um simulado que já foi enviado. Cancele o envio primeiro.', 'warning')
                return redirect(url_for('secretaria_educacao.meus_simulados'))
            
            # Converter para dicionário com todos os dados necessários
            simulado_data = {
                'id': simulado.id,
                'disciplina_id': simulado.disciplina_id,
                'Ano_escolar_id': simulado.Ano_escolar_id,
                'mes_id': simulado.mes_id,
                'status': simulado.status,
                'disciplina_nome': simulado.disciplina_nome,
                'Ano_escolar_nome': simulado.Ano_escolar_nome,
                'mes_nome': simulado.mes_nome
            }
            
            # Buscar questões do simulado
            questoes_selecionadas = db.session.query(
                BancoQuestoes.id,
                BancoQuestoes.questao,
                BancoQuestoes.alternativa_a,
                BancoQuestoes.alternativa_b,
                BancoQuestoes.alternativa_c,
                BancoQuestoes.alternativa_d,
                BancoQuestoes.alternativa_e,
                BancoQuestoes.questao_correta,
                BancoQuestoes.assunto,
                BancoQuestoes.disciplina_id,
                BancoQuestoes.Ano_escolar_id,
                BancoQuestoes.mes_id
            ).join(
                SimuladoQuestoes,
                SimuladoQuestoes.questao_id == BancoQuestoes.id
            ).filter(
                SimuladoQuestoes.simulado_id == simulado_id
            ).order_by(
                SimuladoQuestoes.id
            ).all()
    
    return render_template('secretaria_educacao/criar_simulado.html', 
                         disciplinas=disciplinas,
                         Ano_escolar=Anos_escolares,
                         meses=meses,
                         simulado=simulado_data,
                         questoes_selecionadas=questoes_selecionadas)

@secretaria_educacao_bp.route('/salvar_simulado', methods=['POST'])
@login_required
def salvar_simulado():
    print("1. Iniciando salvar_simulado")
    if current_user.tipo_usuario_id not in [5, 6]:
        print("Usuário não autorizado")
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        print("2. Obtendo dados do request")
        dados = request.get_json()
        print(f"Dados recebidos: {dados}")
        
        # Extrair dados do JSON
        Ano_escolar_id = dados.get('Ano_escolar_id')
        mes_id = dados.get('mes_id')
        disciplina_id = dados.get('disciplina_id')
        questoes = dados.get('questoes', [])
        simulado_id = dados.get('simulado_id')
        
        print(f"3. Dados extraídos:")
        print(f"- Ano_escolar_id: {Ano_escolar_id}")
        print(f"- mes_id: {mes_id}")
        print(f"- disciplina_id: {disciplina_id}")
        print(f"- Número de questões: {len(questoes)}")
        print(f"- simulado_id: {simulado_id}")
        
        # Validar dados obrigatórios
        if not all([Ano_escolar_id, mes_id, disciplina_id]) or not questoes:
            print("Dados incompletos:")
            print(f"- Ano_escolar_id presente: {bool(Ano_escolar_id)}")
            print(f"- mes_id presente: {bool(mes_id)}")
            print(f"- disciplina_id presente: {bool(disciplina_id)}")
            print(f"- questoes presentes: {bool(questoes)}")
            return jsonify({'success': False, 'message': 'Dados incompletos'}), 400
        
        print("4. Verificando se é edição ou novo simulado")
        if simulado_id:  # Edição
            print(f"4.1 Editando simulado {simulado_id}")
            # Buscar simulado existente
            simulado = SimuladosGerados.query.get(simulado_id)
            if not simulado:
                print(f"Simulado {simulado_id} não encontrado")
                return jsonify({'success': False, 'message': 'Simulado não encontrado'}), 404
            
            # Atualizar dados do simulado
            simulado.Ano_escolar_id = Ano_escolar_id
            simulado.mes_id = mes_id
            simulado.disciplina_id = disciplina_id
            
            # Remover questões antigas
            print("Removendo questões antigas")
            SimuladoQuestoes.query.filter_by(simulado_id=simulado_id).delete()
        else:  # Novo simulado
            print("4.2 Criando novo simulado")
            simulado = SimuladosGerados(
                Ano_escolar_id=Ano_escolar_id,
                mes_id=mes_id,
                disciplina_id=disciplina_id,
                status='gerado',
                data_envio=datetime.now(),
                codigo_ibge=current_user.codigo_ibge  # Adicionar código IBGE
            )
            db.session.add(simulado)
            db.session.flush()  # Para obter o ID do simulado
            print(f"Novo simulado criado com ID: {simulado.id}")
        
        print("5. Adicionando questões")
        # Adicionar novas questões
        for i, questao in enumerate(questoes):
            print(f"Processando questão {i+1}:")
            print(f"- Dados da questão: {questao}")
            
            questao_id = questao.get('id')
            pontuacao = questao.get('pontuacao', 1.0)
            
            print(f"- ID da questão: {questao_id}")
            print(f"- Pontuação: {pontuacao}")
            
            simulado_questao = SimuladoQuestoes(
                simulado_id=simulado.id,
                questao_id=questao_id,
                pontuacao=pontuacao
            )
            db.session.add(simulado_questao)
        
        print("6. Salvando no banco de dados")
        db.session.commit()
        print("Commit realizado com sucesso")
        
        return jsonify({
            'success': True,
            'message': 'Simulado salvo com sucesso',
            'simulado_id': simulado.id,
            'redirect': '/secretaria_educacao/meus_simulados'
        })
    
    except Exception as e:
        print(f"ERRO: {str(e)}")
        print(f"Tipo do erro: {type(e)}")
        import traceback
        print(f"Traceback completo:")
        print(traceback.format_exc())
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao salvar simulado: {str(e)}'}), 500

        
# @secretaria_educacao_bp.route('/buscar_questoes', methods=['GET'])
# @login_required
# def buscar_questoes():
#     if current_user.tipo_usuario_id not in [5, 6]:
#         return jsonify({'error': 'Acesso não autorizado'}), 403

#     Ano_escolar_id = request.args.get('Ano_escolar_id', '')
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
#         LEFT JOIN Ano_escolar s ON bq.Ano_escolar_id = s.id
#         LEFT JOIN disciplinas d ON bq.disciplina_id = d.id
#         WHERE 1=1
#     """
#     params = []

#     if Ano_escolar_id:
#         query += " AND bq.Ano_escolar_id = ?"
#         params.append(Ano_escolar_id)
    
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
#                 'Ano_escolar_id': q[10],
#                 'mes_id': q[11],
#                 'disciplina_nome': q[12],
#                 'Ano_escolar_nome': q[13]
#             }
#             questoes_list.append(questao)

#         return jsonify(questoes_list)
#     except Exception as e:
#         print(f"Erro ao buscar questões: {str(e)}")
#         return jsonify({'error': 'Erro ao buscar questões'}), 500

@secretaria_educacao_bp.route('/buscar_questoes', methods=['GET'])
@login_required
def buscar_questoes():
    """Buscar questões para o simulado."""
    print("1. Iniciando busca de questões")
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        print("2. Pegando parâmetros da URL")
        # Pegar parâmetros da URL
        disciplina_id = request.args.get('disciplina_id', '')
        Ano_escolar_id = request.args.get('Ano_escolar_id', '')
        mes_id = request.args.get('mes_id', '')
        assunto = request.args.get('assunto', '')
        
        print(f"3. Parâmetros recebidos: disciplina={disciplina_id}, Ano_escolar={Ano_escolar_id}, mes={mes_id}, assunto={assunto}")
        
        print("4. Construindo query base")
        # Construir a query base usando SQL nativo
        sql = """
            SELECT bq.id, bq.questao, bq.alternativa_a, bq.alternativa_b, bq.alternativa_c, 
                   bq.alternativa_d, bq.alternativa_e, bq.questao_correta, bq.assunto,
                   bq.disciplina_id, bq.Ano_escolar_id, bq.mes_id,
                   d.nome as disciplina_nome, ae.nome as Ano_escolar_nome
            FROM banco_questoes bq
            JOIN disciplinas d ON bq.disciplina_id = d.id
            JOIN Ano_escolar ae ON bq.Ano_escolar_id = ae.id
            WHERE bq.codigo_ibge = :codigo_ibge
        """
        params = {'codigo_ibge': current_user.codigo_ibge}
        
        # Adicionar filtros conforme os parâmetros
        if disciplina_id and disciplina_id != '' and disciplina_id.isdigit():
            sql += " AND bq.disciplina_id = :disciplina_id"
            params['disciplina_id'] = int(disciplina_id)
        if Ano_escolar_id and Ano_escolar_id != '' and Ano_escolar_id.isdigit():
            sql += " AND bq.Ano_escolar_id = :Ano_escolar_id"
            params['Ano_escolar_id'] = int(Ano_escolar_id)
        if mes_id and mes_id != '' and mes_id.isdigit():
            sql += " AND bq.mes_id = :mes_id"
            params['mes_id'] = int(mes_id)
        if assunto and assunto.strip():
            sql += " AND bq.assunto LIKE :assunto"
            params['assunto'] = f"%{assunto}%"
            
        sql += " ORDER BY bq.id DESC"
        
        print("5. Executando query")
        # Executar a query
        result = db.session.execute(text(sql), params)
        questoes = result.fetchall()
        
        print(f"6. Query executada, {len(questoes)} questões encontradas")
        
        # Formatar resultado
        resultado = []
        for q in questoes:
            questao_dict = {
                'id': q.id,
                'questao': q.questao,
                'alternativa_a': q.alternativa_a,
                'alternativa_b': q.alternativa_b,
                'alternativa_c': q.alternativa_c,
                'alternativa_d': q.alternativa_d,
                'alternativa_e': q.alternativa_e,
                'questao_correta': q.questao_correta,
                'assunto': q.assunto,
                'disciplina_id': q.disciplina_id,
                'Ano_escolar_id': q.Ano_escolar_id,
                'mes_id': q.mes_id,
                'disciplina_nome': q.disciplina_nome,
                'Ano_escolar_nome': q.Ano_escolar_nome
            }
            
            # Processar imagens nas questões e alternativas
            for campo in ['questao', 'alternativa_a', 'alternativa_b', 'alternativa_c', 'alternativa_d', 'alternativa_e']:
                if questao_dict[campo] and '<img' in questao_dict[campo]:
                    if '{{ url_for' in questao_dict[campo]:
                        import re
                        pre_img = questao_dict[campo].split('<img')[0]
                        match = re.search(r"filename='([^']*)'?\s*", questao_dict[campo])
                        if match:
                            filename = match.group(1).strip()
                            questao_dict[campo] = f'{pre_img}<img src="/static/{filename}'
            
            resultado.append(questao_dict)
        
        print("7. Retornando resultado")
        return jsonify({'success': True, 'questoes': resultado})
    
    except Exception as e:
        print(f"ERRO: {str(e)}")
        print(f"Tipo do erro: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)}), 500

@secretaria_educacao_bp.route('/gerar_simulado_automatico', methods=['POST'])
@login_required
def gerar_simulado_automatico():
    """Gera um simulado automaticamente com base nos parâmetros fornecidos."""
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        # Pegar dados do formulário
        Ano_escolar_id = request.form.get('Ano_escolar_id')
        mes_id = request.form.get('mes_id')
        disciplina_id = request.form.get('disciplina_id')
        num_questoes = request.form.get('num_questoes', type=int)
        
        if not all([Ano_escolar_id, mes_id, disciplina_id, num_questoes]):
            return jsonify({'success': False, 'message': 'Dados incompletos'}), 400
        
        # Buscar questões aleatórias do banco
        questoes = db.session.query(BancoQuestoes).filter(
            BancoQuestoes.Ano_escolar_id == Ano_escolar_id,
            BancoQuestoes.mes_id == mes_id,
            BancoQuestoes.disciplina_id == disciplina_id,
            BancoQuestoes.codigo_ibge == current_user.codigo_ibge
        ).order_by(
            func.random()
        ).limit(num_questoes).all()
        
        if not questoes:
            return jsonify({
                'success': False, 
                'message': 'Não há questões suficientes para gerar o simulado'
            }), 400
        
        # Criar novo simulado
        simulado = SimuladosGerados(
            Ano_escolar_id=Ano_escolar_id,
            mes_id=mes_id,
            disciplina_id=disciplina_id,
            status='gerado',
            codigo_ibge=current_user.codigo_ibge
        )
        db.session.add(simulado)
        db.session.flush()  # Para obter o ID do simulado
        
        # Inserir questões do simulado
        for questao in questoes:
            questao_simulado = SimuladoQuestoes(
                simulado_id=simulado.id,
                questao_id=questao.id
            )
            db.session.add(questao_simulado)
        
        db.session.commit()
        
        # Formatar questões para retorno
        questoes_formatadas = [{
            'id': q.id,
            'questao': q.questao,
            'alternativa_a': q.alternativa_a,
            'alternativa_b': q.alternativa_b,
            'alternativa_c': q.alternativa_c,
            'alternativa_d': q.alternativa_d,
            'alternativa_e': q.alternativa_e,
            'questao_correta': q.questao_correta,
            'assunto': q.assunto
        } for q in questoes]
        
        return jsonify({
            'success': True,
            'message': 'Simulado gerado com sucesso',
            'simulado_id': simulado.id,
            'questoes': questoes_formatadas
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500



# @secretaria_educacao_bp.route('/salvar_simulado', methods=['POST'])
# @login_required
# def salvar_simulado():
#     if current_user.tipo_usuario_id not in [5, 6]:
#         return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
#     try:
#         # Pegar dados do formulário
#         Ano_escolar_id = request.form.get('Ano_escolar_id')
#         mes_id = request.form.get('mes_id')
#         disciplina_id = request.form.get('disciplina_id')
#         questoes = request.form.getlist('questoes[]')  # Lista de IDs das questões
        
#         if not all([Ano_escolar_id, mes_id, disciplina_id, questoes]):
#             return jsonify({'success': False, 'message': 'Dados incompletos'}), 400
        
#         # Criar novo simulado
#         query = """
#             INSERT INTO simulados_gerados (Ano_escolar_id, mes_id, disciplina_id, status, data_envio)
#             VALUES (?, ?, ?, 'gerado', CURRENT_TIMESTAMP)
#         """
#         cursor = get_db().cursor()
#         cursor.execute(query, (Ano_escolar_id, mes_id, disciplina_id))
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
    """Lista todas as questões do banco."""
    if current_user.tipo_usuario_id not in [3, 5]:  # Permitir acesso para professores (3) e secretaria (5)
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
            Ano_escolar_id = request.form.get('Ano_escolar_id')
            mes_id = request.form.get('mes_id')
            codigo_ibge = current_user.codigo_ibge

            # Validar dados
            if not all([questao, alternativa_a, alternativa_b, alternativa_c, alternativa_d,
                       questao_correta, disciplina_id, Ano_escolar_id]):
                return jsonify({
                    'success': False,
                    'message': 'Por favor, preencha todos os campos obrigatórios'
                }), 400

            # Processar questão e alternativas para garantir que as tags de imagem estejam corretas
            def processar_conteudo(texto):
                if texto:
                    # Garantir que as tags de imagem usem url_for
                    return texto.replace('src="/static/', 'src="{{ url_for(\'static\', filename=\'')
                return texto

            questao = processar_conteudo(questao)
            alternativa_a = processar_conteudo(alternativa_a)
            alternativa_b = processar_conteudo(alternativa_b)
            alternativa_c = processar_conteudo(alternativa_c)
            alternativa_d = processar_conteudo(alternativa_d)
            alternativa_e = processar_conteudo(alternativa_e)

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
                Ano_escolar_id=Ano_escolar_id,
                mes_id=mes_id,
                usuario_id=current_user.id,
                codigo_ibge=codigo_ibge
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
        anos_escolares = db.session.query(Ano_escolar).order_by(Ano_escolar.nome).all()
        disciplinas = db.session.query(Disciplinas).order_by(Disciplinas.nome).all()
        
        # Buscar questões com informações relacionadas
        questoes = db.session.query(
            BancoQuestoes,
            Disciplinas.nome.label('disciplina_nome'),
            Ano_escolar.nome.label('ano_escolar_nome'),
            MESES.nome.label('mes_nome')
        ).join(
            Disciplinas, Disciplinas.id == BancoQuestoes.disciplina_id
        ).join(
            Ano_escolar, Ano_escolar.id == BancoQuestoes.Ano_escolar_id
        ).outerjoin(
            MESES, MESES.id == BancoQuestoes.mes_id
        )
        
        # Se for professor, filtrar apenas suas próprias questões
        # Se for secretaria, filtrar por código IBGE
        if current_user.tipo_usuario_id == 3:
            questoes = questoes.filter(
                BancoQuestoes.usuario_id == current_user.id
            )
        else:  # tipo 5 - secretaria
            questoes = questoes.filter(
                BancoQuestoes.codigo_ibge == current_user.codigo_ibge
            )
        
        questoes = questoes.order_by(BancoQuestoes.id.desc()).all()

        # Processar os resultados para incluir todos os campos necessários
        questoes_processadas = []
        for q in questoes:
            # Processar conteúdo para exibir imagens corretamente
            def processar_conteudo_exibicao(texto):
                if texto:
                    return texto.replace('src="{{ url_for(\'static\', filename=\'', 'src="/static/')
                return texto

            questao_dict = {
                'id': q.BancoQuestoes.id,
                'questao': processar_conteudo_exibicao(q.BancoQuestoes.questao),
                'alternativa_a': processar_conteudo_exibicao(q.BancoQuestoes.alternativa_a),
                'alternativa_b': processar_conteudo_exibicao(q.BancoQuestoes.alternativa_b),
                'alternativa_c': processar_conteudo_exibicao(q.BancoQuestoes.alternativa_c),
                'alternativa_d': processar_conteudo_exibicao(q.BancoQuestoes.alternativa_d),
                'alternativa_e': processar_conteudo_exibicao(q.BancoQuestoes.alternativa_e),
                'questao_correta': q.BancoQuestoes.questao_correta,
                'assunto': q.BancoQuestoes.assunto,
                'disciplina_nome': q.disciplina_nome,
                'Ano_escolar_nome': q.ano_escolar_nome,
                'mes_nome': q.mes_nome if q.mes_nome else '-',
                'mes_id': q.BancoQuestoes.mes_id
            }
            questoes_processadas.append(questao_dict)

        # Lista de meses
        meses = [{'id': i, 'nome': nome} for i, nome in MESES_NOMES.items()]

        return render_template('secretaria_educacao/banco_questoes.html',
                            questoes=questoes_processadas,
                            disciplinas=disciplinas,
                            Ano_escolar=anos_escolares,
                            meses=meses)

    except Exception as e:
        print("DEBUG - Erro completo:", str(e))
        flash(f"Erro ao carregar banco de questões: {str(e)}", "danger")
        return redirect(url_for("index"))

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
        Ano_escolar, Usuarios.Ano_escolar_id == Ano_escolar.id
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
        .join(Usuarios, SimuladosGerados.Ano_escolar_id == Usuarios.Ano_escolar_id)\
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
    ).join(Ano_escolar, SimuladosGerados.Ano_escolar_id == Ano_escolar.id)\
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
    """Lista todos os simulados gerados."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    try:
        # Buscar simulados com informações relacionadas
        simulados = db.session.query(
            SimuladosGerados.id,
            SimuladosGerados.status,
            SimuladosGerados.data_envio,
            SimuladosGerados.disciplina_id,
            SimuladosGerados.Ano_escolar_id,
            SimuladosGerados.mes_id,
            Disciplinas.nome.label('disciplina_nome'),
            Ano_escolar.nome.label('Ano_escolar_nome'),
            MESES.nome.label('mes_nome'),
            func.count(SimuladoQuestoes.id).label('total_questoes')
        ).join(
            Disciplinas, Disciplinas.id == SimuladosGerados.disciplina_id
        ).join(
            Ano_escolar, Ano_escolar.id == SimuladosGerados.Ano_escolar_id
        ).join(
            MESES, MESES.id == SimuladosGerados.mes_id
        ).outerjoin(
            SimuladoQuestoes, SimuladoQuestoes.simulado_id == SimuladosGerados.id
        ).filter(
            SimuladosGerados.codigo_ibge == current_user.codigo_ibge
        ).group_by(
            SimuladosGerados.id,
            SimuladosGerados.status,
            SimuladosGerados.data_envio,
            SimuladosGerados.disciplina_id,
            SimuladosGerados.Ano_escolar_id,
            SimuladosGerados.mes_id,
            Disciplinas.nome,
            Ano_escolar.nome,
            MESES.nome
        ).order_by(
            SimuladosGerados.id.desc()
        ).all()
        
        # Formatar dados para a template
        simulados_formatados = []
        for s in simulados:
            simulado_dict = {
                'id': s.id,
                'Ano_escolar_nome': s.Ano_escolar_nome,
                'disciplina_nome': s.disciplina_nome,
                'mes_nome': s.mes_nome,
                'status': s.status,
                'data_envio': s.data_envio.strftime('%d/%m/%Y %H:%M') if s.data_envio else '',
                'total_questoes': s.total_questoes
            }
            simulados_formatados.append(simulado_dict)
        
        return render_template(
            'secretaria_educacao/meus_simulados.html',
            simulados=simulados_formatados
        )
        
    except Exception as e:
        print(f"Erro ao carregar simulados: {str(e)}")
        flash(f"Erro ao carregar simulados: {str(e)}", "danger")
        return redirect(url_for("index"))@secretaria_educacao_bp.route('/meus_simulados', methods=['GET'])

@secretaria_educacao_bp.route('/enviar_simulado/<int:simulado_id>', methods=['POST'])
@login_required
def enviar_simulado(simulado_id):
    """Envia um simulado para os alunos."""
    print(f"\n=== Iniciando envio do simulado {simulado_id} ===")
    print(f"Usuário atual: {current_user.id} - tipo: {current_user.tipo_usuario_id}")
    
    if current_user.tipo_usuario_id not in [5, 6]:
        print("Erro: Usuário não autorizado")
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        # Limpar o cache da sessão para pegar dados atualizados
        db.session.expire_all()
        
        # Buscar simulado e verificar se pode ser enviado
        simulado = db.session.query(SimuladosGerados).filter(
            SimuladosGerados.id == simulado_id,
            SimuladosGerados.codigo_ibge == current_user.codigo_ibge,
            SimuladosGerados.status == 'gerado'
        ).first()
        
        print(f"Simulado encontrado: {simulado is not None}")
        if simulado:
            print(f"Status do simulado: {simulado.status}")
            print(f"Ano Escolar do simulado: {simulado.Ano_escolar_id}")
        
        if not simulado:
            print("Erro: Simulado não encontrado ou não pode ser enviado")
            return jsonify({
                'success': False,
                'message': 'Simulado não encontrado ou não pode ser enviado'
            }), 404
        
        # Buscar alunos da série do município
        alunos = db.session.query(Usuarios).filter(
            Usuarios.tipo_usuario_id == 4,  # Aluno
            Usuarios.Ano_escolar_id == simulado.Ano_escolar_id,
            Usuarios.codigo_ibge == current_user.codigo_ibge
        ).all()
        
        print(f"Número de alunos encontrados: {len(alunos)}")
        
        if not alunos:
            print("Erro: Nenhum aluno encontrado para esta série")
            return jsonify({
                'success': False,
                'message': 'Nenhum aluno encontrado para esta série'
            }), 404
        
        try:
            # Primeiro, criar um registro em simulados_enviados para cada turma
            turmas_ids = set(aluno.turma_id for aluno in alunos if aluno.turma_id is not None)
            simulados_enviados = {}
            
            for turma_id in turmas_ids:
                simulado_enviado = SimuladosEnviados(
                    simulado_id=simulado_id,  # ID do simulado gerado
                    turma_id=turma_id,
                    data_envio=datetime.now(),
                    status='enviado'
                )
                db.session.add(simulado_enviado)
                db.session.flush()  # Para obter o ID
                simulados_enviados[turma_id] = simulado_enviado.id
            
            # Atualizar status do simulado
            simulado.status = 'enviado'
            simulado.data_envio = datetime.now()
            print(f"Status do simulado atualizado para: {simulado.status}")
            
            # Criar registros de desempenho para cada aluno
            for aluno in alunos:
                if aluno.turma_id is None:
                    print(f"Pulando aluno {aluno.id} - sem turma definida")
                    continue
                    
                print(f"\nCriando registro para aluno {aluno.id}:")
                print(f"Escola: {aluno.escola_id}")
                print(f"Ano Escolar: {simulado.Ano_escolar_id}")
                print(f"Turma: {aluno.turma_id}")
                
                try:
                    desempenho = DesempenhoSimulado(
                        aluno_id=aluno.id,
                        simulado_id=simulados_enviados[aluno.turma_id],  # ID do simulado_enviado da turma
                        escola_id=aluno.escola_id,
                        Ano_escolar_id=simulado.Ano_escolar_id,
                        codigo_ibge=int(current_user.codigo_ibge),
                        respostas_aluno='{}',  # JSON vazio
                        respostas_corretas='{}',  # JSON vazio
                        desempenho=0.0,  # Inicialmente 0
                        turma_id=aluno.turma_id
                    )
                    db.session.add(desempenho)
                    print("Registro de desempenho criado com sucesso")
                except Exception as e:
                    print(f"Erro ao criar registro de desempenho: {str(e)}")
                    raise e
            
            # Commit dos registros
            db.session.commit()
            print("\nCommit realizado com sucesso!")
            return jsonify({'success': True, 'message': 'Simulado enviado com sucesso'})
            
        except Exception as e:
            print(f"\nErro no commit: {str(e)}")
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
            
    except Exception as e:
        print(f"\nErro geral na função: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@secretaria_educacao_bp.route('/visualizar_simulado/<int:simulado_id>')
@login_required
def visualizar_simulado(simulado_id):
    """Visualiza os detalhes de um simulado."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    try:
        # Buscar informações do simulado
        simulado = db.session.query(
            SimuladosGerados.id,
            SimuladosGerados.status,
            SimuladosGerados.data_envio,
            Disciplinas.nome.label('disciplina_nome'),
            Ano_escolar.nome.label('Ano_escolar_nome'),
            MESES.nome.label('mes_nome')
        ).join(
            Disciplinas, Disciplinas.id == SimuladosGerados.disciplina_id
        ).join(
            Ano_escolar, Ano_escolar.id == SimuladosGerados.Ano_escolar_id
        ).join(
            MESES, MESES.id == SimuladosGerados.mes_id
        ).filter(
            SimuladosGerados.id == simulado_id,
            SimuladosGerados.codigo_ibge == current_user.codigo_ibge
        ).first()
        
        if not simulado:
            flash("Simulado não encontrado.", "danger")
            return redirect(url_for("secretaria_educacao.meus_simulados"))
        
        # Buscar questões do simulado
        questoes = db.session.query(
            BancoQuestoes.id,
            BancoQuestoes.questao,
            BancoQuestoes.alternativa_a,
            BancoQuestoes.alternativa_b,
            BancoQuestoes.alternativa_c,
            BancoQuestoes.alternativa_d,
            BancoQuestoes.alternativa_e,
            BancoQuestoes.questao_correta,
            BancoQuestoes.assunto
        ).join(
            SimuladoQuestoes, SimuladoQuestoes.questao_id == BancoQuestoes.id
        ).filter(
            SimuladoQuestoes.simulado_id == simulado_id
        ).order_by(
            SimuladoQuestoes.id
        ).all()

        # Processar questões para garantir que as imagens sejam renderizadas corretamente
        questoes_processadas = []
        for q in questoes:
            questao_dict = q._asdict()
            # Garantir que as imagens usem o caminho correto
            for campo in ['questao', 'alternativa_a', 'alternativa_b', 'alternativa_c', 'alternativa_d', 'alternativa_e']:
                if questao_dict[campo] and '<img' in questao_dict[campo]:
                    # Processar url_for no texto
                    if '{{ url_for' in questao_dict[campo]:
                        import re
                        # Extrai o texto antes da tag img
                        pre_img = questao_dict[campo].split('<img')[0]
                        # Busca o filename
                        match = re.search(r"filename='([^']*)'?\s*", questao_dict[campo])
                        if match:
                            filename = match.group(1).strip()
                            # Reconstrói a questão com a nova tag img
                            questao_dict[campo] = f'{pre_img}<img src="/static/{filename}'
            questoes_processadas.append(questao_dict)
        
        return render_template(
            'secretaria_educacao/visualizar_simulado.html',
            simulado=simulado,
            questoes=questoes_processadas
        )
        
    except Exception as e:
        flash(f"Erro ao carregar simulado: {str(e)}", "danger")
        return redirect(url_for("secretaria_educacao.meus_simulados"))

@secretaria_educacao_bp.route('/excluir_simulado/<int:simulado_id>', methods=['POST'])
@login_required
def excluir_simulado(simulado_id):
    """Exclui um simulado e suas questões."""
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        # Verificar se o simulado existe e pode ser excluído
        simulado = db.session.query(SimuladosGerados).filter(
            SimuladosGerados.id == simulado_id,
            SimuladosGerados.codigo_ibge == current_user.codigo_ibge,
            SimuladosGerados.status == 'gerado'
        ).first()
        
        if not simulado:
            return jsonify({
                'success': False,
                'message': 'Simulado não encontrado ou não pode ser excluído'
            }), 404
        
        # Excluir questões do simulado
        db.session.query(SimuladoQuestoes).filter(
            SimuladoQuestoes.simulado_id == simulado_id
        ).delete()
        
        # Excluir simulado
        db.session.delete(simulado)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Simulado excluído com sucesso'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@secretaria_educacao_bp.route('/salvar_edicao_simulado/<int:simulado_id>', methods=['POST'])
@login_required
def salvar_edicao_simulado(simulado_id):
    """Salva as alterações feitas em um simulado."""
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        # Pegar dados do formulário
        questoes = request.form.getlist('questoes[]')  # Lista de IDs das questões
        
        if not questoes:
            return jsonify({'success': False, 'message': 'Nenhuma questão selecionada'}), 400
        
        # Buscar simulado e verificar se pode ser editado
        simulado = db.session.query(SimuladosGerados).filter(
            SimuladosGerados.id == simulado_id,
            SimuladosGerados.codigo_ibge == current_user.codigo_ibge,
            SimuladosGerados.status == 'gerado'
        ).first()
        
        if not simulado:
            return jsonify({
                'success': False,
                'message': 'Simulado não encontrado ou não pode ser editado'
            }), 404
        
        # Remover questões antigas
        db.session.query(SimuladoQuestoes).filter(
            SimuladoQuestoes.simulado_id == simulado_id
        ).delete()
        
        # Inserir novas questões
        for questao_id in questoes:
            questao = SimuladoQuestoes(
                simulado_id=simulado_id,
                questao_id=questao_id
            )
            db.session.add(questao)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Simulado atualizado com sucesso'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

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
            LEFT JOIN Ano_escolar s ON q.Ano_escolar_id = s.id
            WHERE q.id = ?
        """, (questao_id,))
        
        questao = cursor.fetchone()
        
        if questao is None:
            return jsonify({'success': False, 'message': 'Questão não encontrada'}), 404
        
        # Converter o número do mês para nome
        mes_nome = MESES_NOMES.get(questao[11]) if questao[11] else None
        
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
                'Ano_escolar_id': questao[10],
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
        Ano_escolar_id = request.form.get('Ano_escolar_id')
        mes_id = request.form.get('mes_id')
        
        # Converte para None se vazio
        Ano_escolar_id = None if not Ano_escolar_id else int(Ano_escolar_id)
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
                Ano_escolar_id = ?,
                mes_id = ?
            WHERE id = ?
        """, (questao, alternativa_a, alternativa_b, alternativa_c, alternativa_d,
              alternativa_e, questao_correta, disciplina_id, assunto, Ano_escolar_id, mes_id, questao_id))
        
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
    mes = request.args.get('mes', type=int)
    
    # Condição de data para filtrar por mês
    data_condition = []
    if mes:
        data_condition = [extract('month', DesempenhoSimulado.data_resposta) == mes]
    
    # Consulta escolas
    escolas_query = db.session.query(
        Escolas.id,
        Escolas.nome_da_escola.label('nome'),  # Mudado para nome_da_escola
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.escola_id == Escolas.id,  # Mudado para Escolas
            Usuarios.tipo_usuario_id == 4  # Alunos
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).group_by(
        Escolas.id, Escolas.nome_da_escola  # Mudado para nome_da_escola
    ).order_by(
        Escolas.nome_da_escola  # Mudado para nome_da_escola
    ).all()

    # Consulta anos escolares
    anos_query = db.session.query(
        Ano_escolar.id,
        Ano_escolar.nome.label('Ano_escolar_nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.Ano_escolar_id == Ano_escolar.id,
            Usuarios.tipo_usuario_id == 4
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).group_by(
        Ano_escolar.id, Ano_escolar.nome
    ).order_by(
        Ano_escolar.id
    ).all()

    # Consulta disciplinas
    disciplinas_query = db.session.query(
        Disciplinas.id,
        Disciplinas.nome,
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        SimuladosGerados, SimuladosGerados.disciplina_id == Disciplinas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.simulado_id == SimuladosGerados.id,
            *data_condition
        )
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).order_by(
        Disciplinas.nome
    ).all()

    # Dados para os gráficos
    escolas_nomes = [escola.nome for escola in escolas_query]
    escolas_medias = [float(escola.media) for escola in escolas_query]
    participacao_escolas = [float(escola.alunos_ativos / escola.total_alunos * 100) if escola.total_alunos > 0 else 0 for escola in escolas_query]
    
    anos_nomes = [ano.Ano_escolar_nome for ano in anos_query]
    anos_medias = [float(ano.media) for ano in anos_query]
    
    disciplinas_nomes = [disc.nome for disc in disciplinas_query]
    disciplinas_medias = [float(disc.media) for disc in disciplinas_query]

    # Debug dos dados
    print("Dados dos gráficos:")
    print("Escolas:", escolas_nomes, escolas_medias)
    print("Anos:", anos_nomes, anos_medias)
    print("Disciplinas:", disciplinas_nomes, disciplinas_medias)
    print("Participação:", participacao_escolas)

    # Calcular totais
    total_escolas = len(escolas_query)
    total_alunos = sum(escola.total_alunos for escola in escolas_query)
    total_simulados = db.session.query(func.count(DesempenhoSimulado.id)).filter(*data_condition).scalar() or 0
    media_geral = sum(escola.media * escola.alunos_ativos for escola in escolas_query) / sum(escola.alunos_ativos for escola in escolas_query) if sum(escola.alunos_ativos for escola in escolas_query) > 0 else 0

    return render_template('secretaria_educacao/relatorio_rede_municipal.html',
                         mes=mes,
                         escolas=escolas_query,
                         total_escolas=total_escolas,
                         total_alunos=total_alunos,
                         total_simulados=total_simulados,
                         media_geral=round(media_geral, 1),
                         escolas_nomes=escolas_nomes,
                         escolas_medias=escolas_medias,
                         participacao_escolas=participacao_escolas,
                         anos_nomes=anos_nomes,
                         anos_medias=anos_medias,
                         disciplinas_nomes=disciplinas_nomes,
                         disciplinas_medias=disciplinas_medias,
                         anos_query=anos_query)

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
    
    codigo_ibge = current_user.codigo_ibge
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    from sqlalchemy import func, and_, extract, case, literal_column
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Aba Visão Geral - Dados das escolas
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
    
    df_escolas = pd.DataFrame(escolas)
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
    disciplinas_query = db.session.query(
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
    
    disciplinas = [dict(zip(['disciplina', 'total_alunos', 'total_questoes', 'media_acertos'], disc)) 
                  for disc in disciplinas_query.all()]
    
    df_disciplinas = pd.DataFrame(disciplinas)
    if not df_disciplinas.empty:
        df_disciplinas = df_disciplinas.rename(columns={
            'disciplina': 'Disciplina',
            'total_alunos': 'Total de Alunos',
            'total_questoes': 'Total de Questões',
            'media_acertos': 'Média de Acertos (%)'
        })
    df_disciplinas.to_excel(writer, sheet_name='Desempenho por Disciplina', index=False)

    # Buscar todas as séries
    Ano_escolar = db.session.query(Ano_escolar.id, Ano_escolar.nome).order_by(Ano_escolar.id).all()

    # Para cada série, criar uma aba com desempenho por escola
    for Ano_escolar in Ano_escolar:
        Ano_escolar_id = Ano_escolar[0]
        Ano_escolar_nome = Ano_escolar[1]
        
        # Query para dados da série específica
        anos_escolares_query = db.session.query(
            Escolas.id.label('escola_id'),
            Escolas.nome_da_escola,
            func.count(func.distinct(Usuarios.id)).label('total_alunos'),
            func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_responderam'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral'),
            Disciplinas.nome.label('disciplina'),
            func.coalesce(
                func.avg(case((
                    and_(
                        DesempenhoSimulado.tipo_usuario_id == 5,
                        SimuladosGerados.disciplina_id == Disciplinas.id
                    ), DesempenhoSimulado.desempenho
                ))), 0.0
            ).label('media_disciplina')
        ).outerjoin(
            Usuarios, and_(
                Usuarios.escola_id == Escolas.id,
                Usuarios.tipo_usuario_id == 4,
                Usuarios.Ano_escolar_id == Ano_escolar_id,
                Usuarios.codigo_ibge == codigo_ibge
            )
        ).outerjoin(
            DesempenhoSimulado, and_(
                DesempenhoSimulado.aluno_id == Usuarios.id,
                *data_condition
            )
        ).outerjoin(
            SimuladosGerados, SimuladosGerados.id == DesempenhoSimulado.simulado_id
        ).outerjoin(
            Disciplinas
        ).filter(
            Escolas.codigo_ibge == codigo_ibge
        ).group_by(
            Escolas.id, Escolas.nome_da_escola, Disciplinas.id, Disciplinas.nome
        ).having(
            func.count(func.distinct(Usuarios.id)) > 0
        ).order_by(
            db.desc('media_geral')
        )
        
        rows = anos_escolares_query.all()
        
        if rows:
            # Converter para DataFrame
            df_Ano_escolar = pd.DataFrame([
                dict(zip(
                    ['escola_id', 'nome_da_escola', 'total_alunos', 'alunos_responderam', 
                     'media_geral', 'disciplina', 'media_disciplina'],
                    row
                )) for row in rows
            ])
            
            # Renomear colunas
            df_Ano_escolar = df_Ano_escolar.rename(columns={
                'nome_da_escola': 'Escola',
                'total_alunos': 'Total de Alunos',
                'alunos_responderam': 'Alunos Ativos',
                'media_geral': 'Média Geral (%)'
            })
            
            # Arredondar médias
            df_Ano_escolar['Média Geral (%)'] = df_Ano_escolar['Média Geral (%)'].round(1)
            
            # Pivotear para ter disciplinas como colunas
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
                # Se não houver dados de disciplinas, salvar apenas dados gerais
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
    
    # Preparar dados para o gráfico
    disciplinas_nomes = [d['disciplina'] for d in disciplinas]
    disciplinas_medias = [float(d['media_acertos']) for d in disciplinas]
    
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
    
    codigo_ibge = current_user.codigo_ibge
    
    # Buscar todas as escolas do município
    escolas = db.session.query(
        Escolas.id, 
        Escolas.nome_da_escola.label('nome')
    ).filter(
        Escolas.codigo_ibge == codigo_ibge
    ).order_by(
        Escolas.nome_da_escola
    ).all()
    
    # Obter escola_id e mês da query string
    escola_id = request.args.get('escola_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Se uma escola foi selecionada, buscar seus dados
    if escola_id:
        from sqlalchemy import func, and_, extract, case
        
        # Construir a condição de data
        data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
        if mes:
            data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
        
        # Buscar dados gerais da escola
        escola = db.session.query(
            Escolas.nome_da_escola.label('nome'),
            func.count(func.distinct(Usuarios.id)).label('total_alunos'),
            func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
            func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral')
        ).outerjoin(
            Usuarios, and_(
                Usuarios.escola_id == Escolas.id,
                Usuarios.tipo_usuario_id == 4
            )
        ).outerjoin(
            DesempenhoSimulado, and_(
                DesempenhoSimulado.aluno_id == Usuarios.id,
                *data_condition
            )
        ).filter(
            Escolas.id == escola_id
        ).group_by(
            Escolas.id, Escolas.nome_da_escola
        ).first()
        
        # Buscar dados por série
        anos_escolares_query = db.session.query(
            Ano_escolar.id,
            Ano_escolar.nome.label('Ano_escolar_nome'),
            func.count(func.distinct(Usuarios.id)).label('total_alunos'),
            func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
        ).outerjoin(
            Usuarios, and_(
                Usuarios.Ano_escolar_id == Ano_escolar.id,
                Usuarios.tipo_usuario_id == 4,
                Usuarios.escola_id == escola_id
            )
        ).outerjoin(
            DesempenhoSimulado, and_(
                DesempenhoSimulado.aluno_id == Usuarios.id,
                *data_condition
            )
        ).group_by(
            Ano_escolar.id, Ano_escolar.nome
        ).order_by(
            Ano_escolar.id
        ).all()
        
        anos_escolares = [dict(zip(['id', 'Ano_escolar_nome', 'total_alunos', 'alunos_ativos', 'media'], ano)) 
                       for ano in anos_escolares_query]
        
        # Buscar dados por disciplina
        disciplinas = db.session.query(
            Disciplinas.nome.label('disciplina'),
            func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
            func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_questoes'),
            func.round(func.avg(DesempenhoSimulado.desempenho), 1).label('media_acertos')
        ).outerjoin(
            SimuladosGerados, SimuladosGerados.disciplina_id == Disciplinas.id
        ).outerjoin(
            DesempenhoSimulado, and_(
                DesempenhoSimulado.simulado_id == SimuladosGerados.id,
                *data_condition
            )
        ).join(
            Usuarios, and_(
                Usuarios.id == DesempenhoSimulado.aluno_id,
                Usuarios.escola_id == escola_id
            )
        ).group_by(
            Disciplinas.id, Disciplinas.nome
        ).having(
            func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
        ).order_by(
            db.desc('media_acertos')
        ).all()
        
        # Buscar dados por turma
        turmas = db.session.query(
            Turmas.id,
            (Ano_escolar.nome + ' ' + Turmas.turma).label('turma'),
            func.count(func.distinct(Usuarios.id)).label('total_alunos'),
            func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
        ).join(
            Ano_escolar, Ano_escolar.id == Turmas.Ano_escolar_id
        ).outerjoin(
            Usuarios, and_(
                Usuarios.turma_id == Turmas.id,
                Usuarios.tipo_usuario_id == 4,
                Usuarios.escola_id == escola_id
            )
        ).outerjoin(
            DesempenhoSimulado, and_(
                DesempenhoSimulado.aluno_id == Usuarios.id,
                *data_condition
            )
        ).group_by(
            Turmas.id, Turmas.turma, Ano_escolar.nome
        ).having(
            func.count(func.distinct(Usuarios.id)) > 0
        ).order_by(
            Ano_escolar.nome, Turmas.turma
        ).all()
        
        # Buscar dados dos alunos por turma com desempenho por disciplina
        alunos = db.session.query(
            Turmas.id.label('turma_id'),
            Usuarios.id.label('aluno_id'),
            Usuarios.nome.label('aluno_nome'),
            func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
        ).join(
            Ano_escolar, Ano_escolar.id == Turmas.Ano_escolar_id
        ).join(
            Usuarios, and_(
                Usuarios.turma_id == Turmas.id,
                Usuarios.tipo_usuario_id == 4,
                Usuarios.escola_id == escola_id
            )
        ).outerjoin(
            DesempenhoSimulado, and_(
                DesempenhoSimulado.aluno_id == Usuarios.id,
                *data_condition
            )
        ).group_by(
            Turmas.id,
            Usuarios.id,
            Usuarios.nome
        ).order_by(
            Usuarios.nome
        ).all()

        # Buscar médias por disciplina separadamente
        medias_disciplinas = db.session.query(
            Usuarios.id.label('aluno_id'),
            Disciplinas.id.label('disciplina_id'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
        ).join(
            DesempenhoSimulado, and_(
                DesempenhoSimulado.aluno_id == Usuarios.id,
                *data_condition
            )
        ).join(
            SimuladosGerados, SimuladosGerados.id == DesempenhoSimulado.simulado_id
        ).join(
            Disciplinas, Disciplinas.id == SimuladosGerados.disciplina_id
        ).filter(
            Usuarios.escola_id == escola_id
        ).group_by(
            Usuarios.id,
            Disciplinas.id
        ).all()

        # Criar dicionário com médias por disciplina
        medias_por_aluno = {}
        for media in medias_disciplinas:
            if media.aluno_id not in medias_por_aluno:
                medias_por_aluno[media.aluno_id] = {
                    'media_matematica': 0.0,
                    'media_portugues': 0.0,
                    'media_ciencias': 0.0,
                    'media_historia': 0.0,
                    'media_geografia': 0.0
                }
            
            if media.disciplina_id == 1:
                medias_por_aluno[media.aluno_id]['media_portugues'] = media.media
            elif media.disciplina_id == 2:
                medias_por_aluno[media.aluno_id]['media_matematica'] = media.media
            elif media.disciplina_id == 3:
                medias_por_aluno[media.aluno_id]['media_ciencias'] = media.media
            elif media.disciplina_id == 4:
                medias_por_aluno[media.aluno_id]['media_historia'] = media.media
            elif media.disciplina_id == 5:
                medias_por_aluno[media.aluno_id]['media_geografia'] = media.media

        # Adicionar médias por disciplina aos resultados dos alunos
        alunos_completos = []
        for aluno in alunos:
            medias = medias_por_aluno.get(aluno.aluno_id, {
                'media_matematica': 0.0,
                'media_portugues': 0.0,
                'media_ciencias': 0.0,
                'media_historia': 0.0,
                'media_geografia': 0.0
            })
            alunos_completos.append({
                'turma_id': aluno.turma_id,
                'aluno_id': aluno.aluno_id,
                'aluno_nome': aluno.aluno_nome,
                'total_simulados': aluno.total_simulados,
                'media': aluno.media,
                **medias
            })
        
        return render_template('secretaria_educacao/relatorio_escola.html',
                                 ano=ano,
                                 mes=mes,
                                 escolas=escolas,
                                 escola_id=escola_id,
                                 media_geral=round(escola.media_geral, 1),
                                 total_alunos=escola.total_alunos,
                                 alunos_ativos=escola.alunos_ativos,
                                 total_simulados=escola.total_simulados,
                                 Ano_escolar=anos_escolares,  # Mantive o mesmo nome da variável para manter compatibilidade
                                 disciplinas=disciplinas,
                                 turmas=turmas,
                                 alunos=alunos_completos)
    
    return render_template('secretaria_educacao/relatorio_escola.html',
                         ano=ano,
                         mes=mes,
                         escolas=escolas,
                         escola_id=None)
                         
@secretaria_educacao_bp.route('/relatorio_escola/export_pdf')
@login_required
def export_pdf_escola():
    """Exportar relatório da escola em PDF."""
    if current_user.tipo_usuario_id not in [3, 5]:  # Permitir acesso para professores (3) e secretaria (5)
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    # Obter escola_id e mês da query string
    escola_id = request.args.get('escola_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    if not escola_id:
        flash("Escola não especificada.", "danger")
        return redirect(url_for("secretaria_educacao.relatorio_escola"))
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Buscar dados da escola
    escola = db.session.query(
        Escolas.nome_da_escola.label('nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.escola_id == Escolas.id,
            Usuarios.tipo_usuario_id == 4
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).filter(
        Escolas.id == escola_id
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).first()
    
    # Buscar dados por série
    anos_escolares_query = db.session.query(
        Ano_escolar.id,
        Ano_escolar.nome.label('Ano_escolar_nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.Ano_escolar_id == Ano_escolar.id,
            Usuarios.tipo_usuario_id == 4,
            Usuarios.escola_id == escola_id
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).group_by(
        Ano_escolar.id, Ano_escolar.nome
    ).order_by(
        Ano_escolar.id
    ).all()
    
    anos_escolares = [dict(zip(['id', 'Ano_escolar_nome', 'total_alunos', 'alunos_ativos', 'media'], ano)) 
                   for ano in anos_escolares_query]
    
    # Buscar dados por disciplina
    disciplinas = db.session.query(
        Disciplinas.nome.label('disciplina'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_questoes'),
        func.round(func.avg(DesempenhoSimulado.desempenho), 1).label('media_acertos')
    ).outerjoin(
        SimuladosGerados, SimuladosGerados.disciplina_id == Disciplinas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.simulado_id == SimuladosGerados.id,
            *data_condition
        )
    ).join(
        Usuarios, and_(
            Usuarios.id == DesempenhoSimulado.aluno_id,
            Usuarios.escola_id == escola_id
        )
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        db.desc('media_acertos')
    ).all()
    
    # Renderizar o template HTML
    html = render_template('secretaria_educacao/relatorio_escola_pdf.html',
                         ano=ano,
                         mes=MESES_NOMES.get(mes) if mes else None,
                         escola=escola,
                         media_geral=round(escola.media_geral, 1),
                         total_alunos=escola.total_alunos,
                         alunos_ativos=escola.alunos_ativos,
                         total_simulados=escola.total_simulados,
                         Ano_escolar=anos_escolares,
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
    
    # Obter escola_id e mês da query string
    escola_id = request.args.get('escola_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    if not escola_id:
        flash("Escola não especificada.", "danger")
        return redirect(url_for("secretaria_educacao.relatorio_escola"))
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Aba Visão Geral
    escola = db.session.query(
        Escolas.nome_da_escola.label('nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.escola_id == Escolas.id,
            Usuarios.tipo_usuario_id == 4
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).filter(
        Escolas.id == escola_id
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).first()
    
    df_geral = pd.DataFrame([{
        'Indicador': 'Média Geral',
        'Valor': f"{round(escola.media_geral, 1)}%"
    }, {
        'Indicador': 'Total de Alunos',
        'Valor': str(escola.total_alunos)
    }, {
        'Indicador': 'Alunos Ativos',
        'Valor': str(escola.alunos_ativos)
    }, {
        'Indicador': 'Simulados Realizados',
        'Valor': str(escola.total_simulados)
    }])
    df_geral.to_excel(writer, sheet_name='Visão Geral', index=False)
    
    # Aba Desempenho por Ano Escolar
    anos_escolares_query = db.session.query(
        Ano_escolar.nome.label('Ano_escolar_nome'),
        func.count(func.distinct(Usuarios.id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('alunos_ativos'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, and_(
            Usuarios.Ano_escolar_id == Ano_escolar.id,
            Usuarios.tipo_usuario_id == 4,
            Usuarios.escola_id == escola_id
        )
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).group_by(
        Ano_escolar.id, Ano_escolar.nome
    ).order_by(
        Ano_escolar.id
    ).all()
    
    df_anos_escolares = pd.DataFrame([{
        'Ano_escolar': s.Ano_escolar_nome,
        'total_alunos': s.total_alunos,
        'alunos_ativos': s.alunos_ativos,
        'media': s.media
    } for s in anos_escolares_query])
    
    if not df_anos_escolares.empty:
        df_anos_escolares = df_anos_escolares.rename(columns={
            'Ano_escolar': 'Ano Escolar',
            'total_alunos': 'Total de Alunos',
            'alunos_ativos': 'Alunos Ativos',
            'media': 'Média (%)'
        })
        df_anos_escolares['Média (%)'] = df_anos_escolares['Média (%)'].round(1)
    df_anos_escolares.to_excel(writer, sheet_name='Desempenho por Ano Escolar', index=False)
    
    # Aba Desempenho por Disciplina
    disciplinas = db.session.query(
        Disciplinas.nome.label('disciplina'),
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_questoes'),
        func.round(func.avg(DesempenhoSimulado.desempenho), 1).label('media_acertos')
    ).outerjoin(
        SimuladosGerados, SimuladosGerados.disciplina_id == Disciplinas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.simulado_id == SimuladosGerados.id,
            *data_condition
        )
    ).join(
        Usuarios, and_(
            Usuarios.id == DesempenhoSimulado.aluno_id,
            Usuarios.escola_id == escola_id
        )
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        db.desc('media_acertos')
    ).all()
    
    df_disciplinas = pd.DataFrame([{
        'disciplina': d.disciplina,
        'total_alunos': d.total_alunos,
        'total_questoes': d.total_questoes,
        'media_acertos': d.media_acertos
    } for d in disciplinas])
    
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
    
    codigo_ibge = current_user.codigo_ibge
    
    # Buscar todas as disciplinas
    disciplinas = db.session.query(
        Disciplinas.id,
        Disciplinas.nome
    ).order_by(
        Disciplinas.nome
    ).all()
    
    # Obter disciplina_id e mês da query string
    disciplina_id = request.args.get('disciplina_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Se uma disciplina foi selecionada, buscar seus dados
    if disciplina_id:
        # Construir a condição de data
        data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
        if mes:
            data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
        
        # Subquery para simulados da disciplina
        simulados_disciplina = db.session.query(
            DesempenhoSimulado.aluno_id,
            DesempenhoSimulado.simulado_id,
            DesempenhoSimulado.desempenho
        ).filter(
            or_(
                and_(
                    DesempenhoSimulado.tipo_usuario_id == 5,
                    exists().where(
                        and_(
                            SimuladosGerados.id == DesempenhoSimulado.simulado_id,
                            SimuladosGerados.disciplina_id == disciplina_id
                        )
                    )
                ),
                and_(
                    DesempenhoSimulado.tipo_usuario_id == 3,
                    exists().where(
                        and_(
                            SimuladosGeradosProfessor.id == DesempenhoSimulado.simulado_id,
                            SimuladosGeradosProfessor.disciplina_id == disciplina_id
                        )
                    )
                )
            ),
            DesempenhoSimulado.codigo_ibge == codigo_ibge,
            *data_condition
        ).subquery()
        
        # Buscar dados gerais da disciplina
        disciplina = db.session.query(
            Disciplinas.nome,
            func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
            func.count(func.distinct(simulados_disciplina.c.simulado_id)).label('total_simulados'),
            func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
            func.coalesce(func.avg(simulados_disciplina.c.desempenho), 0.0).label('media_geral')
        ).outerjoin(
            simulados_disciplina, literal(True)
        ).filter(
            Disciplinas.id == disciplina_id
        ).group_by(
            Disciplinas.id, Disciplinas.nome
        ).first()
        
        # Buscar dados por série
        anos_escolares_query = db.session.query(
            Ano_escolar.id,
            Ano_escolar.nome.label('Ano_escolar_nome'),
            func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
            func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
            func.coalesce(func.avg(simulados_disciplina.c.desempenho), 0.0).label('media')
        ).outerjoin(
            Usuarios, Usuarios.Ano_escolar_id == Ano_escolar.id
        ).outerjoin(
            simulados_disciplina, simulados_disciplina.c.aluno_id == Usuarios.id
        ).group_by(
            Ano_escolar.id, Ano_escolar.nome
        ).order_by(
            Ano_escolar.id
        ).all()
        
        anos_escolares = [dict(zip(['id', 'Ano_escolar_nome', 'total_alunos', 'total_questoes', 'media'], ano)) 
                       for ano in anos_escolares_query]
        
        # Buscar dados por escola
        escolas = db.session.query(
            Escolas.nome_da_escola.label('nome'),
            func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
            func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
            func.round(func.avg(simulados_disciplina.c.desempenho), 1).label('media_acertos')
        ).outerjoin(
            Usuarios, Usuarios.escola_id == Escolas.id
        ).outerjoin(
            simulados_disciplina, simulados_disciplina.c.aluno_id == Usuarios.id
        ).filter(
            Escolas.codigo_ibge == codigo_ibge
        ).group_by(
            Escolas.id, Escolas.nome_da_escola
        ).having(
            func.count(func.distinct(simulados_disciplina.c.aluno_id)) > 0
        ).order_by(
            db.desc('media_acertos')
        ).all()
        
        return render_template('secretaria_educacao/relatorio_disciplina.html',
                             ano=ano,
                             mes=mes,
                             disciplinas=disciplinas,
                             disciplina_id=disciplina_id,
                             media_geral=round(disciplina.media_geral, 1),
                             total_alunos=disciplina.total_alunos,
                             total_questoes=disciplina.total_questoes,
                             total_simulados=disciplina.total_simulados,
                             Ano_escolar=anos_escolares,
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
    
    # Obter disciplina_id e mês da query string
    disciplina_id = request.args.get('disciplina_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    if not disciplina_id:
        flash("Disciplina não especificada.", "danger")
        return redirect(url_for("secretaria_educacao.relatorio_disciplina"))
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Subquery para simulados da disciplina
    simulados_disciplina = db.session.query(
        DesempenhoSimulado.aluno_id,
        DesempenhoSimulado.simulado_id,
        DesempenhoSimulado.desempenho
    ).filter(
        or_(
            and_(
                DesempenhoSimulado.tipo_usuario_id == 5,
                exists().where(
                    and_(
                        SimuladosGerados.id == DesempenhoSimulado.simulado_id,
                        SimuladosGerados.disciplina_id == disciplina_id
                    )
                )
            ),
            and_(
                DesempenhoSimulado.tipo_usuario_id == 3,
                exists().where(
                    and_(
                        SimuladosGeradosProfessor.id == DesempenhoSimulado.simulado_id,
                        SimuladosGeradosProfessor.disciplina_id == disciplina_id
                    )
                )
            )
        ),
        DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
        *data_condition
    ).subquery()
    
    # Buscar dados da disciplina
    disciplina = db.session.query(
        Disciplinas.nome,
        func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
        func.count(func.distinct(simulados_disciplina.c.simulado_id)).label('total_simulados'),
        func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_disciplina.c.desempenho), 0.0).label('media_geral')
    ).outerjoin(
        simulados_disciplina, literal(True)
    ).filter(
        Disciplinas.id == disciplina_id
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).first()
    
    # Buscar dados por série
    anos_escolares_query = db.session.query(
        Ano_escolar.id,
        Ano_escolar.nome.label('Ano_escolar_nome'),
        func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
        func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_disciplina.c.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, Usuarios.Ano_escolar_id == Ano_escolar.id
    ).outerjoin(
        simulados_disciplina, simulados_disciplina.c.aluno_id == Usuarios.id
    ).group_by(
        Ano_escolar.id, Ano_escolar.nome
    ).order_by(
        Ano_escolar.id
    ).all()
    
    anos_escolares = [dict(zip(['id', 'Ano_escolar_nome', 'total_alunos', 'total_questoes', 'media'], ano)) 
                   for ano in anos_escolares_query]
    
    # Buscar dados por escola
    escolas = db.session.query(
        Escolas.nome_da_escola.label('nome'),
        func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
        func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
        func.round(func.avg(simulados_disciplina.c.desempenho), 1).label('media_acertos')
    ).outerjoin(
        Usuarios, Usuarios.escola_id == Escolas.id
    ).outerjoin(
        simulados_disciplina, simulados_disciplina.c.aluno_id == Usuarios.id
    ).filter(
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).having(
        func.count(func.distinct(simulados_disciplina.c.aluno_id)) > 0
    ).order_by(
        db.desc('media_acertos')
    ).all()
    
    # Renderizar o template HTML
    html = render_template('secretaria_educacao/relatorio_disciplina_pdf.html',
                         ano=ano,
                         mes=MESES_NOMES.get(mes) if mes else None,
                         disciplina=disciplina,
                         media_geral=round(disciplina.media_geral, 1),
                         total_alunos=disciplina.total_alunos,
                         total_questoes=disciplina.total_questoes,
                         total_simulados=disciplina.total_simulados,
                         Ano_escolar=anos_escolares,
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
    
    # Obter disciplina_id e mês da query string
    disciplina_id = request.args.get('disciplina_id', type=int)
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    if not disciplina_id:
        flash("Disciplina não especificada.", "danger")
        return redirect(url_for("secretaria_educacao.relatorio_disciplina"))
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Subquery para simulados da disciplina
    simulados_disciplina = db.session.query(
        DesempenhoSimulado.aluno_id,
        DesempenhoSimulado.simulado_id,
        DesempenhoSimulado.desempenho
    ).filter(
        or_(
            and_(
                DesempenhoSimulado.tipo_usuario_id == 5,
                exists().where(
                    and_(
                        SimuladosGerados.id == DesempenhoSimulado.simulado_id,
                        SimuladosGerados.disciplina_id == disciplina_id
                    )
                )
            ),
            and_(
                DesempenhoSimulado.tipo_usuario_id == 3,
                exists().where(
                    and_(
                        SimuladosGeradosProfessor.id == DesempenhoSimulado.simulado_id,
                        SimuladosGeradosProfessor.disciplina_id == disciplina_id
                    )
                )
            )
        ),
        DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
        *data_condition
    ).subquery()
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Buscar dados da disciplina para a aba Visão Geral
    disciplina = db.session.query(
        Disciplinas.nome,
        func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
        func.count(func.distinct(simulados_disciplina.c.simulado_id)).label('total_simulados'),
        func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_disciplina.c.desempenho), 0.0).label('media_geral')
    ).outerjoin(
        simulados_disciplina, literal(True)
    ).filter(
        Disciplinas.id == disciplina_id
    ).group_by(
        Disciplinas.id, Disciplinas.nome
    ).first()
    
    df_geral = pd.DataFrame([{
        'Indicador': 'Média Geral',
        'Valor': f"{round(disciplina.media_geral, 1)}%"
    }, {
        'Indicador': 'Total de Alunos',
        'Valor': str(disciplina.total_alunos)
    }, {
        'Indicador': 'Total de Questões',
        'Valor': str(disciplina.total_questoes)
    }, {
        'Indicador': 'Simulados com a Disciplina',
        'Valor': str(disciplina.total_simulados)
    }])
    df_geral.to_excel(writer, sheet_name='Visão Geral', index=False)
    
    # Buscar dados por série
    anos_escolares_query = db.session.query(
        Ano_escolar.nome.label('Ano_escolar_nome'),
        func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
        func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_disciplina.c.desempenho), 0.0).label('media')
    ).outerjoin(
        Usuarios, Usuarios.Ano_escolar_id == Ano_escolar.id
    ).outerjoin(
        simulados_disciplina, simulados_disciplina.c.aluno_id == Usuarios.id
    ).group_by(
        Ano_escolar.id, Ano_escolar.nome
    ).order_by(
        Ano_escolar.id
    ).all()
    
    df_anos_escolares = pd.DataFrame([{
        'Ano Escolar': s.Ano_escolar_nome,
        'Total de Alunos': s.total_alunos,
        'Total de Questões': s.total_questoes,
        'Média (%)': round(s.media, 1)
    } for s in anos_escolares_query])
    df_anos_escolares.to_excel(writer, sheet_name='Desempenho por Ano Escolar', index=False)
    
    # Buscar dados por escola
    escolas = db.session.query(
        Escolas.nome_da_escola.label('escola'),
        func.count(func.distinct(simulados_disciplina.c.aluno_id)).label('total_alunos'),
        func.count(simulados_disciplina.c.simulado_id).label('total_questoes'),
        func.round(func.avg(simulados_disciplina.c.desempenho), 1).label('media_acertos')
    ).outerjoin(
        Usuarios, Usuarios.escola_id == Escolas.id
    ).outerjoin(
        simulados_disciplina, simulados_disciplina.c.aluno_id == Usuarios.id
    ).filter(
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola
    ).having(
        func.count(func.distinct(simulados_disciplina.c.aluno_id)) > 0
    ).order_by(
        db.desc('media_acertos')
    ).all()
    
    df_escolas = pd.DataFrame([{
        'Escola': e.escola,
        'Total de Alunos': e.total_alunos,
        'Total de Questões': e.total_questoes,
        'Média de Acertos (%)': e.media_acertos
    } for e in escolas])
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
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Subquery para simulados dos alunos
    simulados_alunos = db.session.query(
        DesempenhoSimulado.aluno_id,
        DesempenhoSimulado.simulado_id,
        DesempenhoSimulado.desempenho,
        Usuarios.escola_id,
        Escolas.tipo_ensino_id
    ).join(
        Usuarios, Usuarios.id == DesempenhoSimulado.aluno_id
    ).join(
        Escolas, Escolas.id == Usuarios.escola_id
    ).filter(
        DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
        *data_condition
    ).subquery()
    
    # Obter dados gerais
    dados_gerais = db.session.query(
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(func.distinct(simulados_alunos.c.simulado_id)).label('total_simulados'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media_geral')
    ).first()
    
    # Obter dados por tipo de ensino
    tipos_ensino = db.session.query(
        TiposEnsino.nome,
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media')
    ).outerjoin(
        simulados_alunos, simulados_alunos.c.tipo_ensino_id == TiposEnsino.id
    ).group_by(
        TiposEnsino.id, TiposEnsino.nome
    ).having(
        func.count(func.distinct(simulados_alunos.c.aluno_id)) > 0
    ).order_by(
        db.desc('media')
    ).all()
    
    # Obter dados por escola
    escolas = db.session.query(
        Escolas.nome_da_escola.label('nome'),
        TiposEnsino.nome.label('tipo_ensino'),
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media')
    ).join(
        TiposEnsino, TiposEnsino.id == Escolas.tipo_ensino_id
    ).outerjoin(
        simulados_alunos, simulados_alunos.c.escola_id == Escolas.id
    ).filter(
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola, TiposEnsino.nome
    ).having(
        func.count(func.distinct(simulados_alunos.c.aluno_id)) > 0
    ).order_by(
        db.desc('media')
    ).all()
    
    return render_template(
        'secretaria_educacao/relatorio_tipo_ensino.html',
        ano=ano,
        mes=mes,
        media_geral=dados_gerais.media_geral,
        total_alunos=dados_gerais.total_alunos,
        total_questoes=dados_gerais.total_questoes,
        total_simulados=dados_gerais.total_simulados,
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
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Subquery para simulados dos alunos
    simulados_alunos = db.session.query(
        DesempenhoSimulado.aluno_id,
        DesempenhoSimulado.simulado_id,
        DesempenhoSimulado.desempenho,
        Usuarios.escola_id,
        Escolas.tipo_ensino_id
    ).join(
        Usuarios, Usuarios.id == DesempenhoSimulado.aluno_id
    ).join(
        Escolas, Escolas.id == Usuarios.escola_id
    ).filter(
        DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
        *data_condition
    ).subquery()
    
    # Obter dados gerais
    dados_gerais = db.session.query(
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(func.distinct(simulados_alunos.c.simulado_id)).label('total_simulados'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media_geral')
    ).first()
    
    # Obter dados por tipo de ensino
    tipos_ensino = db.session.query(
        TiposEnsino.nome,
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media')
    ).outerjoin(
        simulados_alunos, simulados_alunos.c.tipo_ensino_id == TiposEnsino.id
    ).group_by(
        TiposEnsino.id, TiposEnsino.nome
    ).having(
        func.count(func.distinct(simulados_alunos.c.aluno_id)) > 0
    ).order_by(
        db.desc('media')
    ).all()
    
    # Obter dados por escola
    escolas = db.session.query(
        Escolas.nome_da_escola.label('nome'),
        TiposEnsino.nome.label('tipo_ensino'),
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media')
    ).join(
        TiposEnsino, TiposEnsino.id == Escolas.tipo_ensino_id
    ).outerjoin(
        simulados_alunos, simulados_alunos.c.escola_id == Escolas.id
    ).filter(
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola, TiposEnsino.nome
    ).having(
        func.count(func.distinct(simulados_alunos.c.aluno_id)) > 0
    ).order_by(
        db.desc('media')
    ).all()
    
    # Renderizar o template
    html = render_template(
        'secretaria_educacao/relatorio_tipo_ensino_pdf.html',
        ano=ano,
        mes=MESES_NOMES.get(mes) if mes else None,
        media_geral=dados_gerais.media_geral,
        total_alunos=dados_gerais.total_alunos,
        total_questoes=dados_gerais.total_questoes,
        total_simulados=dados_gerais.total_simulados,
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
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Subquery para simulados dos alunos
    simulados_alunos = db.session.query(
        DesempenhoSimulado.aluno_id,
        DesempenhoSimulado.simulado_id,
        DesempenhoSimulado.desempenho,
        Usuarios.escola_id,
        Escolas.tipo_ensino_id
    ).join(
        Usuarios, Usuarios.id == DesempenhoSimulado.aluno_id
    ).join(
        Escolas, Escolas.id == Usuarios.escola_id
    ).filter(
        DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
        *data_condition
    ).subquery()
    
    # Obter dados gerais
    dados_gerais = db.session.query(
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(func.distinct(simulados_alunos.c.simulado_id)).label('total_simulados'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media_geral')
    ).first()
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Aba Visão Geral
    df_geral = pd.DataFrame([{
        'Indicador': 'Média Geral',
        'Valor': f"{round(dados_gerais.media_geral, 1)}%"
    }, {
        'Indicador': 'Total de Alunos',
        'Valor': str(dados_gerais.total_alunos)
    }, {
        'Indicador': 'Total de Questões',
        'Valor': str(dados_gerais.total_questoes)
    }, {
        'Indicador': 'Total de Simulados',
        'Valor': str(dados_gerais.total_simulados)
    }])
    df_geral.to_excel(writer, sheet_name='Visão Geral', index=False)
    
    # Obter dados por tipo de ensino
    tipos_ensino = db.session.query(
        TiposEnsino.nome,
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media')
    ).outerjoin(
        simulados_alunos, simulados_alunos.c.tipo_ensino_id == TiposEnsino.id
    ).group_by(
        TiposEnsino.id, TiposEnsino.nome
    ).having(
        func.count(func.distinct(simulados_alunos.c.aluno_id)) > 0
    ).order_by(
        db.desc('media')
    ).all()
    
    df_tipos = pd.DataFrame([{
        'Tipo de Ensino': t.nome,
        'Total de Alunos': t.total_alunos,
        'Total de Questões': t.total_questoes,
        'Média (%)': round(t.media, 1)
    } for t in tipos_ensino])
    df_tipos.to_excel(writer, sheet_name='Desempenho por Tipo', index=False)
    
    # Obter dados por escola
    escolas = db.session.query(
        Escolas.nome_da_escola.label('nome'),
        TiposEnsino.nome.label('tipo_ensino'),
        func.count(func.distinct(simulados_alunos.c.aluno_id)).label('total_alunos'),
        func.count(simulados_alunos.c.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(simulados_alunos.c.desempenho), 0.0).label('media')
    ).join(
        TiposEnsino, TiposEnsino.id == Escolas.tipo_ensino_id
    ).outerjoin(
        simulados_alunos, simulados_alunos.c.escola_id == Escolas.id
    ).filter(
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola, TiposEnsino.nome
    ).having(
        func.count(func.distinct(simulados_alunos.c.aluno_id)) > 0
    ).order_by(
        db.desc('media')
    ).all()
    
    df_escolas = pd.DataFrame([{
        'Escola': e.nome,
        'Tipo de Ensino': e.tipo_ensino,
        'Total de Alunos': e.total_alunos,
        'Total de Questões': e.total_questoes,
        'Média (%)': round(e.media, 1)
    } for e in escolas])
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
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    # Pegar parâmetros da URL
    escola_id = request.args.get('escola_id', type=int)
    turma_id = request.args.get('turma_id', type=int)
    ano = request.args.get('ano', default=datetime.now().year, type=int)
    mes = request.args.get('mes', type=int)

    # Construir condição de data
    data_condition = []
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)

    # Buscar todas as escolas
    escolas = db.session.query(
        Escolas.id, 
        Escolas.nome_da_escola
    ).filter(
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).order_by(
        Escolas.nome_da_escola
    ).all()

    if escola_id:
        # Buscar turmas da escola selecionada
        turmas_query = db.session.query(
            Turmas.id,
            Turmas.turma,
            Ano_escolar.nome.label('Ano_escolar'),
            func.count(func.distinct(Usuarios.id)).label('total_alunos'),
            func.count(func.distinct(
                case((DesempenhoSimulado.id != None, Usuarios.id))
            )).label('alunos_ativos'),
            func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
        ).filter(
            Turmas.escola_id == escola_id
        ).join(
            Ano_escolar, Ano_escolar.id == Turmas.Ano_escolar_id
        ).outerjoin(
            Usuarios, and_(
                Usuarios.turma_id == Turmas.id,
                Usuarios.tipo_usuario_id == 4
            )
        ).outerjoin(
            DesempenhoSimulado, DesempenhoSimulado.aluno_id == Usuarios.id
        ).group_by(
            Turmas.id, Turmas.turma, Ano_escolar.nome
        ).order_by(Turmas.turma)

        turmas = turmas_query.all()

        # Buscar métricas gerais da escola
        escola_query = db.session.query(
            func.count(func.distinct(Usuarios.id)).label('total_alunos'),
            func.count(func.distinct(
                case((DesempenhoSimulado.id != None, Usuarios.id))
            )).label('alunos_ativos'),
            func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral')
        ).outerjoin(
            DesempenhoSimulado, DesempenhoSimulado.aluno_id == Usuarios.id
        ).filter(
            Usuarios.escola_id == escola_id,
            Usuarios.tipo_usuario_id == 4
        )

        escola = escola_query.first()

        # Subquery para médias por disciplina
        simulados_disciplinas = db.session.query(
            DesempenhoSimulado.aluno_id,
            DesempenhoSimulado.simulado_id,
            DesempenhoSimulado.desempenho,
            case(
                (SimuladosGerados.disciplina_id != None, SimuladosGerados.disciplina_id),
                (SimuladosGeradosProfessor.disciplina_id != None, SimuladosGeradosProfessor.disciplina_id)
            ).label('disciplina_id'),
            Usuarios.turma_id
        ).join(
            Usuarios, Usuarios.id == DesempenhoSimulado.aluno_id
        ).outerjoin(
            SimuladosGerados, and_(
                SimuladosGerados.id == DesempenhoSimulado.simulado_id,
                DesempenhoSimulado.tipo_usuario_id == 5
            )
        ).outerjoin(
            SimuladosGeradosProfessor, and_(
                SimuladosGeradosProfessor.id == DesempenhoSimulado.simulado_id,
                DesempenhoSimulado.tipo_usuario_id == 3
            )
        ).filter(
            Usuarios.escola_id == escola_id,
            *data_condition
        ).subquery()

        # Query para alunos e suas médias
        alunos_query = db.session.query(
            Turmas.id.label('turma_id'),
            Usuarios.id.label('aluno_id'),
            Usuarios.nome.label('aluno_nome'),
            func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media'),
            func.max(case(
                (simulados_disciplinas.c.disciplina_id == 2, simulados_disciplinas.c.desempenho)
            )).label('media_matematica'),
            func.max(case(
                (simulados_disciplinas.c.disciplina_id == 1, simulados_disciplinas.c.desempenho)
            )).label('media_portugues'),
            func.max(case(
                (simulados_disciplinas.c.disciplina_id == 3, simulados_disciplinas.c.desempenho)
            )).label('media_ciencias'),
            func.max(case(
                (simulados_disciplinas.c.disciplina_id == 4, simulados_disciplinas.c.desempenho)
            )).label('media_historia'),
            func.max(case(
                (simulados_disciplinas.c.disciplina_id == 5, simulados_disciplinas.c.desempenho)
            )).label('media_geografia')
        ).join(
            Usuarios, and_(
                Usuarios.turma_id == Turmas.id,
                Usuarios.tipo_usuario_id == 4,
                Usuarios.escola_id == escola_id
            )
        ).outerjoin(
            DesempenhoSimulado, DesempenhoSimulado.aluno_id == Usuarios.id
        ).outerjoin(
            simulados_disciplinas, and_(
                simulados_disciplinas.c.aluno_id == Usuarios.id,
                simulados_disciplinas.c.turma_id == Turmas.id
            )
        )

        if turma_id:
            alunos_query = alunos_query.filter(Turmas.id == turma_id)

        alunos = alunos_query.group_by(
            Turmas.id, Turmas.turma, Usuarios.id, Usuarios.nome
        ).order_by(
            Turmas.turma, Usuarios.nome
        ).all()

        return render_template('secretaria_educacao/relatorio_turma.html',
                             ano=ano,
                             mes=mes,
                             escolas=escolas,
                             escola_id=escola_id,
                             turma_id=turma_id,
                             media_geral=round(escola.media_geral, 1),
                             total_alunos=escola.total_alunos,
                             alunos_ativos=escola.alunos_ativos,
                             total_simulados=escola.total_simulados,
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
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Obter dados gerais
    dados_gerais = db.session.query(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
        func.count(DesempenhoSimulado.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral')
    ).join(
        Usuarios, Usuarios.id == DesempenhoSimulado.aluno_id
    ).filter(
        DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
        *data_condition
    ).first()
    
    # Obter dados por turma
    turmas = db.session.query(
        Turmas.turma,
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(DesempenhoSimulado.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).join(
        Usuarios, Usuarios.turma_id == Turmas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
            *data_condition
        )
    ).filter(
        Usuarios.tipo_usuario_id == 1,
        Usuarios.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Turmas.id, Turmas.turma
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        Turmas.turma
    ).all()
    
    # Obter dados por escola e turma
    escolas_turmas = db.session.query(
        Escolas.nome_da_escola.label('escola'),
        Turmas.turma,
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(DesempenhoSimulado.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).join(
        Usuarios, Usuarios.escola_id == Escolas.id
    ).join(
        Turmas, Turmas.id == Usuarios.turma_id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
            *data_condition
        )
    ).filter(
        Usuarios.tipo_usuario_id == 1,
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola, Turmas.id, Turmas.turma
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        Escolas.nome_da_escola, Turmas.turma
    ).all()
    
    # Renderizar o template
    html = render_template(
        'secretaria_educacao/relatorio_turma_pdf.html',
        ano=ano,
        mes=MESES_NOMES.get(mes) if mes else None,
        media_geral=dados_gerais.media_geral,
        total_alunos=dados_gerais.total_alunos,
        total_questoes=dados_gerais.total_questoes,
        total_simulados=dados_gerais.total_simulados,
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
    
    # Obter mês da query string
    mes = request.args.get('mes', type=int)
    ano = 2025  # Fixado em 2025
    
    # Construir a condição de data
    data_condition = [extract('year', DesempenhoSimulado.data_resposta) == ano]
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    
    # Obter dados gerais
    dados_gerais = db.session.query(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(func.distinct(DesempenhoSimulado.simulado_id)).label('total_simulados'),
        func.count(DesempenhoSimulado.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral')
    ).join(
        Usuarios, Usuarios.id == DesempenhoSimulado.aluno_id
    ).filter(
        DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
        *data_condition
    ).first()
    
    # Criar um Excel writer
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Aba Visão Geral
    df_geral = pd.DataFrame([{
        'Indicador': 'Média Geral',
        'Valor': f"{round(dados_gerais.media_geral, 1)}%"
    }, {
        'Indicador': 'Total de Alunos',
        'Valor': str(dados_gerais.total_alunos)
    }, {
        'Indicador': 'Total de Questões',
        'Valor': str(dados_gerais.total_questoes)
    }, {
        'Indicador': 'Total de Simulados',
        'Valor': str(dados_gerais.total_simulados)
    }])
    df_geral.to_excel(writer, sheet_name='Visão Geral', index=False)
    
    # Obter dados por turma
    turmas = db.session.query(
        Turmas.turma,
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(DesempenhoSimulado.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).join(
        Usuarios, Usuarios.turma_id == Turmas.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
            *data_condition
        )
    ).filter(
        Usuarios.tipo_usuario_id == 1,
        Usuarios.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Turmas.id, Turmas.turma
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        Turmas.turma
    ).all()
    
    df_turmas = pd.DataFrame([{
        'Turma': t.turma,
        'Total de Alunos': t.total_alunos,
        'Total de Questões': t.total_questoes,
        'Média (%)': round(t.media, 1)
    } for t in turmas])
    
    if not df_turmas.empty:
        df_turmas.to_excel(writer, sheet_name='Desempenho por Turma', index=False)
    
    # Obter dados por escola e turma
    escolas_turmas = db.session.query(
        Escolas.nome_da_escola.label('escola'),
        Turmas.turma,
        func.count(func.distinct(DesempenhoSimulado.aluno_id)).label('total_alunos'),
        func.count(DesempenhoSimulado.simulado_id).label('total_questoes'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
    ).join(
        Usuarios, Usuarios.escola_id == Escolas.id
    ).join(
        Turmas, Turmas.id == Usuarios.turma_id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            DesempenhoSimulado.codigo_ibge == current_user.codigo_ibge,
            *data_condition
        )
    ).filter(
        Usuarios.tipo_usuario_id == 1,
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).group_by(
        Escolas.id, Escolas.nome_da_escola, Turmas.id, Turmas.turma
    ).having(
        func.count(func.distinct(DesempenhoSimulado.aluno_id)) > 0
    ).order_by(
        Escolas.nome_da_escola, Turmas.turma
    ).all()
    
    df_escolas = pd.DataFrame([{
        'Escola': e.escola,
        'Turma': e.turma,
        'Total de Alunos': e.total_alunos,
        'Total de Questões': e.total_questoes,
        'Média (%)': round(e.media, 1)
    } for e in escolas_turmas])
    
    if not df_escolas.empty:
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
    """Cancelar o envio de um simulado."""
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'error': 'Acesso não autorizado'}), 403
    
    try:
        # Verificar se o simulado existe
        simulado = db.session.query(SimuladosGerados).get(simulado_id)
        
        if not simulado:
            return jsonify({'success': False, 'error': 'Simulado não encontrado'}), 404
        
        # Remover registros de aluno_simulado
        db.session.query(AlunoSimulado).filter(
            AlunoSimulado.simulado_id == simulado_id
        ).delete()
        
        # Atualizar status para gerado
        simulado.status = 'gerado'
        simulado.data_envio = None
        
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao cancelar envio do simulado: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@secretaria_educacao_bp.route('/relatorio_individual')
@login_required
def relatorio_individual():
    """Página de relatório de desempenho individual."""
    if current_user.tipo_usuario_id not in [5, 6]:  # Verifica se é secretaria
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    # Obtém o ano atual
    ano = datetime.now().year
    
    # Obtém os parâmetros de filtro
    mes = request.args.get('mes', type=int)
    aluno_id = request.args.get('aluno_id', type=int)
    nome_filtro = request.args.get('nome', '')
    escola_id = request.args.get('escola_id', type=int)
    ano_escolar_id = request.args.get('ano_escolar_id', type=int)
    turma_id = request.args.get('turma_id', type=int)
    
    # Condição para filtrar por data
    data_condition = []
    if mes:
        data_condition.append(extract('month', DesempenhoSimulado.data_resposta) == mes)
    data_condition.append(extract('year', DesempenhoSimulado.data_resposta) == ano)
    
    # Query base para alunos
    alunos_query = db.session.query(
        Usuarios.id,
        Usuarios.nome.label('nome'),
        Escolas.nome_da_escola.label('escola'),
        Turmas.turma.label('turma'),
        Ano_escolar.nome.label('ano_escolar'),
        func.count(DesempenhoSimulado.id).label('total_simulados'),
        func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media_geral')
    ).join(
        Escolas, Usuarios.escola_id == Escolas.id
    ).join(
        Turmas, Usuarios.turma_id == Turmas.id
    ).join(
        Ano_escolar, Turmas.Ano_escolar_id == Ano_escolar.id
    ).outerjoin(
        DesempenhoSimulado, and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            *data_condition
        )
    ).filter(
        Usuarios.tipo_usuario_id == 4  # Tipo aluno
    )

    # Aplicar filtros
    if nome_filtro:
        alunos_query = alunos_query.filter(Usuarios.nome.ilike(f'%{nome_filtro}%'))
    if escola_id:
        alunos_query = alunos_query.filter(Usuarios.escola_id == escola_id)
    if ano_escolar_id:
        alunos_query = alunos_query.filter(Turmas.Ano_escolar_id == ano_escolar_id)
    if turma_id:
        alunos_query = alunos_query.filter(Usuarios.turma_id == turma_id)

    # Aplicar group by e order by
    alunos_query = alunos_query.group_by(
        Usuarios.id,
        Usuarios.nome,
        Escolas.nome_da_escola,
        Turmas.turma,
        Ano_escolar.nome
    ).order_by(
        Escolas.nome_da_escola,
        Ano_escolar.nome,
        Turmas.turma,
        Usuarios.nome
    )
    
    alunos = alunos_query.all()
    
    # Buscar dados para os filtros
    escolas = db.session.query(Escolas.id, Escolas.nome_da_escola).order_by(Escolas.nome_da_escola).all()
    anos_escolares = db.session.query(Ano_escolar.id, Ano_escolar.nome).order_by(Ano_escolar.nome).all()
    turmas = db.session.query(Turmas.id, Turmas.turma).order_by(Turmas.turma).all()
    
    # Se um aluno específico foi selecionado
    aluno_data = None
    if aluno_id:
        # Desempenho por disciplina
        disciplinas_query = db.session.query(
            Disciplinas.nome.label('disciplina'),
            func.count(DesempenhoSimulado.id).label('total_simulados'),
            func.sum(func.json_length(DesempenhoSimulado.respostas_corretas)).label('total_questoes'),
            func.coalesce(func.avg(DesempenhoSimulado.desempenho), 0.0).label('media')
        ).join(
            SimuladosGerados, SimuladosGerados.id == DesempenhoSimulado.simulado_id
        ).join(
            Disciplinas, Disciplinas.id == SimuladosGerados.disciplina_id
        ).filter(
            DesempenhoSimulado.aluno_id == aluno_id,
            *data_condition
        ).group_by(
            Disciplinas.nome
        ).order_by(
            Disciplinas.nome
        ).all()
        
        # Histórico de desempenho
        historico_query = db.session.query(
            DesempenhoSimulado.data_resposta,
            Disciplinas.nome.label('disciplina'),
            DesempenhoSimulado.desempenho.label('nota'),
            func.json_length(DesempenhoSimulado.respostas_corretas).label('total_questoes'),
            func.json_length(case((DesempenhoSimulado.respostas_aluno == DesempenhoSimulado.respostas_corretas, DesempenhoSimulado.respostas_aluno), else_=None)).label('questoes_corretas')
        ).join(
            SimuladosGerados, SimuladosGerados.id == DesempenhoSimulado.simulado_id
        ).join(
            Disciplinas, Disciplinas.id == SimuladosGerados.disciplina_id
        ).filter(
            DesempenhoSimulado.aluno_id == aluno_id,
            *data_condition
        ).order_by(
            DesempenhoSimulado.data_resposta.desc()
        ).all()

        # Converter os resultados em dicionários
        historico_list = []
        for item in historico_query:
            historico_list.append({
                'data_resposta': item.data_resposta,
                'disciplina': item.disciplina,
                'nota': float(item.nota) if item.nota else 0.0,
                'total_questoes': item.total_questoes,
                'questoes_corretas': item.questoes_corretas
            })
        
        # Dados do aluno
        aluno = db.session.query(
            Usuarios.nome,
            Escolas.nome_da_escola.label('escola'),
            Turmas.turma.label('turma'),
            Ano_escolar.nome.label('ano_escolar')
        ).join(
            Escolas, Usuarios.escola_id == Escolas.id
        ).join(
            Turmas, Usuarios.turma_id == Turmas.id
        ).join(
            Ano_escolar, Turmas.Ano_escolar_id == Ano_escolar.id
        ).filter(
            Usuarios.id == aluno_id
        ).first()
        
        aluno_data = {
            'info': {
                'nome': aluno.nome,
                'escola': aluno.escola,
                'turma': aluno.turma,
                'ano_escolar': aluno.ano_escolar
            },
            'disciplinas': disciplinas_query,
            'historico': historico_list
        }
    
    return render_template(
        'secretaria_educacao/relatorio_individual.html',
        alunos=alunos,
        aluno_data=aluno_data,
        mes=mes,
        ano=ano,
        escolas=escolas,
        anos_escolares=anos_escolares,
        turmas=turmas,
        nome_filtro=nome_filtro,
        escola_id=escola_id,
        ano_escolar_id=ano_escolar_id,
        turma_id=turma_id
    )


@secretaria_educacao_bp.route('/gerenciar_imagens')
@login_required
def gerenciar_imagens():
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    disciplinas = db.session.query(Disciplinas).order_by(Disciplinas.nome).all()
    imagens = ImagemQuestao.query.order_by(ImagemQuestao.data_upload.desc()).all()
    return render_template('secretaria_educacao/gerenciar_imagens.html', 
                         disciplinas=disciplinas,
                         imagens=imagens)

@secretaria_educacao_bp.route('/upload_imagem', methods=['POST'])
@login_required
def upload_imagem():
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        if 'imagem' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhuma imagem enviada'}), 400
            
        file = request.files['imagem']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nenhuma imagem selecionada'}), 400
            
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join('static', 'uploads', 'imagens_questoes', filename)
            
            # Cria o diretório se não existir
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Salva o arquivo
            file.save(filepath)
            
            # Cria o registro no banco
            imagem = ImagemQuestao(
                nome=request.form.get('nome', filename),
                url=filepath,
                disciplina_id=request.form.get('disciplina_id'),
                assunto=request.form.get('assunto'),
                descricao=request.form.get('descricao'),
                tipo=request.form.get('tipo')
            )
            
            db.session.add(imagem)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Imagem enviada com sucesso'})
            
    except Exception as e:
        print(f"Erro ao fazer upload: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@secretaria_educacao_bp.route('/filtrar_imagens')
@login_required
def filtrar_imagens():
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
        
    disciplina = request.args.get('disciplina')
    assunto = request.args.get('assunto')
    tipo = request.args.get('tipo')
    busca = request.args.get('busca')
    
    query = ImagemQuestao.query
    
    if disciplina:
        query = query.filter_by(disciplina_id=disciplina)
    if assunto:
        query = query.filter(ImagemQuestao.assunto.ilike(f'%{assunto}%'))
    if tipo:
        query = query.filter_by(tipo=tipo)
    if busca:
        query = query.filter(or_(
            ImagemQuestao.nome.ilike(f'%{busca}%'),
            ImagemQuestao.descricao.ilike(f'%{busca}%')
        ))
    
    imagens = query.order_by(ImagemQuestao.data_upload.desc()).all()
    
    return jsonify({
        'success': True,
        'imagens': [{
            'id': img.id,
            'url': img.url,
            'nome': img.nome,
            'descricao': img.descricao,
            'disciplina_nome': img.disciplina.nome if img.disciplina else None,
            'assunto': img.assunto,
            'tipo': img.tipo
        } for img in imagens]
    })

@secretaria_educacao_bp.route('/deletar_imagem/<int:id>', methods=['DELETE'])
@login_required
def deletar_imagem(id):
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
        
    try:
        imagem = ImagemQuestao.query.get_or_404(id)
        
        # Remove o arquivo físico
        caminho_arquivo = os.path.join('static', imagem.url)
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)
            
            # Remove o diretório se estiver vazio
            diretorio = os.path.dirname(caminho_arquivo)
            if not os.listdir(diretorio):
                os.rmdir(diretorio)
            
        # Remove do banco
        db.session.delete(imagem)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Erro ao deletar imagem: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@secretaria_educacao_bp.route('/adicionar_questao', methods=['POST'])
@login_required
def adicionar_questao():
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        # Recebe os dados do formulário
        questao = request.form.get('questao')
        disciplina_id = request.form.get('disciplina_id')
        assunto = request.form.get('assunto')
        alternativa_a = request.form.get('alternativa_a')
        alternativa_b = request.form.get('alternativa_b')
        alternativa_c = request.form.get('alternativa_c')
        alternativa_d = request.form.get('alternativa_d')
        alternativa_e = request.form.get('alternativa_e')
        questao_correta = request.form.get('questao_correta')
        Ano_escolar_id = request.form.get('Ano_escolar_id')
        mes_id = request.form.get('mes_id')
        codigo_ibge = current_user.codigo_ibge
        
        # Validação básica
        if not all([questao, disciplina_id, questao_correta]):
            return jsonify({'success': False, 'message': 'Todos os campos obrigatórios devem ser preenchidos'}), 400
            
        # Cria nova questão
        nova_questao = BancoQuestoes(
            questao=questao,
            disciplina_id=disciplina_id,
            assunto=assunto,
            alternativa_a=alternativa_a,
            alternativa_b=alternativa_b,
            alternativa_c=alternativa_c,
            alternativa_d=alternativa_d,
            alternativa_e=alternativa_e,
            questao_correta=questao_correta,
            Ano_escolar_id=Ano_escolar_id,
            mes_id=mes_id,
            codigo_ibge=codigo_ibge
        )
        
        db.session.add(nova_questao)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Questão cadastrada com sucesso'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao cadastrar questão: {str(e)}'}), 500
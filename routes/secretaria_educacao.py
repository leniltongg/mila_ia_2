from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, send_file, current_app
from flask_login import login_required, current_user
import os
from werkzeug.utils import secure_filename
import pandas as pd
from weasyprint import HTML
import tempfile
from io import BytesIO
from datetime import datetime
from extensions import db
from models import (
    Usuarios, Escolas, Ano_escolar, SimuladosGerados, Disciplinas, 
    DesempenhoSimulado, MESES, BancoQuestoes, RespostasSimulado, 
    SimuladosEnviados, Turmas, SimuladosGeradosProfessor, Cidades
)
from sqlalchemy import text, func, extract, and_, case, exists, or_, literal
from models import SimuladoQuestoes
from utils import verificar_permissao
from models import ImagemQuestao
from PyPDF2 import PdfReader
from models import db, BancoQuestoes, Assuntos
import re

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
            SimuladosGerados.ano_escolar_id,
            SimuladosGerados.mes_id,
            SimuladosGerados.status,
            Disciplinas.nome.label('disciplina_nome'),
            Ano_escolar.nome.label('Ano_escolar_nome'),
            MESES.nome.label('mes_nome')
        ).join(
            Disciplinas, Disciplinas.id == SimuladosGerados.disciplina_id
        ).join(
            Ano_escolar, Ano_escolar.id == SimuladosGerados.ano_escolar_id
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
                'ano_escolar_id': simulado.ano_escolar_id,
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
                BancoQuestoes.ano_escolar_id,
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
    print("\n1. Iniciando função salvar_simulado")
    print(f"1.1 Tipo de usuário: {current_user.tipo_usuario_id}")
    
    if current_user.tipo_usuario_id not in [5, 6]:
        print("1.2 Acesso não autorizado - usuário não é secretaria")
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        print("2. Tentando obter dados do request")
        dados = request.get_json()
        print(f"2.1 Dados recebidos: {dados}")
        
        # Extrair dados do JSON
        ano_escolar_id = dados.get('ano_escolar_id')
        mes_id = dados.get('mes_id')
        disciplina_id = dados.get('disciplina_id')
        questoes = dados.get('questoes', [])
        simulado_id = dados.get('simulado_id')
        pontuacao_total = float(dados.get('pontuacao_total', 0))
        
        print(f"3. Dados extraídos:")
        print(f"- ano_escolar_id: {ano_escolar_id}")
        print(f"- mes_id: {mes_id}")
        print(f"- disciplina_id: {disciplina_id}")
        print(f"- Número de questões: {len(questoes)}")
        print(f"- simulado_id: {simulado_id}")
        print(f"- pontuacao_total: {pontuacao_total}")
        
        # Validar dados obrigatórios
        if not all([ano_escolar_id, mes_id, disciplina_id]) or not questoes:
            print("Dados incompletos:")
            print(f"- ano_escolar_id presente: {bool(ano_escolar_id)}")
            print(f"- mes_id presente: {bool(mes_id)}")
            print(f"- disciplina_id presente: {bool(disciplina_id)}")
            print(f"- questoes presentes: {bool(questoes)}")
            return jsonify({'success': False, 'message': 'Dados incompletos'}), 400
        
        # Validar a soma das pontuações
        soma_pontuacoes = sum(float(q.get('pontuacao', 1.0)) for q in questoes)
        if abs(soma_pontuacoes - pontuacao_total) > 0.01:  # Usando uma pequena margem para evitar problemas com ponto flutuante
            return jsonify({
                'success': False, 
                'message': f'A soma das pontuações das questões ({soma_pontuacoes}) deve ser igual à pontuação total do simulado ({pontuacao_total})'
            }), 400
        
        print("4. Verificando se é edição ou novo simulado")
        if simulado_id:  # Edição
            print(f"4.1 Editando simulado {simulado_id}")
            # Buscar simulado existente
            simulado = SimuladosGerados.query.get(simulado_id)
            if not simulado:
                print(f"Simulado {simulado_id} não encontrado")
                return jsonify({'success': False, 'message': 'Simulado não encontrado'}), 404
            
            # Atualizar dados do simulado
            simulado.ano_escolar_id = ano_escolar_id
            simulado.mes_id = mes_id
            simulado.disciplina_id = disciplina_id
            simulado.pontuacao_total = pontuacao_total
            
            # Remover questões antigas
            print("Removendo questões antigas")
            SimuladoQuestoes.query.filter_by(simulado_id=simulado_id).delete()
        else:  # Novo simulado
            print("4.2 Criando novo simulado")
            simulado = SimuladosGerados(
                ano_escolar_id=ano_escolar_id,
                mes_id=mes_id,
                disciplina_id=disciplina_id,
                status='gerado',
                data_envio=datetime.now(),
                codigo_ibge=current_user.codigo_ibge,
                pontuacao_total=pontuacao_total
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
        ano_escolar_id = request.args.get('ano_escolar_id', '')
        mes_id = request.args.get('mes_id', '')
        assunto = request.args.get('assunto', '')
        
        print(f"3. Parâmetros recebidos: disciplina={disciplina_id}, Ano_escolar={ano_escolar_id}, mes={mes_id}, assunto={assunto}")
        
        print("4. Construindo query base")
        # Construir a query base usando SQL nativo
        sql = """
            SELECT bq.id, bq.questao, bq.alternativa_a, bq.alternativa_b, bq.alternativa_c, 
                   bq.alternativa_d, bq.alternativa_e, bq.questao_correta, bq.assunto,
                   bq.disciplina_id, bq.ano_escolar_id, bq.mes_id,
                   d.nome as disciplina_nome, ae.nome as Ano_escolar_nome
            FROM banco_questoes bq
            JOIN disciplinas d ON bq.disciplina_id = d.id
            JOIN Ano_escolar ae ON bq.ano_escolar_id = ae.id
            WHERE bq.codigo_ibge = :codigo_ibge
        """
        params = {'codigo_ibge': current_user.codigo_ibge}
        
        # Adicionar filtros conforme os parâmetros
        if disciplina_id and disciplina_id != '' and disciplina_id.isdigit():
            sql += " AND bq.disciplina_id = :disciplina_id"
            params['disciplina_id'] = int(disciplina_id)
        if ano_escolar_id and ano_escolar_id != '' and ano_escolar_id.isdigit():
            sql += " AND bq.ano_escolar_id = :ano_escolar_id"
            params['ano_escolar_id'] = int(ano_escolar_id)
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
                'ano_escolar_id': q.ano_escolar_id,
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
        ano_escolar_id = request.form.get('ano_escolar_id')
        mes_id = request.form.get('mes_id')
        disciplina_id = request.form.get('disciplina_id')
        num_questoes = request.form.get('num_questoes', type=int)
        
        if not all([ano_escolar_id, mes_id, disciplina_id, num_questoes]):
            return jsonify({'success': False, 'message': 'Dados incompletos'}), 400
        
        # Buscar questões aleatórias do banco
        questoes = db.session.query(BancoQuestoes).filter(
            BancoQuestoes.ano_escolar_id == ano_escolar_id,
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
            ano_escolar_id=ano_escolar_id,
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
            ano_escolar_id = request.form.get('ano_escolar_id')
            mes_id = request.form.get('mes_id')
            codigo_ibge = current_user.codigo_ibge

            # Validar dados
            if not all([questao, alternativa_a, alternativa_b, alternativa_c, alternativa_d,
                       questao_correta, disciplina_id, ano_escolar_id]):
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
                ano_escolar_id=ano_escolar_id,
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
            Ano_escolar, Ano_escolar.id == BancoQuestoes.ano_escolar_id
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

    # Buscar disciplinas para o formulário de importação
    disciplinas = Disciplinas.query.all()

    return render_template(
        "secretaria_educacao/portal_secretaria_educacao.html",
        simulados_gerados=simulados_gerados,
        total_escolas=total_escolas,
        total_alunos=numero_alunos,
        total_simulados=numero_simulados_gerados,
        media_geral=media_geral,
        disciplinas=disciplinas  # Adicionado disciplinas ao contexto
    )

# @secretaria_educacao_bp.route('/portal_secretaria_educacao', methods=['GET'])
# @login_required
# def portal_secretaria_educacao():
#     if current_user.tipo_usuario_id not in [5, 6]:  # Verifica se é uma Secretaria de Educação
#         flash("Acesso não autorizado.", "danger")
#         return redirect(url_for("index"))

#     # Buscar simulados gerados
#     simulados_gerados = Simulados.query.filter_by(
#         codigo_ibge=current_user.codigo_ibge
#     ).order_by(Simulados.data_criacao.desc()).all()

#     # Buscar estatísticas
#     total_escolas = Escolas.query.filter_by(codigo_ibge=current_user.codigo_ibge).count()
    
#     # Número de alunos
#     numero_alunos = Usuarios.query.filter_by(
#         codigo_ibge=current_user.codigo_ibge,
#         tipo_usuario_id=4
#     ).count()

#     # Número de simulados gerados
#     numero_simulados_gerados = Simulados.query.filter_by(
#         codigo_ibge=current_user.codigo_ibge
#     ).count()

#     # Média geral dos alunos
#     media_geral = 0
#     resultados = ResultadosSimulados.query.join(
#         Simulados, ResultadosSimulados.simulado_id == Simulados.id
#     ).filter(
#         Simulados.codigo_ibge == current_user.codigo_ibge
#     ).all()

#     if resultados:
#         media_geral = sum(r.nota for r in resultados) / len(resultados)

#     # Buscar assuntos para o formulário de importação
#     assuntos = Assuntos.query.all()

#     return render_template(
#         "secretaria_educacao/portal_secretaria_educacao.html",
#         simulados_gerados=simulados_gerados,
#         total_escolas=total_escolas,
#         total_alunos=numero_alunos,
#         total_simulados=numero_simulados_gerados,
#         media_geral=media_geral,
#         assuntos=assuntos
#     )

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

    filepath = None  # Inicializa filepath como None
    
    if arquivo and arquivo.filename.endswith('.pdf'):
        try:
            # Salvar o arquivo temporariamente
            filename = secure_filename(arquivo.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            arquivo.save(filepath)

            # Processar o arquivo PDF
            reader = PdfReader(filepath)
            questoes_importadas = 0
                
            # Extrair texto de cada página
            texto_completo = ""
            for pagina in reader.pages:
                texto_completo += pagina.extract_text()
            
            print("Texto completo:", texto_completo)  # Debug
                
            # Dividir o texto em questões
            import re
            questoes = re.split(r'Questão\s+\d+\s+', texto_completo)[1:]  # Ajustado o padrão para incluir espaços extras
            print(f"Número de questões encontradas: {len(questoes)}")  # Debug
            
            for texto_questao in questoes:
                if len(texto_questao.strip()) > 10:
                    print("\n\nProcessando questão:", texto_questao)  # Debug
                    
                    # Extrair alternativas usando um padrão mais preciso
                    padrao_alternativas = r'\(([A-E])\)(.*?)(?=\([A-E]\)|Resposta Correta:|$)'
                    alternativas_match = re.findall(padrao_alternativas, texto_questao, re.DOTALL)
                    alternativas = {}
                    for letra, texto in alternativas_match:
                        alternativas[letra] = texto.strip()
                    
                    print("Alternativas encontradas:", alternativas)  # Debug
                    
                    # Extrair resposta correta
                    resposta_match = re.search(r'Resposta Correta:\s*([A-E])', texto_questao)
                    resposta_correta = resposta_match.group(1) if resposta_match else 'A'
                    print("Resposta correta:", resposta_correta)  # Debug
                    
                    # Extrair disciplina
                    disciplina_match = re.search(r'Disciplina:\s*(\w+)', texto_questao)
                    disciplina = disciplina_match.group(1) if disciplina_match else None
                    print("Disciplina:", disciplina)  # Debug
                    
                    # Extrair assunto
                    assunto_match = re.search(r'Assunto:\s*([^\n]+)', texto_questao)
                    assunto = assunto_match.group(1).strip() if assunto_match else None
                    print("Assunto:", assunto)  # Debug
                    
                    # Extrair série
                    serie_match = re.search(r'Ano_escolar_id\s*:\s*(\d+)', texto_questao)
                    serie_id = int(serie_match.group(1)) if serie_match else None
                    print("Série ID:", serie_id)  # Debug
                    
                    # Extrair mês
                    mes_match = re.search(r'Mes_id:\s*(\d+)', texto_questao)
                    mes_id = int(mes_match.group(1)) if mes_match else None
                    print("Mês ID:", mes_id)  # Debug
                    
                    # Buscar a disciplina no banco pelo nome
                    disciplina_obj = Disciplinas.query.filter(Disciplinas.nome.ilike(f"%{disciplina}%")).first()
                    disciplina_id = disciplina_obj.id if disciplina_obj else None
                    print("Disciplina ID:", disciplina_id)  # Debug
                    
                    # Criar nova questão no banco
                    nova_questao = BancoQuestoes(
                        questao=texto_questao.split('(A)')[0].strip(),  # Texto até a primeira alternativa
                        alternativa_a=alternativas.get('A', ''),
                        alternativa_b=alternativas.get('B', ''),
                        alternativa_c=alternativas.get('C', ''),
                        alternativa_d=alternativas.get('D', ''),
                        alternativa_e=alternativas.get('E', ''),
                        questao_correta=resposta_correta,
                        disciplina_id=disciplina_id,
                        assunto=assunto,
                        ano_escolar_id=serie_id,
                        mes_id=mes_id,
                        codigo_ibge=current_user.codigo_ibge,
                        usuario_id=current_user.id
                    )
                    db.session.add(nova_questao)
                    questoes_importadas += 1
            
            db.session.commit()
            flash(f'Arquivo processado com sucesso! {questoes_importadas} questões importadas.', 'success')
            
        except ValueError as ve:
            flash(str(ve), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao processar arquivo: {str(e)}', 'danger')
        finally:
            # Remover o arquivo temporário se ele foi criado
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
                
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
            SimuladosGerados.ano_escolar_id,
            SimuladosGerados.mes_id,
            Disciplinas.nome.label('disciplina_nome'),
            Ano_escolar.nome.label('Ano_escolar_nome'),
            MESES.nome.label('mes_nome'),
            func.count(SimuladoQuestoes.id).label('total_questoes')
        ).join(
            Disciplinas, Disciplinas.id == SimuladosGerados.disciplina_id
        ).join(
            Ano_escolar, Ano_escolar.id == SimuladosGerados.ano_escolar_id
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
            SimuladosGerados.ano_escolar_id,
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
            print(f"Ano Escolar do simulado: {simulado.ano_escolar_id}")
        
        if not simulado:
            print("Erro: Simulado não encontrado ou não pode ser enviado")
            return jsonify({
                'success': False,
                'message': 'Simulado não encontrado ou não pode ser enviado'
            }), 404
        
        # Buscar alunos da série do município
        alunos = db.session.query(Usuarios).filter(
            Usuarios.tipo_usuario_id == 4,  # Aluno
            Usuarios.ano_escolar_id == simulado.ano_escolar_id,
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
                print(f"Ano Escolar: {simulado.ano_escolar_id}")
                print(f"Turma: {aluno.turma_id}")
                
                try:
                    desempenho = DesempenhoSimulado(
                        aluno_id=aluno.id,
                        simulado_id=simulados_enviados[aluno.turma_id],  # ID do simulado_enviado da turma
                        escola_id=aluno.escola_id,
                        ano_escolar_id=simulado.ano_escolar_id,
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
            Ano_escolar, Ano_escolar.id == SimuladosGerados.ano_escolar_id
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
            SimuladoQuestoes,
            SimuladoQuestoes.questao_id == BancoQuestoes.id
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
            LEFT JOIN Ano_escolar s ON q.ano_escolar_id = s.id
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
        
        # Processar URLs das imagens - remover sintaxe Jinja2 e adicionar /static/
        def process_image_urls(text):
            if text:
                # Remove sintaxe Jinja2
                text = re.sub(r"{{\s*url_for\('static',\s*filename='([^']+)'\)\s*}}", r"/static/\1", text)
                # Garante que todas as URLs de imagem começam com /static/
                text = re.sub(r'src="(?!/static/)([^"]+)"', r'src="/static/\1"', text)
            return text
        
        # Processar URLs em todos os campos
        questao = process_image_urls(questao)
        alternativa_a = process_image_urls(alternativa_a)
        alternativa_b = process_image_urls(alternativa_b)
        alternativa_c = process_image_urls(alternativa_c)
        alternativa_d = process_image_urls(alternativa_d)
        alternativa_e = process_image_urls(alternativa_e)
        
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
            # Usar o caminho absoluto para salvar a imagem
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'imagens_questoes')
            os.makedirs(upload_folder, exist_ok=True)
            
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            
            # Salvar apenas o caminho relativo ao diretório static no banco
            url_path = os.path.join('uploads', 'imagens_questoes', filename).replace('\\', '/')
            
            # Cria o registro no banco
            imagem = ImagemQuestao(
                nome=filename,  # Usar o nome do arquivo como nome
                url=url_path,  # Caminho relativo à pasta static
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
        ano_escolar_id = request.form.get('ano_escolar_id')
        mes_id = request.form.get('mes_id')
        codigo_ibge = current_user.codigo_ibge
        
        # Processar URLs das imagens - remover sintaxe Jinja2 e adicionar /static/
        def process_image_urls(text):
            if text:
                # Remove sintaxe Jinja2
                text = re.sub(r"{{\s*url_for\('static',\s*filename='([^']+)'\)\s*}}", r"/static/\1", text)
                # Garante que todas as URLs de imagem começam com /static/
                text = re.sub(r'src="(?!/static/)([^"]+)"', r'src="/static/\1"', text)
            return text
        
        # Processar URLs em todos os campos
        questao = process_image_urls(questao)
        alternativa_a = process_image_urls(alternativa_a)
        alternativa_b = process_image_urls(alternativa_b)
        alternativa_c = process_image_urls(alternativa_c)
        alternativa_d = process_image_urls(alternativa_d)
        alternativa_e = process_image_urls(alternativa_e)
        
        # Validação básica
        if not all([questao, alternativa_a, alternativa_b, alternativa_c, alternativa_d, 
                   questao_correta, disciplina_id, assunto]):
            return jsonify({'success': False, 'message': 'Por favor, preencha todos os campos obrigatórios'}), 400
            
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
            ano_escolar_id=ano_escolar_id,
            mes_id=mes_id,
            codigo_ibge=codigo_ibge
        )
        
        db.session.add(nova_questao)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Questão cadastrada com sucesso'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao cadastrar questão: {str(e)}'}), 500

@secretaria_educacao_bp.route('/perfil')
@login_required
def perfil():
    try:
        # Buscar informações do usuário
        usuario = db.session.query(Usuarios).filter(
            Usuarios.id == current_user.id
        ).first()

        # Buscar informações da cidade
        cidade = None
        if usuario.cidade_id:
            cidade = db.session.query(Cidades).filter(
                Cidades.id == usuario.cidade_id
            ).first()

        # Formatação dos dados
        if usuario.data_nascimento:
            try:
                # Tentar converter para o formato brasileiro
                data = datetime.strptime(usuario.data_nascimento, '%Y-%m-%d')
                usuario.data_nascimento = data.strftime('%d/%m/%Y')
            except:
                pass

        # Formatar CPF se existir
        if usuario.cpf:
            cpf = usuario.cpf
            if len(cpf) == 11:
                usuario.cpf = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

        return render_template('secretaria_educacao/perfil.html',
                             usuario=usuario,
                             cidade=cidade)
    except Exception as e:
        import traceback
        print(f"Erro detalhado ao carregar perfil: {str(e)}")
        print(traceback.format_exc())
        flash('Erro ao carregar perfil', 'danger')
        return redirect(url_for('secretaria_educacao.portal_secretaria_educacao'))
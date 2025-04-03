from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, send_file, current_app
from flask_login import login_required, current_user
from extensions import db
from sqlalchemy import desc, func, distinct, and_, text, extract, exists, or_, literal, case
from models import (
    Escolas, Usuarios, SimuladosGerados, Disciplinas,
    BancoQuestoes, SimuladoQuestoes, DesempenhoSimulado,
    MESES, Turmas, Ano_escolar, TiposEnsino, ImagemQuestao,
    TIPO_USUARIO_ADMIN, TIPO_USUARIO_SECRETARIA, TIPO_USUARIO_PROFESSOR,
    TIPO_USUARIO_ALUNO, TIPO_USUARIO_SECRETARIA_EDUCACAO,
    BancoQuestoes, SimuladoQuestoes, TemasRedacao, Ano_escolar, RedacoesAlunos
)
from datetime import datetime
import os
import json
import re
from werkzeug.utils import secure_filename
import calendar
from datetime import datetime
from flask import jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func, desc, literal
from models import db, RedacoesAlunos, Usuarios, Escolas, Ano_escolar


def nl2br(text):
    """Converte quebras de linha em <br>"""
    if not text:
        return ""
    return text.replace('\n', '<br>')

bp = Blueprint('secretaria_educacao', __name__)


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
bp = Blueprint('secretaria_educacao', __name__, url_prefix='/secretaria_educacao')

# Filtro para nome do mês
@bp.app_template_filter('mes_nome')
def mes_nome(mes_id):
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
    return meses.get(int(mes_id), '-')

def get_db():
    return db

@bp.teardown_app_request
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

@bp.route('/criar_simulado', methods=['GET'])
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

@bp.route('/salvar_simulado', methods=['POST'])
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

@bp.route('/buscar_questoes', methods=['GET'])
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
                   d.nome as disciplina_nome, ae.nome as Ano_escolar_nome,
                   m.nome as mes_nome
            FROM banco_questoes bq
            JOIN disciplinas d ON bq.disciplina_id = d.id
            JOIN Ano_escolar ae ON bq.ano_escolar_id = ae.id
            LEFT JOIN meses m ON bq.mes_id = m.id
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
            sql += " AND LOWER(bq.assunto) LIKE :assunto"
            params['assunto'] = f"%{assunto.lower()}%"
            
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
                'Ano_escolar_nome': q.Ano_escolar_nome,
                'mes_nome': q.mes_nome if q.mes_nome else '-',
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

@bp.route('/gerar_simulado_automatico', methods=['POST'])
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
        
#         if not all([ano_escolar_id, mes_id, disciplina_id]) or not questoes:
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

@bp.route('/banco_questoes', methods=['GET', 'POST'])
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
                    texto = texto.replace('src="/static/', 'src="{{ url_for(\'static\', filename=\'')
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
                'message': 'Questão cadastrada com sucesso'
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
                    # Garantir que as imagens usem o caminho correto
                    texto = texto.replace('src="{{ url_for(\'static\', filename=\'', 'src="/static/')
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
                'ano_escolar_nome': q.ano_escolar_nome,
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


@bp.route("/portal_secretaria_educacao", methods=["GET", "POST"])
@login_required
def portal_secretaria_educacao():
    if current_user.tipo_usuario_id not in [5, 6]:  # Verifica se é uma Secretaria de Educação
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    # Obtém estatísticas gerais
    total_escolas = Escolas.query.count()
    total_alunos = db.session.query(
        Usuarios.id
    ).filter(
        Usuarios.tipo_usuario_id == 4  # Tipo aluno
    ).count()
    total_simulados = SimuladosGerados.query.count()
    
    # Calcular média geral de todos os simulados do município
    media_query = db.session.query(
        func.avg(DesempenhoSimulado.desempenho).label('media_geral'),
        func.avg(DesempenhoSimulado.pontuacao).label('media_pontos')
    ).join(
        Usuarios, 
        and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            Usuarios.tipo_usuario_id == 4  # Tipo aluno
        )
    ).first()
    
    media_geral = float(media_query.media_geral or 0)
    media_pontos = float(media_query.media_pontos or 0)

    # Calcular distribuição de desempenho
    faixas = db.session.query(
        func.sum(case((DesempenhoSimulado.desempenho <= 20, 1), else_=0)).label('faixa_0_20'),
        func.sum(case((and_(DesempenhoSimulado.desempenho > 20, DesempenhoSimulado.desempenho <= 40), 1), else_=0)).label('faixa_21_40'),
        func.sum(case((and_(DesempenhoSimulado.desempenho > 40, DesempenhoSimulado.desempenho <= 60), 1), else_=0)).label('faixa_41_60'),
        func.sum(case((and_(DesempenhoSimulado.desempenho > 60, DesempenhoSimulado.desempenho <= 80), 1), else_=0)).label('faixa_61_80'),
        func.sum(case((and_(DesempenhoSimulado.desempenho > 80, DesempenhoSimulado.desempenho <= 100), 1), else_=0)).label('faixa_81_100')
    ).join(
        Usuarios,
        and_(
            DesempenhoSimulado.aluno_id == Usuarios.id,
            Usuarios.tipo_usuario_id == 4  # Tipo aluno
        )
    ).first()

    # Garantir que todas as variáveis tenham valores padrão
    faixa_0_20 = faixas[0] if faixas and faixas[0] is not None else 0
    faixa_21_40 = faixas[1] if faixas and faixas[1] is not None else 0
    faixa_41_60 = faixas[2] if faixas and faixas[2] is not None else 0
    faixa_61_80 = faixas[3] if faixas and faixas[3] is not None else 0
    faixa_81_100 = faixas[4] if faixas and faixas[4] is not None else 0

    # Buscar o ranking de escolas
    ranking_escolas_query = db.session.query(
        Escolas.nome_da_escola.label('nome'),
        func.avg(DesempenhoSimulado.desempenho).label('media_geral')
    ).join(
        Usuarios,
        and_(
            Usuarios.escola_id == Escolas.id,
            Usuarios.tipo_usuario_id == 4  # Tipo aluno
        )
    ).join(
        DesempenhoSimulado,
        DesempenhoSimulado.aluno_id == Usuarios.id
    ).group_by(
        Escolas.id,
        Escolas.nome_da_escola
    ).order_by(
        func.avg(DesempenhoSimulado.desempenho).desc()
    ).all()

    ranking_escolas = [
        {
            'nome': escola.nome,
            'media_geral': float(escola.media_geral)
        }
        for escola in ranking_escolas_query
    ]

    # Buscar o ranking de alunos
    ranking_alunos_query = db.session.query(
        Usuarios.nome,
        Usuarios.ano_escolar_id,
        func.avg(DesempenhoSimulado.desempenho).label('media_geral')
    ).join(
        DesempenhoSimulado,
        DesempenhoSimulado.aluno_id == Usuarios.id
    ).filter(
        Usuarios.tipo_usuario_id == 4  # Tipo aluno
    ).group_by(
        Usuarios.id,
        Usuarios.nome,
        Usuarios.ano_escolar_id
    ).order_by(
        func.avg(DesempenhoSimulado.desempenho).desc()
    ).all()

    ranking_alunos = [
        {
            'nome': aluno.nome,
            'ano_escolar': f"{aluno.ano_escolar_id}º Ano",
            'media_geral': float(aluno.media_geral)
        }
        for aluno in ranking_alunos_query
    ]

    # Preparar dados para os gráficos
    escolas_labels = [escola['nome'] for escola in ranking_escolas[:5]]
    escolas_data = [escola['media_geral'] for escola in ranking_escolas[:5]]
    alunos_labels = [aluno['nome'] for aluno in ranking_alunos[:5]]
    alunos_data = [aluno['media_geral'] for aluno in ranking_alunos[:5]]

    return render_template(
        'secretaria_educacao/portal_secretaria_educacao.html',
        total_escolas=total_escolas,
        total_alunos=total_alunos,
        total_simulados=total_simulados,
        media_geral=media_geral,
        media_pontos=media_pontos,
        faixa_0_20=faixa_0_20,
        faixa_21_40=faixa_21_40,
        faixa_41_60=faixa_41_60,
        faixa_61_80=faixa_61_80,
        faixa_81_100=faixa_81_100,
        ranking_escolas=ranking_escolas,
        ranking_alunos=ranking_alunos,
        escolas_labels=escolas_labels,
        escolas_data=escolas_data,
        alunos_labels=alunos_labels,
        alunos_data=alunos_data
    )


@bp.route('/importar_questoes', methods=['POST'])
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
            # Usar o caminho absoluto para salvar a arquivo
            upload_folder = os.path.join('static', 'uploads', 'imagens_questoes')
            os.makedirs(upload_folder, exist_ok=True)
            
            filepath = os.path.join(upload_folder, filename)
            arquivo.save(filepath)

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

@bp.route('/meus_simulados', methods=['GET'])
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
            Disciplinas.nome.label('disciplina_nome'),
            Ano_escolar.nome.label('Ano_escolar_nome'),
            MESES.nome.label('mes_nome'),
            func.count(SimuladoQuestoes.questao_id).label('total_questoes')
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
        return redirect(url_for("index"))

@bp.route('/enviar_simulado/<int:simulado_id>', methods=['POST'])
@login_required
def enviar_simulado(simulado_id):
    """Envia um simulado para os alunos."""
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    try:
        # Buscar simulado e verificar se pode ser enviado
        simulado = db.session.query(SimuladosGerados).filter(
            SimuladosGerados.id == simulado_id,
            SimuladosGerados.codigo_ibge == current_user.codigo_ibge,
            SimuladosGerados.status == 'gerado'
        ).first()
        
        if not simulado:
            return jsonify({
                'success': False,
                'message': 'Simulado não encontrado ou não pode ser enviado'
            }), 404
        
        # Buscar alunos da série do município para validação
        alunos = db.session.query(Usuarios).filter(
            Usuarios.tipo_usuario_id == 4,
            Usuarios.ano_escolar_id == simulado.ano_escolar_id,
            Usuarios.codigo_ibge == current_user.codigo_ibge
        ).all()
        
        if not alunos:
            return jsonify({
                'success': False,
                'message': 'Nenhum aluno encontrado para esta série'
            }), 404
        
        # Atualizar status do simulado
        simulado.status = 'enviado'
        simulado.data_envio = datetime.now()
        
        # Commit da alteração
        db.session.commit()
        return jsonify({'success': True, 'message': 'Simulado enviado com sucesso'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500





@bp.route('/gerenciar_imagens')
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

@bp.route('/upload_imagem', methods=['POST'])
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
            upload_folder = os.path.join('static', 'uploads', 'imagens_questoes')
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

@bp.route('/filtrar_imagens')
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
        query = query.filter(ImagemQuestao.assunto.like(f'%{assunto}%'))
    if tipo:
        query = query.filter_by(tipo=tipo)
    if busca:
        query = query.filter(or_(
            ImagemQuestao.nome.like(f'%{busca}%'),
            ImagemQuestao.descricao.like(f'%{busca}%')
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

@bp.route('/deletar_imagem/<int:id>', methods=['DELETE'])
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


@bp.route('/adicionar_questao', methods=['POST'])
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
        def processar_conteudo(texto):
            if texto:
                # Remove sintaxe Jinja2
                texto = re.sub(r"{{\s*url_for\('static',\s*filename='([^']*)'?\s*\)\s*}}", r"/static/\1", texto)
                # Garante que todas as URLs de imagem começam com /static/
                texto = re.sub(r'src="([^"]*)\s+([^"]*)"', r'src="\1\2"', texto)
                texto = re.sub(r"src='([^']*)\s+([^']*)'", r"src='\1\2'", texto)
            return texto
        
        # Processar URLs em todos os campos
        questao = processar_conteudo(questao)
        alternativa_a = processar_conteudo(alternativa_a)
        alternativa_b = processar_conteudo(alternativa_b)
        alternativa_c = processar_conteudo(alternativa_c)
        alternativa_d = processar_conteudo(alternativa_d)
        alternativa_e = processar_conteudo(alternativa_e)

        # Validação básica
        if not all([questao, alternativa_a, alternativa_b, alternativa_c, alternativa_d, 
                   questao_correta, disciplina_id, ano_escolar_id]):
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

@bp.route('/perfil')
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

@bp.route('/')
@login_required
def index():
    if current_user.tipo_usuario_id not in [5, 6]:  # Apenas secretaria de educação
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))

    return redirect(url_for('secretaria_educacao.portal_secretaria_educacao'))

@bp.route('/ranking-escolas')
@login_required
def ranking_escolas():
    """Página com o ranking completo das escolas."""
    # Busca todas as disciplinas
    disciplinas = Disciplinas.query.all()
    
    # Obtém o ano selecionado e tipo de ranking dos parâmetros da URL
    ano_selecionado = request.args.get('ano', 'todos')
    tipo_ranking = request.args.get('tipo_ranking', 'pontuacao')
    mes_selecionado = request.args.get('mes', 'todos')

    # Busca todos os anos escolares
    anos_escolares = Ano_escolar.query.order_by(Ano_escolar.nome).all()

    # Ranking Geral
    query_geral = db.session.query(
        Escolas,
        func.count(distinct(Usuarios.id)).label('total_alunos'),
        func.avg(DesempenhoSimulado.pontuacao).label('media_pontos'),
        func.avg(DesempenhoSimulado.desempenho).label('media_geral'),
        func.count(distinct(SimuladosGerados.id)).label('total_simulados')
    ).join(Usuarios, Usuarios.escola_id == Escolas.id)\
     .join(DesempenhoSimulado, DesempenhoSimulado.aluno_id == Usuarios.id)\
     .join(SimuladosGerados, SimuladosGerados.id == DesempenhoSimulado.simulado_id)\
     .filter(Usuarios.tipo_usuario_id == 4)

    # Aplicar filtro de ano escolar se necessário
    if ano_selecionado != 'todos':
        query_geral = query_geral.filter(SimuladosGerados.ano_escolar_id == ano_selecionado)

    # Aplicar filtro de mês se necessário
    if mes_selecionado != 'todos':
        query_geral = query_geral.filter(SimuladosGerados.mes_id == mes_selecionado)

    # Agrupar e ordenar
    query_geral = query_geral.group_by(Escolas.id)
    if tipo_ranking == 'pontuacao':
        query_geral = query_geral.order_by(func.avg(DesempenhoSimulado.pontuacao).desc())
    else:
        query_geral = query_geral.order_by(func.avg(DesempenhoSimulado.desempenho).desc())

    ranking_geral_results = query_geral.all()

    # Formata o ranking geral
    ranking_geral = {
        'todos': [
            {
                'id': escola.id,
                'nome': escola.nome_da_escola,
                'codigo_ibge': escola.codigo_ibge,
                'total_alunos': total_alunos,
                'media_pontos': media_pontos,
                'media_geral': media_geral,
                'total_simulados': total_simulados
            }
            for escola, total_alunos, media_pontos, media_geral, total_simulados in ranking_geral_results
        ]
    }

    # Ranking por Disciplina
    ranking_disciplinas = {}
    for disciplina in disciplinas:
        ranking_disciplinas[disciplina.id] = {'todos': []}
        
        query_disc = db.session.query(
            Escolas,
            func.count(distinct(Usuarios.id)).label('total_alunos'),
            func.avg(DesempenhoSimulado.pontuacao).label('media_pontos'),
            func.avg(DesempenhoSimulado.desempenho).label('media_geral'),
            func.count(distinct(SimuladosGerados.id)).label('total_simulados')
        ).join(
            Usuarios, 
            and_(
                Usuarios.escola_id == Escolas.id,
                Usuarios.tipo_usuario_id == 4
            )
        ).join(
            DesempenhoSimulado, 
            DesempenhoSimulado.aluno_id == Usuarios.id
        ).join(
            SimuladosGerados, 
            and_(
                SimuladosGerados.id == DesempenhoSimulado.simulado_id,
                SimuladosGerados.disciplina_id == disciplina.id
            )
        )

        # Aplicar filtro de ano escolar se necessário
        if ano_selecionado != 'todos':
            query_disc = query_disc.filter(SimuladosGerados.ano_escolar_id == ano_selecionado)

        # Aplicar filtro de mês se necessário
        if mes_selecionado != 'todos':
            query_disc = query_disc.filter(SimuladosGerados.mes_id == mes_selecionado)

        # Agrupar e ordenar
        query_disc = query_disc.group_by(Escolas.id)
        if tipo_ranking == 'pontuacao':
            query_disc = query_disc.order_by(func.avg(DesempenhoSimulado.pontuacao).desc())
        else:
            query_disc = query_disc.order_by(func.avg(DesempenhoSimulado.desempenho).desc())

        ranking = query_disc.all()
        
        ranking_disciplinas[disciplina.id]['todos'] = [
            {
                'id': escola.id,
                'nome': escola.nome_da_escola,
                'codigo_ibge': escola.codigo_ibge,
                'total_alunos': total_alunos,
                'media_pontos': media_pontos,
                'media_geral': media_geral,
                'total_simulados': total_simulados
            }
            for escola, total_alunos, media_pontos, media_geral, total_simulados in ranking
        ]

    return render_template(
        'secretaria_educacao/ranking_escolas.html',
        disciplinas=disciplinas,
        ranking_geral=ranking_geral,
        rankings_disciplinas=ranking_disciplinas,
        anos_escolares=anos_escolares,
        ano_selecionado=ano_selecionado,
        tipo_ranking=tipo_ranking,
        mes_selecionado=mes_selecionado
    )

@bp.route('/ranking-alunos')
@login_required
def ranking_alunos():
    """Página com o ranking completo dos alunos."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('index'))

    # Busca todas as disciplinas
    disciplinas = Disciplinas.query.all()

    # Busca todos os anos escolares
    anos_escolares = db.session.query(
        Ano_escolar.nome
    ).join(
        Usuarios, Usuarios.ano_escolar_id == Ano_escolar.id
    ).filter(
        Usuarios.tipo_usuario_id == 4  # Tipo aluno
    ).distinct().order_by(
        Ano_escolar.nome
    ).all()
    anos_escolares = [ano[0] for ano in anos_escolares]  # Converte de tupla para lista

    # Busca todas as escolas que têm o mesmo código IBGE do usuário da secretaria
    escolas = db.session.query(
        Escolas.nome_da_escola
    ).filter(
        Escolas.codigo_ibge == current_user.codigo_ibge
    ).order_by(
        Escolas.nome_da_escola
    ).all()
    escolas = [escola[0] for escola in escolas]  # Converte de tupla para lista

    # Ranking Geral
    ranking_geral = db.session.query(
        Usuarios.id,
        Usuarios.nome,
        Ano_escolar.nome.label('ano_escolar'),
        Escolas.nome_da_escola.label('escola'),
        Turmas.turma.label('turma'),
        func.avg(DesempenhoSimulado.pontuacao).label('media_pontuacao'),
        func.avg(DesempenhoSimulado.desempenho).label('media_geral'),
        func.count(distinct(DesempenhoSimulado.simulado_id)).label('total_simulados')
    ).join(
        DesempenhoSimulado, DesempenhoSimulado.aluno_id == Usuarios.id
    ).outerjoin(
        Escolas, Escolas.id == Usuarios.escola_id
    ).outerjoin(
        Ano_escolar, Ano_escolar.id == Usuarios.ano_escolar_id
    ).outerjoin(
        Turmas, Turmas.id == Usuarios.turma_id
    ).filter(
        Usuarios.tipo_usuario_id == 4  # Tipo aluno
    ).group_by(
        Usuarios.id,
        Usuarios.nome,
        Ano_escolar.nome,
        Escolas.nome_da_escola,
        Turmas.turma
    ).order_by(
        desc('media_geral')
    ).all()

    # Ranking por disciplina e ano escolar
    ranking_disciplinas = {}
    for disciplina in disciplinas:
        # Busque o desempenho dos alunos por disciplina
        ranking = db.session.query(
            Usuarios.id,
            Usuarios.nome,
            Ano_escolar.nome.label('ano_escolar'),
            Escolas.nome_da_escola.label('escola'),
            Turmas.turma.label('turma'),
            func.avg(DesempenhoSimulado.pontuacao).label('media_pontuacao'),
            func.avg(DesempenhoSimulado.desempenho).label('media_disciplina'),
            func.count(distinct(DesempenhoSimulado.simulado_id)).label('total_simulados')
        ).join(
            DesempenhoSimulado, DesempenhoSimulado.aluno_id == Usuarios.id
        ).outerjoin(
            Escolas, Escolas.id == Usuarios.escola_id
        ).outerjoin(
            Ano_escolar, Ano_escolar.id == Usuarios.ano_escolar_id
        ).outerjoin(
            Turmas, Turmas.id == Usuarios.turma_id
        ).join(
            SimuladosGerados, SimuladosGerados.id == DesempenhoSimulado.simulado_id
        ).filter(
            Usuarios.tipo_usuario_id == 4,  # Tipo aluno
            SimuladosGerados.disciplina_id == disciplina.id  # Filtra pela disciplina
        ).group_by(
            Usuarios.id,
            Usuarios.nome,
            Ano_escolar.nome,
            Escolas.nome_da_escola,
            Turmas.turma
        ).having(
            func.count(distinct(DesempenhoSimulado.simulado_id)) > 0  # Garante que o aluno fez pelo menos um simulado
        ).order_by(
            desc('media_disciplina')
        ).all()

        if ranking:  # Só adiciona a disciplina se houver dados
            # Converte os resultados para dicionário
            alunos = [
                {
                    'id': aluno[0],
                    'nome': aluno[1] or 'Não informado',
                    'ano_escolar': aluno[2] or 'Não informado',
                    'escola': aluno[3] or 'Não informada',
                    'turma': aluno[4] or 'Não informada',
                    'media_pontuacao': float(aluno[5] or 0),
                    'media_disciplina': float(aluno[6] or 0),
                    'total_simulados': aluno[7] or 0
                }
                for aluno in ranking
            ]

            # Adiciona todos os alunos na chave 'todos'
            ranking_disciplinas[disciplina.nome] = {'todos': alunos}

            # Agrupa os alunos por ano escolar
            for ano in anos_escolares:
                alunos_do_ano = [
                    aluno for aluno in alunos
                    if aluno['ano_escolar'] == ano
                ]
                if alunos_do_ano:  # Só adiciona o ano se houver alunos
                    ranking_disciplinas[disciplina.nome][ano] = alunos_do_ano

    # Formata o ranking geral
    ranking_geral = [
        {
            'id': aluno[0],
            'nome': aluno[1] or 'Não informado',
            'ano_escolar': aluno[2] or 'Não informado',
            'escola': aluno[3] or 'Não informada',
            'turma': aluno[4] or 'Não informada',
            'media_pontuacao': float(aluno[5] or 0),
            'media_geral': float(aluno[6] or 0),
            'total_simulados': aluno[7] or 0
        }
        for aluno in ranking_geral
    ]

    return render_template(
        'secretaria_educacao/ranking_alunos.html',
        disciplinas=disciplinas,
        anos_escolares=anos_escolares,
        escolas=escolas,
        ranking_geral=ranking_geral,
        ranking_disciplinas=ranking_disciplinas
    )
@bp.route('/buscar-turmas')
@login_required
def buscar_turmas():
    """Retorna as turmas de uma escola e ano escolar específicos."""
    if current_user.tipo_usuario_id not in [5, 6]:
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    escola = request.args.get('escola')
    ano_escolar = request.args.get('ano_escolar')
    
    if not escola:
        return jsonify({'error': 'Escola não especificada'})

    query = """
        SELECT DISTINCT t.turma
        FROM turmas t
        JOIN escolas e ON t.escola_id = e.id
        WHERE e.nome_da_escola = :escola
    """
    params = {'escola': escola}

    if ano_escolar != 'todos':
        query += " AND t.ano_escolar_id = :ano_escolar"
        params['ano_escolar'] = ano_escolar

    query += " ORDER BY t.turma"
    
    result = db.session.execute(text(query), params)
    turmas = [row[0] for row in result]
    
    return jsonify({'turmas': turmas})

@bp.route('/visualizar_simulado/<int:simulado_id>')
@login_required
def visualizar_simulado(simulado_id):
    """Visualiza um simulado específico."""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
    
    try:
        # Buscar informações do simulado
        simulado = db.session.query(
            SimuladosGerados,
            Disciplinas.nome.label('disciplina_nome'),
            Ano_escolar.nome.label('Ano_escolar_nome'),
            MESES.nome.label('mes_nome')
        ).join(
            Disciplinas, SimuladosGerados.disciplina_id == Disciplinas.id
        ).join(
            Ano_escolar, SimuladosGerados.ano_escolar_id == Ano_escolar.id
        ).join(
            MESES, SimuladosGerados.mes_id == MESES.id
        ).filter(
            SimuladosGerados.id == simulado_id,
            SimuladosGerados.codigo_ibge == current_user.codigo_ibge
        ).first()

        if not simulado:
            flash("Simulado não encontrado.", "danger")
            return redirect(url_for("secretaria_educacao.meus_simulados"))

        # Buscar questões do simulado
        questoes = db.session.query(
            BancoQuestoes
        ).join(
            SimuladoQuestoes,
            SimuladoQuestoes.questao_id == BancoQuestoes.id
        ).filter(
            SimuladoQuestoes.simulado_id == simulado_id
        ).all()

        # Função para tratar imagens
        def tratar_imagens(texto):
            if texto and '<img' in texto:
                if '{{ url_for' in texto:
                    import re
                    pre_img = texto.split('<img')[0]
                    match = re.search(r"filename='([^']*)'?\s*", texto)
                    if match:
                        filename = match.group(1).strip()
                        texto = f'{pre_img}<img src="/static/{filename}'
            
            # Remove espaços extras nas URLs
            texto = re.sub(r'src="([^"]*)\s+([^"]*)"', r'src="\1\2"', texto)
            texto = re.sub(r"src='([^']*)\s+([^']*)'", r"src='\1\2'", texto)
            return texto

        # Formatar questões tratando as imagens
        questoes_formatadas = []
        for q in questoes:
            questoes_formatadas.append({
                'questao': tratar_imagens(q.questao),
                'alternativa_a': tratar_imagens(q.alternativa_a),
                'alternativa_b': tratar_imagens(q.alternativa_b),
                'alternativa_c': tratar_imagens(q.alternativa_c),
                'alternativa_d': tratar_imagens(q.alternativa_d),
                'alternativa_e': tratar_imagens(q.alternativa_e),
                'questao_correta': q.questao_correta
            })

        return render_template(
            'secretaria_educacao/visualizar_simulado.html',
            simulado={
                'id': simulado.SimuladosGerados.id,
                'status': simulado.SimuladosGerados.status,
                'data_envio': simulado.SimuladosGerados.data_envio.strftime('%d/%m/%Y %H:%M') if simulado.SimuladosGerados.data_envio else '',
                'disciplina_nome': simulado.disciplina_nome,
                'Ano_escolar_nome': simulado.Ano_escolar_nome,
                'mes_nome': simulado.mes_nome
            },
            questoes=questoes_formatadas
        )

    except Exception as e:
        print(f"Erro ao visualizar simulado: {str(e)}")
        flash(f"Erro ao visualizar simulado: {str(e)}", "danger")
        return redirect(url_for("secretaria_educacao.meus_simulados"))

@bp.route('/dados-grafico')
@login_required
def dados_grafico():
    disciplina = request.args.get('disciplina', '0')
    ano = request.args.get('ano', '0')
    tipo = request.args.get('tipo', 'desempenho')
    periodo = request.args.get('periodo', 'ano')
    mes = int(request.args.get('mes', datetime.now().month))

    # Dados base
    query = """
        SELECT 
            e.nome_da_escola,
            DATE(d.data_resposta) as data_resposta,
            AVG(CASE 
                WHEN :tipo = 'pontuacao' THEN d.pontuacao 
                ELSE d.desempenho
            END) as media
        FROM escolas e
        JOIN usuarios u ON u.escola_id = e.id
        JOIN desempenho_simulado d ON d.aluno_id = u.id
        JOIN simulados_gerados s ON d.simulado_id = s.id
        JOIN turmas t ON u.turma_id = t.id
        JOIN ano_escolar a ON u.ano_escolar_id = a.id
        WHERE u.tipo_usuario_id = 4
        AND d.data_resposta IS NOT NULL
        AND e.codigo_ibge = :codigo_ibge
    """
    params = {'tipo': tipo, 'codigo_ibge': current_user.codigo_ibge}

    # Adicionar filtros
    if disciplina != '0':
        query += " AND s.disciplina_id = :disciplina"
        params['disciplina'] = disciplina
    if ano != '0':
        query += " AND a.id = :ano"
        params['ano'] = ano
    if periodo == 'mes':
        query += " AND MONTH(d.data_resposta) = :mes"
        params['mes'] = mes

    # Agrupar por escola e data
    query += """
        GROUP BY e.nome_da_escola, DATE(d.data_resposta)
        ORDER BY e.nome_da_escola, data_resposta
    """
    
    try:
        result = db.session.execute(text(query), params)
        dados = result.fetchall()

        # Processar dados por escola
        escolas_dados = {}
        for row in dados:
            nome_escola = row[0]
            data = row[1]
            media = float(row[2])
            mes = data.month
            dia = data.day
            
            if nome_escola not in escolas_dados:
                escolas_dados[nome_escola] = []
            
            escolas_dados[nome_escola].append({
                'mes': mes,
                'dia': dia,
                'media': media
            })

        # Calcular média geral
        media_geral = []
        if periodo == 'ano':
            for mes in range(1, 13):
                medias_mes = [d['media'] for escola_data in escolas_dados.values() 
                            for d in escola_data if d['mes'] == mes]
                media = sum(medias_mes) / len(medias_mes) if medias_mes else 0
                media_geral.append({
                    'mes': mes,
                    'dia': 1,
                    'media': media
                })
        else:
            max_dia = calendar.monthrange(2024, mes)[1]
            for dia in range(1, max_dia + 1):
                medias_dia = [d['media'] for escola_data in escolas_dados.values() 
                            for d in escola_data if d['dia'] == dia and d['mes'] == mes]
                media = sum(medias_dia) / len(medias_dia) if medias_dia else 0
                media_geral.append({
                    'mes': mes,
                    'dia': dia,
                    'media': media
                })

        # Formatar resposta
        response_data = []

        # Adicionar média geral primeiro
        response_data.append({
            'name': 'Média Geral',
            'isMedia': True,
            'data': media_geral
        })

        # Adicionar dados das escolas
        for escola, dados in escolas_dados.items():
            response_data.append({
                'name': escola,
                'isMedia': False,
                'data': sorted(dados, key=lambda x: (x['mes'], x['dia']))
            })

        return jsonify(response_data)

    except Exception as e:
        print(f"Erro ao buscar dados do gráfico: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/buscar-escolas-grafico')
@login_required
def buscar_escolas_grafico():
    q = request.args.get('q', '').lower()
    escolas = db.session.query(Escolas.nome_da_escola).distinct().all()
    escolas = [e[0] for e in escolas if q in e[0].lower()]
    return jsonify(escolas)

@bp.route('/buscar-turmas-grafico')
@login_required
def buscar_turmas_grafico():
    try:
        escola = request.args.get('escola')
        ano_escolar = request.args.get('ano_escolar')

        if not escola:
            return jsonify({'error': 'Escola não especificada'})

        query = """
            SELECT DISTINCT t.turma
            FROM turmas t
            JOIN escolas e ON t.escola_id = e.id
            WHERE e.nome_da_escola = :escola
        """
        params = {'escola': escola}

        if ano_escolar != 'todos':
            query += " AND t.ano_escolar_id = :ano_escolar"
            params['ano_escolar'] = ano_escolar

        query += " ORDER BY t.turma"
        
        result = db.session.execute(text(query), params)
        turmas = [row[0] for row in result]
        
        return jsonify({'turmas': turmas})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/buscar-alunos-turma-grafico')
@login_required
def buscar_alunos_turma_grafico():
    try:
        escola = request.args.get('escola')
        turma = request.args.get('turma')

        if not escola or not turma:
            return jsonify([])
            
        alunos = db.session.query(
            Usuarios.id,
            Usuarios.nome
        ).join(
            Turmas, Usuarios.turma_id == Turmas.id
        ).join(
            Escolas, Usuarios.escola_id == Escolas.id
        ).filter(
            Escolas.nome_da_escola == escola,
            Turmas.turma == turma,
            Usuarios.tipo_usuario_id == 4
        ).order_by(
            Usuarios.nome
        ).all()

        return jsonify([{'id': a.id, 'nome': a.nome} for a in alunos])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/dados-grafico-alunos')
@login_required
def dados_grafico_alunos():
    tipo = request.args.get('tipo', 'pontuacao')
    periodo = request.args.get('periodo', 'ano')
    mes = int(request.args.get('mes', datetime.now().month))
    disciplina = request.args.get('disciplina', 'todos')
    ano = request.args.get('ano', 'todos')
    escola = request.args.get('escola')
    turma = request.args.get('turma')
    alunos = request.args.get('alunos', '')  # Pegar os IDs dos alunos da query string
    print(f"Recebendo requisição para dados_grafico_alunos com parâmetros: disciplina={disciplina}, ano={ano}, tipo={tipo}, periodo={periodo}, mes={mes}, escola={escola}, turma={turma}, alunos={alunos}")

    # Dados base
    query = """
        SELECT 
            u.nome as nome_aluno,
            e.nome_da_escola,
            a.nome as ano_escolar,
            t.turma,
            t.turno,
            DATE(d.data_resposta) as data_resposta,
            AVG(CASE 
                WHEN :tipo = 'pontuacao' THEN d.pontuacao 
                ELSE d.desempenho
            END) as media
        FROM usuarios u
        JOIN desempenho_simulado d ON d.aluno_id = u.id
        JOIN escolas e ON u.escola_id = e.id
        JOIN simulados_gerados s ON d.simulado_id = s.id
        JOIN turmas t ON u.turma_id = t.id
        JOIN ano_escolar a ON u.ano_escolar_id = a.id
        WHERE u.tipo_usuario_id = 4
        AND d.data_resposta IS NOT NULL
        AND e.codigo_ibge = :codigo_ibge
    """
    params = {
        'tipo': tipo,
        'codigo_ibge': current_user.codigo_ibge
    }

    # Adicionar filtro de alunos se especificado
    if alunos:
        alunos_ids = [int(id) for id in alunos.split(',') if id.isdigit()]
        if alunos_ids:
            query += " AND u.id IN :alunos_ids"
            params['alunos_ids'] = tuple(alunos_ids)

    # Adicionar outros filtros
    if disciplina != 'todos':
        query += " AND s.disciplina_id = :disciplina"
        params['disciplina'] = disciplina
    if ano != 'todos':
        query += " AND a.nome = :ano"
        params['ano'] = ano
    if escola:
        query += " AND e.nome_da_escola = :escola"
        params['escola'] = escola
    if turma:
        query += " AND t.turma = :turma"
        params['turma'] = turma
    if periodo == 'mes':
        query += " AND MONTH(d.data_resposta) = :mes"
        params['mes'] = mes

    # Agrupar
    query += """
        GROUP BY u.nome, e.nome_da_escola, a.nome, t.turma, t.turno,
        DATE(d.data_resposta)
        ORDER BY u.nome, data_resposta
    """

    try:
        result = db.session.execute(text(query), params)
        dados = result.fetchall()
        print(f"Dados recuperados do banco: {len(dados)} registros")
        print(f"Exemplo de registro: {dados[0] if dados else 'Nenhum dado'}")

        # Processar dados por aluno
        alunos_dados = {}
        alunos_info = {}  # Novo dicionário para armazenar informações do aluno
        for row in dados:
            nome_aluno = f"{row[0]} ({row[1]})"  # nome_aluno (escola)
            data = row[5]
            media = float(row[6])
            mes = data.month
            dia = data.day
            
            # Armazenar informações do aluno
            if nome_aluno not in alunos_info:
                alunos_info[nome_aluno] = {
                    'escola': row[1],
                    'ano_escolar': row[2],
                    'turma': row[3],
                    'turno': row[4]
                }
            
            if nome_aluno not in alunos_dados:
                alunos_dados[nome_aluno] = []
            
            alunos_dados[nome_aluno].append({
                'mes': mes,
                'dia': dia,
                'media': media
            })

        # Calcular média geral
        media_geral = []
        if periodo == 'ano':
            for mes in range(1, 13):
                medias_mes = [d['media'] for aluno_data in alunos_dados.values() 
                            for d in aluno_data if d['mes'] == mes]
                media = sum(medias_mes) / len(medias_mes) if medias_mes else 0
                media_geral.append({
                    'mes': mes,
                    'dia': 1,
                    'media': media
                })
        else:
            max_dia = calendar.monthrange(2024, mes)[1]
            for dia in range(1, max_dia + 1):
                medias_dia = [d['media'] for aluno_data in alunos_dados.values() 
                            for d in aluno_data if d['dia'] == dia and d['mes'] == mes]
                media = sum(medias_dia) / len(medias_dia) if medias_dia else 0
                media_geral.append({
                    'mes': mes,
                    'dia': dia,
                    'media': media
                })

        # Formatar resposta
        response_data = []

        # Adicionar média geral primeiro
        response_data.append({
            'name': 'Média Geral',
            'isMedia': True,
            'data': media_geral
        })

        # Adicionar dados dos alunos (limitado a 10)
        for aluno, dados in list(alunos_dados.items())[:10]:
            info = alunos_info[aluno]  # Pegar informações armazenadas do aluno
            response_data.append({
                'name': aluno,
                'isMedia': False,
                'escola': info['escola'],
                'ano_escolar': info['ano_escolar'],
                'turma': info['turma'],
                'turno': info['turno'],
                'data': sorted(dados, key=lambda x: (x['mes'], x['dia']))
            })

        print(f"Dados formatados para resposta: {len(response_data)} alunos")
        return jsonify(response_data)

    except Exception as e:
        print(f"Erro ao buscar dados do gráfico: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/buscar-escolas-ranking')
@login_required
def buscar_escolas_ranking():
    """Retorna lista de escolas para autocomplete."""
    try:
        print(f"[DEBUG] Usuário tipo: {current_user.tipo_usuario_id}")
        if current_user.tipo_usuario_id not in [5, 6]:
            print("[DEBUG] Usuário não autorizado")
            return jsonify([])
            
        termo = request.args.get('termo', '')
        print(f"[DEBUG] Buscando escolas. Termo: '{termo}', IBGE: {current_user.codigo_ibge}")
        
        escolas = db.session.query(
            Escolas.nome_da_escola
        ).filter(
            Escolas.codigo_ibge == current_user.codigo_ibge,
            Escolas.nome_da_escola.like(f'%{termo}%')
        ).order_by(
            Escolas.nome_da_escola
        ).all()
        
        resultado = [escola[0] for escola in escolas]
        print(f"[DEBUG] Escolas encontradas: {len(resultado)}")
        print(f"[DEBUG] Escolas: {resultado}")
        return jsonify(resultado)
    
    except Exception as e:
        print(f"[DEBUG] Erro ao buscar escolas: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/buscar-turmas-ranking')
@login_required
def buscar_turmas_ranking():
    """Retorna turmas de uma escola e ano escolar específicos."""
    try:
        print(f"[DEBUG] Usuário tipo: {current_user.tipo_usuario_id}")
        if current_user.tipo_usuario_id not in [5, 6]:
            print("[DEBUG] Usuário não autorizado")
            return jsonify([])
            
        escola = request.args.get('escola')
        ano_escolar = request.args.get('ano')
        
        if not escola or not ano_escolar:
            return jsonify([])
        
        # Buscar todas as turmas da escola e ano escolar, independente de terem desempenho
        turmas = db.session.query(
            distinct(Turmas.turma)
        ).join(
            Usuarios, Usuarios.turma_id == Turmas.id
        ).join(
            Escolas, Escolas.id == Usuarios.escola_id
        ).join(
            Ano_escolar, Ano_escolar.id == Usuarios.ano_escolar_id
        ).filter(
            Escolas.nome_da_escola == escola,
            Ano_escolar.nome == ano_escolar
        ).order_by(
            Turmas.turma
        ).all()

        return jsonify([turma[0] for turma in turmas])
    
    except Exception as e:
        print(f"[DEBUG] Erro ao buscar turmas: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/buscar-escolas-grafico-alunos')
@login_required
def buscar_escolas_grafico_alunos():
    termo = request.args.get('term', '')
    
    try:
        query = """
            SELECT DISTINCT e.nome_da_escola
            FROM escolas e
            JOIN usuarios u ON u.escola_id = e.id
            WHERE u.tipo_usuario_id = 4
            AND e.nome_da_escola LIKE :termo
            ORDER BY e.nome_da_escola
            LIMIT 10
        """
        
        result = db.session.execute(text(query), {'termo': f'%{termo}%'})
        escolas = [row[0] for row in result]
        
        return jsonify(escolas)
    except Exception as e:
        print(f"Erro ao buscar escolas: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/buscar-anos-escolares-grafico')
@login_required
def buscar_anos_escolares_grafico():
    """Retorna lista de anos escolares disponíveis."""
    try:
        query = """
            SELECT DISTINCT ae.nome
            FROM ano_escolar ae
            JOIN usuarios u ON u.ano_escolar_id = ae.id
            WHERE u.tipo_usuario_id = 4
            AND u.codigo_ibge = :codigo_ibge
            ORDER BY ae.nome
        """
        
        result = db.session.execute(text(query), {'codigo_ibge': current_user.codigo_ibge})
        anos = [row[0] for row in result]
        
        return jsonify(anos)
    except Exception as e:
        print(f"Erro ao buscar anos escolares: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/buscar-alunos-ranking')
@login_required
def buscar_alunos_ranking():
    """Retorna alunos filtrados por município, escola, ano e turma."""
    try:
        print("[DEBUG] Iniciando busca de alunos")
        if current_user.tipo_usuario_id not in [5, 6]:
            print("[DEBUG] Usuário não autorizado")
            return jsonify([])
            
        termo = request.args.get('term', '')
        ano_escolar = request.args.get('ano')
        escola = request.args.get('escola')
        turma = request.args.get('turma')
        
        print(f"[DEBUG] Parâmetros: termo='{termo}', ano='{ano_escolar}', escola='{escola}', turma='{turma}'")
        
        # Query base
        query = db.session.query(
            Usuarios.nome.label('nome'),
            Usuarios.id.label('id')
        ).filter(
            Usuarios.tipo_usuario_id == 4  # Alunos
        )
        
        # Filtro de município
        if current_user.codigo_ibge:
            print(f"[DEBUG] Filtrando por município: {current_user.codigo_ibge}")
            query = query.join(
                Escolas, 
                Escolas.id == Usuarios.escola_id
            ).filter(
                Escolas.codigo_ibge == current_user.codigo_ibge
            )
        
        # Join em ano escolar se necessário
        if ano_escolar and ano_escolar != 'todos':
            print(f"[DEBUG] Filtrando por ano: {ano_escolar}")
            query = query.join(
                Ano_escolar,
                Ano_escolar.id == Usuarios.ano_escolar_id
            ).filter(Ano_escolar.nome == ano_escolar)
            
        # Filtro por escola
        if escola:
            print(f"[DEBUG] Filtrando por escola: {escola}")            
            query = query.filter(Escolas.nome_da_escola == escola)
            
        # Join em turmas se necessário
        if turma:
            print(f"[DEBUG] Filtrando por turma: {turma}")
            query = query.join(
                Turmas,
                Turmas.id == Usuarios.turma_id
            ).filter(
                Turmas.turma == turma
            )
            
        # Filtro por nome do aluno
        if termo:
            print(f"[DEBUG] Filtrando por termo: {termo}")
            query = query.filter(Usuarios.nome.ilike(f'%{termo}%'))
            
        # Debug da query
        print("[DEBUG] SQL Query:")
        print(str(query.statement.compile(compile_kwargs={'literal_binds': True})))
        
        # Executar query
        alunos = query.order_by(Usuarios.nome).limit(10).all()
        
        print(f"[DEBUG] Encontrados {len(alunos)} alunos")
        for aluno in alunos:
            print(f"[DEBUG] - {aluno.nome} (ID: {aluno.id})")
        
        return jsonify([{
            'id': aluno.id,
            'label': aluno.nome,
            'value': aluno.nome
        } for aluno in alunos])
        
    except Exception as e:
        print(f"[DEBUG] Erro ao buscar alunos: {str(e)}")
        print(f"[DEBUG] Tipo do erro: {type(e)}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@bp.route('/temas_redacao')
@login_required
def temas_redacao():
    """Lista os temas de redação"""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash('Acesso não autorizado', 'danger')
        return redirect(url_for('index'))
        
    temas = TemasRedacao.query.filter_by(
        codigo_ibge=current_user.codigo_ibge
    ).order_by(TemasRedacao.data_envio.desc()).all()
    
    return render_template(
        'secretaria_educacao/temas_redacao.html',
        temas=temas
    )

@bp.route('/novo_tema_redacao', methods=['GET', 'POST'])
@login_required
def novo_tema_redacao():
    """Cria um novo tema de redação"""
    if current_user.tipo_usuario_id not in [5, 6]:
        flash('Acesso não autorizado', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        tema = TemasRedacao(
            titulo=request.form['titulo'],
            descricao=request.form['descricao'],
            tipo=request.form['tipo'],
            data_limite=datetime.strptime(request.form['data_limite'], '%Y-%m-%d') if request.form['data_limite'] else None,
            codigo_ibge=current_user.codigo_ibge,
            ano_escolar_id=request.form['ano_escolar_id']
        )
        
        db.session.add(tema)
        db.session.commit()
        
        flash('Tema de redação criado com sucesso!', 'success')
        return redirect(url_for('secretaria_educacao.temas_redacao'))
        
    anos_escolares = Ano_escolar.query.all()
    return render_template(
        'secretaria_educacao/novo_tema_redacao.html',
        anos_escolares=anos_escolares
    )

@bp.route('/gerenciar-temas-redacao')
@login_required
def gerenciar_temas_redacao():
    """Página para gerenciar temas de redação"""
    if current_user.tipo_usuario_id != 5:  # Secretaria de Educação
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('index'))
        
    temas = TemasRedacao.query.all()
    return render_template('secretaria_educacao/gerenciar_temas_redacao.html', temas=temas)

@bp.route('/excluir-tema-redacao/<int:tema_id>', methods=['DELETE'])
@login_required
def excluir_tema_redacao(tema_id):
    """Exclui um tema de redação"""
    if current_user.tipo_usuario_id != 5:  # Secretaria de Educação
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
        
    tema = TemasRedacao.query.get_or_404(tema_id)
    
    try:
        db.session.delete(tema)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/editar-tema-redacao/<int:tema_id>', methods=['GET', 'POST'])
@login_required
def editar_tema_redacao(tema_id):
    """Edita um tema de redação existente"""
    if current_user.tipo_usuario_id != 5:  # Secretaria de Educação
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('index'))
        
    tema = TemasRedacao.query.get_or_404(tema_id)
    
    if request.method == 'POST':
        try:
            tema.titulo = request.form['titulo']
            tema.descricao = request.form['descricao']
            tema.tipo = request.form['tipo']
            tema.data_limite = datetime.strptime(request.form['data_limite'], '%Y-%m-%d') if request.form['data_limite'] else None
            tema.ano_escolar_id = request.form['ano_escolar_id']
            
            db.session.commit()
            flash('Tema de redação atualizado com sucesso!', 'success')
            return redirect(url_for('secretaria_educacao.gerenciar_temas_redacao'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar tema de redação: {str(e)}', 'danger')
            return redirect(url_for('secretaria_educacao.editar_tema_redacao', tema_id=tema_id))
    
    anos_escolares = Ano_escolar.query.all()
    return render_template(
        'secretaria_educacao/editar_tema_redacao.html',
        tema=tema,
        anos_escolares=anos_escolares
    )

@bp.route('/alternar-status-tema-redacao/<int:tema_id>', methods=['POST'])
@login_required
def alternar_status_tema_redacao(tema_id):
    """Alterna o status de um tema de redação entre ativo e inativo"""
    if current_user.tipo_usuario_id != 5:  # Secretaria de Educação
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
        
    tema = TemasRedacao.query.get_or_404(tema_id)
    
    try:
        tema.ativo = not tema.ativo
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/ranking_redacoes')
@login_required
def ranking_redacoes():
    """Retorna o ranking de redações por aluno e escola"""
    try:
        tipo = request.args.get('tipo', 'alunos')
        periodo = request.args.get('periodo', 'total')
        ano_escolar_id = request.args.get('ano_escolar_id')
        
        print(f"[DEBUG] Parâmetros recebidos: tipo={tipo}, periodo={periodo}, ano_escolar_id={ano_escolar_id}")
        
        # Sempre usa o código IBGE do usuário atual
        codigo_ibge = current_user.codigo_ibge
        print(f"[DEBUG] Código IBGE: {codigo_ibge}")

        # Busca anos escolares
        anos_escolares = db.session.query(
            Ano_escolar.nome
        ).join(
            Usuarios, Usuarios.ano_escolar_id == Ano_escolar.id
        ).filter(
            Usuarios.tipo_usuario_id == 4  # Tipo aluno
        ).distinct().order_by(
            Ano_escolar.nome
        ).all()
        anos_escolares = [ano[0] for ano in anos_escolares]  # Converte de tupla para lista

        # Busca escolas do mesmo código IBGE
        escolas = db.session.query(
            Escolas.nome_da_escola
        ).filter(
            Escolas.codigo_ibge == current_user.codigo_ibge
        ).order_by(
            Escolas.nome_da_escola
        ).all()
        escolas = [escola[0] for escola in escolas]  # Converte de tupla para lista

        # Query base
        if tipo == 'alunos':
            print("[DEBUG] Construindo query para ranking de alunos")
            query = db.session.query(
                RedacoesAlunos.aluno_id,
                Usuarios.nome.label('aluno'),
                Escolas.nome_da_escola.label('escola'),
                Ano_escolar.nome.label('ano_escolar'),
                func.avg(RedacoesAlunos.comp1).label('comp1'),
                func.avg(RedacoesAlunos.comp2).label('comp2'),
                func.avg(RedacoesAlunos.comp3).label('comp3'),
                func.avg(RedacoesAlunos.comp4).label('comp4'),
                func.avg(RedacoesAlunos.comp5).label('comp5'),
                func.count(RedacoesAlunos.id).label('total_redacoes')
            ).join(Usuarios, RedacoesAlunos.aluno_id == Usuarios.id)\
             .join(Escolas, Usuarios.escola_id == Escolas.id)\
             .join(Ano_escolar, Usuarios.ano_escolar_id == Ano_escolar.id)\
             .filter(RedacoesAlunos.comp1.isnot(None))\
             .filter(Usuarios.tipo_usuario_id == TIPO_USUARIO_ALUNO)  # Apenas alunos
        else:
            print("[DEBUG] Construindo query para ranking de escolas")
            query = db.session.query(
                Escolas.id,
                literal('-').label('aluno'),
                Escolas.nome_da_escola.label('escola'),
                literal('-').label('ano_escolar'),
                func.avg(RedacoesAlunos.comp1).label('comp1'),
                func.avg(RedacoesAlunos.comp2).label('comp2'),
                func.avg(RedacoesAlunos.comp3).label('comp3'),
                func.avg(RedacoesAlunos.comp4).label('comp4'),
                func.avg(RedacoesAlunos.comp5).label('comp5'),
                func.count(RedacoesAlunos.id).label('total_redacoes')
            ).join(Usuarios, RedacoesAlunos.aluno_id == Usuarios.id)\
             .join(Escolas, Usuarios.escola_id == Escolas.id)\
             .filter(RedacoesAlunos.comp1.isnot(None))\
             .filter(Usuarios.tipo_usuario_id == TIPO_USUARIO_ALUNO)  # Apenas alunos

        # Filtros
        query = query.filter(Escolas.codigo_ibge == codigo_ibge)
        print(f"[DEBUG] Filtro por código IBGE aplicado: {codigo_ibge}")

        if ano_escolar_id:
            query = query.filter(Usuarios.ano_escolar_id == ano_escolar_id)
            print(f"[DEBUG] Filtro por ano escolar aplicado: {ano_escolar_id}")

        if periodo == 'mes':
            hoje = datetime.now()
            primeiro_dia = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(RedacoesAlunos.data_envio >= primeiro_dia)
            print(f"[DEBUG] Filtro por período aplicado: {primeiro_dia}")
        elif periodo.isdigit():  # Se for um ID de mês específico
            mes_id = int(periodo)
            query = query.filter(extract('month', RedacoesAlunos.data_envio) == mes_id)
            print(f"[DEBUG] Filtro por mês específico: {mes_id}")

        # Agrupamento
        if tipo == 'alunos':
            query = query.group_by(
                RedacoesAlunos.aluno_id, 
                Usuarios.nome, 
                Escolas.nome_da_escola,
                Ano_escolar.nome
            )
        else:
            query = query.group_by(Escolas.id, Escolas.nome_da_escola)

        # Ordenação
        query = query.order_by(desc(
            (func.avg(RedacoesAlunos.comp1) + 
             func.avg(RedacoesAlunos.comp2) + 
             func.avg(RedacoesAlunos.comp3) + 
             func.avg(RedacoesAlunos.comp4) + 
             func.avg(RedacoesAlunos.comp5)) / 5
        ))

        # Print da query SQL gerada
        print("[DEBUG] Query SQL gerada:")
        print(str(query.statement.compile(compile_kwargs={"literal_binds": True})))

        resultados = query.all()
        print(f"[DEBUG] Total de resultados encontrados: {len(resultados)}")
        
        # Busca meses disponíveis
        meses = MESES.query.order_by(MESES.id).all()
        
        ranking = []
        for r in resultados:
            media_geral = (r.comp1 + r.comp2 + r.comp3 + r.comp4 + r.comp5) / 5 if None not in (r.comp1, r.comp2, r.comp3, r.comp4, r.comp5) else 0
            ranking.append({
                'aluno_id': r.aluno_id,  # Campo específico para o ID do aluno
                'aluno': r.aluno,
                'escola': r.escola,
                'ano_escolar': r.ano_escolar,
                'media_geral': round(media_geral, 1),
                'competencias': {
                    'comp1': round(r.comp1, 1) if r.comp1 else 0,
                    'comp2': round(r.comp2, 1) if r.comp2 else 0,
                    'comp3': round(r.comp3, 1) if r.comp3 else 0,
                    'comp4': round(r.comp4, 1) if r.comp4 else 0,
                    'comp5': round(r.comp5, 1) if r.comp5 else 0
                },
                'total_redacoes': r.total_redacoes
            })
        
        print(f"[DEBUG] Total de itens no ranking após filtro de média > 0: {len(ranking)}")

        return jsonify({
            'success': True,
            'ranking': ranking,
            'anos_escolares': anos_escolares,
            'escolas': escolas,
            'meses': [{'id': mes.id, 'nome': mes.nome} for mes in meses]
        })

    except Exception as e:
        import traceback
        print(f"[DEBUG] Erro no ranking de redações:")
        print(f"[DEBUG] Tipo do erro: {type(e)}")
        print(f"[DEBUG] Erro: {str(e)}")
        print(f"[DEBUG] Stack trace:")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/pagina_ranking_redacoes')
@login_required
def pagina_ranking_redacoes():
    """Página que mostra o ranking de redações"""
    if current_user.tipo_usuario_id not in [TIPO_USUARIO_SECRETARIA_EDUCACAO, TIPO_USUARIO_ADMIN]:
        return redirect(url_for('index'))
    return render_template('secretaria_educacao/ranking_redacoes.html')

@bp.route('/redacoes_aluno/<int:aluno_id>')
@login_required
def redacoes_aluno(aluno_id):
    """Página que mostra as redações de um aluno específico"""
    if current_user.tipo_usuario_id not in [5, 6]:  # Secretaria (5) e Admin (6)
        return redirect(url_for('index'))
        
    try:
        print(f"[DEBUG] Buscando redações do aluno {aluno_id}")
        
        # Busca informações do aluno
        aluno = db.session.query(
            Usuarios.nome,
            Escolas.nome_da_escola.label('escola'),
            Ano_escolar.nome.label('ano_escolar')
        ).join(
            Escolas, Usuarios.escola_id == Escolas.id
        ).join(
            Ano_escolar, Usuarios.ano_escolar_id == Ano_escolar.id
        ).filter(
            Usuarios.id == aluno_id,
            Usuarios.tipo_usuario_id == 4  # Tipo aluno
        ).first()

        print(f"[DEBUG] Informações do aluno: {aluno}")

        if not aluno:
            print(f"[DEBUG] Aluno {aluno_id} não encontrado")
            flash('Aluno não encontrado.', 'danger')
            return redirect(url_for('secretaria_educacao.pagina_ranking_redacoes'))

        # Busca redações do aluno
        redacoes_query = db.session.query(
            RedacoesAlunos,
            TemasRedacao.titulo.label('tema')
        ).join(
            TemasRedacao, TemasRedacao.id == RedacoesAlunos.tema_id
        ).filter(
            RedacoesAlunos.aluno_id == aluno_id,
            RedacoesAlunos.comp1.isnot(None)  # Apenas redações corrigidas
        ).order_by(
            RedacoesAlunos.data_envio.desc()
        )

        print(f"[DEBUG] Query redações: {str(redacoes_query)}")
        redacoes = redacoes_query.all()
        print(f"[DEBUG] Total de redações encontradas: {len(redacoes)}")

        # Formata as redações
        redacoes_formatadas = []
        for r in redacoes:
            media = (r.RedacoesAlunos.comp1 + r.RedacoesAlunos.comp2 + r.RedacoesAlunos.comp3 + 
                    r.RedacoesAlunos.comp4 + r.RedacoesAlunos.comp5) / 5
            redacoes_formatadas.append({
                'id': r.RedacoesAlunos.id,
                'tema': r.tema,
                'data_envio': r.RedacoesAlunos.data_envio.strftime('%d/%m/%Y'),
                'media': round(media, 1),
                'competencias': {
                    'comp1': r.RedacoesAlunos.comp1,
                    'comp2': r.RedacoesAlunos.comp2,
                    'comp3': r.RedacoesAlunos.comp3,
                    'comp4': r.RedacoesAlunos.comp4,
                    'comp5': r.RedacoesAlunos.comp5
                },
                'texto': r.RedacoesAlunos.texto,
                'feedback': {
                    'estrutura': r.RedacoesAlunos.analise_estrutura,
                    'argumentos': r.RedacoesAlunos.analise_argumentos,
                    'gramatical': r.RedacoesAlunos.analise_gramatical,
                    'sugestoes': r.RedacoesAlunos.sugestoes_melhoria
                }
            })

        print(f"[DEBUG] Redações formatadas: {len(redacoes_formatadas)}")
        return render_template(
            'secretaria_educacao/redacoes_aluno.html',
            aluno=aluno,
            redacoes=redacoes_formatadas
        )

    except Exception as e:
        print("[DEBUG] Erro ao buscar redações do aluno:")
        print(f"[DEBUG] Tipo do erro: {type(e)}")
        print(f"[DEBUG] Erro: {str(e)}")
        print("[DEBUG] Stack trace:")
        import traceback
        traceback.print_exc()
        flash('Erro ao buscar redações do aluno.', 'danger')
        return redirect(url_for('secretaria_educacao.pagina_ranking_redacoes'))
